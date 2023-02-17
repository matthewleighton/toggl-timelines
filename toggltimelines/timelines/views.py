import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, make_response, jsonify

from toggltimelines import helpers

bp = Blueprint("timelines", __name__)

DAYS_SYNC = 2
DAYS_DISPLAY = 7

@bp.route("/")
def index():
	return render_template("index.html")

# The main timelines page.
@bp.route("/timelines")
def timelines_page():
	now = datetime.utcnow().replace(hour=0, minute=0, second=0)

	sync_start_datetime = now - timedelta(days=DAYS_SYNC)
	query_start_datetime = now - timedelta(days=DAYS_DISPLAY)

	helpers.toggl_sync(sync_start_datetime)

	db_entries = helpers.get_db_entries(query_start_datetime)
	dispalyed_days = helpers.sort_db_entries_by_day(db_entries)

	page_data = {
		'days': dispalyed_days,
		'times': range(0, 24),
		'heart': True if is_user_johanna() else False
	}

	return make_response(render_template('timelines/timelines.html', data=page_data))

# Load more days on the timelines page.
@bp.route("/timelines/load_more", methods=['POST'])
def load_more():
	reloading = request.json.get('reload')

	start_days_ago = request.json.get('start_days_ago')
	end_days_ago = request.json.get('end_days_ago')

	start, end = get_query_start_end(reloading, start_days_ago, end_days_ago)

	if reloading:
		helpers.toggl_sync(days=0)


	db_entries = helpers.get_db_entries(start, end)

	displayed_days = helpers.sort_db_entries_by_day(db_entries)

	page_data = {
		'days': displayed_days
	}

	# TODO: Rendering all the data into HTML is slow.
	# Instead, just return the data and render it on the client side.

	rendered_template = render_template('timelines/day.html', data=page_data)
	return jsonify(rendered_template)


# Get the start and end datetimes for the query to load more days.
def get_query_start_end(reloading, start_days_ago, end_days_ago):
	today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
	
	if reloading:
		start = today_start
		end = False

	else:
		if start_days_ago:
			start = today_start - timedelta(days=start_days_ago)
		else:
			start = False			

		end = today_start - timedelta(days=end_days_ago, microseconds=1)

	if start:
		start_tz = helpers.get_user_timezone_at_date(start)
		start = helpers.to_utc(start, start_tz)

	if end:
		end_tz = helpers.get_user_timezone_at_date(end)
		end = helpers.to_utc(end, end_tz)

	return start, end

def is_user_johanna():
	username = os.environ.get('USER').lower()
	return True if 'johanna' in username else False