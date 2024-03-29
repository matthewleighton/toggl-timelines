from flask import Blueprint, render_template, request, current_app, make_response, jsonify

from sqlalchemy import func

import calendar
from datetime import date, datetime, timedelta
import os

import requests

from toggltimelines import db, helpers
from toggltimelines.reading.models import Book, Readthrough
from toggltimelines.timelines.models import Project

from time import perf_counter

from pprint import pprint

bp = Blueprint("reading", __name__)

@bp.route("/reading")
def reading_home():
	start = perf_counter()

	if not os.path.exists(current_app.covers_directory):
		os.makedirs(current_app.covers_directory)

	sync_start = perf_counter()
	sync_start_datetime = datetime.utcnow().replace(hour=0, minute=0, second=0)
	helpers.toggl_sync(sync_start_datetime)
	sync_stop = perf_counter()
	print(f"Syncing took {sync_stop-sync_start} seconds.")

	# TODO: Maybe this shouldn't be fired on every page load.
	# Instead add a button which searches for new books.
	# The user clicks the button when they've started a new book.
	# populate_books()

	active_readthroughs = get_readthroughs('active')
	books = get_all_books()

	verify_covers(active_readthroughs)

	page_data = {
		'active_readthroughs': active_readthroughs,
		'books': books
	}

	start_response = perf_counter()
	response = make_response(render_template('reading/index.html', data=page_data))
	stop_response = perf_counter()
	print(f"Response took {stop_response-start_response} seconds.")

	stop = perf_counter()
	print(f"Reading home page loaded in {stop-start} seconds.")

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

	# Save the covers if they don't already exist locally.
	for book in books:
		book.get_cover()


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
	print('\n\n starting load_past_readthroughs... \n\n')

	start = perf_counter()

	amount_per_request = 10

	all_past_readthroughs = get_readthroughs('complete')

	refresh = request.json['refresh']
	load_all = request.json['load_all']

	if refresh:
		target_start_number = 0
		target_end_number = request.json['number_loaded'] + amount_per_request
	elif load_all:
		target_start_number = request.json['number_loaded']
		target_end_number = len(all_past_readthroughs)
	else:
		target_start_number = request.json['number_loaded']
		target_end_number = target_start_number + amount_per_request

	sort_by = request.json['sort_by']

	sort_order = request.json['sort_order']

	reverse = True if sort_order == 'desc' else False

	if sort_by == 'total-time':
		all_past_readthroughs = sorted(all_past_readthroughs,
								reverse=reverse, 
								key=lambda readthrough: readthrough.get_current_reading_time(raw=True))
	elif sort_by == 'daily-time':
		all_past_readthroughs = sorted(all_past_readthroughs,
								reverse=reverse, 
								key=lambda readthrough: readthrough.get_average_daily_reading_time(raw=True))
	elif sort_by == 'total-days':
		all_past_readthroughs = sorted(all_past_readthroughs,
								reverse=reverse, 
								key=lambda readthrough: readthrough.get_total_days_reading(raw=True))
	elif sort_by == 'daily-progress':
		all_past_readthroughs = sorted(all_past_readthroughs,
								reverse=reverse, 
								key=lambda readthrough: readthrough.get_average_daily_progress(raw=True, force_percentage=True))
	elif sort_by == 'time-per-percentage':
		all_past_readthroughs = sorted(all_past_readthroughs,
								reverse=reverse, 
								key=lambda readthrough: readthrough.get_time_per_position_unit(raw=True, force_percentage=True))
	elif sort_by == 'date':
		all_past_readthroughs = sorted(all_past_readthroughs,
						reverse=reverse, 
						key=lambda readthrough: readthrough.end_date)


	readthroughs_to_return = all_past_readthroughs[target_start_number : target_end_number]

	verify_covers(readthroughs_to_return)

	none_remaining = True if target_end_number >= len(all_past_readthroughs) else False

	stop = perf_counter()
	print(f"Time to load past readthroughs: {stop - start}")

	return jsonify(
		html = render_template('reading/readthrough_list.html', readthroughs=readthroughs_to_return ),
		amount_per_request = amount_per_request,
		none_remaining = none_remaining
	)

@bp.route("/reading/search_readthroughs", methods=['POST'])
def search_readthroughs():
	title = request.json['title']
	readthroughs = get_readthroughs(status='complete', title=title)

	verify_covers(readthroughs)

	pprint(readthroughs)


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

	book.update_cover(cover_url)

	readthrough = Readthrough.query.get(readthrough_id)

	return jsonify(render_template('reading/readthrough.html', readthrough=readthrough))

