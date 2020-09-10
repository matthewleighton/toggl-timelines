from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import current_app
from flask import make_response
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
	
	sync_start_datetime = datetime.utcnow() - timedelta(days=2)
	helpers.toggl_sync(sync_start_datetime)

	dispaly_start_datetime = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=7)

	dispalyed_days = get_db_entries_by_day(start=dispaly_start_datetime)

	#print(dispalyed_days)

	page_data = {
		'days': dispalyed_days,
		'times': range(0, 24),
		'heart': False # TODO
	}

	response = make_response(render_template('timelines/timelines.html', data=page_data))

	return response

def get_db_entries_by_day(start=False, end=False):
	db_entries = helpers.get_db_entries(start, end)

	sorted_by_day = {}

	for entry in db_entries:
		entry_date_label = entry.start.strftime('%Y-%m-%d')

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