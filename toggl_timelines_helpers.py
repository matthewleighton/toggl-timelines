from datetime import datetime, time, timedelta
from calendar import monthrange
import pytz
import csv
import getpass

import toggl_timelines_config as config

def is_entry_next_day(target_time, entry_time):
	if target_time.day == entry_time.day:
		return False
	else:
		return True

def get_day_in_month():
	print('test')

def end_of_day(timestamp):
	dt = timestamp_to_datetime(timestamp)

	end_of_day = datetime.combine(dt, time.max)

	end_of_day_timestamp = datetime_to_timestamp(end_of_day)

	return end_of_day_timestamp

def timestamp_to_datetime(timestamp, string_format='%Y-%m-%dT%H:%M:%S%z'):
	timestamp = remove_colon_from_timezone(timestamp)
	
	return datetime.strptime(timestamp, string_format) 

def datetime_to_timestamp(dt, string_format='%Y-%m-%dT%H:%M:%S%z'):
	return remove_colon_from_timezone(datetime.strftime(dt, string_format))

def remove_colon_from_timezone(timezone_string):
	if timezone_string[-3] == ':':
		return timezone_string[:-3] + timezone_string[-2:]
	else:
		return timezone_string

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

# If an entry spans over midnight, split it into two.
def split_entry_over_midnight(entry):
	start = entry['start']
	end = entry['end']

	if start.day == end.day:
		return [entry]

	midnight_datetime = entry['end'].replace(hour=0, minute=0, second=0)

	before_midnight = entry.copy()
	before_midnight['end'] = midnight_datetime
	duration_before = (midnight_datetime - before_midnight['start']).seconds*1000
	before_midnight['dur'] = duration_before

	after_midnight = entry.copy()
	after_midnight['start'] = midnight_datetime
	duration_after = (after_midnight['end'] - midnight_datetime).seconds*1000
	after_midnight['dur'] = duration_after

	halves = [before_midnight, after_midnight]

	return [before_midnight, after_midnight]

def get_entry_tooltip(entry):
	start_time = entry['start'].strftime('%H:%M')
	end_time = entry['end'].strftime('%H:%M')

	project = entry.get('project')
	description = entry.get('description', '')
	duration = format_duration(entry.get('dur'))
	client = entry.get('client', '')

	if not project:
		project = 'No Project'
		entry['project_hex_color'] = '#C8C8C8'

	return '<b>{0}</b>: {1}<br/>Client: {2}<br/>{3}-{4}<br/>{5}'.format(project, description, client, start_time, end_time, duration)

# Turn an amount of milliseconds into "x hours, y minutes"
def format_duration(milliseconds):
	seconds=(milliseconds/1000)%60
	seconds = int(seconds)
	minutes=(milliseconds/(1000*60))%60
	minutes = int(minutes)
	hours=(milliseconds/(1000*60*60))%24

	hours_string = ("%d hour, " % (hours)) if hours >=1 else ''
	if hours_string and hours >= 2:
		hours_string.replace('hour', 'hours')

	minutes_string = ("%d minutes" % (minutes))

	return hours_string + minutes_string

def get_local_utc_offset():
	local_hours = datetime.now().hour
	utc_hours = datetime.utcnow().hour

	utc_offset = local_hours - utc_hours

	return utc_offset

def get_untracked_time(target_time, entry, after_midnight=False):
	# The after_midnight variable indicates that we're now running the function for a second time,
	# getting the second half of untracked time, which appears after midnight.

	untracked_time_list = []

	if not after_midnight and is_entry_next_day(target_time, entry['start']):

		run_again_after_midnight = True

		next_day = target_time.day + 1
		
		month = target_time.month
		next_month = month + 1

		days_in_month = monthrange(target_time.year, target_time.month)[1]

		if next_day > days_in_month:
			month += 1
			next_day = 1
		
		untracked_end = target_time.replace(month=month, day=next_day, hour=0, minute=0, second=0)
		

		new_target_time = untracked_end

	else:
		untracked_end = entry['start']
		new_target_time = entry['end']
		run_again_after_midnight = False

	dur = (untracked_end - target_time).seconds*1000

	untracked_time = {
		'start': target_time,
		'end': entry['end'],
		'dur' : dur,
		'class': 'untracked_time ',
		'tooltip': 'Untracked'
		#'tooltip': 'Untracked<br/>{0}<br/>{1}'.format(target_time, untracked_end)
	}

	if after_midnight:
		return untracked_time

	untracked_time_list.append(untracked_time)
	
	if run_again_after_midnight:
		untracked_time_list.append(get_untracked_time(new_target_time, entry, True))

	return untracked_time_list

def get_client_hex_color(client):
	hex_color_config = config.client_colors

	if client in hex_color_config.keys():
		return hex_color_config[client]
	else:
		return '#a6a6a6'

def display_heart():
	system_username = getpass.getuser()

	if 'johanna' in system_username.lower():
		return True
	else:
		return False