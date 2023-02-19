import calendar
import csv
import pytz
from time import perf_counter

from pprint import pprint
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, make_response, jsonify, session

from toggltimelines import helpers

bp = Blueprint("comparison", __name__)

@bp.route("/comparison")
def index():
	helpers.toggl_sync(days=2)

	page_data = {
		'comparison_defaults': get_comparison_defaults()
	}

	return make_response(render_template('comparison/index.html', data=page_data))

@bp.route("/comparison/data", methods=['POST'])
def comparison_data():
	if request.json.get('reload'):
		helpers.toggl_sync(days=1)

	start_time = perf_counter()

	calendar_period 		= get_calendar_period()
	goals_mode 				= get_goals_mode()
	hide_completed 			= bool(request.json.get('hide_completed'))
	live_mode_calendar 		= bool(request.json.get('live_mode_calendar'))
	number_of_current_days  = int(request.json.get('timeframe'))
	number_of_historic_days = int(request.json.get('datarange'))
	period_type 			= request.json.get('period_type')
	show_clients 			= bool(request.json.get('show_clients'))
	show_projects 			= bool(request.json.get('show_projects'))
	sort_type 				= request.json.get('sort_type')
	target_weekdays 		= get_target_weekdays()

	project_data = helpers.get_project_data(comparison_mode=True)
	goals, goals_projects = prepare_goals(project_data)

	print('number_of_current_days: ', number_of_current_days)

	start_end_values = get_comparison_start_end(period_type, number_of_current_days, number_of_historic_days, calendar_period, live_mode_calendar)
	
	current_days = prepare_current_days(start_end_values)
	historic_days = prepare_historic_days(start_end_values)
	
	sum_category_durations(current_days, project_data, period_type, historic=False, weekdays=target_weekdays)

	if not goals_mode:
		sum_category_durations(historic_days, project_data, period_type, historic=True, live_mode=live_mode_calendar, weekdays=target_weekdays)

	if show_clients and not goals_mode:
		add_client_comparisons(project_data)

	assign_historic_time(category_data=project_data,
						 view_type=period_type,
						 historic_days=historic_days,
						 current_days=current_days,
						 goals_projects=goals_projects,
						 goals=goals)


	if not show_projects and not goals_mode:
		hide_project_comparisons(project_data)

	response = calculate_ratios(project_data, period_type, goals, hide_completed)
	sorted_response = sorted(response, key=lambda k: k[sort_type])

	end_time = perf_counter()
	print('Time elapsed: ', end_time - start_time)

	return jsonify(sorted_response)

def get_target_weekdays():
	target_weekdays = request.json.get('weekdays')

	if type(target_weekdays) is not list:
		target_weekdays = [target_weekdays]

	return target_weekdays

def get_calendar_period():
	goals_mode = get_goals_mode()
	
	if goals_mode:
		return request.json.get('goals_period')
	else:
		return request.json.get('calendar_period')

def get_goals_mode():
	return True if request.json.get('period_type') == 'goals' else False


def prepare_goals(project_data):
	goals = {}
	goals_projects = []
	
	if not get_goals_mode():
		return goals, goals_projects

	goals_projects = []
	calendar_period = get_calendar_period()
	live_mode_goals = bool(request.json.get('live_mode_goals'))

	goals_raw = get_comparison_goals() # Get goals from csv file.
	remove_projects_without_goals(goals_raw, project_data)

	for goal in goals_raw:
		update_goal(goal, project_data, goals, goals_projects, calendar_period, live_mode_goals)
	
	return goals, goals_projects

