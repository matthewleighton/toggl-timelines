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



@bp.route('/frequency/frequency_data', methods=['POST'])
def frequency_data():
	submission_data = request.json

	print(submission_data)

	data = []

	scope_type = submission_data[0]['scope_type']
	graph_type = submission_data[0]['graph_type']
	print(graph_type)

	for line in submission_data:
		frequency_weekdays = [0, 0, 0, 0, 0, 0, 0]

		frequency_months = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

		start_datetime = datetime.strptime(line['start'], '%Y-%m-%d')
		end_datetime = datetime.strptime(line['end'], '%Y-%m-%d')


		line_data_container = get_line_data_container(graph_type, scope_type, start_datetime, end_datetime)

		#pp.pprint(line_data_container)

		if isinstance(line['projects'], str):
			line['projects'] = [line['projects']]

		

		#print(line['description'])
	
		# TODO: Need to consider the timezones here.
		# The request will be made purely in UTC, but it should be first converted from the user's timezone? 
		entries = helpers.get_db_entries(
			start_datetime,
			end_datetime,
			projects=line['projects'],
			description=line['description']
		)



		frequency_minutes = get_day_minutes_list()


		calendar_period_dict = get_calendar_period_dict(scope_type, start_datetime, end_datetime)

		target_date = start_datetime


		if scope_type == 'days':
			date_format = '%Y-%m-%d'
		elif scope_type == 'months':
			date_format = '%Y-%m'
		else:
			date_format = '%Y'


		for entry in entries:
			
			# entry_start = entry.get_local_start_time()

			# duration_minutes = math.ceil(entry.dur / 60000)
			# target_minute = get_minute_of_day(entry_start)

			# weekday 	 = entry_start.weekday()
			# month 		 = entry_start.month
			# day_of_month = entry_start.day
			# year 		 = entry_start.year

			# target_day = entry_start



			# # Minute 1440 does not exist.
			# if target_minute >= 1440:
			# 	target_minute = 0



			target_moment = entry.get_local_start_time()

			while target_moment <= entry.get_local_end_time():
				moment_label = get_moment_label(target_moment, graph_type, scope_type)
				line_data_container[moment_label] += 1

				target_moment += timedelta(minutes=1)


			# i = 0
			# while i <= duration_minutes:

			# 	frequency_minutes[target_minute] += 1



			# 	datestamp = target_day.strftime(date_format)

			# 	if graph_type == 'normal':
			# 		calendar_period_dict[datestamp] += 1

			# 	target_minute += 1

			# 	frequency_weekdays[weekday] += 1
			# 	frequency_months[month] += 1

			# 	if target_minute >= 1440: # If the entry overflows to the next day...
			# 		target_minute = 0
			# 		target_day += timedelta(days=1)

			# 		weekday += 1
			# 		day_of_month += 1

			# 		if weekday == 7:
			# 			weekday = 0

			# 		last_day_of_month = calendar.monthrange(year, month)[1]

			# 		if day_of_month > last_day_of_month:
			# 			month += 1

			# 			if month > 12:
			# 				month = 1

			# 	i += 1

		# Semi-temporary fix because we end up getting a lot of additional minutes tracked at minute 0.
		# frequency_minutes[0] = frequency_minutes[1439]







		# if submission_data[0]['y_axis_type'] in ['relative', 'percentage-tracked-time']:
		# 	period_duration = end_datetime - start_datetime
		# 	frequency_minutes = [i / period_duration.days for i in frequency_minutes]

		# 	total_minutes = sum(frequency_weekdays)

		# 	frequency_weekdays = list(map(lambda n: n/total_minutes, frequency_weekdays))

		# 	frequency_months = list(map(lambda n: n/total_minutes, frequency_months))

		# elif submission_data[0]['y_axis_type'] == 'average':
		# 	weekday_occurances = get_weekday_occurances(start_datetime, end_datetime)

		# 	for i in range(0, 7):
		# 		frequency_weekdays[i] = frequency_weekdays[i] / weekday_occurances[i]







		# frequency_months.pop(0) # Remove the first month, since we want them to be zero indexed.

		# print(graph_type)
		# print(scope_type)




		# if graph_type == 'normal':
		# 	entry_data = calendar_period_dict
		# else:
		# 	if scope_type == 'minutes':
		# 		entry_data = frequency_minutes
		# 		print('Weeeeee!')
		# 	elif scope_type == 'days':
		# 		entry_data = frequency_weekdays
		# 	elif scope_type == 'months':
		# 		entry_data = frequency_months





		#print(entry_data)

		# pp.pprint(line_data_container)

		values = list(line_data_container.values())
		keys = list(line_data_container.keys())


		data.append({
			'line_data': line,
			#'minutes': frequency_minutes,
			#'days': frequency_weekdays,
			#'months': frequency_months,
			#'calendar': calendar_period_dict
			'entry_data': line_data_container,
			'values': values,
			'keys': keys
		})

	return jsonify(data)

