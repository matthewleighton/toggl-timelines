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
import math
from datetime import date, datetime, timedelta

from toggltimelines import db
from toggltimelines.timelines.models import Entry, Project
from toggltimelines import helpers

import pprint
pp = pprint.PrettyPrinter(indent=4)

weekdays = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']

bp = Blueprint("frequency", __name__)

@bp.route("/frequency")
def index():
	helpers.toggl_sync(days=2)

	projects = helpers.get_project_data()

	page_data = {
		'projects': projects
	}

	response = make_response(render_template('frequency/index.html', data=page_data))

	return response

@bp.route('/frequency/new_frequency_line', methods=['POST'])
def new_frequency_line():
	unsorted_projects = helpers.get_project_data()

	project_names_sorted = sorted(unsorted_projects.keys(), key=lambda x:x.lower())

	sorted_project_data = {}

	for project_name in project_names_sorted:
		sorted_project_data[project_name] = unsorted_projects[project_name]

	page_data = {
		'projects': sorted_project_data,
		'today_date': date.today()
	}

	return jsonify(render_template('frequency/frequency_line_controls.html', data=page_data))

date_formats = {
	'minutes': '%Y-%m-%d %H:%M',
	'days': '%Y-%m-%d',
	'weeks': '%W',
	'months': '%Y-%m'
}


@bp.route('/frequency/frequency_data', methods=['POST'])
def frequency_data():
	submission_data = request.json

	print(submission_data)

	data = []

	scope_type = submission_data[0]['scope_type']
	graph_type = submission_data[0]['graph_type']

	for line in submission_data:
		start_datetime = datetime.strptime(line['start'], '%Y-%m-%d')
		end_datetime = datetime.strptime(line['end'], '%Y-%m-%d')

		line_data_container = get_line_data_container(graph_type, scope_type, start_datetime, end_datetime)
		#pp.pprint(line_data_container)

		if isinstance(line['projects'], str):
			line['projects'] = [line['projects']]

		# TODO: Need to consider the timezones here.
		# The request will be made purely in UTC, but it should be first converted from the user's timezone? 
		entries = helpers.get_db_entries(
			start_datetime,
			end_datetime,
			projects=line['projects'],
			description=line['description']
		)

		target_date = start_datetime

		for entry in entries:
		
			target_moment = entry.get_local_start_time()

			while target_moment <= entry.get_local_end_time():
				moment_label = get_moment_label(target_moment, graph_type, scope_type)
				line_data_container[moment_label] += 1

				target_moment += timedelta(minutes=1)


		y_axis_type = submission_data[0]['y_axis_type']
		values = list(line_data_container.values())

		if y_axis_type == 'percentage_tracked':
			total_minutes = sum(values)

			for key, value in line_data_container.items():
				line_data_container[key] = (value/total_minutes) * 100
		
		elif y_axis_type == 'average':
			time_block_occurances = get_time_block_occurances(start_datetime, end_datetime, scope_type)
			pp.pprint(time_block_occurances)
			for key, value in line_data_container.items():
				line_data_container[key] = line_data_container[key] / time_block_occurances[key]
		elif y_axis_type == 'percentage_occurance':
			# Note: this only makes sense for Frequency-Minute graphs
			days = (end_datetime - start_datetime).days

			for key, value in line_data_container.items():
				line_data_container[key] = (line_data_container[key] / days)*100

		values = list(line_data_container.values())
		keys = list(line_data_container.keys())


		data.append({
			'line_data': line,
			'entry_data': line_data_container,
			'values': values,
			'keys': keys
		})

	return jsonify(data)


# Get how many times a certain time block (week/month) occurs between two dates.
def get_time_block_occurances(start_datetime, end_datetime, scope_type):
	if scope_type == 'days':
		return get_weekday_occurances(start_datetime, end_datetime)
	elif scope_type == 'months':
		return get_month_occurances(start_datetime, end_datetime)

# Get how many times each weekday occurs between two dates.
def get_weekday_occurances(start_datetime, end_datetime):
	period = end_datetime - start_datetime
	number_of_days = period.days

	weekday_occurances = [0] * 7

	full_weeks = number_of_days // 7
	remainder = number_of_days % 7
	first_day = start_datetime.weekday()

	for i in range(0, 7):
		weekday_occurances[i] = full_weeks
	
	for i in range(0, remainder):
		weekday_occurances[(first_day + i) % 7] += 1

	# Turn the result into our dictionary format.
	return_value = {}
	for i, day in enumerate(weekdays):
		return_value[day] = weekday_occurances[i]

	return return_value

# Get how many times each month occurs between two dates.
def get_month_occurances(start_datetime, end_datetime):
	period = end_datetime - start_datetime

	month_occurances = [0] * 12

	target_datetime = start_datetime
	while target_datetime <= end_datetime:
		month_number = target_datetime.month - 1
		month_occurances[month_number] += 1

		target_datetime += timedelta(days=35)
		target_datetime = target_datetime.replace(day=1)

	# Turn the result into our dictionary format.
	return_value = {}
	for i, day in enumerate(months):
		return_value[day] = month_occurances[i]

	return return_value

# Generate the main container which will hold the data for our line. 
def get_line_data_container(graph_type, scope_type, start_datetime, end_datetime):
	if graph_type == 'frequency':
		if scope_type == 'minutes':
			 line_data_container = { i : 0 for i in list(range(0,1440)) }
		elif scope_type == 'days':
			line_data_container = {i : 0 for i in weekdays}
		elif scope_type == 'weeks':
			line_data_container = {i: 0 for i in range(0, 54)}
		elif scope_type == 'months':
			line_data_container = {i : 0 for i in months}
	else:
		line_data_container = {}
		target = start_datetime

		if scope_type == 'minutes':
			increment = 1
		else:
			increment = 60*24

		date_format = date_formats[scope_type]
			
		while target <= end_datetime:
			
			if scope_type == 'weeks': # For weeks we're doing this inside of the loop,
									  # since we need to remove the leading 0s from week number
				week_number = int(target.strftime('%W'))
				date_format = f"'%-y w{week_number}"

			date = target.strftime(date_format)

			if not date in line_data_container.keys():
				line_data_container[date] = 0

			target += timedelta(minutes=increment)

	return line_data_container

# Get a label describing the given moment.
# i.e. date string or month name, etc.
def get_moment_label(moment_datetime,graph_type, scope_type):
	if graph_type == 'normal':
		date_format = date_formats[scope_type]

		if scope_type == 'weeks':
			week_number = int(moment_datetime.strftime('%W'))
			date_format = f"'%-y w{week_number}"

		return moment_datetime.strftime(date_format)

	else:
		if scope_type == 'minutes':
			label = moment_datetime.hour * 60 + moment_datetime.minute
		elif scope_type == 'days':
			day_number = moment_datetime.weekday()
			label = weekdays[day_number]
		elif scope_type == 'weeks':
			label = int(moment_datetime.strftime('%W'))
		elif scope_type == 'months':
			month_number = moment_datetime.month - 1
			label = months[month_number]

		return label