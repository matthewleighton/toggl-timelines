from flask import current_app
from sqlalchemy import func

import math, pytz
from datetime import datetime, timedelta

from toggltimelines.timelines.models import Entry
from toggltimelines import db
from toggltimelines import helpers

class Book(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(200))
	fiction = db.Column(db.Boolean)
	readthroughs = db.relationship('Readthrough', backref='book')
	image_url = db.Column(db.String(200))



class Readthrough(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
	book_format = db.Column(db.String(10))
	first_page = db.Column(db.Integer)
	last_page = db.Column(db.Integer)
	current_position = db.Column(db.Integer)

	start_date = db.Column(db.DateTime(timezone=True))
	end_date = db.Column(db.DateTime(timezone=True))
	target_end_date = db.Column(db.DateTime(timezone=True))
	daily_reading_goal = db.Column(db.Integer)

	def format_start(self):
		date_format = '%a %-d %b %Y'
		return self.start_date.strftime(date_format)

	# i.e. The unit for physical books is a page, while for digital it is a percentage.
	def get_position_unit(self):
		return 'page' if self.book_format == 'physical' else 'percentage'

	def current_position_label(self):
		if self.book_format == 'digital':
			return 'Current percentage'
		elif self.book_format == 'physical':
			return 'Current page'

	def format_current_position(self):
		if self.book_format == 'digital':
			return str(self.current_position) + '%'
		elif self.book_format == 'physical':
			
			equivalent_percentage = str(self.get_completion_percentage()) + '%' 

			return f"Page {str(self.current_position)} ({equivalent_percentage})"

	def get_average_daily_progress(self, raw = False):
		book_format = self.book_format

		if book_format == 'digital':
			completed_units = self.current_position
		elif book_format == 'physical':
			completed_units = self.current_position - self.first_page

		days_reading = self.get_total_days_reading()

		average_daily_progress = round(completed_units / days_reading, 1)

		if raw:
			return average_daily_progress

		if book_format == 'physical':
			return str(average_daily_progress) + ' pages'
		elif book_format == 'digital':
			return str(average_daily_progress) + '%'

	def get_total_days_reading(self):
		today = helpers.get_current_datetime_in_user_timezone().replace(tzinfo=None)

		return (today - self.start_date).days

	def get_remaining_units(self):
		if self.book_format == 'digital':
			return 100 - self.current_position
		elif self.book_format == 'physical':
			return self.last_page - self.first_page - self.current_position

	def get_estimated_completion_date(self, raw_datetime=False):
		average_daily_progress = self.get_average_daily_progress(raw=True)

		remaining_units = self.get_remaining_units()

		remaining_days = math.ceil(remaining_units / average_daily_progress)

		today = helpers.get_current_datetime_in_user_timezone().replace(tzinfo=None)

		estimated_completion_date = today + timedelta(days=remaining_days)

		if raw_datetime:
			return estimated_completion_date

		date_format = '%a %-d %b %Y'

		return estimated_completion_date.strftime(date_format)

	def get_all_readthrough_entries(self):
		query = Entry.query.filter(Entry.start >= self.start_date)
		query = query.filter(func.lower(Entry.description).contains(self.book.title.lower()))
		return query.all()

	# Get the total current time spend on this readthrough. (Raw time in milliseconds)
	def get_current_reading_time(self, raw = False):
		reading_entries = self.get_all_readthrough_entries()

		total_milliseconds = 0
		for entry in reading_entries:
			total_milliseconds += entry.dur

		total_milliseconds = total_milliseconds
		if raw:
			return total_milliseconds
		else:
			return helpers.format_milliseconds(total_milliseconds, days=False)

	# Get the daily average time spent reading on this readthrough. (Average time in milliseconds)
	def get_average_daily_reading_time(self, raw=False):
		total_reading_time = self.get_current_reading_time(raw = True)
		total_days_reading = self.get_total_days_reading()

		average = total_reading_time/total_days_reading

		if raw:
			return average
		else:
			return helpers.format_milliseconds(average, days=False)

	# Get the total time spend reading on the readthrough today (in the user's timezone).
	def get_readthrough_time_today(self, raw=False):
		today_user = helpers.get_current_datetime_in_user_timezone()
		
		today_user_start = today_user.replace(hour=0, minute=0, second=0)
		today_user_end = today_user.replace(hour=23, minute=59, second=59)

		today_utc_start = today_user_start.astimezone(tz=pytz.utc)
		today_utc_end = today_user_end.astimezone(tz=pytz.utc)

		query = Entry.query
		query = query.filter(func.lower(Entry.description).contains(self.book.title.lower()))
		query = query.filter(Entry.start >= today_utc_start)
		query = query.filter(Entry.start <= today_utc_end)

		entries = query.all()

		milliseconds = 0
		for entry in entries:
			milliseconds += entry.dur

		if raw:
			return milliseconds
		else:
			return helpers.format_milliseconds(milliseconds, days=False)

	def is_daily_reading_goal_complete(self):
		seconds_today = self.get_readthrough_time_today(raw=True) / 1000
		minutes_today = seconds_today / 60

		daily_goal = self.daily_reading_goal

		return True if minutes_today > daily_goal else False

	def get_completion_percentage(self):
		if self.book_format == 'digital':
			return self.current_position

		pages_to_read = self.last_page - self.first_page

		percentage = round((self.current_position / pages_to_read) * 100, 1)

		return percentage

	def get_estimated_completion_time(self, raw=False):
		current_reading_time = self.get_current_reading_time(raw=True)
		current_percentage = self.get_completion_percentage()

		time_per_percentage = current_reading_time / current_percentage

		estimated_completion_time = time_per_percentage * 100

		if raw:
			return estimated_completion_time
		else:
			return helpers.format_milliseconds(estimated_completion_time, days=False)