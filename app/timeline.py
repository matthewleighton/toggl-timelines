from app import app
from app import helpers

from datetime import datetime, timedelta

from flask import make_response, render_template, request, jsonify

initial_timelines_page_load_amount = 7

@app.route('/timelines')
def timelines_page():
	helpers.update_database(3)

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
		helpers.update_database(1)

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

# Return a list of days with entries.
def get_days_list(loading_additional_days = False, amount = 8, start = False, end = False):
	db_entries = helpers.get_entries_from_database(start, end)

	days_list = helpers.sort_entries_by_day(db_entries)
	
	return days_list









@app.route('/sync')
def sync_page():
	import_complete = False
	days_per_request = 50

	start_days_ago = days_per_request
	end_days_ago = 0

	i = 0
	
	while not import_complete:
		entries_added = helpers.update_database(start_days_ago, end_days_ago)
		
		end_days_ago = start_days_ago
		start_days_ago += days_per_request

		i += 1

		#if (i > 3):
		#	import_complete = True

		print('Import loop: {0}'.format(i))
		print('Start: {0}'.format(start_days_ago))

		if len(entries_added) == 0:
			import_complete = True
	
	response = make_response('Syncing...')

	return response