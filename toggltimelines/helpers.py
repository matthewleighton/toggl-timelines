from flask import current_app

from sqlalchemy import func
from datetime import datetime, timedelta
import pytz
import csv
import sys
import copy
import pprint
import math
pp = pprint.PrettyPrinter(indent=4)

from toggltimelines.timelines.models import Entry
from toggltimelines.timelines.models import Project
from toggltimelines.timelines.models import Client
from toggltimelines.timelines.models import Tag
from toggltimelines import db


def toggl_sync(start_date=False, end_date=False, days=False):	
	if days is not False:
		start_date = datetime.utcnow().replace(hour=0, minute=0, second=0) - timedelta(days=days)
		start_date = start_date.replace(tzinfo=pytz.utc)

	if not end_date:
		end_date = datetime.utcnow().replace(tzinfo=pytz.utc)

	# The Toggl API seems to return all entries on any day that is queried.
	# So for our database requests to match with this, we set the times to the start/end of the start/end days.
	# Also, Toggl understands all our requests as being in the user's timezone.
	timezone = get_current_timezone()
	start_date = start_date.replace(hour=0, minute=0, second=0).astimezone(tz=timezone)
	end_date = end_date.replace(hour=23, minute=59, second=59).astimezone(tz=timezone)


	entries = get_entries_from_toggl(start_date, end_date)


	#Only get the current entry if we're getting today's entries.
	if start_date <= datetime.now().replace(tzinfo=timezone) <= end_date:
		current_entry = get_current_toggl_entry()
		if current_entry:
			entries.append(current_entry)

	entries = split_entries_over_midnight(entries)

	# local_projects = get_all_projects_from_database()

	# Remove database entries which already exist in the sync window.
	existing_db_entries = get_db_entries(start_date, end_date)
	for db_entry in existing_db_entries:
		db.session.delete(db_entry)

	db.session.commit() # This is here because of issues when an entry was deleted and re-added during resync. 
						# Project wasn't correctly updating if changed to NULL.

	for entry in entries:
		project_id = entry['pid'] if 'pid' in entry.keys() else None
		db_project = get_or_create_project(project_id)

		db_tags = get_or_create_tags(entry['tags'])

		start_datetime = timestamp_to_datetime(entry['start'])
		end_datetime = timestamp_to_datetime(entry['end'])

		location = get_entry_location(start_datetime)

		description = entry['description'] if 'description' in entry.keys() else ''

		db_entry = create_entry({
			'id': 		   entry['id'],
			'description': description,
			'start': 	   start_datetime,
			'end': 		   end_datetime,
			'dur': 		   entry['dur'],
			'location':	   location,
			'user_id': 	   entry['uid'],
			'db_project':  db_project,
			'tags':		   db_tags
		})

	check_project_client_integrity()

	db.session.commit()

	return entries

# Make sure that the database projects are assigned to the same clients as in Toggl.
# (Also check database projects colors against Toggl).
def check_project_client_integrity():
	user_toggl_data = get_user_toggl_data()
	toggl_projects = user_toggl_data['projects']
	toggl_clients = user_toggl_data['clients']

	db_projects = Project.query.all()

	for db_project in db_projects:
		project_id = db_project.id
		toggl_project = get_toggl_project(project_id)

		toggl_client_id = toggl_project['cid'] if 'cid' in toggl_project.keys() else None
		db_client_id = db_project.client_id

		if toggl_client_id != db_client_id:
			
			if toggl_client_id:
				db_client = get_or_create_client(toggl_client_id)
			
			db_project.client_id = toggl_client_id

		toggl_project_color = toggl_project['hex_color']
		db_project_color = db_project.project_hex_color

		if toggl_project_color != db_project_color:
			db_project.project_hex_color = toggl_project_color



def get_toggl_project(project_id):
	toggl_project_list = get_user_toggl_data()['projects']

	toggl_project = next((project for project in toggl_project_list if project['id'] == project_id), None)

	return toggl_project

def get_toggl_client(client_id):
	toggl_client_list = get_user_toggl_data()['clients']

	toggl_client = next((client for client in toggl_client_list if client['id'] == client_id), None)

	return toggl_client


# Get a project from the datbase if it exists, or create it otherwise.
def get_or_create_project(project_id):
	if not project_id:
		return None

	db_project = Project.query.get(project_id)

	if db_project:
		return db_project

	toggl_project = get_toggl_project(project_id)	

	if not toggl_project:
		return False

	client_id = toggl_project['cid'] if 'cid' in toggl_project.keys() else None

	db_project = create_project({
				'project_id': 		 project_id,
				'project_name': 	 toggl_project['name'],
				'project_hex_color': toggl_project['hex_color'],
				'client_id':		 client_id
			})

	if client_id:
		get_or_create_client(client_id)

	return db_project

