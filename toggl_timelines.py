from datetime import datetime, date, time, timedelta
import calendar
import csv
import pytz
import math

import toggl_timelines_config as config

from flask import Flask, url_for, render_template, request, make_response, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from TogglPy import Toggl

import toggl_timelines_helpers as helpers

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///toggl-timelines.db'

# -------------------------------------------------------------------------------------
# ------------------------------------Database-----------------------------------------
# -------------------------------------------------------------------------------------

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
	#project = db.Column(db.String(50))

	project_id = db.Column(db.Integer, db.ForeignKey('project.id'))

	client = db.Column(db.String(50))
	project_hex_color = db.Column(db.String(7))
	tags = db.relationship('Tag', secondary=tags, backref=db.backref('entries', lazy=True), lazy='select')
	user_id = db.Column(db.Integer)
	utc_offset = db.Column(db.Integer)

	def __repr__(self):
		return "<Entry (Description: " + self.description + ") (Start: " + str(self.start) + ") (End: " + str(self.end) + ") (Duration: " + str(self.dur) + ") (ID: " + str(self.id) + ")"

	def get_tooltip(self):
		start_time = self.start.strftime('%H:%M')
		end_time = self.end.strftime('%H:%M')

		project = self.get_project_name()
		description = self.description
		duration = helpers.format_duration(self.dur)
		client = self.client

		return '<b>{0}</b>: {1}<br/>Client: {2}<br/>{3}-{4}<br/>{5}'.format(project, description, client, start_time, end_time, duration)

	def get_day_percentage(self):
		duration = self.dur/1000
		seconds_in_day = 86400

		return (duration/seconds_in_day)*100

	def get_start_percentage(self):
		seconds_since_midnight = (self.start - self.start.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

		return (seconds_since_midnight / 86400) * 100

	def get_client_hex_color(self):
		hex_color_config = config.client_colors

		if self.client in hex_color_config.keys():
			return hex_color_config[self.client]
		else:
			return '#a6a6a6'

	def get_project_color(self):
		project = self.project

		if project:
			return project.project_hex_color
		else:
			return '#C8C8C8'

	def get_project_name(self):
		project = self.project

		if project:
			return project.project_name
		else:
			return 'No Project'

	def get_raw_start_time(self):
		start = self.start
		utc_offset = self.utc_offset

		return start - timedelta(hours = utc_offset)


class Project(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	project_name = db.Column(db.String(50))
	project_hex_color = db.Column(db.String(7))
	entries = db.relationship('Entry', backref='project')



class Tag(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	tag_name = db.Column(db.String(50))

	def __repr__(self):
		return "<Tag Name: " + self.tag_name + ")"

#------------- END OF DATABASE CODE -----------------------------



# -------------------------------------------------------------------------------------
# ------------------------------------Common Purpose Functions-------------------------
# -------------------------------------------------------------------------------------

# Update the local database from Toggl's API
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
			db.session.commit() # Not sure whether we need this.

		start = helpers.remove_colon_from_timezone(entry['start'])
		start = helpers.timestamp_to_datetime(start)
				
		toggl_utc_offset = int(start.utcoffset().total_seconds()/(60*60))
		# Toggl's values are adjusted based on whatever the current account timezone is.
		# toggl_utc_offset is the number of hours we need to SUBTRACT from the time to get it into UTC.

		start = start - timedelta(hours = toggl_utc_offset)

		end = helpers.remove_colon_from_timezone(entry['end'])
		end = helpers.timestamp_to_datetime(end)
		end = end - timedelta(hours = toggl_utc_offset)


		if entry['project']:
			db_project = Project.query.filter_by(id=entry['pid']).first()
			if not db_project:
				db_project = Project(
					id = entry['pid'],
					project_name = entry['project'],
					project_hex_color = entry['project_hex_color']
				)

				db.session.add(db_project)
		else:
			db_project = False

		db_entry = Entry(
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

def get_entries_from_database(start=False, end=False, projects=False, clients=False, tags=False, description=False):
	
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
		print('Filter description!')
		#query = query.filter(func.lower(Entry.description) == description.lower())
		query = query.filter(func.lower(Entry.description).contains(description.lower()))

	
	#if tags:
		#query = query.filter(Entry.tags.in_(clients))
		
	entries = query.order_by(Entry.start).all()

	apply_utc_offsets(entries)

	entries = split_entries_over_midnight(entries)


	return entries

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
			

			second_half = Entry(
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

# Return a list of days with entries.
def get_days_list(loading_additional_days = False, amount = 8, start = False, end = False):
	db_entries = get_entries_from_database(start, end)

	days_list = sort_entries_by_day(db_entries)
	
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

#------------- END OF COMMON PURPOSE FUNCTIONS -----------------------------


# -------------------------------------------------------------------------------------
# ------------------------------------Home Page----------------------------------
# -------------------------------------------------------------------------------------

@app.route('/')
def home_page():
	response = make_response(render_template('home.html'))

	return response

# -------------------------------------------------------------------------------------
# ------------------------------------Timelines Page----------------------------------
# -------------------------------------------------------------------------------------

initial_timelines_page_load_amount = 7

@app.route('/timelines')
def timelines_page():
	update_database(3)

	start = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=initial_timelines_page_load_amount)

	displayed_days = get_days_list(start=start)

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

	start_days_ago = request.json.get('start_days_ago')
	end_days_ago = request.json.get('end_days_ago')

	if reloading:
		update_database(1)

		start = datetime.now().replace(hour=0, minute=0, second=0)
		end = False
		
	else:
		
		if start_days_ago:
			start = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=start_days_ago)
		else:
			start = False			

		end = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=end_days_ago)

	displayed_days = get_days_list(start=start, end=end)

	page_data = {
		'days': displayed_days
	}

	return jsonify(render_template('day.html', data=page_data))

#------------- END OF TIMELINES PAGE -----------------------------




# -------------------------------------------------------------------------------------
# ------------------------------------Comparison Page----------------------------------
# -------------------------------------------------------------------------------------

@app.route('/comparison')
def comparison_page():
	update_database(3)

	response = make_response(render_template('comparison.html'))

	return response

@app.route('/comparison_data', methods=['POST'])
def comparison_data():
	reload_data = request.json.get('reload')

	if reload_data:
		update_database(1)

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

			goal_period = goal['time_period']
			goal_value_in_seconds = int(goal['goal_value']) * 60

			seconds_in_day = 86400
			now = datetime.now()

			seconds = {
				'day': seconds_in_day,
				'week': seconds_in_day * 7,
				'month': seconds_in_day * calendar.monthrange(now.year, now.month)[1],
				'year': seconds_in_day * (366 if (calendar.isleap(now.year)) else 365)
			}

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

	current_days = get_days_list(
		start=start_end_values['current_start'],
		end=start_end_values['current_end'],
		amount = False
	)


	if period_type != "goals": # Don't need to do historic days work if we're in goals mode.

		historic_days=get_days_list(
			start=start_end_values['historic_start'],
			end=start_end_values['historic_end'],
			amount = False
		)

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
		for entry in entries:
	
			if entry.project in (None, 'No Project'):
				continue

			weekday = str(entry.start.weekday())
			if weekday not in weekdays:
				continue

			project_name = entry.get_project_name()

			if historic and live_mode and day == days[0] and entry == entries[-1]: # If this is the most recent historic entry...
				#now = helpers.get_current_datetime_in_user_timezone()
				now = datetime.utcnow()
				
				entry_mid = entry.get_raw_start_time().replace(hour=now.hour, minute=now.minute)
				entry_start = entry.get_raw_start_time()
				# Here we need to deal with the raw UTC time.
				# The reason is that we don't know what time zone the user was in at the historic period. Can't assume it's the same as now.
				# So we compare things in UTC.

				time_difference = entry_mid - entry_start
				duration = time_difference.seconds #...Find duration based on how much of entry is complete.
			else:
				duration = entry.dur/1000

			if not historic and view_type == 'goals':
				tags = entry.tags
				if tags:
					for tag in tags:
						if tag.tag_name in categories:
							categories[tag.tag_name]['current_tracked'] += duration

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

# Calculate how the ratio of time tracked in a current vs historic period. Return as a list.
def calculate_ratios(category_data, view_type, goals=[]):
	response = []
	for project_name in category_data:
		
		current_tracked = category_data[project_name]['current_tracked']

		average = category_data[project_name]['average']

		category_data[project_name]['difference'] = current_tracked - average

		if average == 0:
			ratio = 100
		else:
			ratio = current_tracked/average

		category_data[project_name]['ratio'] = ratio

		if current_tracked > 0 or view_type == 'goals': # Don't include projects with no recently tracked time.
			
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

#------------- END OF COMPARISON PAGE -----------------------------



# -------------------------------------------------------------------------------------
# ------------------------------------Frequency Page-----------------------------------
# -------------------------------------------------------------------------------------

@app.route('/frequency')
def frequency_page():
	update_database(1)

	projects = get_project_data()

	page_data = {
		'projects': projects
	}

	response = make_response(render_template('frequency.html', data=page_data))

	return response

@app.route('/frequency_data', methods=['POST'])
def frequency_data():
	submission_data = request.json

	data = []

	for line in submission_data:

		if isinstance(line['projects'], str):
			line['projects'] = [line['projects']]

		start_datetime = datetime.strptime(line['start'], '%Y-%m-%d')
		end_datetime = datetime.strptime(line['end'], '%Y-%m-%d')
		print(line['description'])
	
		entries = get_entries_from_database(
			start=start_datetime,
			end=end_datetime,
			projects=line['projects'],
			description=line['description']
		)

		day_minutes_list = get_day_minutes_list()

		for entry in entries:
			duration_minutes = math.ceil(entry.dur / 60000)
			target_minute = get_minute_of_day(entry.start)

			# Minute 1440 does not exist.
			if target_minute >= 1440:
				target_minute = 0

			i = 0
			while i <= duration_minutes:
				day_minutes_list[target_minute] += 1
				target_minute += 1

				if target_minute >= 1440:
					target_minute = 0

				i += 1

		# Semi-temporary fix because we end up getting a lot of additional minutes tracked at minute 0.
		day_minutes_list[0] = day_minutes_list[1439]

		if submission_data[0]['y_axis_type'] == 'relative':
			period_duration = end_datetime - start_datetime
			day_minutes_list = [i / period_duration.days for i in day_minutes_list]


		data.append({
			'line_data': line,
			'minutes': day_minutes_list
		})

	return jsonify(data)

@app.route('/new_frequency_line', methods=['POST'])
def new_frequency_line():
	unsorted_projects = get_project_data()

	project_names_sorted = sorted(unsorted_projects.keys(), key=lambda x:x.lower())

	sorted_project_data = {}

	for project_name in project_names_sorted:
		sorted_project_data[project_name] = unsorted_projects[project_name]

	page_data = {
		'projects': sorted_project_data
	}

	return jsonify(render_template('frequency_line_controls.html', data=page_data))


# Return a dictionary with minutes from 0 to 1440, each with a value of 0.
def get_day_minutes_list():
	return [0] * 1440

def get_minute_of_day(dt):
	hour = dt.hour
	minute = dt.minute

	minute_of_day = 60*hour + minute

	return minute_of_day

#------------- END OF FREQUENCY PAGE -----------------------------



# -----------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------------------------

app.run(host='0.0.0.0', port=config.port, debug=True)