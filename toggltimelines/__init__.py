import os

import click
from flask import Flask
from flask import current_app
from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy

from datetime import datetime, timedelta
import pytz
import csv
import requests

#from toggl.TogglPy import Toggl

import sys
print("Python version")
print (sys.version)
print("Version info.")
print (sys.version_info)


__version__ = (1, 0, 0, "dev")

db = SQLAlchemy()

app = current_app


def create_app(test_config=None):
	"""Create and configure an instance of the Flask application."""
	app = Flask(__name__, instance_relative_config=True)

	app.config.from_object("config.DevelopmentConfig")

	# Use this to store the User's Toggl data if we get it via API request.
	app.user_toggl_data = False

	from toggltimelines import MyTogglPy
	app.toggl = MyTogglPy.MyTogglPy()
	app.toggl.setAPIKey(app.config['API_KEY'])

	# some deploy systems set the database url in the environ
	db_url = os.environ.get("DATABASE_URL")

	if db_url is None:
		# default to a sqlite database in the instance folder
		db_path = os.path.join(app.instance_path, "toggltimelines.sqlite")
		db_url = f"sqlite:///{db_path}"
		# ensure the instance folder exists
	os.makedirs(app.instance_path, exist_ok=True)

	app.config.from_mapping(
		# default secret that should be overridden in environ or config
		SECRET_KEY=os.environ.get("SECRET_KEY", "dev"),
		SQLALCHEMY_DATABASE_URI=db_url,
		SQLALCHEMY_TRACK_MODIFICATIONS=False,
	)

	if test_config is None:
		# load the instance config, if it exists, when not testing
		app.config.from_pyfile("config.py", silent=True)
	else:
		# load the test config if passed in
		app.config.update(test_config)

	# initialize Flask-SQLAlchemy and the init-db command
	db.init_app(app)

	app.cli.add_command(init_db_command)
	app.cli.add_command(toggl_sync_all)
	# app.cli.add_command(mytest)
	app.cli.add_command(update_book_covers)

	# Timeline Page
	from toggltimelines import timelines
	app.register_blueprint(timelines.bp)
	app.add_url_rule("/", endpoint="index")
	app.add_url_rule("/timelines", endpoint="timelines")

	# Comparison Page
	from toggltimelines import comparison
	app.register_blueprint(comparison.bp)
	app.add_url_rule("/comparison", endpoint="comparison")

	# Graphing Page
	from toggltimelines import frequency
	app.register_blueprint(frequency.bp)
	app.add_url_rule("/frequency", endpoint="frequency")

	# Reading Page
	from toggltimelines import reading
	app.register_blueprint(reading.bp)
	app.add_url_rule("/reading", endpoint="reading")

	# Sync Page
	from toggltimelines import sync
	app.register_blueprint(sync.bp)
	app.add_url_rule("/sync", endpoint="sync")

	app.failed_image_api_search = False
	app.covers_directory = os.path.dirname(os.path.realpath(__file__)) + '/static/img/covers/'

	return app

def init_db():
	#db.drop_all()
	db.create_all()

@click.command("init-db")
@with_appcontext
def init_db_command():
	init_db()
	click.echo("Initialized the database.")


@click.command("toggl-sync-all")
@with_appcontext
def toggl_sync_all():
	import_complete = False
	days_per_request = 250

	i = 0

	end = datetime.now()

	start = end - timedelta(days=days_per_request)

	while not import_complete:
		print(f"Start: {start}")
		print(f"End: {end}")

		entries = helpers.toggl_sync(start, end)
		print(len(entries))

		i+=1
		
		if len(entries) == 0:
			import_complete = True

		end = start - timedelta(days=1)
		start = end - timedelta(days=days_per_request)


from toggltimelines.reading.models import Book, Readthrough
from toggltimelines.timelines.models import Entry, Project, Tag, Client

import pprint
pp = pprint.PrettyPrinter(indent=4)

# Use Bing API to find covers for books which don't already have one.
@click.command('update-book-covers')
@with_appcontext
def update_book_covers():
	subscription_key = app.config['BING_API_KEY']
	search_url = "https://api.cognitive.microsoft.com/bing/v7.0/images/search"
	headers = {"Ocp-Apim-Subscription-Key" : subscription_key}

	books_without_cover = Book.query.filter(Book.image_url == None).all()

	if not books_without_cover:
		print("All books have covers.")

	for book in books_without_cover:
		print(f"Searching for cover for {book.title}...")

		params  = {"q": book.title + ' book cover'}
		response = requests.get(search_url, headers=headers, params=params)
		search_results = response.json()

		if not len(search_results):
			print (f"No cover found for {book.title}")
			break

		cover_url = False
		for result in search_results['value']:
			if result['height'] > result['width']: # Check that the image is taller than it is wide.
				cover_url = result['contentUrl']
				break

		if not cover_url:
			cover_url = search_results['value'][0]['contentUrl']

		print(f"Cover found:")
		print(cover_url)
		print('')

		book.image_url = cover_url

	db.session.commit()