# Given a list of tag names, return the database versions, creating them if they don't exist.
def get_or_create_tags(toggl_tags):
	db_tags = []

	for tag_name in toggl_tags:
		db_tag = Tag.query.filter(Tag.tag_name == tag_name).first()

		if db_tag:
			db_tags.append(db_tag)
			continue

		db_tag = Tag(
			# id 		 = t['project_id'],
			tag_name = tag_name,
		)

		db.session.add(db_tag)

		db_tags.append(db_tag)

	return db_tags

def get_or_create_client(client_id):
	db_client = Client.query.get(client_id)

	if db_client:
		return db_client

	toggl_client = get_toggl_client(client_id)

	if not toggl_client:
		return False

	db_client = create_client({
			'client_id': client_id,
			'client_name': toggl_client['name']
		})

	return db_client



# If an entry received from Toggl spans midnight, we split it into two.
def split_entries_over_midnight(entries):
	current_timezone = get_current_timezone()
	
	for entry in entries:
		start = entry['start']
		end = entry['end']

		start = timestamp_to_datetime(start, utc=False)
		end = timestamp_to_datetime(end, utc=False)

		entry_location = get_entry_location(start)
		entry_timezone = pytz.timezone(entry_location)

		start = start.astimezone(tz=entry_timezone)
		end = end.astimezone(tz=entry_timezone)

		if start.day != end.day:
			end_of_first_day = start.replace(hour=23, minute=59, second=59)
			start_of_next_day = end_of_first_day + timedelta(seconds=1)

			start1 = entry['start']
			end1 = end_of_first_day.isoformat()

			start2 = start_of_next_day.isoformat()
			end2 = entry['end']

			dur1 = (end_of_first_day - start).total_seconds() * 1000
			dur2 = (end - start_of_next_day).total_seconds() * 1000

			entry_before_midnight = entry
			entry_after_midnight = copy.deepcopy(entry)

			entry_before_midnight['start'] = start1
			entry_before_midnight['end'] = end1
			entry_before_midnight['dur'] = dur1

			entry_after_midnight['start'] = start2
			entry_after_midnight['end'] = end2
			entry_after_midnight['dur'] = dur2

			# TODO: Is this a goodway of handling the ID?
			# Just adding a 0 onto the end of the new entry.
			entry_after_midnight['id'] = str(entry['id']) + '0'

			entries.append(entry_after_midnight)

	return entries

def get_entry_location(entry_datetime):
	with open('location_history.csv', 'r') as file:
		reader = csv.DictReader(file)

		timestamp_format = '%Y-%m-%dT%H:%M'

		location = current_app.config['DEFAULT_LOCATION']

		for row in reader:
			location_start_datetime = datetime.strptime(row['start'], timestamp_format).astimezone(tz=pytz.utc)
			location_end_datetime = datetime.strptime(row['end'], timestamp_format).astimezone(tz=pytz.utc)

			if location_start_datetime <= entry_datetime <= location_end_datetime:
				location = row['location']

	return location

def get_db_entries(start=False, end=False, projects=False, clients=False, description=False, tags=False, tags_mode='OR'):
	query = Entry.query

	if start:
		start = start.astimezone(pytz.utc).replace(microsecond=0)
		query = query.filter(Entry.start >= start)

	if end:
		end = end.astimezone(pytz.utc).replace(microsecond=0)
		query = query.filter(Entry.start <= end)

	if projects:
		query = query.join(Entry.project, aliased=True)
		query = query.filter(Project.project_name.in_(projects))

	if clients:
		query = query.filter(Entry.client.in_(clients))

	if description:

		if (isinstance(description, str)):
			query = query.filter(func.lower(Entry.description).contains(description.lower()))
		else:
			query = query.filter(func.lower(Entry.description).in_([x.lower() for x in description]))

	if tags:

		if tags_mode.upper() == 'OR':
			query = query.filter(Entry.tags.any(Tag.id.in_(tags)))
		else:
			for tag in tags:
				query = query.filter(Entry.tags.any(Tag.id == tag))

	entries = query.order_by(Entry.start).all()

	# Entries are timezone naive when we retreive them.
	# Need to make them aware that they are in UTC.
	for entry in entries:
		entry.tzinfo_to_utc()

	return entries

# Return the entries in a new list, grouped by day,
def sort_db_entries_by_day(db_entries, return_as_dict=False):
	sorted_by_day = {}
	for entry in db_entries:

		#entry.start = entry.start.replace(tzinfo=pytz.utc)
		# Below we use get_local_start_time() because we need to make sure we're sorting
		# with reference to what day it was in the user's location. Not simply UTC.
		entry_date_label = entry.get_local_start_time().strftime('%Y-%m-%d')

		if entry_date_label not in sorted_by_day:
			date = entry.get_local_start_time()
			toggl_date_url = get_toggl_date_url(date)

			sorted_by_day[entry_date_label] = {
				'entries': [],
				'date': date.strftime('%a %d %b, %Y'),
				'toggl_date_url': toggl_date_url
			}

		sorted_by_day[entry_date_label]['entries'].append(entry)

	if return_as_dict:
		return sorted_by_day

	days_list = []
	for day in sorted_by_day.values():
		days_list.append(day)

	days_list.reverse()

	return days_list

