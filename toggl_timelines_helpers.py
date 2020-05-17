from datetime import datetime, time, timedelta
import calendar
from calendar import monthrange
import pytz
import csv
import getpass
from TogglPy import Toggl

import toggl_timelines_config as config

# Get a ratio (0 to 1) describing how much a certain period of time (e.g. today/this week/month/year) is complete/over.
def get_period_completion_ratio(period, working_time_start=False, working_time_end=False):
	now = get_current_datetime_in_user_timezone()
	
	hour_of_day = now.hour
	minute_of_hour = now.minute

	#------ Figuring out how long a workday is based on the start and end times.
	if working_time_start:
		dt = datetime.strptime(working_time_start, '%H:%M')
		work_start_datetime = now.replace(hour=dt.hour, minute=dt.minute)
	else:
		work_start_datetime = now.replace(hour=0, minute=0, second=0)

	if working_time_end:
		dt = datetime.strptime(working_time_end, '%H:%M')
		work_end_datetime = now.replace(hour=dt.hour, minute=dt.minute)
	else:
		work_end_datetime = now.replace(hour=23, minute=59, second=59) + timedelta(seconds=1)

	if now > work_start_datetime: # If work day has started...
		worked_until_today = min(now, work_end_datetime)
	else:
		worked_until_today = work_start_datetime

	minutes_complete_today = (worked_until_today - work_start_datetime).seconds/60

	minutes_in_a_day = (work_end_datetime - work_start_datetime).seconds/60
	if minutes_in_a_day == 0: # Fixing weird case of above line returning 0.
		minutes_in_a_day = 60*24


	#------ Now figuring out how much of the workday is complete.
	if period == 'day':
		completion_ratio = minutes_complete_today / minutes_in_a_day

	elif period == 'week':
		weekday = now.weekday()

		minutes_complete_this_week = weekday * minutes_in_a_day + minutes_complete_today
		minutes_in_a_week = minutes_in_a_day * 7

		completion_ratio = minutes_complete_this_week / minutes_in_a_week

	elif period == 'month':
		days_complete_this_month = now.day - 1

		minutes_complete_this_week = minutes_in_a_day * days_complete_this_month + minutes_complete_today

		days_in_this_month = calendar.monthrange(now.year, now.month)[1]
		minutes_in_this_month = minutes_in_a_day * days_in_this_month

		completion_ratio = minutes_complete_this_week / minutes_in_this_month

	elif period == 'year':
		days_complete_this_year = datetime.now().timetuple().tm_yday - 1
		minutes_complete_this_year = minutes_in_a_day * days_complete_this_year + minutes_complete_today

		days_this_year = 366 if (calendar.isleap(now.year)) else 365
		minutes_in_this_year = days_this_year * minutes_in_a_day

		completion_ratio = minutes_complete_this_year / minutes_in_this_year

	return completion_ratio

def get_project_data(comparison_mode = False):
	toggl = Toggl()
	toggl.setAPIKey(config.api_key)

	raw_project_data = toggl.request("https://www.toggl.com/api/v8/me?with_related_data=true")['data']['projects']
	project_data = {}

	for project in raw_project_data:
		project_name = project['name']
		project_data.update( {project_name: project} )
		project['color'] = project['hex_color']

		if comparison_mode:
			project_data[project_name]['historic_tracked'] = 0
			project_data[project_name]['current_tracked'] = 0
			project_data[project_name]['average'] = 0

	return project_data


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