def update_goal(goal, project_data, goals, goals_projects, calendar_period, live_mode_goals):
	goals_projects.append(goal['name'])
	goal_name = goal['name']
	goal_days = [int(day)-1 for day in list(goal['days'])] if goal['days'] is not None else list(range(0,7))

	if goal['type']  in ('tag', 'client'):
		project_data[goal_name] = {
			'historic_tracked': 0,
			'current_tracked': 0,
			'average': 0,
			'name': goal_name,
			'type': goal['type']
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
	goal_value = goal['goal_value']

	# The goal is written as hours.minutes. We now convert this into a number of seconds.
	if goal_value.find('.') < 0:
		goal_value += '.0'

	goal_hours, goal_minutes = list(map(int, goal_value.split('.')))
	goal_value_in_seconds = goal_hours*60*60 + goal_minutes*60

	period_ratio 				= seconds[calendar_period] / seconds[goal_period]
	goal_seconds_in_view_period = period_ratio * goal_value_in_seconds

	# period_ratio is the ratio of goal_days in the calendar_period to goal_days in the goal_period.
	period_ratio = goal_days_in_period(calendar_period, goal_days, completed_only=False) / goal_days_in_period(goal_period, goal_days, completed_only=False)
	goal_seconds_in_view_period = period_ratio * goal_value_in_seconds

	if goal_seconds_in_view_period == 0:
		del project_data[goal['name']]

	if live_mode_goals: # If live mode, reduce the goal relative to how much of the period is over.
						# E.g. if we're halfway through a day, the daily goal is half.
		period_completion = get_period_completion_ratio(calendar_period, goal['working_time_start'], goal['working_time_end'], goal_days)

		# Don't show projects which have goals currently requiring 0 time. i.e. working hours haven't started.
		if period_completion == 0 and goal['name'] in project_data:
				del project_data[goal['name']]

		goal_seconds_in_view_period = goal_seconds_in_view_period * period_completion

	goals.update( {goal['name']: goal_seconds_in_view_period })


def prepare_current_days(start_end_values):
	db_entries = helpers.get_db_entries(start_end_values['current_start'], start_end_values['current_end'])
	return helpers.sort_db_entries_by_day(db_entries)

def prepare_historic_days(start_end_values):
	if get_goals_mode():
		return []
	
	db_entries = helpers.get_db_entries(start_end_values['historic_start'], start_end_values['historic_end'])
	return helpers.sort_db_entries_by_day(db_entries)










# Given a list of goals, remove any projects from the project_data dict if it has no goal.
def remove_projects_without_goals(goals, project_data):
	goal_names_list = [goal['name'] for goal in goals]

	projects_without_goals = []
	for project_name, project in project_data.items():
		if project_name not in goal_names_list:
			projects_without_goals.append(project_name)

	for project_name in projects_without_goals:
		project_data.pop(project_name)

def sum_category_durations(days, categories, view_type, historic=False, live_mode=False, weekdays=[]):
	current_or_historic_tracked = 'historic_tracked' if historic else 'current_tracked'

	for day in days:
		entries = day['entries']

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
				entry_mid = entry.start.replace(hour=now.hour, minute=now.minute)
				entry_start = entry.start

				time_difference = entry_mid - entry_start

				duration = min(time_difference.seconds, entry.dur/1000)
			else:
				duration = entry.dur/1000

			if not historic and view_type == 'goals':
				tags = entry.tags
				if tags:
					for tag in tags:
						if tag.tag_name in categories and categories[tag.tag_name]['type'] == 'tag':
								categories[tag.tag_name]['current_tracked'] += duration

				project_name = entry.get_project_name()

				client = entry.get_client()
				if client and client.client_name in categories and categories[client.client_name]['type'] == 'client':
					categories[client.client_name]['current_tracked'] += duration

			# This is needed because goals which have not started yet are removed from the categories list.
			if not project_name in categories.keys():
				continue

			# Do not add duration based on project name if we are in goals mode, looking at a non-project based goal.
			if view_type == 'goals' and 'type' in categories[project_name].keys() and categories[project_name]['type'] != 'project':
				continue
			else:
				categories[project_name][current_or_historic_tracked] += duration



# Get a ratio (0 to 1) describing how much a certain period of time (e.g. today/this week/month/year) is complete/over.
def get_period_completion_ratio(period, working_time_start=False, working_time_end=False, goal_days=[0,1,2,3,4,5,6]):
	now = helpers.get_current_datetime_in_user_timezone()
	
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

	today_weekday = now.weekday()

	if today_weekday not in goal_days:
		minutes_complete_today = 0


	minutes_in_a_day = (work_end_datetime - work_start_datetime).seconds/60
	if minutes_in_a_day == 0: # Fixing weird case of above line returning 0.
		minutes_in_a_day = 60*24



	#------ Now figuring out how much of the workday is complete.
	if period == 'day':
		completion_ratio = minutes_complete_today / minutes_in_a_day

	elif period == 'week':
		minutes_complete_this_week = goal_days_in_period('week', goal_days) * minutes_in_a_day + minutes_complete_today
		minutes_in_a_week = minutes_in_a_day * len(goal_days)

		completion_ratio = minutes_complete_this_week / minutes_in_a_week

	elif period == 'month':
		minutes_complete_this_month = goal_days_in_period('month', goal_days) * minutes_in_a_day + minutes_complete_today
		days_in_this_month = goal_days_in_period('month', goal_days, completed_only=False)
		minutes_in_this_month = minutes_in_a_day * days_in_this_month

		completion_ratio = minutes_complete_this_month / minutes_in_this_month

	elif period == 'year':
		minutes_complete_this_year = goal_days_in_period('year', goal_days, completed_only=False) * minutes_in_a_day + minutes_complete_today
		days_this_year = goal_days_in_period('year', goal_days, completed_only=False)
		minutes_in_this_year = days_this_year * minutes_in_a_day

		completion_ratio = minutes_complete_this_year / minutes_in_this_year

	return completion_ratio

# Get the number of goal days in a given period. Goal days are defined by the weekdays listed in goal_days.
# completed_only causes the function to only consider days which have been completed.
def goal_days_in_period(period_name, goal_days, completed_only=True):
	now = datetime.now()

	goal_days_completed = 0

	if period_name == 'week':
		period_start = now - timedelta(days=now.weekday())
	if period_name == 'month':
		period_start = now - timedelta(days=now.day-1)
	if period_name == 'year':
		period_start = now - timedelta(days=now.timetuple().tm_yday-1)

	if not completed_only:
		if period_name == 'day':
			if now.weekday() in goal_days:
				return 1
			else:
				return 0

		elif period_name == 'week':
			period_end = now + timedelta(days=6-now.weekday())
		elif period_name == 'month':
			days_in_this_month = calendar.monthrange(now.year, now.month)[1]
			days_remaining = days_in_this_month - now.day + 1
			period_end = now + timedelta(days_remaining)
		elif period_name == 'year':
			period_end = now.replace(month=12, day=31)
	else:
		period_end = now

	while period_start < period_end:
		if period_start.weekday() in goal_days:
			goal_days_completed += 1

		period_start += timedelta(days=1)

	return goal_days_completed


# Calculate how the ratio of time tracked in a current vs historic period. Return as a list.
def calculate_ratios(category_data, view_type, goals=[], hide_completed=False):
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

		# In not in goals mode, don't include projecst with no recent/historic tracked time.
		if view_type != 'goals' and current_tracked == 0 and historic_tracked == 0:
			continue

		if view_type == 'goals':
			if project_name not in goals.keys():
				continue # Don't include projects which don't have goals.

			if hide_completed and ratio >= 1:
				continue # Don't include completed goals if 'Hide completed' is checked.
		
		response.append(category_data[project_name])

	return response

def get_comparison_goals():
	goals = []

	with open ('goals.csv', 'r') as file:
		reader = csv.DictReader(file)
		for row in reader:
			goals.append(row)

	return goals

def get_now_in_user_timezone():
	user_timezone = helpers.get_current_timezone()
	now = datetime.utcnow().replace(tzinfo=pytz.utc)
	return now.astimezone(user_timezone)

# Returns a dictionary containing the start and end datetimes for the current and historic periods.
def get_comparison_start_end(period_type, number_of_current_days, number_of_historic_days, calendar_period, live_mode):
	now = get_now_in_user_timezone()

	if period_type == 'custom':
		current_start, historic_start, historic_end = get_custom_start_end()

	else:
		current_start  = get_current_start(calendar_period)
		historic_start = get_historic_start(calendar_period, current_start)
		historic_end   = get_historic_end(calendar_period, historic_start, live_mode)

	return {
		'current_start': current_start,
		'current_end': now,
		'historic_start': historic_start,
		'historic_end': historic_end
	}

def get_custom_start_end():
	now = get_now_in_user_timezone()

	number_of_current_days 	= int(request.json.get('timeframe'))
	number_of_historic_days = int(request.json.get('datarange'))

	current_start = (now - timedelta(days=number_of_current_days-1)).replace(hour=0, minute=0, second=0)

	historic_end = current_start - timedelta(seconds=1)
	historic_start = (historic_end - timedelta(days=number_of_historic_days-1)).replace(hour=0, minute=0, second=0)

	return current_start, historic_start, historic_end


# Returns the start of the current period, based on the calendar_period argument.
# For example, if calendar_period is 'day', this will return the start of today.
# Or if calendar_period is 'week', this will return the start of the current week.
def get_current_start(calendar_period):
	now = get_now_in_user_timezone()

	today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
	now.replace(hour=0, minute=0, second=0, microsecond=0)

	if calendar_period == 'day':
		return today_start

	if calendar_period == 'week':
		current_start = today_start - timedelta(days=today_start.weekday())
		return current_start
	
	if calendar_period in ['month', 'month-of-year']:
		return today_start.replace(day=1)
	
	if calendar_period == 'quarter':
		current_quarter = (today_start.month-1)//3 # First quarter is 0
		first_month_of_current_quarter = 1 + current_quarter*3
		return today_start.replace(month=first_month_of_current_quarter, day=1)

	if calendar_period == 'half-year':
		current_half = (today_start.month-1)//6 # First half is 0
		first_month_of_current_half = 1 + current_half*6
		return today_start.replace(month=first_month_of_current_half, day=1)
	
	if calendar_period == 'year':
		return today_start.replace(month=1, day=1)
	
	raise ValueError('Invalid calendar period: ' + calendar_period)

def get_historic_start(calendar_period, current_start):
	if get_goals_mode():
		return None

	now = get_now_in_user_timezone()

	today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

	if calendar_period == 'day':
		return current_start - timedelta(days=1)

	if calendar_period == 'week':
		return current_start - timedelta(days=7)
	
	if calendar_period == 'month':
		return (current_start - timedelta(days=1)).replace(day=1)

	if calendar_period == 'quarter':
		current_quarter = (now.month-1)//3 # First quarter is 0
		previous_quarter = (current_quarter - 1) if current_quarter > 0 else 3
		first_month_of_previous_quarter = 1 + previous_quarter*3
		historic_year = now.year if current_quarter > previous_quarter else now.year - 1

		return today_start.replace(year=historic_year, month=first_month_of_previous_quarter, day=1)

	if calendar_period == 'half-year':
		current_half = (now.month-1)//6 # First half is 0
		previous_half = 0 if (current_half == 1) else 1
		first_month_of_previous_half = 1 + previous_half*6
		historic_year = now.year if current_half > previous_half else now.year - 1

		return today_start.replace(year=historic_year, month=first_month_of_previous_half, day=1)

	if calendar_period == 'year':
		return today_start.replace(year=now.year-1, month=1, day=1)

	if calendar_period == 'month-of-year':
		return current_start.replace(year=now.year-1)

	raise ValueError('Invalid calendar period: ' + calendar_period)	

def get_historic_end(calendar_period, historic_start, live_mode):
	if get_goals_mode():
		return None
	
	now = get_now_in_user_timezone()

	if calendar_period == 'day':
		today_end   = now.replace(hour=23, minute=59, second=59)
		
		if live_mode:
			return now - timedelta(days=1)
		else:
			return today_end - timedelta(days=1)
	
	if calendar_period == 'week':
		if live_mode:
			return now - timedelta(days=7)
		else:
			return historic_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
			
	if calendar_period == 'month':
		previous_month = (now.month-1) or 12
		historic_year = now.year if previous_month != 12 else now.year - 1

		last_day_of_previous_month = calendar.monthrange(historic_year, previous_month)[1]

		if live_mode:
			return historic_start.replace(day=min(now.day, last_day_of_previous_month), hour=now.hour, minute=now.minute)
		else:
			return historic_start.replace(day=last_day_of_previous_month, hour=23, minute=59, second=59)

	if calendar_period == 'quarter':
		historic_year, first_month_of_previous_quarter = get_historic_year_and_first_division_month(calendar_period)

		if live_mode:
			month_of_current_quarter = (now.month-1) % 3  # First month of quarter is 0
			equivalent_month_of_previous_quarter = first_month_of_previous_quarter + month_of_current_quarter
			last_day_of_equivalent_month = calendar.monthrange(historic_year, equivalent_month_of_previous_quarter)[1]
			
			return historic_start.replace(
				year = historic_year,
				month = equivalent_month_of_previous_quarter,
				day = min(now.day, last_day_of_equivalent_month),
				hour = now.hour,
				minute = now.minute
			)
		else:
			last_month_of_previous_quarter = first_month_of_previous_quarter + 2
			last_day_of_previous_quarter = calendar.monthrange(historic_year, last_month_of_previous_quarter)[1]
	
			return historic_start.replace(
				year = historic_year,
				month = last_month_of_previous_quarter,
				day = last_day_of_previous_quarter,
				hour = 23,
				minute = 59
			)

	if calendar_period == 'half-year':
		historic_year, first_month_of_previous_half = get_historic_year_and_first_division_month(calendar_period)

		if live_mode:
			month_of_current_half = (now.month-1) % 6 # First month of half is 0
			equivalent_month_of_previous_half = first_month_of_previous_half + month_of_current_half
			last_day_of_equivalent_half = calendar.monthrange(historic_year, equivalent_month_of_previous_half)[1]

			return historic_start.replace(
				year = historic_year,
				month = equivalent_month_of_previous_half,
				day = min(now.day, last_day_of_equivalent_half),
				hour = now.hour,
				minute = now.minute
			)
		else:
			last_month_of_previous_half = first_month_of_previous_half + 5
			last_day_of_previous_half = calendar.monthrange(historic_year, last_month_of_previous_half)[1]

			return historic_start.replace(
				year = historic_year,
				month = last_month_of_previous_half,
				day = last_day_of_previous_half,
				hour = 23,
				minute = 59
			)

	if calendar_period == 'year':
		today_start = now.replace(hour=0, minute=0, second=0)

		if live_mode:
			historic_day = now.day
			if historic_day == 29 and now.month == 2:
				historic_day = 28 # Leap years.

			return today_start.replace(
				year = now.year - 1,
				month = now.month,
				day = historic_day,
				hour = now.hour,
				minute = now.minute
			)
		else:
			return today_start.replace(
				year = now.year - 1,
				month = 12,
				day = 31,
				hour = 23,
				minute = 59
			)

	if calendar_period == 'month-of-year':
		last_day_of_month = calendar.monthrange(now.year, now.month)[1]	

		if live_mode:
			return historic_start.replace(day=now.day, hour=now.hour, minute=now.minute)
		else:
			return historic_start.replace(day=last_day_of_month, hour=23, minute=59, second=59)

	raise Exception('Invalid calendar period: ' + calendar_period)

# Returns the year and first month of the historic period, based on the calendar_period argument.
# "division" means quarter or half-year.
# For example, if calendar_period is 'quarter', this will return the year and first month of the previous quarter.
def get_historic_year_and_first_division_month(calendar_period):
	if calendar_period not in ['quarter', 'half-year']:
		raise ValueError('Invalid calendar period: ' + calendar_period)

	# Number of months in a division.
	num_months = 3 if calendar_period == 'quarter' else 6
	
	# Number of divisions in a year.
	max_division = 3 if calendar_period == 'quarter' else 1
	
	now = get_now_in_user_timezone()

	current_division = (now.month-1) // num_months # First division is 0
	previous_division = (current_division - 1) if current_division > 0 else max_division
	
	historic_year = now.year if current_division > previous_division else now.year - 1
	first_month_of_previous_division = 1 + previous_division * num_months

	return historic_year, first_month_of_previous_division


# Calculate the average time spent on various projects in a given historic period. (Or, assign goal time if in goals mode)
def assign_historic_time(category_data, view_type, historic_days, current_days, goals_projects=[], goals=[]):
	for project_name in category_data:

		seconds = category_data[project_name]['historic_tracked']
		
		if view_type == 'custom':
			number_of_historic_days = len(historic_days)
			number_of_current_days = len(current_days)

			if number_of_historic_days == 0:
				historic_time = 0
			else:
				historic_time = (seconds/number_of_historic_days)*number_of_current_days

		elif view_type == 'calendar':
			historic_time = seconds # When using calendar mode, we aren't actually taking an average, but just the amount of time tracked in that period.
		elif view_type == 'goals':
			if not project_name in goals_projects: # Ignore projects which don't have goals.
				continue
			historic_time = goals[project_name]
		
		# TODO: Calling the value 'average' is because the system originally only worked with averages.
		# The name should be changed. (Maybe 'value'?)
		category_data[project_name]['average'] = historic_time

@bp.route("/comparison/set_default", methods=['POST'])
def set_default():
	# print('------------set_default---------------')
	data = request.json

	session['comparison_defaults'] = data

	# print(data)

	return jsonify(data)

def get_comparison_defaults():
	# print('------------get_comparison_defaults---------------')
	# print(session)

	if 'comparison_defaults' in session.keys():
		return session['comparison_defaults']

	return False

def hide_project_comparisons(project_data):
	projects = helpers.get_all_projects_from_database()

	for project in projects:
		del project_data[project.project_name]


# Distribute the project time among their parent clients, and add it to the project_data dictionary.
def add_client_comparisons(project_data):
	all_clients = helpers.get_all_clients_from_database()

	for client in all_clients:
		current_tracked = 0
		historic_tracked = 0

		for project in client.projects:
			if project.project_name in project_data:
				current_tracked += project_data[project.project_name]['current_tracked']
				historic_tracked += project_data[project.project_name]['historic_tracked']


		client_info = {
			'average': 0,
			'color': helpers.get_client_color(client.client_name),
			# 'color': 'red',
			'current_tracked': current_tracked,
			'historic_tracked': historic_tracked,
			'name': client.client_name,
			'type': 'client'
		}

		project_data[client.client_name] = client_info