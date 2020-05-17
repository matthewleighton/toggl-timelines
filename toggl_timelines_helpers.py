from datetime import datetime, time, timedelta
import calendar
from calendar import monthrange
import pytz
import csv
import getpass
from TogglPy import Toggl

import toggl_timelines_config as config

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

# Return a datetime for the current time in the user's current timezone.
def get_current_datetime_in_user_timezone():
	with open ('utc_offsets.csv', 'r') as file:
		reader = csv.DictReader(file)
		timezone_name = next(reader)['location']

	timezone = pytz.timezone(timezone_name)

	user_time = datetime.now(timezone)

	return user_time

def display_heart():
	system_username = getpass.getuser()

	if 'johanna' in system_username.lower():
		return True
	else:
		return False