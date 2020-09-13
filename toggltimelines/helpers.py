from flask import current_app

from sqlalchemy import func
from datetime import datetime, timedelta
import pytz
import csv
import sys
import copy

from toggltimelines.timelines.models import Entry
from toggltimelines.timelines.models import Project
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


	# print(f"toggl_sync... Start: {start_date}")
	# print(f"toggl_sync... End: {end_date}")

	entries = get_entries_from_toggl(start_date, end_date)

	#print(f"Toggl entries: {len(entries)}")

	#Only get the current entry if we're getting today's entries.
	if start_date <= datetime.now().replace(tzinfo=timezone) <= end_date:
		current_entry = get_current_toggl_entry()
		if current_entry:
			entries.append(current_entry)

	entries = split_entries_over_midnight(entries)

	local_projects = get_all_projects_from_database()

	# Toggl needed the user timezone, but our database is all in UTC. So we convert.
	start_date = start_date.astimezone(tz=pytz.utc)
	end_date = end_date.astimezone(tz=pytz.utc)

	# print(f"Deleting start: {start_date}")
	# print(f"Deleting end: {end_date}")

	# Remove database entries which already exist in the sync window.
	existing_db_entries = get_db_entries(start_date, end_date)
	for db_entry in existing_db_entries:
		db.session.delete(db_entry)

	db.session.commit() # This is here because of issues when an entry was deleted and re-added during resync. 
						# Project wasn't correctly updating if changed to NULL.

	for entry in entries:
		project_id = entry['pid'] if 'pid' in entry.keys() else None

		db_project = get_database_project_by_id(project_id, local_projects)

		if project_id and not db_project : # Create the database project if it doesn't exist.

			if not 'project' in entry.keys(): # If the project name isn't given in the entry details, we ask Toggl for details about all projects
											  # (This is the case for currently running projects).
				toggl_projects = get_user_toggl_data()['projects']

				for toggl_project in toggl_projects:
					toggl_project_id = toggl_project['id']

					if toggl_project_id == project_id:
						entry['project'] = toggl_project['name']
						entry['project_hex_color'] = toggl_project['hex_color']
						break

			db_project = create_project({
				'project_id': 		 project_id,
				'project_name': 	 entry['project'],
				'project_hex_color': entry['project_hex_color']
			})

			local_projects.append(db_project)


		start_datetime = timestamp_to_datetime(entry['start'])
		end_datetime = timestamp_to_datetime(entry['end'])


		if not 'client' in entry.keys():
			entry['client'] = None #TODO: This is temporary. Need to check how clients are actually working.
								   # Clients should probably be their own table. I'll leave this as is for now until I do that rework.

		location = get_entry_location(start_datetime)

		description = entry['description'] if 'description' in entry.keys() else ''

		db_entry = create_entry({
			'id': 		   entry['id'],
			'description': description,
			'start': 	   start_datetime,
			'end': 		   end_datetime,
			'dur': 		   entry['dur'],
			'client': 	   entry['client'],
			'location':	   location,
			'user_id': 	   entry['uid'],
			'db_project':  db_project
		})

	db.session.commit()

	return entries

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
			#print(entry)

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

			print(entry_before_midnight)
			print(entry_after_midnight)
			print('')


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

def get_db_entries(start_datetime=False, end_datetime=False, projects=False, clients=False, description=False):
	query = Entry.query



	if start_datetime:
		start_datetime = start_datetime.astimezone(pytz.utc)
		query = query.filter(Entry.start >= start_datetime)

	if end_datetime:
		end_datetime = end_datetime.astimezone(pytz.utc)
		query = query.filter(Entry.start <= end_datetime)

	if projects:
		query = query.join(Entry.project, aliased=True)
		query = query.filter(Project.project_name.in_(projects))

	if clients:
		query = query.filter(Entry.client.in_(clients))

	if description:
		query = query.filter(func.lower(Entry.description).contains(description.lower()))


	#print(f"\n{query}\n")

	entries = query.order_by(Entry.start).all()

	# Entries are timezone naive when we retreive them.
	# Need to make them aware that they are in UTC.
	for entry in entries:
		entry.tzinfo_to_utc()

	return entries

# Return the entries in a new list, grouped by day,
def sort_db_entries_by_day(db_entries):
	sorted_by_day = {}

	for entry in db_entries:
		# Below we use get_local_start_time() because we need to make sure we're sorting
		# with reference to what day it was in the user's location. Not simply UTC.
		entry_date_label = entry.get_local_start_time().strftime('%Y-%m-%d')

		if entry_date_label not in sorted_by_day:
			sorted_by_day[entry_date_label] = {
				'entries': [],
				'date': entry.get_local_start_time().strftime('%a %d %b, %Y')
			}

		sorted_by_day[entry_date_label]['entries'].append(entry)

	days_list = []
	for day in sorted_by_day.values():
		days_list.append(day)

	days_list.reverse()

	return days_list

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
		client 			  = entry_data['client'],
		location 		  = entry_data['location'],
		user_id 		  = entry_data['user_id']
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

	return current_entry

def get_user_toggl_data():
	user_data = current_app.toggl.request("https://www.toggl.com/api/v8/me?with_related_data=true")['data']

	projects = user_data['projects']
	clients = user_data['clients']

	return user_data

def get_all_projects_from_database():
	#print('get_projects_from_database')
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