def get_toggl_date_url(date):
	workspace_id = current_app.config['WORKSPACE_ID']
	date_string = date.strftime('%Y-%m-%d')

	url = f'https://track.toggl.com/reports/summary/{workspace_id}/from/{date_string}/to/{date_string}'

	return url

# Save a new entry to the database
def create_entry(entry_data):
	# This is here to catch an edge case of when an old version of an entry still exists.
	# (The old one is usually already deleted, by can remain if the edge of the sync window has an entry overflowing midnight)#
	# Could maybe find a better way of doing this? How much extra time does it take to check each entry like this?
	old_entry = Entry.query.get(entry_data['id'])
	if old_entry:
		db.session.delete(old_entry)
		db.session.commit()

	db_entry = Entry(
		id 				  = entry_data['id'],
		description 	  = entry_data['description'],
		start 			  = entry_data['start'],
		end 			  = entry_data['end'],
		dur 			  = entry_data['dur'],
		#client 			  = entry_data['client'],
		location 		  = entry_data['location'],
		user_id 		  = entry_data['user_id'],
		tags 			  = entry_data['tags']
	)

	if entry_data['db_project']:
		db_entry.project = entry_data['db_project']

	db.session.add(db_entry)
	#db.session.commit()

	return db_entry

# Save a new project to the database
def create_project(project_data):
	db_project = Project(
		id 				  = project_data['project_id'],
		project_name 	  = project_data['project_name'],
		project_hex_color = project_data['project_hex_color']
	)

	db.session.add(db_project)

	return db_project

def create_client(client_data):
	db_client = Client(
			id = client_data['client_id'],
			client_name = client_data['client_name']
		)

	db.session.add(db_client)

	return db_client

# Given a project ID, return the project object from the database.
# Can provide a project list, to avoid unneeded database queries.
def get_database_project_by_id(project_id, project_list = None):
	if not project_list:
		project_list = get_all_projects_from_database()
		#TODO: Instead of getting the whole list here, this should just be a query for the particular project.

	db_project = False

	for project in project_list:
		if project.id == project_id:
			db_project = project
			break

	return db_project

# Get entries between two dates from the Toggl API.
# Will NOT include an entry which is currently being tracked.
def get_entries_from_toggl(start_date, end_date):
	request_data = {
		'workspace_id': current_app.config['WORKSPACE_ID'],
		'since': start_date,
		'until': end_date
	}

	entries = current_app.toggl.getDetailedReportPages(request_data)['data']

	return entries

# Note: current entries are returned from Toggl in UTC,
# while past entries are returned in the user's assigned timezone.
def get_current_toggl_entry():
	current_entry = current_app.toggl.currentRunningTimeEntry()

	if not current_entry:
		return False

	start_datetime = timestamp_to_datetime(current_entry['start'])

	utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)

	time_since_entry_start = utc_now - start_datetime

	end_datetime = start_datetime + timedelta(seconds = time_since_entry_start.seconds)

	current_entry['dur'] = time_since_entry_start.seconds * 1000 # Duration is in milliseconds
	current_entry['end'] = datetime_to_timestamp(end_datetime)

	if 'tags' not in current_entry.keys():
		current_entry['tags'] = []

	return current_entry

# Return a dictionary of all the user data. (Projects, clients, etc)
# Store it as an app variable, so we only make the API request once.
def get_user_toggl_data():
	if not current_app.user_toggl_data:
		request_url = "https://www.toggl.com/api/v8/me?with_related_data=true"
		current_app.user_toggl_data = current_app.toggl.request(request_url)['data']

	return current_app.user_toggl_data

def get_all_projects_from_database():
	projects = Project.query.all()

	return projects

# Convert a timestamp string to a datetime object.
def timestamp_to_datetime(timestamp, string_format='%Y-%m-%dT%H:%M:%S%z', utc=True):
	timestamp = remove_colon_from_timezone(timestamp)
	
	dt = datetime.strptime(timestamp, string_format)

	if utc:
		test = pytz.timezone('UTC')
		dt=dt.astimezone(tz=test)

	return dt

def datetime_to_timestamp(dt, string_format='%Y-%m-%dT%H:%M:%S%z'):
	return remove_colon_from_timezone(datetime.strftime(dt, string_format))