def get_line_data_container(graph_type, scope_type, start_datetime, end_datetime):
	if graph_type == 'frequency':
		if scope_type == 'minutes':
			 line_data_container = { i : 0 for i in list(range(0,1440)) }
		elif scope_type == 'days':
			line_data_container = {i : 0 for i in weekdays}
		elif scope_type == 'months':
			line_data_container = {i : 0 for i in months}
	else:
		line_data_container = {}
		target = start_datetime

		if scope_type == 'minutes':
			increment = 1
			date_format = '%Y-%m-%d %H:%M'
		elif scope_type == 'days':
			increment = 60*24
			date_format = '%Y-%m-%d'
		elif scope_type == 'months':
			increment = 60*24
			date_format = '%Y-%m'
			
		while target <= end_datetime:
			date = target.strftime(date_format)

			if not date in line_data_container.keys():
				line_data_container[date] = 0

			target += timedelta(minutes=increment)

	return line_data_container

def get_moment_label(moment_datetime,graph_type, scope_type):
	if graph_type == 'normal':
		if scope_type == 'minutes':
			date_format = '%Y-%m-%d %H:%M'
		elif scope_type == 'days':
			date_format = '%Y-%m-%d'
		elif scope_type == 'months':
			date_format = '%Y-%m'

		return moment_datetime.strftime(date_format)
	else:
		if scope_type == 'minutes':
			label = moment_datetime.hour * 60 + moment_datetime.minute
		elif scope_type == 'days':
			day_number = moment_datetime.weekday()
			label = weekdays[day_number]
		elif scope_type == 'months':
			month_number = moment_datetime.month - 1
			label = months[month_number]

		return label


def get_calendar_period_dict(scope_type, start_datetime, end_datetime):
	if scope_type == 'days':
		date_format = '%Y-%m-%d'
	elif scope_type == 'months':
		date_format = '%Y-%m'
	elif scope_type == 'years':
		date_format = '%Y'
	else:
		return {}

	calendar_period_dict = {}

	target_datetime = start_datetime

	while target_datetime <= end_datetime:
		date = target_datetime.strftime(date_format)
		calendar_period_dict[date] = 0

		if scope_type == 'days':
			target_datetime += timedelta(days=1)
		elif scope_type == 'months':
			target_datetime += timedelta(days=1)
		elif scope_type == 'years':
			target_datetime += timedelta(years=1)

	return calendar_period_dict






# Return a list of the number of times each weekdays occured between two dates.
def get_weekday_occurances(start, end):
	period = end - start
	number_of_days = period.days

	weekday_occurances = [0, 0, 0, 0, 0, 0, 0]

	full_weeks = number_of_days // 7
	remainder = number_of_days % 7
	first_day = start.weekday()

	for i in range(0, 7):
		weekday_occurances[i] = full_weeks
	
	for i in range(0, remainder):
		weekday_occurances[(first_day + i) % 7] += 1

	return weekday_occurances

# Return a dictionary with minutes from 0 to 1440, each with a value of 0.
def get_day_minutes_list():
	return [0] * 1440

def get_minute_of_day(dt):
	hour = dt.hour
	minute = dt.minute

	minute_of_day = 60*hour + minute

	return minute_of_day