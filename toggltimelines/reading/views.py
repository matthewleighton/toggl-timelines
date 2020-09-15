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

from toggltimelines import db
from toggltimelines.reading.models import Book, Readthrough
from toggltimelines import helpers




bp = Blueprint("reading", __name__)

@bp.route("/reading")
def reading_home():

	populate_books()

	active_readthroughs = get_active_readthroughs()
	books = get_all_books()

	#print(books)

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

	#print(request.json)

	# print(request.json['start_date'])
	# print(request.json['end_date'])

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
		# Default the current position to the first page.
		readthrough_data['current_position'] = request.json['first_page']
	else:
		readthrough_data['current_position'] = 0 # Position defaults to 0% for digital book.


	create_readthrough(readthrough_data)

	db.session.commit()


	data = request.json

	return jsonify(data)

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

	print(title)

	books = Book.query.filter(func.lower(Book.title).contains(title)).all()

	print(books)
	return jsonify(render_template('reading/books_list.html', books=books))


def get_all_books():
	query = Book.query
	books = query.all()

	return books

def get_active_readthroughs():
	query = Readthrough.query

	active_readthroughs = query.all() # TODO: Actually filter to only get active readthroughs.

	return active_readthroughs

def populate_books():
	db_reading_entries = helpers.get_db_entries(projects=['Reading'])

	uinique_books = set()

	for entry in db_reading_entries:
		uinique_books.add(entry.description)

	for title in uinique_books:
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