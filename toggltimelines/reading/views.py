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

from sqlalchemy import func

import calendar
import csv
import pytz
import math
from datetime import date, datetime, timedelta

import json
import requests
from pprint import pprint

from toggltimelines import db
from toggltimelines.reading.models import Book, Readthrough
from toggltimelines.timelines.models import Project
from toggltimelines import helpers

import pprint
pp = pprint.PrettyPrinter(indent=4)


bp = Blueprint("reading", __name__)

@bp.route("/reading")
def reading_home():

	populate_books()

	active_readthroughs = get_readthroughs('active')
	books = get_all_books()

	page_data = {
		'active_readthroughs': active_readthroughs,
		'books': books
	}

	response = make_response(render_template('reading/index.html', data=page_data))

	return response

@bp.route("/reading/new_readthrough", methods=['POST'])
def new_readthrough():
	
	book_id = request.json['book_id']
	book = Book.query.get(book_id)

	date_format = '%Y-%m-%d'

	start_date = datetime.strptime(request.json['start_date'], date_format)
	end_date = False
	if request.json['end_date'] and 'readthrough_complete' in request.json.keys():
		end_date = datetime.strptime(request.json['end_date'], date_format)

	readthrough_data = {
		'book_id': request.json['book_id'],
		'book_format': request.json['book_format'],
		'start_date': start_date,
		'end_date': end_date
	}

	if request.json['book_format'] == 'physical':
		readthrough_data['first_page'] = request.json['first_page']
		readthrough_data['last_page'] = request.json['last_page']

		if end_date:
			readthrough_data['current_position'] = request.json['last_page']
		else:
			readthrough_data['current_position'] = request.json['first_page']
	else:
		if end_date:
			readthrough_data['current_position'] = 100
		else:
			readthrough_data['current_position'] = 0


	readthrough = create_readthrough(readthrough_data)

	db.session.commit()

	data = {
		'active_readthroughs': get_readthroughs('active'),
	}

	return jsonify(
		html = render_template('reading/active_readthroughs.html', data=data),
		reload_active_readthroughs = not bool(end_date)
	)

@bp.route("/reading/update_position", methods=['POST'])
def update_position():
	new_position = request.json['value']
	readthrough_id = request.json['readthrough_id']

	readthrough = Readthrough.query.get(readthrough_id)

	readthrough.update_position(new_position)

	db.session.commit()

	return jsonify(
		readthrough_fields = render_template('reading/readthrough_fields.html', readthrough=readthrough),
		readthrough_position = render_template('reading/readthrough_position.html', readthrough=readthrough)
	)

@bp.route("/reading/update_end_date", methods=['POST'])
@bp.route("/reading/update_start_date", methods=['POST'])
@bp.route("/reading/update_target_end_date", methods=['POST'])
def update_date():
	new_date = request.json['value']
	readthrough_id = request.json['readthrough_id']
	endpoint = request.json['endpoint']

	readthrough = Readthrough.query.get(readthrough_id)

	if endpoint == 'update_start_date':
		date_type = 'start'
	elif endpoint == 'update_end_date':
		date_type = 'end'
	elif endpoint == 'update_target_end_date':
		date_type = 'target_end'

	readthrough.update_date(new_date, date_type)

	db.session.commit()

	return jsonify(
		readthrough_fields = render_template('reading/readthrough_fields.html', readthrough=readthrough),
		readthrough_position = render_template('reading/readthrough_position.html', readthrough=readthrough)
	)

@bp.route("/reading/update_daily_reading_goal", methods=['POST'])
def update_daily_reading_goal():
	new_goal = request.json['value']
	readthrough_id = request.json['readthrough_id']
	readthrough = Readthrough.query.get(readthrough_id)

	readthrough.update_daily_reading_goal(new_goal)

	db.session.commit()

	return jsonify(
		readthrough_fields = render_template('reading/readthrough_fields.html', readthrough=readthrough),
		readthrough_position = render_template('reading/readthrough_position.html', readthrough=readthrough)
	)

@bp.route("/reading/search_books", methods=['POST'])
def search_books():
	title = request.json['title'].lower()

	books = Book.query.filter(func.lower(Book.title).contains(title)).all()

	print(books)

	return jsonify(render_template('reading/books_list.html', books=books))

@bp.route("/reading/delete_readthrough", methods=['POST'])
def delete_readthrough():
	readthrough_id = request.json['readthrough_id']
	readthrough = Readthrough.query.get(readthrough_id)

	db.session.delete(readthrough)
	db.session.commit()

	return jsonify(readthrough_id)

