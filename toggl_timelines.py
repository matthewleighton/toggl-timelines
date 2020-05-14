from datetime import datetime, date, time, timedelta
import calendar
import csv
import pytz

import toggl_timelines_config as config

from flask import Flask, url_for, render_template, request, make_response, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from TogglPy import Toggl

import toggl_timelines_helpers as helpers

app = Flask(__name__)
initial_load_number = 8


app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///toggl-timelines.db'

db = SQLAlchemy(app)

tags = db.Table('tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True),
    db.Column('entry_id', db.Integer, db.ForeignKey('entry.id'), primary_key=True)
)

class Entry(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	description = db.Column(db.String(200))
	start = db.Column(db.DateTime(timezone=True))
	end = db.Column(db.DateTime(timezone=True))
	dur = db.Column(db.Integer)
	project = db.Column(db.String(50))
	client = db.Column(db.String(50))
	project_hex_color = db.Column(db.String(7))
	tags = db.relationship('Tag', secondary=tags, backref=db.backref('entries', lazy=True), lazy='dynamic')
	user_id = db.Column(db.Integer)
	utc_offset = db.Column(db.Integer)

class Tag(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	tag_name = db.Column(db.String(50))



@app.route('/')
def home_page():
	update_database(3)

	displayed_days = get_days_list()

	heart = helpers.display_heart()

	page_data = {
		'days': displayed_days,
		'times': range(0, 24),
		'heart': heart
	}

	response = make_response(render_template('timelines.html', data=page_data))

	return response

@app.route('/load_more', methods=['GET', 'POST'])
def load_more():
	reloading = request.json.get('reload')

	if reloading:
		skip_first_days = False
		days = 1
		update_database(1)
	else:
		skip_first_days = True
		days = 8

	displayed_days = get_days_list(skip_first_days, days)

	page_data = {
		'days': displayed_days
	}

	return jsonify(render_template('day.html', data=page_data))


@app.route('/frequency')
def frequency_page():
	update_database(3)

	response = make_response(render_template('frequency.html'))

	return response




@app.route('/comparison')
def averages_page():
	update_database(3)

	response = make_response(render_template('comparison.html'))

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
					day = min(now.day, equivalent_month_of_previous_quarter),
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
					day = min(now.day, equivalent_month_of_previous_half),
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

	print('Current start: ' + str(current_start))
	print('Current end: ' + str(current_end))
	print('Historic start: ' + str(historic_start))
	print('Historic end: ' + str(historic_end))
	

	return {
		'current_start': current_start,
		'current_end': current_end,
		'historic_start': historic_start,
		'historic_end': historic_end
	}

@app.route('/comparison_data', methods=['POST'])
def comparison_data():
	reload_data = request.json.get('reload')

	if reload_data:
		update_database(1)

	live_mode_calendar = bool(request.json.get('live_mode_calendar'))

	number_of_current_days = int(request.json.get('timeframe'))
	number_of_historic_days = int(request.json.get('datarange'))
	target_weekdays = request.json.get('weekdays')

	period_type = request.json.get('period_type')

	project_data = helpers.get_project_data(comparison_mode=True)

	if period_type == 'goals':
		calendar_period = request.json.get('goals_period')
		live_mode_goals = request.json.get('live_mode_goals')

		goals_raw = get_comparison_goals()
		goals_projects = []
		goal_tags = []
		goals = {}

		for goal in goals_raw:
			goals_projects.append(goal['name'])
			goal_name = goal['name']

			if goal['type'] == 'tag':
				project_data[goal_name] = {
					'historic_tracked': 0,
					'current_tracked': 0,
					'average': 0,
					'name': goal_name
				}

			if goal['color']:
				project_data[goal_name]['color'] = goal['color']

			goal_period = goal['time_period']
			goal_value_in_seconds = int(goal['goal_value']) * 60

			day = 60*60*24
			now = datetime.now()

			seconds = {
				'day': day,
				'week': day * 7,
				'month': day * calendar.monthrange(now.year, now.month)[1],
				'year': day * (366 if (calendar.isleap(now.year)) else 365)
			}

			period_ratio 				= seconds[calendar_period] / seconds[goal_period]
			goal_seconds_in_view_period = period_ratio * goal_value_in_seconds

			if live_mode_goals: # If live mode, reduce the goal relative to how much of the period is over.
								# E.g. if we're halfway through a day, the daily goal is half.
				period_completion = helpers.get_period_completion_ratio(calendar_period, goal['working_time_start'], goal['working_time_end'])

				if period_completion == 0: # Don't show projects which have goals currently requiring 0 time.
										   # i.e. working hours haven't started.
					del project_data[goal['name']]

				goal_seconds_in_view_period = goal_seconds_in_view_period * period_completion

			goals.update( {goal['name']: goal_seconds_in_view_period })
	else:
		calendar_period = request.json.get('calendar_period')


	if type(target_weekdays) is not list:
		target_weekdays = [target_weekdays]

	start_end_values = get_comparison_start_end(period_type, number_of_current_days, number_of_historic_days, calendar_period, live_mode_calendar)

	current_days = get_days_list(
		start=start_end_values['current_start'],
		end=start_end_values['current_end'],
		amount = False
	)

	number_of_current_days = len(current_days)


	if period_type != "goals": # Don't need to do historic days work if we're in goals mode.

		historic_days=get_days_list(
			start=start_end_values['historic_start'],
			end=start_end_values['historic_end'],
			amount = False
		)

		number_of_historic_days = len(historic_days)

		#print('Historic Days: ')
		for day in historic_days:

			#print(day['date'])
			entries = day['entries']
			for entry in entries:
		
				if not 'project' in entry.keys() or entry['project'] == None:
					continue

				weekday = str(entry['start'].weekday())
				if weekday not in target_weekdays:
					continue

				project = entry['project']

				if day == historic_days[0] and entry == entries[-1]: # If this is the most recent historic entry...
					now = helpers.get_current_datetime_in_user_timezone()
					duration = (entry['start'].replace(hour=now.hour, minute=now.minute) - entry['start']).seconds #...Find duration based on how much of entry is complete.
				else:
					duration = entry['dur']/1000

				project_data[project]['historic_tracked'] += duration


	for project in project_data:

		seconds = project_data[project]['historic_tracked']
		
		if period_type == 'custom':
			average = (seconds/number_of_historic_days)*number_of_current_days	
		elif period_type == 'calendar':
			average = seconds # When using calendar mode, we aren't actually taking an average, but just the amount of time tracked in that period.
		elif period_type == 'goals':
			if not project in goals_projects: # Ignore projects which don't have goals.
				continue
			average = goals[project]
		
		project_data[project]['average'] = average
	
	#print('Current Days: ')
	for day in current_days:
		#print(day['date'])
		entries = day['entries']
		for entry in entries:

			if not 'project' in entry.keys() or entry['project'] in (None, 'No Project'): # Skips untracked time
				continue

			weekday = str(entry['start'].weekday())
			if weekday not in target_weekdays:
				continue

			project = entry['project']
			duration = entry['dur']/1000
			color = entry['project_hex_color']

			project_data[project]['current_tracked'] += duration

			tags = entry['tags']
			if period_type == 'goals' and tags:

				for tag in tags:
					if tag in project_data:
						project_data[tag]['current_tracked'] += duration

	response = []
	for project in project_data:
		
		current_tracked = project_data[project]['current_tracked']

		average = project_data[project]['average']

		project_data[project]['difference'] = current_tracked - average

		if average == 0:
			ratio = 100
		else:
			ratio = current_tracked/average

		project_data[project]['ratio'] = ratio

		if current_tracked > 0 or period_type == 'goals': # Don't include projects with no recently tracked time.
			
			if period_type == 'goals' and project not in goals.keys():
				continue # Don't include projects which don't have goals.

			response.append(project_data[project])


	sort_type = 'ratio' # difference, ratio
	sorted_response = sorted(response, key=lambda k: k[sort_type])

	"""
	for project in sorted_response:
		print(project)
		print('')
	"""

	return jsonify(sorted_response)



# -----------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------


def get_days_list(loading_additional_days = False, amount = 8, start = False, end = False):
	db_entries = get_entries_from_database(start, end)
	days = sort_entries_by_day(db_entries)
	
	days_list = []
	for day in days.values():
		days_list.append(day)

	days_list.reverse()

	if amount:
		if loading_additional_days:
			return days_list[amount:]
		else:
			return days_list[:amount]
	else:
		return days_list


def update_database(start_days_ago, end_days_ago=0):	
	start = datetime.today() - timedelta(days=start_days_ago)
	end   = datetime.today() - timedelta(days=end_days_ago)

	request_data = {
	    'workspace_id': config.workspace_id,
	    'since': start,
	    'until': end,
	}

	toggl = Toggl()
	toggl.setAPIKey(config.api_key)

	entries = toggl.getDetailedReportPages(request_data)['data']
	
	currently_tracking = get_currently_tracking()
	if currently_tracking:
		entries.append(currently_tracking)
	
	delete_days_from_database(start_days_ago, end_days_ago)

	for entry in entries:

		location_utc_offset = helpers.get_toggl_entry_utc_offset(entry)
		# This is the utc offset of the location I was in when the entry was recorded.
		
		entry_id = entry['id']
		
		existing_entry = Entry.query.filter_by(id=entry_id).first()
		
		if existing_entry:
			db.session.delete(existing_entry)

		start = helpers.remove_colon_from_timezone(entry['start'])
		start = helpers.timestamp_to_datetime(start)
				
		toggl_utc_offset = int(start.utcoffset().total_seconds()/(60*60))
		# Toggl's values are adjusted based on whatever the current account timezone is.
		# toggl_utc_offset is the number of hours we need to SUBTRACT from the time to get it into UTC.

		start = start - timedelta(hours = toggl_utc_offset)

		end = helpers.remove_colon_from_timezone(entry['end'])
		end = helpers.timestamp_to_datetime(end)
		end = end - timedelta(hours = toggl_utc_offset)

		db_entry = Entry(
			id 				  = entry['id'],
			description 	  = entry['description'],
			start 			  = start,
			end 			  = end,
			dur 			  = entry['dur'],
			project 		  = entry['project'],
			client 			  = entry['client'],
			project_hex_color = entry['project_hex_color'],
			utc_offset 		  = location_utc_offset,
			user_id 		  = entry['uid']
		)
		db.session.add(db_entry)

		tags = entry['tags']
		for tag_name in tags:
			db_tag = Tag.query.filter_by(tag_name=tag_name).first()

			if not db_tag:
				db_tag = Tag(
					tag_name = tag_name
				)
				db.session.add(db_tag)

			db_tag.entries.append(db_entry)
				
	db.session.commit()

	return entries

def delete_days_from_database(start_days_ago, end_days_ago=0):
	start = datetime.today() - timedelta(days=start_days_ago)
	end   = datetime.today() - timedelta(days=end_days_ago)

	db_entries = Entry.query.filter(Entry.start <= end).filter(Entry.start >= start)

	for entry in db_entries:
		db.session.delete(entry)

	db.session.commit()

def fill_untracked_time(entries):
	completed_entries = []

	target_time = entries[0].start.replace(hour=0, minute=0, second=0)

	for entry in entries:
		

		tags = []
		
		for tag in entry.tags:
			tags.append(tag.tag_name)


		#print(tags)

		entry = entry.__dict__

		entry['tags'] = tags


		entry.pop('_sa_instance_state', None)

		
		entry['start'] = entry['start'] + timedelta(hours=entry['utc_offset'])
		entry['end'] = entry['end'] + timedelta(hours=entry['utc_offset'])

		# ----------------------------------Untracked Time---------------------
		if target_time < entry['start']:

			untracked_time = helpers.get_untracked_time(target_time, entry)

			for period in untracked_time:
				completed_entries.append(period)
			
		entry_halves = helpers.split_entry_over_midnight(entry)

		for entry_half in entry_halves:
			
			entry_half['tooltip'] = helpers.get_entry_tooltip(entry_half)
			entry_half['client_hex_color'] = helpers.get_client_hex_color(entry['client'])

			completed_entries.append(entry_half)
			
		target_time = entry['end']


	# ----------------------------Adding percentages-------------------	
	for entry in completed_entries:
		entry_seconds = entry['dur']/1000
		seconds_in_day = 60*60*24

		entry['day_percentage'] = (entry_seconds/seconds_in_day)*100

		if not entry.get('class'):
			entry['class'] = 'tracked_time'

	return completed_entries

def get_entries_from_database(start = False, end = False):
	
	# Times are stored in database as UTC. So we need to convert the request times to UTC.
	if start:
		#if start.tzinfo is not None and start.tzinfo.utcoffset(start) is not None:
		start = start.astimezone(pytz.utc)

	if end:
		#if end.tzinfo is not None and end.tzinfo.utcoffset(end) is not None:
		end = end.astimezone(pytz.utc)

	if start and end:
		entries = Entry.query.filter(Entry.start >= start).filter(Entry.start <= end).order_by(Entry.start).all()
	elif start:
		entries = Entry.query.filter(Entry.start >= start).order_by(Entry.start).order_by(Entry.start).all()
	elif end:
		entries = Entry.query.filter(Entry.start <= end).order_by(Entry.start).order_by(Entry.start).all()
	else:
		entries = Entry.query.order_by(Entry.start).all()

	completed_entries = fill_untracked_time(entries)

	return completed_entries

# Get the currently tracking entry, and add/format the required data so it matches the historic entries.
def get_currently_tracking():
	toggl = Toggl()
	toggl.setAPIKey(config.api_key)

	user_data = toggl.request("https://www.toggl.com/api/v8/me?with_related_data=true")
	projects = user_data['data']['projects']
	clients = user_data['data']['clients']

	current = toggl.currentRunningTimeEntry()

	if not current:
		return False

	start_string = helpers.remove_colon_from_timezone(current['start'])
	start = helpers.timestamp_to_datetime(start_string).replace(tzinfo=None)
	utc_now = datetime.utcnow()
	difference = utc_now - start
	seconds = difference.seconds
	milliseconds = seconds*1000

	start_datetime = helpers.timestamp_to_datetime(current['start'])
	end_datetime = start_datetime + timedelta(seconds=seconds)
	end_string = helpers.datetime_to_timestamp(end_datetime)

	current['dur'] = milliseconds
	current['end'] = end_string
	current['project_hex_color'] = '#C8C8C8'
	
	if 'tags' not in current:
		current['tags'] = []

	current['project'] = 'No Project'
	client_id = False

	if 'pid' in current:
		for project in projects:
			if project['id'] == current['pid']:
				current['project'] 			 = project['name']
				current['project_hex_color'] = project['hex_color']
				client_id = project['cid']
				break;

	for client in clients:
		if client['id'] == client_id:
			current['client'] = client['name']
			break

		current['client'] = 'None'

	if not 'description' in current:
		current['description'] = ''

	return current

def sort_entries_by_day(entries):
	sorted_by_day = {}

	for entry in entries:
		entry_date = entry['start'].strftime('%Y-%m-%d')
		
		if entry_date not in sorted_by_day:
			sorted_by_day[entry_date] = {
				'entries': [],
				'date': entry['start'].strftime('%a %d %b, %Y')
			}

		sorted_by_day[entry_date]['entries'].append(entry)

	return sorted_by_day

app.run(host='0.0.0.0', port=config.port, debug=True)