@bp.route("/reading/load_single_readthrough", methods=['POST'])
def load_single_readthrough():
	readthrough_id = request.json['readthrough_id']
	readthrough = Readthrough.query.get(readthrough_id)

	return jsonify(
		html = render_template('reading/readthrough.html',
				readthrough = readthrough,
				hide_readthrough_buttons = True),
		book_title = readthrough.book.title
		)

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
		'end': end.strftime('%Y-%m-%d'),
		'scale_from_zero': True
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

	year = datetime.today().year
	raw_average_daily_reading_time_this_year = get_average_daily_reading_time(year)
	average_daily_reading_time_this_year = helpers.format_milliseconds(raw_average_daily_reading_time_this_year, short_labels=True)

	data = {
		'years': years,
		'yearly_stats': yearly_stats,
		'average_daily_reading_time_this_year': average_daily_reading_time_this_year,
		'raw_average_daily_reading_time_this_year': raw_average_daily_reading_time_this_year
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
					'readthrough_id': readthroughs[0].id,
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
				i += 1

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
		readthroughs = get_readthroughs(year=year,
										status='all',
										order_by='end', 
										include_readthroughs_completed_in_next_year=False
									)

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

			target_date += timedelta(days=1)

			entries = entries[i:]

			i = 0

		data.append({
			'year': year,
			'dates': list(dates.keys()),
			'values': list(dates.values())
		});


	return jsonify(data)

def get_average_daily_reading_time(year):
	year_end = min([datetime.now(), datetime(year, 12, 31)])
	# year = today.year

	year_start = datetime(year, 1, 1)

	reading_entries = helpers.get_db_entries(start=year_start, end=year_end, projects=['Reading'])

	reading_time = 0

	for entry in reading_entries:
		reading_time += entry.dur

	days = (year_end - year_start).days + 1
	average_daily_reading_time = reading_time / days

	return average_daily_reading_time


def get_all_reading_years():
	first_year = get_readthroughs(year=False)[-1].start_date.year
	current_year = datetime.now().year

	years = list(range(first_year, current_year+1))
	years.reverse()

	return years

def get_history_year_data():
	data = []
	summed_values = {
			'number_of_books': 0,
			'average_days_per_book': 0,
			'average_time_per_book': 0,
			'total_reading_time': 0,
			'average_daily_reading_time': 0,
			'raw_average_time_per_book': 0,
			'raw_average_days_per_book': 0,
			'raw_average_daily_reading_time': 0
	}

	years = get_all_reading_years()
	number_of_years = len(years)

	for year in years:
		
		# These are the readthroughs which were completed in the target year.
		readthroughs = get_readthroughs(year=year,
										status='complete',
										include_readthroughs_completed_in_next_year=False
									)

		number_of_books = len(readthroughs)

		average_days_per_book = 0
		average_time_per_book = 0
		#average_daily_reading_time = 0
		total_reading_time = 0

		for readthrough in readthroughs:
			average_days_per_book += readthrough.get_total_days_reading(raw = True)
			average_time_per_book += readthrough.get_current_reading_time(raw = True)
			#average_daily_reading_time += readthrough.get_average_daily_reading_time(raw = True)
			total_reading_time += readthrough.get_current_reading_time(raw = True)


		divider = number_of_books if number_of_books > 0 else 1

		average_days_per_book /= divider
		average_time_per_book /= divider
		#average_daily_reading_time /= number_of_books

		raw_average_daily_reading_time = get_average_daily_reading_time(year)
		raw_average_time_per_book = average_time_per_book
		raw_average_days_per_book = average_days_per_book
		#raw_total_reading_time = total_reading_time

		summed_values['number_of_books'] += number_of_books
		summed_values['average_days_per_book'] += average_days_per_book
		summed_values['average_time_per_book'] += average_time_per_book
		summed_values['average_daily_reading_time'] += raw_average_daily_reading_time
		summed_values['total_reading_time'] += total_reading_time

		summed_values['raw_average_days_per_book'] += raw_average_days_per_book
		summed_values['raw_average_time_per_book'] += raw_average_time_per_book
		summed_values['raw_average_daily_reading_time'] += raw_average_daily_reading_time
		#summed_values['raw_total_reading_time'] += raw_total_reading_time

		year_data = {}
		year_data['raw_average_days_per_book'] = raw_average_days_per_book
		year_data['raw_average_time_per_book'] = raw_average_time_per_book
		#year_data['raw_total_reading_time'] = raw_total_reading_time

		average_days_per_book = str(round(average_days_per_book)) + ' days'
		average_time_per_book = helpers.format_milliseconds(average_time_per_book, days=True)
		#average_daily_reading_time = helpers.format_milliseconds(average_daily_reading_time, days=False)
		total_reading_time = helpers.format_milliseconds(total_reading_time, days=True)
		average_daily_reading_time = helpers.format_milliseconds(raw_average_daily_reading_time, days=False)

		year_data['year'] = year
		year_data['number_of_books'] = number_of_books
		year_data['average_days_per_book'] = average_days_per_book
		year_data['average_time_per_book'] = average_time_per_book
		year_data['average_daily_reading_time'] = average_daily_reading_time
		year_data['total_reading_time'] = total_reading_time


		data.append(year_data)

	for key, value in summed_values.items():
		
		summed_values[key] = summed_values[key] / number_of_years

		if not key in ['raw_average_time_per_book', 'raw_average_days_per_book']:
			summed_values[key] = round(summed_values[key])

		if key == 'average_days_per_book':
			summed_values[key] = str(summed_values[key]) + ' days'
			continue

		if key in ['average_time_per_book', 'total_reading_time', 'average_daily_reading_time']:
			summed_values[key] = helpers.format_milliseconds(summed_values[key])
			continue

		else:
			continue

	summed_values['year'] = 'Average'
	# data.insert(0, summed_values)
	data.append(summed_values)


	return data

@bp.route("/reading/history_year_data", methods=['POST'])
def history_year_data():
	data = []

	years = get_all_reading_years()

	for year in years:
	
		readthroughs = get_readthroughs(year=year, status='complete', include_readthroughs_completed_in_next_year=False)
		number_of_books = len(readthroughs)

		if not len(readthroughs):
			continue

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

	return jsonify(
		html = render_template('reading/history_year.html', data=data)
	)
	

def get_all_books():
	start = perf_counter()

	query = Book.query
	books = query.all()
	
	end = perf_counter()
	print(f'get_all_books: {round(end - start, 2)} seconds.' )

	return books

# Use a status of 'active' to only get currently read books. Or a status of 'complete' for finished books.
def get_readthroughs(status='all', title=False, year=False, include_readthroughs_completed_in_next_year=True, order_by='start'):
	start = perf_counter()
	
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
		current_year = datetime.now().year

		if not year == current_year:
			query = query.filter(Readthrough.end_date != None)

		query = query.filter( (Readthrough.start_date <= year_end) | (Readthrough.end_date == None))
		query = query.filter((Readthrough.end_date >= year_start) | (Readthrough.end_date == None))
		
		if not include_readthroughs_completed_in_next_year:
			query = query.filter((Readthrough.end_date <= year_end) | (Readthrough.end_date == None))

	if (order_by == 'start'):
		query = query.order_by(Readthrough.start_date.desc())
	else:
		query = query.order_by(Readthrough.end_date.desc())

	readthroughs = query.all()

	end = perf_counter()
	print(f'Got readthroughs in {round(end - start, 2)} seconds.')

	return readthroughs

@bp.route('/reading/populate_books', methods=['POST'])
def populate_books():
	print('\n------------Populating books...')
	start = perf_counter()

	# All the entires with a project of 'Reading'.
	db_reading_entries = helpers.get_db_entries(projects=['Reading'])

	# Create a list of all the unique books.
	unique_books = set()
	for entry in db_reading_entries:
		unique_books.add(entry.description)

	# Create a book for each unique book.
	for title in unique_books:
		create_book(title)

	db.session.commit()

	end = perf_counter()

	print(f'Populated books in {round(end - start, 2)} seconds.')

	# Return 200 status code.
	if request.method == 'POST':
		return '', 200

# Create a book if it doesn't already exist.
def create_book(title):
	existing_book = get_book(title)

	if existing_book:
		return existing_book

	db_book = Book(
		title = title
	)

	db.session.add(db_book)

	return db_book

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

	if data['end_date']:
		db_readthrough.end_date = data['end_date']

	db.session.add(db_readthrough)

	db.session.commit()

	return db_readthrough


def get_book(title):
	query = Book.query.filter(func.lower(Book.title).contains(title.lower()))

	book = query.all()

	return book

# Check that the cover for each readthrough exists.
# If not, we'll acquire the cover now, so it will be ready before the page loads.
def verify_covers(readthroughs):
	start = perf_counter()

	for readthrough in readthroughs:

		readthrough.book.get_cover()

	stop = perf_counter()
	print(f'Verified covers in {round(stop - start, 2)} seconds.')