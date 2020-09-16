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
from toggltimelines import helpers


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
	if request.json['end_date']:
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


	data = request.json

	return jsonify(render_template('reading/new_readthrough_success.html', readthrough=readthrough))

@bp.route("/reading/update_position", methods=['POST'])
def update_position():
	new_position = request.json['value']
	readthrough_id = request.json['readthrough_id']

	readthrough = Readthrough.query.get(readthrough_id)

	readthrough.update_position(new_position)

	db.session.commit()

	return jsonify(render_template('reading/readthrough.html', readthrough=readthrough))

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

	return jsonify(render_template('reading/readthrough.html', readthrough=readthrough))

@bp.route("/reading/update_daily_reading_goal", methods=['POST'])
def update_daily_reading_goal():
	new_goal = request.json['value']
	readthrough_id = request.json['readthrough_id']
	readthrough = Readthrough.query.get(readthrough_id)

	readthrough.update_daily_reading_goal(new_goal)

	db.session.commit()

	return jsonify(render_template('reading/readthrough.html', readthrough=readthrough))

@bp.route("/reading/search_books", methods=['POST'])
def search_books():
	title = request.json['title'].lower()

	books = Book.query.filter(func.lower(Book.title).contains(title)).all()

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

def get_all_books():
	query = Book.query
	books = query.all()

	return books

# Use a status of 'active' to only get currently read books. Or a status of 'complete' for finished books.
def get_readthroughs(status='all', title=False):
	query = Readthrough.query
	
	if status == 'active':
		query = query.filter(Readthrough.end_date == None)
	elif status == 'complete':
		query = query.filter(Readthrough.end_date != None)

	if title:
		query = query.join(Book).filter(func.lower(Book.title).contains(title.lower()))

	query = query.order_by(Readthrough.start_date.desc())

	active_readthroughs = query.all() # TODO: Actually filter to only get active readthroughs.


	return active_readthroughs

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
		title = title,
		image_url = get_book_cover_url(title)
	)

	db.session.add(db_book)

	return db_book

def get_book_cover_url(title):
	cover_placeholder = '/static/img/cover_placeholder.png'


	if current_app.failed_image_api_search:
		return cover_placeholder

	# Make image API request to Bing to find book covers.
	subscription_key = current_app.config['BING_API_KEY']
	search_url = "https://api.cognitive.microsoft.com/bing/v7.0/images/search"
	headers = {"Ocp-Apim-Subscription-Key" : subscription_key}
	
	params  = {"q": title + ' book cover'}

	response = requests.get(search_url, headers=headers, params=params)

	if response.status_code != 200:
		current_app.failed_image_api_search = True
		return cover_placeholder

	search_results = response.json()
	cover_url = False

	if not len(search_results['value']):
		return cover_placeholder

	for result in search_results['value']:
		if result['height'] > result['width']: # Check that the image is taller than it is wide.
			cover_url = result['contentUrl']
			break

	if not cover_url:
		cover_url = search_results['value'][0]['contentUrl']

	return cover_url

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