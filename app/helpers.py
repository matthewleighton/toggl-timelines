from app import app
from datetime import datetime, date, time, timedelta


from app import TogglPy
from app import models
from app import db
from app import togglconfig

import csv
import pytz
import getpass

import pdb

#import toggl_timelines_config as config # TODO-NEXT: Where to place the config file?

# Update the local database from Toggl's API
def update_database(start_days_ago, end_days_ago=0):
	print('update_database')
	start = datetime.today().replace(hour=0, minute=0, second=0) - timedelta(days=start_days_ago)
	end   = datetime.today() - timedelta(days=end_days_ago)

	request_data = {
	    'workspace_id': togglconfig.workspace_id,
	    'since': start,
	    'until': end,
	}



	toggl = TogglPy.Toggl()
	toggl.setAPIKey(togglconfig.api_key)

	entries = toggl.getDetailedReportPages(request_data)['data']
	
	currently_tracking = get_currently_tracking()
	if currently_tracking:
		entries.append(currently_tracking)
	
	delete_days_from_database(start, end)

	for entry in entries:

		location_utc_offset = get_toggl_entry_utc_offset(entry)
		# This is the utc offset of the location I was in when the entry was recorded.
		
		entry_id = entry['id']
		
		existing_entry = models.Entry.query.filter_by(id=entry_id).first()
		
		if existing_entry:
			print('Existing Entry!')
			print(existing_entry)
			db.session.delete(existing_entry)
			db.session.commit() # Not sure whether we need this.

		start = remove_colon_from_timezone(entry['start'])
		start = timestamp_to_datetime(start)
				
		toggl_utc_offset = int(start.utcoffset().total_seconds()/(60*60))
		# Toggl's values are adjusted based on whatever the current account timezone is.
		# toggl_utc_offset is the number of hours we need to SUBTRACT from the time to get it into UTC.

		start = start - timedelta(hours = toggl_utc_offset)

		end = remove_colon_from_timezone(entry['end'])
		end = timestamp_to_datetime(end)
		end = end - timedelta(hours = toggl_utc_offset)


		if entry['project']:
			db_project = models.Project.query.filter_by(id=entry['pid']).first()
			if not db_project:
				db_project = models.Project(
					id = entry['pid'],
					project_name = entry['project'],
					project_hex_color = entry['project_hex_color']
				)

				db.session.add(db_project)
		else:
			db_project = False

		db_entry = models.Entry(
			id 				  = entry['id'],
			description 	  = entry['description'],
			start 			  = start,
			end 			  = end,
			dur 			  = entry['dur'],
			client 			  = entry['client'],
			utc_offset 		  = location_utc_offset,
			user_id 		  = entry['uid']
		)

		if db_project:
			db_entry.project = db_project	

		db.session.add(db_entry)


		tags = entry['tags']
		for tag_name in tags:
			db_tag = models.Tag.query.filter_by(tag_name=tag_name).first()

			if not db_tag:
				db_tag = models.Tag(
					tag_name = tag_name
				)
				db.session.add(db_tag)

			db_tag.entries.append(db_entry)
				
	db.session.commit()

	return entries

# Get the currently tracking entry, and add/format the required data so it matches the historic entries.
def get_currently_tracking():
	toggl = TogglPy.Toggl()
	toggl.setAPIKey(togglconfig.api_key)

	user_data = toggl.request("https://www.toggl.com/api/v8/me?with_related_data=true")
	projects = user_data['data']['projects']
	clients = user_data['data']['clients']

	current = toggl.currentRunningTimeEntry()

	if not current:
		return False

	start_string = remove_colon_from_timezone(current['start'])
	start = timestamp_to_datetime(start_string).replace(tzinfo=None)
	utc_now = datetime.utcnow()
	difference = utc_now - start
	seconds = difference.seconds
	milliseconds = seconds*1000

	start_datetime = timestamp_to_datetime(current['start'])
	end_datetime = start_datetime + timedelta(seconds=seconds)
	end_string = datetime_to_timestamp(end_datetime)

	current['dur'] = milliseconds
	current['end'] = end_string
	current['project_hex_color'] = '#C8C8C8'
	
	if 'tags' not in current:
		current['tags'] = []

	current['project'] = None
	client_id = False

	if 'pid' in current:
		for project in projects:
			if project['id'] == current['pid']:
				current['project'] 			 = project['name']
				current['project_hex_color'] = project['hex_color']

				client_id = project.get('cid')
				break;

	for client in clients:
		if client['id'] == client_id:
			current['client'] = client['name']
			break

		current['client'] = None

	if not 'description' in current:
		current['description'] = ''

	return current

def remove_colon_from_timezone(timezone_string):
	if timezone_string[-3] == ':':
		return timezone_string[:-3] + timezone_string[-2:]
	else:
		return timezone_string

def datetime_to_timestamp(dt, string_format='%Y-%m-%dT%H:%M:%S%z'):
	return remove_colon_from_timezone(datetime.strftime(dt, string_format))

