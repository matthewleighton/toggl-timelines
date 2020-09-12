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

bp = Blueprint("frequency", __name__)

@bp.route("/frequency")
def index():
	helpers.toggl_sync(days=2)

	projects = helpers.get_project_data()

	page_data = {
		'projects': projects,
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

	data = []

	for line in submission_data:
		days = [0, 0, 0, 0, 0, 0, 0]

		months = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

		if isinstance(line['projects'], str):
			line['projects'] = [line['projects']]
		start_datetime = datetime.strptime(line['start'], '%Y-%m-%d')
		end_datetime = datetime.strptime(line['end'], '%Y-%m-%d')

		#print(line['description'])
	
		# TODO: Need to consider the timezones here.
		# The request will be made purely in UTC, but it should be first converted from the user's timezone? 
		entries = helpers.get_db_entries(
			start_datetime,
			end_datetime,
			projects=line['projects'],
			description=line['description']
		)



		day_minutes_list = get_day_minutes_list()

		for entry in entries:
			
			entry_start = entry.get_local_start_time()

			duration_minutes = math.ceil(entry.dur / 60000)
			target_minute = get_minute_of_day(entry_start)

			weekday 	 = entry_start.weekday()
			month 		 = entry_start.month
			day_of_month = entry_start.day
			year 		 = entry_start.year

			# Minute 1440 does not exist.
			if target_minute >= 1440:
				target_minute = 0

			i = 0
			while i <= duration_minutes:
				day_minutes_list[target_minute] += 1
				target_minute += 1

				days[weekday] += 1
				months[month] += 1

				if target_minute >= 1440: # If the entry overflows to the next day...
					target_minute = 0

					weekday += 1
					day_of_month += 1

					if weekday == 7:
						weekday = 0#

					last_day_of_month = calendar.monthrange(year, month)[1]

					if day_of_month > last_day_of_month:
						month += 1

						if month > 12:
							month = 1

				i += 1

		# Semi-temporary fix because we end up getting a lot of additional minutes tracked at minute 0.
		day_minutes_list[0] = day_minutes_list[1439]

		if submission_data[0]['y_axis_type'] in ['relative', 'percentage-tracked-time']:
			period_duration = end_datetime - start_datetime
			day_minutes_list = [i / period_duration.days for i in day_minutes_list]

			total_minutes = sum(days)

			days = list(map(lambda n: n/total_minutes, days))

			months = list(map(lambda n: n/total_minutes, months))

		elif submission_data[0]['y_axis_type'] == 'average':
			weekday_occurances = get_weekday_occurances(start_datetime, end_datetime)

			for i in range(0, 7):
				days[i] = days[i] / weekday_occurances[i]

		months.pop(0) # Remove the first month, since we want them to be zero indexed.

		print(months)

		data.append({
			'line_data': line,
			'minutes': day_minutes_list,
			'days': days,
			'months': months
		})

	return jsonify(data)

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