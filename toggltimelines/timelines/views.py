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

	db_entries = helpers.get_db_entries(dispaly_start_datetime)

	dispalyed_days = helpers.sort_db_entries_by_day(db_entries)

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

	db_entries = helpers.get_db_entries(start, end)

	displayed_days = helpers.sort_db_entries_by_day(db_entries)

	page_data = {
		'days': displayed_days
	}

	return jsonify(render_template('timelines/day.html', data=page_data))

@bp.route("/timelines/start_stop", methods=['GET', 'POST'])
def start_stop():
	
	config_auth = current_app.config['START_STOP_AUTH']
	submitted_auth = request.args.get('auth')

	validated = False
	if config_auth and config_auth == submitted_auth:
		validated = True


	if not validated:
		return jsonify({'message': 'Invalid password'})


	currently_tracking = helpers.get_current_toggl_entry()

	if not currently_tracking:
		helpers.start_tracking()
		message = 'Started tracking'
	else:
		current_id = currently_tracking['id']
		helpers.stop_tracking(current_id)
		message = 'Stopped tracking'

	return jsonify({'message':message})