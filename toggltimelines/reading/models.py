from flask import current_app
from sqlalchemy import func

import math, pytz
from datetime import datetime, timedelta, date
import os.path
import urllib.request
from PIL import Image
from time import perf_counter

from toggltimelines.timelines.models import Entry
from toggltimelines import db
from toggltimelines import helpers

class Book(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(200))
	fiction = db.Column(db.Boolean)
	readthroughs = db.relationship('Readthrough', backref='book')
	image_url = db.Column(db.String(200))

	def get_cover(self):
		file_location = self.get_cover_location()

		# If the cover exists, return the local file.
		if os.path.isfile(file_location):
			return self.get_cover_url()

		# Check if the book has an cover image URL.
		if self.image_url:
			print(f'Book: {self.title} does NOT have a local cover image.\nDownloading from {self.image_url}...\n')

			# Try to download the cover image.
			if self.update_cover(self.image_url):
				return file_location
			else:
				return self.image_url

		# Fallback to placeholder image.
		return '/static/img/cover_placeholder.png'

	def update_cover(self, url):
		start = perf_counter()

		self.image_url = url
		db.session.commit()

		file_location = self.get_cover_location()

		try:
			urllib.request.urlretrieve(url, file_location)
			image = Image.open(file_location)

			original_width, original_height = image.size

			ratio = original_height / original_width

			new_width = min([original_width, 290])
			new_height = round(new_width * ratio)


			image_small = image.resize((new_width, new_height), Image.ANTIALIAS)
			image_small.save(file_location)

		except:
			return False

		stop = perf_counter()
		print(f'Cover updated in {stop-start} seconds.')
		return True

	def get_cover_location(self):
		covers_directory = current_app.covers_directory
		filepath = covers_directory + self.get_cover_filename()

		return filepath

	def get_cover_url(self):
		return '/static/img/covers/' + self.get_cover_filename()

	def get_cover_filename(self):
		filename = "".join([c for c in self.title if c.isalpha() or c.isdigit() or c==' ']).rstrip() + '.jpg'
		filename = filename.replace(' ', '-')

		return filename

	# Return the date for either the first or last entry of a book.
	def get_default_readthrough_date(self, start_or_end, dt=False):
		reading_entries = self.get_all_reading_entries()

		if not reading_entries:
			return date.today()

		target_entry = reading_entries[0] if start_or_end == 'start' else reading_entries[-1]

		if dt:
			return target_entry.start

		return target_entry.start.strftime('%Y-%m-%d')

	def get_all_reading_entries(self):
		entries = helpers.get_db_entries(description=self.title)

		return entries

		entries = Book.query.filter(func.lower(Entry.description).contains(self.title.lower()))




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

	def __repr__(self):
		return "<Readthrough (Book: " + self.book.title + ") (Start: " + str(self.start_date) + ") (End: " + str(self.end_date) + ")>"

	def format_date(self, dt):
		date_format = '%a %-d %b %Y'

		if not dt:
			return ''

		return dt.strftime(date_format)

	def is_physical(self):
		return True if self.book_format == 'physical' else False

	def is_digital(self):
		return True if self.book_format == 'digital' else False

	# i.e. The unit for physical books is a page, while for digital it is a percentage.
	def get_position_unit(self, plural=False):

		if self.book_format == 'physical':
			return 'pages' if plural else 'page'

		if self.book_format == 'digital':
			return 'percent' if plural else 'percentage'

		#return 'page' if self.book_format == 'physical' else 'percentage'

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

	def get_average_daily_progress(self, raw = False, force_percentage=False):
		book_format = self.book_format

		if book_format == 'digital':
			completed_units = self.current_position
		elif book_format == 'physical':
			
			if force_percentage:
				completed_units = self.get_completion_percentage()
			else:
				completed_units = self.current_position - self.first_page + 1

		days_reading = self.get_total_days_reading(raw=True)

		average_daily_progress = completed_units / days_reading

		if raw:
			return average_daily_progress

		average_daily_progress = round(average_daily_progress, 1)

		if book_format == 'digital' or force_percentage:
			return str(average_daily_progress) + '%'
		else:
			return str(average_daily_progress) + ' pages'

	def get_end_date(self):
		if self.end_date:
			return self.end_date
		else:
			today = helpers.get_current_datetime_in_user_timezone().replace(tzinfo=None)
			return today

	def get_total_days_reading(self, raw=False):
		readthrough_complete = self.is_readthrough_complete()

		if readthrough_complete:
			end_date = self.get_end_date()
		else:
			end_date = helpers.get_current_datetime_in_user_timezone().replace(tzinfo=None)

		days_reading = (end_date - self.start_date).days + 1 # Add 1 since we want to also count the first day as a "reading day".

		if days_reading <= 0:
		 	days_reading = 1

		if raw:
			return days_reading

		day_word = 'day' if days_reading == 1 else 'days'

		return f"{days_reading} {day_word}"

	def get_remaining_units(self):
		if self.book_format == 'digital':
			return 100 - self.current_position
		elif self.book_format == 'physical':
			#return self.last_page - self.first_page - self.current_position
			return self.last_page - self.current_position

	def get_estimated_completion_date(self, raw=False):
		average_daily_progress = self.get_average_daily_progress(raw=True)

		if average_daily_progress == 0:
			estimated_completion_date = False
		else:
			remaining_units = self.get_remaining_units()

			remaining_days = math.ceil(remaining_units / average_daily_progress)

			today = helpers.get_current_datetime_in_user_timezone().replace(tzinfo=None)

			estimated_completion_date = today + timedelta(days=remaining_days)

		if raw:
			return estimated_completion_date

		if not estimated_completion_date:
			return 'Never'

		date_format = '%a %-d %b %Y'

		return estimated_completion_date.strftime(date_format)

	def get_all_readthrough_entries(self):
		entries = helpers.get_db_entries(start=self.start_date, end=self.end_date, description=self.book.title)
		return entries

	# Get the total current time spend on this readthrough. (Raw time in milliseconds)
	def get_current_reading_time(self, raw = False):
		reading_entries = self.get_all_readthrough_entries()

		total_milliseconds = 0
		for entry in reading_entries:
			total_milliseconds += entry.dur

		if raw:
			return total_milliseconds
		else:
			return helpers.format_milliseconds(total_milliseconds, days=False)

	# Get the daily average time spent reading on this readthrough. (Average time in milliseconds)
	def get_average_daily_reading_time(self, raw=False):
		total_reading_time = self.get_current_reading_time(raw = True)
		total_days_reading = self.get_total_days_reading(raw=True)

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

			if milliseconds == 0:
				return 'None'

			return helpers.format_milliseconds(milliseconds, days=False)

	# Return a class name describing whether a reading goal is complete.
	# By default this considered the daily reading-time goal.
	# But can also consider the daily time required for the date goal, using the goal_type argument.
	def get_reading_goal_completion_class(self, goal_type='progress'):
		if goal_type == 'progress' and not self.daily_reading_goal:
			return 'no-reading-goal'

		elif goal_type == 'end_date' and not self.target_end_date:
			return 'no-reading-goal'

		if goal_type == 'end_date':
			goal_value = self.get_required_daily_time_for_target_date(raw=True) / (1000 * 60)
		else:
			goal_value = False

		goal_complete = self.is_daily_reading_goal_complete(goal_value)

		if goal_complete:
			return 'reading-goal-complete'
		else:
			return 'reading-goal-incomplete'

	def get_target_end_date_completion_class(self):
		if not self.target_end_date:
			return 'no-end-date'

	# Can be passed a value to test against, instead of using the daily_reading_goal attribute.
	def is_daily_reading_goal_complete(self, daily_goal=False):
		seconds_today = self.get_readthrough_time_today(raw=True) / 1000
		minutes_today = seconds_today / 60

		if not daily_goal:
			daily_goal = self.daily_reading_goal

		if not daily_goal:
			return False

		return True if minutes_today > daily_goal else False

	def get_completion_percentage(self):
		if self.book_format == 'digital':
			return self.current_position

		pages_to_read = self.last_page - self.first_page + 1 # Adding one, since we do also read the first page.
		relative_position = self.current_position - self.first_page + 1

		percentage = round((relative_position / pages_to_read) * 100, 1)

		return percentage

	# Returns a hue to be used by CSS's hsl function to give a color.
	def get_completion_hue(self):
		percentage = self.get_completion_percentage() / 100
		hue = ((percentage)*120)

		return hue

	def get_estimated_completion_time(self, raw=False):
		current_reading_time = self.get_current_reading_time(raw=True)
		current_percentage = self.get_completion_percentage()

		if current_percentage == 0:
			time_per_percentage = 24*60*60*1000 # If the user hasn't read any yet,
												# default to 24 hours per percentage.
		else:
			time_per_percentage = current_reading_time / current_percentage

		estimated_completion_time = time_per_percentage * 100

		if raw:
			return estimated_completion_time
		else:
			return helpers.format_milliseconds(estimated_completion_time, days=False)

	def get_remaining_reading_time(self, raw=False):
		estimated_completion_time = self.get_estimated_completion_time(raw=True)
		current_reading_time = self.get_current_reading_time(raw=True)

		remaining_reading_time = estimated_completion_time - current_reading_time

		if raw:
			return remaining_reading_time
		else:
			return helpers.format_milliseconds(remaining_reading_time, days=False, short_labels=True)

	def get_time_per_position_unit(self, raw=False, force_percentage=False):
		total_reading_time = self.get_current_reading_time(raw=True)
		current_position = self.current_position

		if self.book_format == 'physical':

			if force_percentage:
				current_position = self.get_completion_percentage()
			else:
				current_position = current_position - self.first_page + 1

		if current_position == 0:
			if raw:
				return False
			else:
				return 'N/A'

		average_time_in_milliseconds = total_reading_time / current_position

		if raw:
			return average_time_in_milliseconds
		else:
			return helpers.format_milliseconds(average_time_in_milliseconds, include_seconds=True)

	def get_target_end_date(self, raw=False):
		target_end_date = self.target_end_date

		if raw:
			return target_end_date

		if not target_end_date:
			return 'None'

		date_format = '%a %-d %b %Y'

		return target_end_date.strftime(date_format)

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
			new_position = max(self.first_page, new_position)

		self.current_position = new_position

		if self.is_readthrough_complete():
			self.end_date = self.get_last_reading_date()
		else:
			self.end_date = None

		return new_position

	def get_last_reading_date(self):
		return self.get_all_readthrough_entries()[-1].end

	def update_date(self, new_date, date_type):
		if new_date == '':
			dt = None
		else:
			dt = datetime.strptime(new_date, '%Y-%m-%d')

		if date_type == 'start':
			self.start_date = dt

			if dt and self.end_date and self.start_date > self.end_date:
				self.end_date = dt

			return self.start_date
		
		elif date_type == 'end':
			self.end_date = dt

			if dt and self.end_date < self.start_date:
				self.start_date = dt

			return self.end_date

		elif date_type == 'target_end':
			
			if dt and dt < self.start_date:
				dt = self.start_date

			if dt:
				dt = dt.replace(hour=23, minute=59, second=59)

			self.target_end_date = dt

			return self.target_end_date

	def get_days_until_target_end(self, raw=False):
		today = helpers.get_current_datetime_in_user_timezone().replace(tzinfo=None)

		days = (self.target_end_date - today).days + 1

		if raw:
			return days

		return self.pluralize_days(days)

	# Returns units per day
	def get_required_daily_units_for_target_end(self, raw=False):
		remaining_days = self.get_days_until_target_end(raw=True)
		remaining_units = self.get_remaining_units()

		if not remaining_days:
			remaining_days = 1

		units_per_day = remaining_units / remaining_days

		if raw:
			return units_per_day

		if self.book_format == 'digital':
			unit_name = '%'
			decimal_digits = 1
		elif self.book_format == 'physical':
			unit_name = ' page' if units_per_day == 1 else ' pages'
			decimal_digits = 0

		units_per_day = round(units_per_day, decimal_digits)

		if self.book_format == 'physical':
			units_per_day = int(units_per_day)

		return f"{units_per_day}{unit_name}"

	def get_daily_reading_goal(self, raw=False):
		goal_in_minutes = self.daily_reading_goal

		if raw:
			if not goal_in_minutes:
				goal_in_minutes = 0
			return goal_in_minutes * 60 * 1000

		if not goal_in_minutes:
			minutes_string = ''
			minutes_display = 'None'
			data_minutes = 0
		else:
			minutes_string = 'minutes'
			minutes_display = goal_in_minutes
			data_minutes = goal_in_minutes

		return f"<span class='hidden-input' data-endpoint='update_daily_reading_goal' data-minutes='{data_minutes}'>{minutes_display}</span> {minutes_string}"

	def update_daily_reading_goal(self, goal_in_minutes):
		if not goal_in_minutes or int(goal_in_minutes) < 0:
			goal_in_minutes = None

		self.daily_reading_goal = goal_in_minutes

		return self.daily_reading_goal

	# Top section
	def get_required_daily_time_for_target_date(self, raw=False):
		required_daily_units = self.get_required_daily_units_for_target_end(raw=True)

		time_per_unit = self.get_time_per_position_unit(raw=True)

		daily_time_in_milliseconds = required_daily_units * time_per_unit

		if raw:
			return daily_time_in_milliseconds

		return helpers.format_milliseconds(daily_time_in_milliseconds)

	#Resulting end date (Bottom section)
	def get_daily_reading_goal_end_estimate(self, raw=False):
		daily_goal = self.get_daily_reading_goal(raw=True)
		time_per_unit = self.get_time_per_position_unit(raw=True)

		units_per_day = daily_goal / time_per_unit

		remaining_units = self.get_remaining_units()

		remaining_days = remaining_units / units_per_day

		today = helpers.get_current_datetime_in_user_timezone().replace(tzinfo=None, hour=0, minute=0, second=0)
		today = today - timedelta(seconds = 1) # We actually want this to be the very end of yesterday.
											   # This seems to get it to match up with the estimate
											   # given by the end date goal.
											   # (Hence subtracting one second).

		estimate_end_date = today + timedelta(days=remaining_days)

		if raw:
			return estimate_end_date

		return self.format_date(estimate_end_date)

	# Return the current streak for the daily reading goal.
	def get_current_streak(self, raw=False):
		streak = 0
		goal_in_minutes = self.daily_reading_goal
		goal_in_milliseconds = goal_in_minutes * 60 * 1000
		
		date_string_format = '%Y-%m-%d'

		entries = self.get_all_readthrough_entries()

		sorted_by_day = helpers.sort_db_entries_by_day(entries, return_as_dict=True)

		target_date = helpers.get_current_datetime_in_user_timezone() - timedelta(days=1) # Yesterday

		goal_complete_on_date = True

		# We start on yesterday, and see how far back we can go before we find a day where the goal was not met.
		while goal_complete_on_date:
			date_string = target_date.strftime(date_string_format)

			if date_string in sorted_by_day.keys():
				time_on_date = 0
				for entry in sorted_by_day[date_string]['entries']:
					time_on_date += entry.dur

				if time_on_date <= goal_in_milliseconds:
					goal_complete_on_date = False
				else:
					target_date = target_date - timedelta(days=1)
					streak += 1
			else:
				goal_complete_on_date = False


		# Now we check if the goal was met today. If so, add today to the streak.
		# (We do it this way since we don't want to show the streak as broken just because today's goal hasn't been met yet.)
		today_string = helpers.get_current_datetime_in_user_timezone().strftime(date_string_format)

		milliseconds_today = 0

		if today_string in sorted_by_day.keys():
			for entry in sorted_by_day[today_string]['entries']:
				milliseconds_today += entry.dur

			if milliseconds_today >= goal_in_milliseconds:
				streak += 1

		if raw:
			return streak

		return self.pluralize_days(streak)

	def get_estimated_total_days(self, raw=False):
		estimated_completion_date = self.get_estimated_completion_date(raw=True)

		if not estimated_completion_date:
			return False if raw else '∞'
		
		days = (estimated_completion_date - self.start_date).days + 1

		if raw:
			return days

		return_string = self.pluralize_days(days)

		return return_string

		percentage = round(days*100/365, 1)

		return f"{return_string} <span>({percentage}% of year)</span>"

	def get_estimated_year_percentage(self, raw=False):
		estimated_days = self.get_estimated_total_days(raw=True)

		percentage = round(estimated_days*100/365, 1)

		return percentage

	def get_current_year_percentage(self, raw=False):
		current_days = self.get_total_days_reading(raw=True)
		percentage = round(current_days*100/365, 1)
		return percentage		

	def pluralize_days(self, number):
		string = f"{number} day"

		if number != 1:
			string += "s"

		return string

	def get_average_time_per_session(self, raw=False):
		if hasattr(self, 'average_time_per_session'):
			average_time_per_session = self.average_time_per_session			
		else:
			number_of_sessions = self.get_number_of_sessions()

			# Rough fix to avoid dividing by zero.
			if not number_of_sessions:
				number_of_sessions = 1

			reading_time = self.get_current_reading_time(raw=True)
			average_time_per_session = reading_time / number_of_sessions

		if raw:
			return average_time_per_session
		
		return helpers.format_milliseconds(average_time_per_session, days=False, include_seconds=True)

	def get_number_of_sessions(self):
		entries = self.get_all_readthrough_entries()

		number_of_sessions = 0

		max_pause_within_session = timedelta(minutes=5)

		for i, entry in enumerate(entries):
			if i == 0:
				number_of_sessions += 1
			else:
				this_entry_start = entry.start
				previous_entry_end = entries[i-1].end

				pause_between_entries = this_entry_start - previous_entry_end


				if pause_between_entries > max_pause_within_session:
					number_of_sessions += 1

		return number_of_sessions
	
	def get_estimated_total_sessions(self):
		average_time_per_session = self.get_average_time_per_session(raw=True)
		estimated_completion_time = self.get_estimated_completion_time(raw=True)

		if not average_time_per_session:
			average_time_per_session = 1

		return round(estimated_completion_time / average_time_per_session)

	def get_remaining_sessions(self):
		current_sessions = self.get_number_of_sessions()
		estimated_total_sessions = self.get_estimated_total_sessions()

		return estimated_total_sessions - current_sessions