def timestamp_to_datetime(timestamp, string_format='%Y-%m-%dT%H:%M:%S%z'):
	timestamp = remove_colon_from_timezone(timestamp)
	
	return datetime.strptime(timestamp, string_format)

def delete_days_from_database(start, end):
	db_entries = models.Entry.query.filter(models.Entry.start <= end).filter(models.Entry.start >= start)

	for entry in db_entries:
		db.session.delete(entry)

	db.session.commit()

def get_toggl_entry_utc_offset(entry):
	
	tags = entry['tags']
	for tag in tags:
		if tag[0:3] == 'UTC':
			return int(tag.replace('UTC', ''))

	# If there was no tag, check the csv file.
	with open ('utc_offsets.csv', 'r') as file:
		reader = csv.DictReader(file)
		for row in reader:
			location_start_date = row['start']
			location_end_date = row['end']
			location = row['location']

			#print('-----------------------------------')
			#print('location Start: ' + location_start_date)
			#print('location End: ' + location_end_date)
			#print('Entry Date: ' + entry['start'])

			if location_start_date <= entry['start'] <= location_end_date:
				dt = datetime.strptime(entry['start'][0:-6], '%Y-%m-%dT%H:%M:%S')
				offset = int(pytz.timezone(location).localize(dt).strftime('%z')[0:3])
				#print('Offset found via csv: ' + str(offset))
				return offset
				

	print('Could not find offset - using local')

	return get_local_utc_offset()

def get_entries_from_database(start=False, end=False, projects=False, clients=False, tags=False, description=False):
	
	Entry = models.Entry

	# Times are stored in database as UTC. So we need to convert the request times to UTC.
	if start:
		#if start.tzinfo is not None and start.tzinfo.utcoffset(start) is not None:
		start = start.astimezone(pytz.utc)

	if end:
		#if end.tzinfo is not None and end.tzinfo.utcoffset(end) is not None:
		end = end.astimezone(pytz.utc)


	query = Entry.query.join(Entry.project, aliased=True)
	
	if start:
		query = query.filter(Entry.start >= start)

	if end:
		query = query.filter(Entry.start <= end)
	
	if projects:
		query = query.filter(Project.project_name.in_(projects))

	if clients:
		query = query.filter(Entry.client.in_(clients))

	if description:
		query = query.filter(func.lower(Entry.description).contains(description.lower()))

	
	#if tags:
		#query = query.filter(Entry.tags.in_(clients))
		
	entries = query.order_by(Entry.start).all()

	#apply_utc_offsets(entries)

	entries = split_entries_over_midnight(entries)


	return entries

def sort_entries_by_day(entries):
	sorted_by_day = {}

	for entry in entries:

		entry_date = entry.start.strftime('%Y-%m-%d')
		
		if entry_date not in sorted_by_day:
			sorted_by_day[entry_date] = {
				'entries': [],
				'date': entry.start.strftime('%a %d %b, %Y')
			}

		sorted_by_day[entry_date]['entries'].append(entry)

	days_list = []
	for day in sorted_by_day.values():
		days_list.append(day)

	days_list.reverse()

	return days_list

# For each entry, adjust its start and end times such that they match the location where the entry was recorded.
def apply_utc_offsets(entries):
	for entry in entries:
		
		if not hasattr(entry, 'offset_fixed'): # Make sure we're not applying the offset for a second time.
			new_start = entry.start + timedelta(hours=entry.utc_offset)
			new_end = entry.end + timedelta(hours=entry.utc_offset)

			entry.start = new_start
			entry.end = new_end
			entry.offset_fixed = True

# Return a version of the entries list, where any entries which span midnight are split in two.
def split_entries_over_midnight(entries):
	completed_entries = []

	for entry in entries:
		
		start = entry.start
		end = entry.end

		if start.day == end.day:
			halves = [entry]
		else:
			midnight_datetime = entry.end.replace(hour=0, minute=0, second=0)
			

			duration_before = (midnight_datetime - entry.start).seconds*1000
			entry.dur = duration_before

			duration_after = (entry.end - midnight_datetime).seconds*1000
			entry.end = midnight_datetime
			

			second_half = models.Entry(
				description 	  = entry.description,
				start 			  = midnight_datetime,
				end 			  = end,
				dur 			  = duration_after,
				project 		  = entry.project,
				client 			  = entry.client,
				project_hex_color = entry.project_hex_color,
				utc_offset 		  = entry.utc_offset,
				user_id 		  = entry.user_id
			)


			# We're using this function after applying the UTC offsets.
			#So we want to mark all these entries as having already had their offset fixed.
			second_half.offset_fixed = True



			halves = [entry, second_half]

		for entry_half in halves:

			completed_entries.append(entry_half)
			
	return completed_entries

def display_heart():
	system_username = getpass.getuser()

	if 'johanna' in system_username.lower():
		return True
	else:
		return False
		