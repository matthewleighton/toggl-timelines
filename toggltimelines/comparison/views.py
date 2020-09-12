from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import current_app
from flask import make_response
from flask import jsonify
from werkzeug.exceptions import abort

import calendar
import csv
import pytz
from datetime import datetime, timedelta

from toggltimelines import db
from toggltimelines.timelines.models import Entry, Project
from toggltimelines import helpers

bp = Blueprint("comparison", __name__)

@bp.route("/comparison")
def index():
	helpers.toggl_sync(days=2)
	return render_template("comparison/index.html")

@bp.route("/comparison/data", methods=['POST'])
def comparison_data():
	reload_data = request.json.get('reload')

	if reload_data:
		helpers.toggl_sync(days=1)

	live_mode 				= bool(request.json.get('live_mode_calendar'))
	number_of_current_days  = int(request.json.get('timeframe'))
	number_of_historic_days = int(request.json.get('datarange'))
	target_weekdays 		= request.json.get('weekdays')
	sort_type 				= request.json.get('sort_type')
	period_type 			= request.json.get('period_type')

	project_data = get_project_data(comparison_mode=True)

	goals_projects = []
	goals = {}

	if period_type == 'goals':
		calendar_period = request.json.get('goals_period')
		live_mode_goals = request.json.get('live_mode_goals')

		goals_raw = get_comparison_goals()
		
		for goal in goals_raw:
			goals_projects.append(goal['name'])
			goal_name = goal['name']

			if goal['type']  in ('tag', 'client'):
				project_data[goal_name] = {
					'historic_tracked': 0,
					'current_tracked': 0,
					'average': 0,
					'name': goal_name
				}

			if goal['color']:
				project_data[goal_name]['color'] = goal['color']

			seconds_in_day = 86400
			now = datetime.now()

			seconds = {
				'day': seconds_in_day,
				'week': seconds_in_day * 7,
				'month': seconds_in_day * calendar.monthrange(now.year, now.month)[1],
				'year': seconds_in_day * (366 if (calendar.isleap(now.year)) else 365)
			}

			goal_period = goal['time_period']
			goal_value_in_seconds = int(goal['goal_value']) * 60

			period_ratio 				= seconds[calendar_period] / seconds[goal_period]
			goal_seconds_in_view_period = period_ratio * goal_value_in_seconds

			if live_mode_goals: # If live mode, reduce the goal relative to how much of the period is over.
								# E.g. if we're halfway through a day, the daily goal is half.
				period_completion = get_period_completion_ratio(calendar_period, goal['working_time_start'], goal['working_time_end'])

				if period_completion == 0: # Don't show projects which have goals currently requiring 0 time.
										   # i.e. working hours haven't started.
					del project_data[goal['name']]

				goal_seconds_in_view_period = goal_seconds_in_view_period * period_completion

			goals.update( {goal['name']: goal_seconds_in_view_period })
	else:
		calendar_period = request.json.get('calendar_period')


	if type(target_weekdays) is not list:
		target_weekdays = [target_weekdays]

	start_end_values = get_comparison_start_end(period_type, number_of_current_days, number_of_historic_days, calendar_period, live_mode)


	db_entries = helpers.get_db_entries(start_end_values['current_start'], start_end_values['current_end'])

	current_days = helpers.sort_db_entries_by_day(db_entries)


	# current_days = helpers.get_days_list(
	# 	start=start_end_values['current_start'],
	# 	end=start_end_values['current_end'],
	# )


	if period_type != "goals": # Don't need to do historic days work if we're in goals mode.

		print(f"Historic start: {start_end_values['historic_start']}")
		print(f"Historic end: {start_end_values['historic_end']}")

		db_entries = helpers.get_db_entries(start_end_values['historic_start'], start_end_values['historic_end'])

		historic_days = helpers.sort_db_entries_by_day(db_entries)


		# historic_days=get_days_list(
		# 	start=start_end_values['historic_start'],
		# 	end=start_end_values['historic_end'],
		# )

		# Assign tracked time to historic data.
		sum_category_durations(historic_days, project_data, period_type, historic=True, live_mode=live_mode, weekdays=target_weekdays)
	else:
		historic_days = []


	calculate_historic_averages(category_data=project_data,
								view_type=period_type,
								historic_days=historic_days,
								current_days=current_days,
								goals_projects=goals_projects,
								goals=goals)

	# Assign tracked time to current data.
	sum_category_durations(current_days, project_data, period_type, historic=False, weekdays=target_weekdays)

	response = calculate_ratios(project_data, period_type, goals)

	sorted_response = sorted(response, key=lambda k: k[sort_type])

	return jsonify(sorted_response)


