from datetime import datetime, date, time, timedelta
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

class Entry(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	description = db.Column(db.String(200))
	start = db.Column(db.DateTime(timezone=True))
	end = db.Column(db.DateTime(timezone=True))
	dur = db.Column(db.Integer)
	project = db.Column(db.String(50))
	client = db.Column(db.String(50))
	project_hex_color = db.Column(db.String(7))
	tags = db.Column(db.String(200))
	user_id = db.Column(db.Integer)
	utc_offset = db.Column(db.Integer)
	"""
	def __repr__(self):
		return f"Entry('{self.id}', '{self.description}', '{self.start}', '{self.end}', '{self.dur}', '{self.project}', '{self.client}', '{self.project_hex_color}', '{self.user_id}',)"
	"""


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

@app.route('/load_more')
def load_more():
	displayed_days = get_days_list(True)
	
	page_data = {
		'days': displayed_days
	}

	return jsonify(render_template('day.html', data=page_data))







@app.route('/comparison')
def averages_page():
	update_database(3)

	response = make_response(render_template('comparison.html'))

	return response



@app.route('/comparison_data')
def comparison_data():
	historic_projects = {}

	number_of_now_days = 1

	now_days = get_days_list(False, number_of_now_days)

	historic_days = get_days_list(True, number_of_now_days)

	number_of_historic_days = len(historic_days)

	project_colors = {'None': '#C8C8C8'}


	for day in historic_days:
		entries = day['entries']
		for entry in entries:
			if not 'project' in entry.keys():
				continue

			project = entry['project']
			duration = entry['dur']/1000

			project_colors[project] = entry['project_hex_color']

			if not project in historic_projects.keys():
				historic_projects[project] = 0

			historic_projects[project] += duration

	for project in historic_projects:
		seconds = historic_projects[project]
		average = seconds/number_of_historic_days

		historic_projects[project] = average
		#This now contains the average seconds per day of each project

	
	now_projects = dict.fromkeys(historic_projects.keys(),0)


	for day in now_days:
		entries = day['entries']
		for entry in entries:
			if not 'project' in entry.keys():
				continue

			project = entry['project']
			duration = entry['dur']/1000

			if not project in now_projects.keys():
				now_projects[project] = 0

			now_projects[project] += duration


	current_comparison = {}

	for project in historic_projects:
		average_seconds = historic_projects[project]
		current_seconds = now_projects[project]

		current_comparison[project] = current_seconds/average_seconds

	current_comparison['None'] = current_comparison.pop(None) #Fixing problems caused by 'None' entry.


	current_comparison.pop('Self') # Temporarily removing this category.

	prepared_data = []

	for project, time in current_comparison.items():
		prepared_data.append({
			'name': project,
			'value' : time,
			'color': project_colors[project]
			})

	return jsonify(prepared_data)








def get_days_list(loading_additional_days = False, amount = 8):
	db_entries = get_entries_from_database()
	days = sort_entries_by_day(db_entries)
	
	days_list = []
	for day in days.values():
		days_list.append(day)

	days_list.reverse()

	#return days_list[:1]

	if loading_additional_days:
		return days_list[amount:]
	else:
		return days_list[:amount]

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

	db.session.commit()

	return entries

def delete_days_from_database(start_days_ago, end_days_ago=0):
	start = datetime.today() - timedelta(days=start_days_ago)
	end   = datetime.today() - timedelta(days=end_days_ago)

	db_entries = Entry.query.filter(Entry.start <= end).filter(Entry.start >= start)

	for entry in db_entries:
		db.session.delete(entry)

	db.session.commit()

def fill_untracked_time(entries, target_time):
	completed_entries = []

	target_time = entries[0].start.replace(hour=0, minute=0, second=0)

	for entry in entries:
		entry = entry.__dict__

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

def get_entries_from_database(start = False):
	if not start:
		start = datetime.today() - timedelta(days=365*10) # Ten years ago
		start = start.replace(microsecond=0).isoformat()

	
	entries = Entry.query.order_by(Entry.start).all()
	#entries = Entry.query.order_by(Entry.start).limit(300).all() # Uncomment for faster load times during development

	completed_entries = fill_untracked_time(entries, start)

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
	current['tags'] = '' # We get no tags info from this request.
	current['end'] = end_string
	current['project_hex_color'] = '#C8C8C8'

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

#app.run(host='0.0.0.0', port=config.port)