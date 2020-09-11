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

import pytz
from datetime import datetime, timedelta

from toggltimelines import db

from toggltimelines.timelines.models import Entry

from toggltimelines import helpers

bp = Blueprint("timelines", __name__)

@bp.route("/")
def index():
	return render_template("index.html")

@bp.route("/timelines")
def timelines_page():
	
	sync_start_datetime = datetime.utcnow().replace(hour=0, minute=0, second=0) - timedelta(days=2)
	helpers.toggl_sync(sync_start_datetime)

	dispaly_start_datetime = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=7)

	dispalyed_days = get_db_entries_by_day(start=dispaly_start_datetime)

	page_data = {
		'days': dispalyed_days,
		'times': range(0, 24),
		'heart': False # TODO
	}

	response = make_response(render_template('timelines/timelines.html', data=page_data))

	return response

@bp.route("/timelines/load_more", methods=['GET', 'POST'])
def load_more():
	#return render_template("index.html")
	reloading = request.json.get('reload')

	start_days_ago = request.json.get('start_days_ago')
	end_days_ago = request.json.get('end_days_ago')

	print(f"Start: {start_days_ago}")
	print(f"End: {end_days_ago}")

	if reloading:
		helpers.toggl_sync(days=0)

		start = datetime.now().replace(hour=0, minute=0, second=0)
		end = False

	else:
		
		if start_days_ago:
			start = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=start_days_ago)
		else:
			start = False			

		end = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=end_days_ago)

	print(f"Start datetime: {start}")
	print(f"End datetime: {end}")

	displayed_days = get_db_entries_by_day(start=start, end=end)

	page_data = {
		'days': displayed_days
	}

	return jsonify(render_template('timelines/day.html', data=page_data))

def get_db_entries_by_day(start=False, end=False):
	db_entries = helpers.get_db_entries(start, end)

	sorted_by_day = {}

	for entry in db_entries:
		# Below we use get_local_start_time() because we need to make sure we're sorting
		# with reference to what day it was in the user's location. Not simply UTC.
		entry_date_label = entry.get_local_start_time().strftime('%Y-%m-%d')

		if entry_date_label not in sorted_by_day:
			sorted_by_day[entry_date_label] = {
				'entries': [],
				'date': entry.start.strftime('%a %d %b, %Y')
			}

		sorted_by_day[entry_date_label]['entries'].append(entry)

	days_list = []
	for day in sorted_by_day.values():
		days_list.append(day)

	days_list.reverse()

	return days_list