def sum_category_durations(days, categories, view_type, historic=False, live_mode=False, weekdays=[]):
	current_or_historic_tracked = 'historic_tracked' if historic else 'current_tracked'

	for day in days:
		entries = day['entries']

		if historic:
				print(f"Historic Entries: {len(entries)}")

		for entry in entries:

			if entry.project in (None, 'No Project'): # Skip entries without projects.
				continue

			weekday = str(entry.start.weekday())
			if weekday not in weekdays: # Skip weekdays which are not selected.
				continue

			project_name = entry.get_project_name()

			if historic and live_mode and day == days[0] and entry == entries[-1]: # If this is the most recent historic entry...
				
				# Here we need to deal with the raw UTC time.
				# The reason is that we don't know what time zone the user was in at the historic period. Can't assume it's the same as now.
				# So we compare things in UTC.

				now = datetime.utcnow()
				# entry_mid = entry.get_raw_start_time().replace(hour=now.hour, minute=now.minute)
				# entry_start = entry.get_raw_start_time()
				entry_mid = entry.start.replace(hour=now.hour, minute=now.minute)
				entry_start = entry.start

				time_difference = entry_mid - entry_start

				duration = min(time_difference.seconds, entry.dur/1000)
			else:
				duration = entry.dur/1000

			if not historic and view_type == 'goals':
				# TODO!!!!: Tags are not yet implemented.
				# tags = entry.tags
				# if tags:
				# 	for tag in tags:
				# 		if tag.tag_name in categories:
				# 			categories[tag.tag_name]['current_tracked'] += duration

				if entry.client in categories:
					categories[entry.client]['current_tracked'] += duration

			categories[project_name][current_or_historic_tracked] += duration



# Get a ratio (0 to 1) describing how much a certain period of time (e.g. today/this week/month/year) is complete/over.
def get_period_completion_ratio(period, working_time_start=False, working_time_end=False):
	now = helpers.get_current_datetime_in_user_timezone()
	
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




# Calculate how the ratio of time tracked in a current vs historic period. Return as a list.
def calculate_ratios(category_data, view_type, goals=[]):
	response = []

	for project_name in category_data:
		
		current_tracked = category_data[project_name]['current_tracked']
		historic_tracked = category_data[project_name]['historic_tracked']

		average = category_data[project_name]['average']

		category_data[project_name]['difference'] = current_tracked - average

		if average == 0:
			ratio = 100
		else:
			ratio = current_tracked/average

		category_data[project_name]['ratio'] = ratio

		if current_tracked > 0 or historic_tracked > 0 or view_type == 'goals': # Don't include projects with no recent/historic tracked time.
			
			if view_type == 'goals' and project_name not in goals.keys():
				continue # Don't include projects which don't have goals.

			response.append(category_data[project_name])

	return response

def get_comparison_goals():
	goals = []

	with open ('goals.csv', 'r') as file:
		reader = csv.DictReader(file)
		for row in reader:
			goals.append(row)

	return goals