@bp.route("/reading/load_past_readthroughs", methods=['POST'])
def load_past_readthroughs():
	amount_per_request = 10

	all_past_readthroughs = get_readthroughs('complete')

	target_start_number = request.json['number_loaded']
	target_end_number = target_start_number + amount_per_request

	readthroughs_to_return = all_past_readthroughs[target_start_number : target_end_number]

	none_remaining = True if target_end_number >= len(all_past_readthroughs) else False

	return jsonify(
		html = render_template('reading/readthrough_list.html', readthroughs=readthroughs_to_return ),
		amount_per_request = amount_per_request,
		none_remaining = none_remaining
	)

@bp.route("/reading/search_readthroughs", methods=['POST'])
def search_readthroughs():
	title = request.json['title']
	readthroughs = get_readthroughs(status='complete', title=title)


	if readthroughs:
		return jsonify(render_template('reading/readthrough_list.html', readthroughs=readthroughs))
	else:
		message = "<h5>No results</h5>"
		return jsonify(message)

@bp.route("/reading/update_cover", methods=['POST'])
def update_cover():
	cover_url = request.json['cover_url']
	book_id = request.json['book_id']
	readthrough_id = request.json['readthrough_id']

	book = Book.query.get(book_id)
	book.image_url = cover_url
	db.session.commit()

	readthrough = Readthrough.query.get(readthrough_id)

	return jsonify(render_template('reading/readthrough.html', readthrough=readthrough))

@bp.route("/reading/toggl_sync", methods=['POST'])
def toggl_sync():
	sync_start = datetime.now() - timedelta(days=1)
	helpers.toggl_sync(sync_start)

	data = {
		'active_readthroughs': get_readthroughs('active'),
	}

	return jsonify(
		html = render_template('reading/active_readthroughs.html', data=data),
	)

@bp.route("/reading/start_track", methods=['POST'])
def start_track():
	readthrough_id = request.json['readthrough_id']
	readthrough = Readthrough.query.get(readthrough_id)
	title = readthrough.book.title

	#TODO: Add the project ID to the request.

	response = helpers.start_tracking(title)

	return jsonify(
		response = response
	)

@bp.route("/reading/stop_track", methods=['POST'])
def stop_track():

	helpers.stop_tracking()

	#TODO: Return something sensible.

	return jsonify('test')

@bp.route("/reading/graph", methods=['GET'])
def graph():
	readthrough_id =  request.args.get('readthrough_id')
	readthrough = Readthrough.query.get(readthrough_id)

	base_url = request.url_root

	if not readthrough:
		return requests.get(base_url + 'reading').text

	project = 'Reading'
	description = readthrough.book.title
	start = readthrough.start_date
	end = readthrough.end_date if readthrough.end_date else datetime.today()

	color = Project.query.filter(Project.project_name >= project).first().project_hex_color

	graph_line = {
		'projects': [project],
		'description': description,
		'label': description,
		'color': color
	}

	graph_data = {
		'lines': [graph_line],
		'graph_type': 'normal',
		'scope_type': 'days',
		'graph_style': 'bar',
		'start': start.strftime('%Y-%m-%d'),
		'end': end.strftime('%Y-%m-%d')
	}

	
	response = requests.post(base_url + 'frequency', json=graph_data).text

	return response

@bp.route("/reading/history", methods=['GET'])
def history():

	first_year = get_readthroughs(year=False)[-1].start_date.year
	current_year = datetime.now().year

	years = list(range(first_year, current_year+1))
	years.reverse()

	yearly_stats = get_history_year_data()

	print('yearly stats')
	pp.pprint(yearly_stats)

	# books_graph_data = get_books_graph_data(years)

	data = {
		'years': years,
		'yearly_stats': yearly_stats

	}

	response = make_response(render_template('reading/history.html', data=data))

	return response

@bp.route('/reading/books_completed_graph_data', methods=['POST'])
def books_completed_graph_data():
	data = []

	years = get_all_reading_years()

	for year in years:
		completed_books = 0
		dates = {}

		completion_info = []

		readthroughs = get_readthroughs(year=year, status='complete', order_by='end')
		readthroughs.reverse()

		date_of_readthrough_completion = readthroughs[0].end_date.date() if len(readthroughs) else False

		target_date = date(year, 1, 1)

		i = 0

		while target_date.year == year:
			if target_date == date_of_readthrough_completion:
				completed_books += 1

				completion_info.append({
					'title': readthroughs[0].book.title,
					'date': target_date.strftime('%d %B %Y'),
					'day_number': i
				})

				readthroughs.pop(0)
				date_of_readthrough_completion = readthroughs[0].end_date.date() if len(readthroughs) else False
				continue

			date_label = target_date.strftime('%d %b')
			dates[date_label] = completed_books

			if target_date >= date.today():
				break

			# For non-leap years, we say that February 29th has the same value as February 28th
			if (date_label == '28 Feb' and not calendar.isleap(year)):
				dates['29 Feb'] = completed_books

			target_date += timedelta(days=1)
			i += 1

		data.append({
			'year': year,
			'dates': list(dates.keys()),
			'values': list(dates.values()),
			'completion_info': completion_info
		});

	return jsonify(data)

