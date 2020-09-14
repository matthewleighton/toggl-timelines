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

	def format_date(self, dt):
		date_format = '%a %-d %b %Y'
		return dt.strftime(date_format)

	# i.e. The unit for physical books is a page, while for digital it is a percentage.
	def get_position_unit(self):
		return 'page' if self.book_format == 'physical' else 'percentage'

	def current_position_label(self):
		if self.book_format == 'digital':
			return 'Current percentage'
		elif self.book_format == 'physical':
			return 'Current page'

	def format_current_position(self, html=False):
		position = str(self.current_position)

		html_output = f"<span class='hidden-input' data-endpoint='update_position'>{position}</span>"

		if self.book_format == 'digital':
			
			if html:
				return f"{html_output}%"
			else:
				return f"{position}%"
				
		elif self.book_format == 'physical':
			
			equivalent_percentage = str(self.get_completion_percentage()) + '%' 

			if html:
				return f"Page {html_output} ({equivalent_percentage})"
			else:
				return f"Page {position} ({equivalent_percentage})"

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

	def get_end_date(self):
		if self.end_date:
			return self.end_date
		else:
			today = helpers.get_current_datetime_in_user_timezone().replace(tzinfo=None)
			return today

	def get_total_days_reading(self):
		readthrough_complete = self.is_readthrough_complete()

		if readthrough_complete:
			end_date = self.get_end_date()
		else:
			end_date = helpers.get_current_datetime_in_user_timezone().replace(tzinfo=None)

		days_reading = (end_date - self.start_date).days

		if days_reading <= 0:
			days_reading = 1

		return days_reading

	def get_remaining_units(self):
		if self.book_format == 'digital':
			return 100 - self.current_position
		elif self.book_format == 'physical':
			return self.last_page - self.first_page - self.current_position

	def get_estimated_completion_date(self, raw_datetime=False):
		average_daily_progress = self.get_average_daily_progress(raw=True)

		if average_daily_progress == 0:
			# Arbitrary date in far future.
			estimated_completion_date = datetime(3000, 1, 1)
		else:
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

		pages_to_read = self.last_page - self.first_page + 1 # Adding one, since we do also read the first page.

		percentage = round((self.current_position / pages_to_read) * 100, 1)

		return percentage

	def get_estimated_completion_time(self, raw=False):
		current_reading_time = self.get_current_reading_time(raw=True)
		current_percentage = self.get_completion_percentage()

		if current_percentage == 0:
			return 'N/A'
		else:
			time_per_percentage = current_reading_time / current_percentage

			estimated_completion_time = time_per_percentage * 100

		if raw:
			return estimated_completion_time
		else:
			return helpers.format_milliseconds(estimated_completion_time, days=False)

	def get_time_per_position_unit(self, raw=False):
		total_reading_time = self.get_current_reading_time(raw=True)
		current_position = self.current_position

		if current_position == 0:
			return 'N/A'

		average_time_in_milliseconds = total_reading_time / current_position

		if raw:
			return average_time_in_milliseconds
		else:
			return helpers.format_milliseconds(average_time_in_milliseconds, include_seconds=True)

	def get_target_end_date(self):
		return 'Some date'

	# Return True/False whether a readthrough has been completed or not.
	def is_readthrough_complete(self):
		book_format = self.book_format
		current_position = self.current_position

		if book_format == 'digital' and current_position == 100:
			return True
		elif book_format == 'physical' and current_position == self.last_page:
			return True

		return False

	def update_position(self, new_position):
		new_position = int(new_position)

		if new_position < 0:
			new_position = 0

		if self.book_format == 'digital':
			new_position = min(100, new_position)
		elif self.book_format == 'physical':
			new_position = min(self.last_page, new_position)

		self.current_position = new_position

		if self.is_readthrough_complete():
			self.end_date = helpers.get_current_datetime_in_user_timezone()
		else:
			self.end_date = None

		return new_position

	def update_date(self, new_date, date_type):
		dt = datetime.strptime(new_date, '%Y-%m-%d')
		
		if date_type == 'start':
			self.start_date = dt

			if self.start_date > self.end_date:
				self.end_date = dt

			return self.start_date
		elif date_type == 'end':
			self.end_date = dt

			if self.end_date < self.start_date:
				self.start_date = dt

			return self.end_date