def get_comparison_start_end(period_type, number_of_current_days, number_of_historic_days, calendar_period, live_mode):
	now = datetime.now()
	today_end = now.replace(hour=23, minute=59, second=59)
	today_start = now.replace(hour=0, minute=0, second=0)
	
	today_day = now.day
	today_hour = now.hour
	today_minute = now.minute

	current_end = now

	if period_type == 'custom':
		current_start = (now - timedelta(days=number_of_current_days-1)).replace(hour=0, minute=0, second=0)

		historic_end = current_start - timedelta(seconds=1)
		historic_start = (historic_end - timedelta(days=number_of_historic_days-1)).replace(hour=0, minute=0, second=0)
	else:
		if calendar_period == 'day':
			current_start = now.replace(hour=0, minute=0, second=0)

			historic_end = (current_end - timedelta(days=1)) if live_mode else (today_end - timedelta(days=1))
			historic_start = historic_end.replace(hour=0, minute=0, second=0)
		
		elif calendar_period == 'week':
			days_since_week_start = now.weekday()
			current_start = today_start - timedelta(days=days_since_week_start)

			historic_start = current_start - timedelta(days=7)
			historic_end = (now - timedelta(days=7)) if live_mode else (historic_start + timedelta(days=6, hours=23, minutes=59, seconds=59))
		
		elif calendar_period == 'month':
			previous_month = (now.month-1) or 12
			historic_year = now.year if previous_month != 12 else now.year - 1

			last_day_of_previous_month = calendar.monthrange(historic_year, previous_month)[1]
			

			current_start = today_start.replace(day=1)

			historic_start = (current_start - timedelta(days=1)).replace(day=1)

			if live_mode:
				historic_end = historic_start.replace(day=min(now.day, last_day_of_previous_month), hour=now.hour, minute=now.minute)
			else:
				historic_end = historic_start.replace(day=last_day_of_previous_month, hour=23, minute=59, second=59)

		elif calendar_period == 'quarter':
			current_quarter = (now.month-1)//3 # First quarter is 0
			first_month_of_current_quarter = 1 + current_quarter*3

			previous_quarter = (current_quarter - 1) if current_quarter > 0 else 3
			first_month_of_previous_quarter = 1 + previous_quarter*3

			historic_year = now.year if current_quarter > previous_quarter else now.year - 1

			month_of_current_quarter = (now.month-1) % 3  # First month of quarter is 0
			equivalent_month_of_previous_quarter = first_month_of_previous_quarter + month_of_current_quarter #If we're in the 2nd month of this quarter, this will be the 2nd month of last quarter.
			last_day_of_equivalent_month = calendar.monthrange(historic_year, equivalent_month_of_previous_quarter)[1]

			last_month_of_previous_quarter = first_month_of_previous_quarter + 2
			last_day_of_previous_quarter = calendar.monthrange(historic_year, last_month_of_previous_quarter)[1]

			current_start = today_start.replace(month=first_month_of_current_quarter, day=1)

			historic_start = today_start.replace(year=historic_year, month=first_month_of_previous_quarter, day=1)

			if live_mode:
				historic_end = historic_start.replace(
					year = historic_year,
					month = equivalent_month_of_previous_quarter,
					day = min(now.day, last_day_of_equivalent_month),
					hour = now.hour,
					minute = now.minute
				)
			else:
				historic_end = historic_start.replace(
					year = historic_year,
					month = last_month_of_previous_quarter,
					day = last_day_of_previous_quarter,
					hour = 23,
					minute = 59
				)

		elif calendar_period == 'half-year': # TODO: Combine this and 'quarter' logic. They should be the same except for some of the numbers.
			current_half = (now.month-1)//6 # First half is 0
			first_month_of_current_half = 1 + current_half*6

			previous_half = 0 if (current_half == 1) else 1
			first_month_of_previous_half = 1 + previous_half*6

			historic_year = now.year if current_half > previous_half else now.year - 1

			month_of_current_half = (now.month-1) % 6 # First month of half is 0
			equivalent_month_of_previous_half = first_month_of_previous_half + month_of_current_half
			last_day_of_equivalent_half = calendar.monthrange(historic_year, equivalent_month_of_previous_half)[1]

			last_month_of_previous_half = first_month_of_previous_half + 5
			last_day_of_previous_half = calendar.monthrange(historic_year, last_month_of_previous_half)[1]

			current_start = today_start.replace(month=first_month_of_current_half, day=1)

			historic_start = today_start.replace(year=historic_year, month=first_month_of_previous_half, day=1)

			if live_mode:
				historic_end = historic_start.replace(
					year = historic_year,
					month = equivalent_month_of_previous_half,
					day = min(now.day, last_day_of_equivalent_half),
					hour = now.hour,
					minute = now.minute
				)
			else:
				historic_end = historic_start.replace(
					year = historic_year,
					month = last_month_of_previous_half,
					day = last_day_of_previous_half,
					hour = 23,
					minute = 59
				)

		elif calendar_period == 'year':
			current_start = today_start.replace(month=1, day=1)

			historic_start = today_start.replace(year=now.year-1, month=1, day=1)

			if live_mode:
				historic_day = now.day
				if historic_day == 29 and now.month == 2:
					historic_day = 28 # Leap years.

				historic_end = today_start.replace(
					year = now.year - 1,
					month = now.month,
					day = historic_day,
					hour = now.hour,
					minute = now.minute
				)
			else:
				historic_end = today_start.replace(
					year = now.year - 1,
					month = 12,
					day = 31,
					hour = 23,
					minute = 59
				)

		elif calendar_period == 'month-of-year':
			historic_year = now.year - 1
			last_day_of_month = calendar.monthrange(now.year, now.month)[1]	

			current_start = today_start.replace(day=1)
			historic_start = current_start.replace(year=historic_year)

			if live_mode:
				historic_end = historic_start.replace(day=now.day, hour=now.hour, minute=now.minute)
			else:
				historic_end = historic_start.replace(day=last_day_of_month, hour=23, minute=59, second=59)

	"""
	print('Current start: ' + str(current_start))
	print('Current end: ' + str(current_end))
	print('Historic start: ' + str(historic_start))
	print('Historic end: ' + str(historic_end))
	"""
	
	return {
		'current_start': current_start,
		'current_end': current_end,
		'historic_start': historic_start,
		'historic_end': historic_end
	}



# Calculate the average time spent on various projects in a given historic period. (Or, assign goal time if in goals mode)
def calculate_historic_averages(category_data, view_type, historic_days, current_days, goals_projects=[], goals=[]):
	for project_name in category_data:

		seconds = category_data[project_name]['historic_tracked']
		
		if view_type == 'custom':
			
			number_of_historic_days = len(historic_days)
			number_of_current_days = len(current_days)

			average = (seconds/number_of_historic_days)*number_of_current_days	
		elif view_type == 'calendar':
			average = seconds # When using calendar mode, we aren't actually taking an average, but just the amount of time tracked in that period.
		elif view_type == 'goals':
			if not project_name in goals_projects: # Ignore projects which don't have goals.
				continue
			average = goals[project_name]
		
		category_data[project_name]['average'] = average



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