@bp.route("/reading/reading_time_graph_data", methods=['POST'])
def reading_time_graph_data():
	years = get_all_reading_years()

	data = []

	for year in years:
		dates = {}
		reading_time = 0

		book_titles = []
		readthroughs = get_readthroughs(year=year, status='complete', order_by='end')

		for readthrough in readthroughs:
			book_titles.append(readthrough.book.title)

		entries = helpers.get_db_entries(
			start = datetime(year, 1, 1), # TODO: These should be in the correct timezones for where the user was at the time.
			end = datetime(year, 12, 31, 23, 59, 59),
			description = book_titles
		)

		target_date = date(year, 1, 1)

		while target_date.year == year:

			i = 0

			for entry in entries:
				if entry.start.date() == target_date:
					reading_time += entry.dur
					i += 1
				else:
					break

			date_label = target_date.strftime('%d %b')
			dates[date_label] = reading_time

			if target_date >= date.today():
				break

			# For non-leap years, we say that February 29th has the same value as February 28th
			if (date_label == '28 Feb' and not calendar.isleap(year)):
				dates['29 Feb'] = reading_time

			print(date_label)

			target_date += timedelta(days=1)

			entries = entries[i:]

			i = 0

		print('')

		data.append({
			'year': year,
			'dates': list(dates.keys()),
			'values': list(dates.values())
		});

	# pp.pprint(data)

	return jsonify(data)



def get_all_reading_years():
	first_year = get_readthroughs(year=False)[-1].start_date.year
	current_year = datetime.now().year

	years = list(range(first_year, current_year+1))
	years.reverse()

	return years

def get_history_year_data():
	data = []

	years = get_all_reading_years()

	for year in years:
	
		readthroughs = get_readthroughs(year=year, status='complete', include_readthroughs_completed_in_next_year=False)
		number_of_books = len(readthroughs)

		# pp.pprint(readthroughs)

		start_of_first_readthrough = readthroughs[-1].start_date
		
		if not year:
			period_start = start_of_first_readthrough
			period_end = datetime.today()

		else:
			start_of_year = datetime(year, 1, 1, 0, 0)

			if start_of_first_readthrough > start_of_year:
				period_start = start_of_year
			else:
				period_start = start_of_first_readthrough

			period_end = min([datetime(year, 12, 31, 23, 59), datetime.today()])

		days = (period_end - period_start).days + 1

		average_days_per_book = str(round(days / number_of_books)) + ' days'

		total_reading_time = 0

		for readthrough in readthroughs:
			total_reading_time += readthrough.get_current_reading_time(raw=True)

		average_time_per_book = helpers.format_milliseconds(round(total_reading_time / number_of_books), days=True)

		average_daily_reading_time = helpers.format_milliseconds(round(total_reading_time / days), days=False)

		total_reading_time = helpers.format_milliseconds(total_reading_time, days=True)

		data.append({
			'year': year,
			'number_of_books': number_of_books,
			'average_days_per_book': average_days_per_book,
			'average_time_per_book': average_time_per_book,
			'total_reading_time': total_reading_time,
			'average_daily_reading_time': average_daily_reading_time
		})

	return data