# The datetime strings we receive from toggl have a colon in the timezone. We need to remove this.
def remove_colon_from_timezone(timestamp):
	if timestamp[-3] == ':':
		return timestamp[:-3] + timestamp[-2:]
	else:
		return timestamp

def get_current_timezone():
	now = datetime.utcnow().replace(tzinfo=pytz.utc)

	location = get_entry_location(now)

	timezone = pytz.timezone(location)

	return timezone

def get_user_timezone_at_date(dt):
	dt = dt.replace(tzinfo=pytz.utc)
	location = get_entry_location(dt)
	timezone = pytz.timezone(location)

	return timezone





# Return a datetime for the current time in the user's current timezone.
def get_current_datetime_in_user_timezone():
	with open ('location_history.csv', 'r') as file:
		reader = csv.DictReader(file)
		location = next(reader)['location']

	timezone = pytz.timezone(location)

	user_time = datetime.now(timezone)

	return user_time

# Return UTC datetimes for when the user's current day starts/ends.  
def get_user_today_start_end_in_utc():
	user_timezone = get_current_timezone()

	now_utc = datetime.utcnow().replace(tzinfo=pytz.utc)

	now_user = now_utc.astimezone(tz=user_timezone)

	today_start_user = now_user.replace(hour=0, minute=0, second=0)
	today_end_user = now_user.replace(hour=23, minute=59, second=59)

	today_start_utc = today_start_user.astimezone(pytz.utc)
	today_end_utc = today_end_user.astimezone(pytz.utc)

	return {
		'start': today_start_utc,
		'end': today_end_user
	}

# Used in Comparison and Frequency pages
def get_project_data(comparison_mode = False):
	projects = Project.query.all()

	project_data = {}

	for project in projects:
		project_name = project.project_name

		project_data[project_name] = {
			'name': project_name,
			'color': project.project_hex_color
		}

		if comparison_mode:
			project_data[project_name]['historic_tracked'] = 0
			project_data[project_name]['current_tracked'] = 0
			project_data[project_name]['average'] = 0

	return project_data

def get_tag_data():
	tags = Tag.query.all()

	return tags

def format_milliseconds(milliseconds, days=True, include_seconds=False, short_labels=False):
	# If we're not including seconds, round the milliseconds up/down to the nearest minute
	milliseconds_per_minute = 60 * 1000
	if not include_seconds:
		milliseconds = milliseconds_per_minute * round(milliseconds/milliseconds_per_minute)

	seconds=(milliseconds/1000)%60
	seconds = int(seconds)
	minutes=(milliseconds/(1000*60))%60
	minutes = int(minutes)
	hours=(milliseconds/(1000*60*60))

	if days and hours >= 24:
		days = math.floor(hours / 24)
		hours = hours % 24
		days_string = f"{days} {'days' if days > 1 else 'day'}, "
	else:
		days_string = ''

	hours_string = ("%d hour, " % (hours)) if hours >=1 else ''
	if hours_string and hours >= 2:
		hours_string = hours_string.replace('hour', 'hours')

	minutes_string = ("%d minutes" % (minutes)) if minutes >= 1 else ''
	if minutes == 1:
		minutes_string = minutes_string.replace('minutes', 'minute')

	if minutes_string and include_seconds:
		minutes_string += ", "


	seconds_string = ("%d seconds" % (seconds))
	if seconds == 1:
		seconds_string = seconds_string.replace('seconds', 'second')		


	formatted_string = days_string + hours_string + minutes_string

	if include_seconds:
		formatted_string += seconds_string

	if short_labels:
		formatted_string = formatted_string.replace(' seconds', 's').replace(' second', 's')
		formatted_string = formatted_string.replace(' minutes', 'm').replace(' minute', 'm')
		formatted_string = formatted_string.replace(' hours', 'h').replace(' hour', 'h')
		formatted_string = formatted_string.replace(' days', 's').replace(' day', 'd')
		formatted_string = formatted_string.replace(',', '')

	formatted_string = formatted_string.strip()

	if not formatted_string:
		if short_labels:
			return '0s'
		return '0 seconds'

	if formatted_string[-1] == ',':
		formatted_string = formatted_string[:-1]

	return formatted_string 

def start_tracking(description='', project=''):
	project = None

	response = current_app.toggl.startTimeEntry(description, project)

	return response

def stop_tracking(current_tracking_id=False):
	if current_tracking_id:
		return current_app.toggl.stopTimeEntry(current_tracking_id)

	current_tracking = get_current_toggl_entry()

	if current_tracking:
		current_tracking_id = current_tracking['id']

		return current_app.toggl.stopTimeEntry(current_tracking_id)

	return False

# Convert a datetime object from tz to UTC.
def to_utc(dt, tz):
	return tz.normalize(tz.localize(dt)).astimezone(pytz.utc)