@bp.route("/reading/history_year_data", methods=['POST'])
def history_year_data():
	data = []

	years = get_all_reading_years()

	for year in years:


	# year = int(request.json['year'])

	# if not int(year):
	# 	year = False
	
		readthroughs = get_readthroughs(year=year, status='complete', include_readthroughs_completed_in_next_year=False)
		number_of_books = len(readthroughs)

		print(year)
		pp.pprint(readthroughs)
		print('')

		start_of_first_readthrough = readthroughs[-1].start_date
		
		if not year:
			period_start = start_of_first_readthrough
			period_end = datetime.today()

		else:
			start_of_year = datetime(year, 1, 1, 0, 0)

			if start_of_first_readthrough > start_of_year:
				period_start = start_of_year
			else:
				period_start = start_of_first_readthrough

			period_end = min([datetime(year, 12, 31, 23, 59), datetime.today()])

		days = (period_end - period_start).days + 1

		

		average_days_per_book = str(round(days / number_of_books)) + ' days'

		total_reading_time = 0

		for readthrough in readthroughs:
			total_reading_time += readthrough.get_current_reading_time(raw=True)

		average_time_per_book = helpers.format_milliseconds(round(total_reading_time / number_of_books), days=True)

		average_daily_reading_time = helpers.format_milliseconds(round(total_reading_time / days), days=False)

		total_reading_time = helpers.format_milliseconds(total_reading_time, days=True)

		data.append({
			'year': year,
			'number_of_books': number_of_books,
			'average_days_per_book': average_days_per_book,
			'average_time_per_book': average_time_per_book,
			'total_reading_time': total_reading_time,
			'average_daily_reading_time': average_daily_reading_time
		})

	


	# data = {
	# 	'year': year,
	# 	'number_of_books': number_of_books,
	# 	'average_days_per_book': average_days_per_book,
	# 	'average_time_per_book': average_time_per_book,
	# 	'total_reading_time': total_reading_time,
	# 	'average_daily_reading_time': average_daily_reading_time
	# }

	return jsonify(
		html = render_template('reading/history_year.html', data=data)
	)
	

def get_all_books():
	query = Book.query
	books = query.all()
	return books

# Use a status of 'active' to only get currently read books. Or a status of 'complete' for finished books.
def get_readthroughs(status='all', title=False, year=False, include_readthroughs_completed_in_next_year=True, order_by='start'):
	query = Readthrough.query
	
	if status == 'active':
		query = query.filter(Readthrough.end_date == None)
	elif status == 'complete':
		query = query.filter(Readthrough.end_date != None)

	if title:
		query = query.join(Book).filter(func.lower(Book.title).contains(title.lower()))

	if year:
		year_start = datetime(year, 1, 1)
		year_end = datetime(year, 12, 31)

		query = query.filter((Readthrough.end_date >= year_start) | (Readthrough.end_date == None))

		if include_readthroughs_completed_in_next_year:
			query = query.filter( (Readthrough.start_date <= year_end) | (Readthrough.end_date == None))
		else:
			query = query.filter((Readthrough.end_date <= year_end) | (Readthrough.end_date == None))

	if (order_by == 'start'):
		query = query.order_by(Readthrough.start_date.desc())
	else:
		query = query.order_by(Readthrough.end_date.desc())

	

	readthroughs = query.all()

	return readthroughs

def populate_books():
	db_reading_entries = helpers.get_db_entries(projects=['Reading'])

	unique_books = set()

	for entry in db_reading_entries:
		unique_books.add(entry.description)

	for title in unique_books:
		create_book(title)

	db.session.commit()


def create_book(title):
	existing_book = get_book(title)

	if existing_book:
		return existing_book

	db_book = Book(
		title = title
	)

	db.session.add(db_book)

	return db_book

# --------- This has been moved to a command, instead of running when each book is imported.
# def get_book_cover_url(title):
# 	cover_placeholder = '/static/img/cover_placeholder.png'


# 	if current_app.failed_image_api_search:
# 		return cover_placeholder

# 	# Make image API request to Bing to find book covers.
# 	subscription_key = current_app.config['BING_API_KEY']
# 	search_url = "https://api.cognitive.microsoft.com/bing/v7.0/images/search"
# 	headers = {"Ocp-Apim-Subscription-Key" : subscription_key}
	
# 	params  = {"q": title + ' book cover'}

# 	response = requests.get(search_url, headers=headers, params=params)

# 	if response.status_code != 200:
# 		current_app.failed_image_api_search = True
# 		return cover_placeholder

# 	search_results = response.json()
# 	cover_url = False

# 	if not len(search_results['value']):
# 		return cover_placeholder

# 	for result in search_results['value']:
# 		if result['height'] > result['width']: # Check that the image is taller than it is wide.
# 			cover_url = result['contentUrl']
# 			break

# 	if not cover_url:
# 		cover_url = search_results['value'][0]['contentUrl']

# 	return cover_url

def create_readthrough(data):
	book = Book.query.get(data['book_id'])

	db_readthrough = Readthrough(
		book = book,
		book_format = data['book_format'],
		start_date = data['start_date'],
		current_position = data['current_position']
	)

	if data['book_format'] == 'physical':
		db_readthrough.first_page = data['first_page']
		db_readthrough.last_page = data['last_page']

	print(data)

	if data['end_date']:
		db_readthrough.end_date = data['end_date']

	db.session.add(db_readthrough)

	db.session.commit()

	return db_readthrough


def get_book(title):
	query = Book.query.filter(func.lower(Book.title).contains(title.lower()))

	book = query.all()

	return book