from flask import current_app

from toggltimelines import db
import pdb
import csv
import pytz
from datetime import datetime, timedelta

class Entry(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	description = db.Column(db.String(200))
	start = db.Column(db.DateTime(timezone=True))
	end = db.Column(db.DateTime(timezone=True))
	dur = db.Column(db.Integer)
	project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
	client = db.Column(db.String(50))
	project_hex_color = db.Column(db.String(7))
	#tags = db.relationship('Tag', secondary=tags, backref=db.backref('entries', lazy=True), lazy='select')
	user_id = db.Column(db.Integer)
	location = db.Column(db.String(50))

	def __repr__(self):
		return "<Entry (Description: " + self.description + ") (Start: " + str(self.start) + ") (End: " + str(self.end) + ") (Duration: " + str(self.dur) + ") (ID: " + str(self.id) + ")"

	# Make entries aware that they are expressed in UTC.
	def tzinfo_to_utc(self):
		self.start = self.start.replace(tzinfo=pytz.utc)
		self.end = self.end.replace(tzinfo=pytz.utc)

	def get_project_color(self):
		project = self.project

		if project:
			return project.project_hex_color
		else:
			return '#C8C8C8'

	def get_client_hex_color(self):
		return '#a6a6a6' #TODO

		hex_color_config = togglconfig.client_colors

		if self.client in hex_color_config.keys():
			return hex_color_config[self.client]
		else:
			return '#a6a6a6'

	def get_day_percentage(self):
		duration = self.dur/1000
		seconds_in_day = 86400

		return (duration/seconds_in_day)*100

	def get_start_percentage(self):
		start_time = self.get_local_start_time()
		seconds_since_midnight = (start_time - start_time.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds()

		return (seconds_since_midnight / 86400) * 100

	def get_local_start_time(self):
		timezone = pytz.timezone(self.location)

		new_dt = self.start.astimezone(tz=timezone)

		return new_dt

	def get_local_end_time(self):
		timezone = pytz.timezone(self.location)

		new_dt = self.start.astimezone(tz=timezone)

		return new_dt

	def get_tooltip(self):
		start_time = self.get_local_start_time().strftime('%H:%M')
		end_time = self.get_local_end_time().strftime('%H:%M')

		project = self.get_project_name()
		description = self.description
		duration = self.format_duration(self.dur)
		client = self.client

		return '<b>{0}</b>: {1}<br/>Client: {2}<br/>{3}-{4}<br/>{5}'.format(project, description, client, start_time, end_time, duration)

	def get_project_name(self):
		project = self.project

		if project:
			return project.project_name
		else:
			return 'No Project'

	# Turn an amount of milliseconds into "x hours, y minutes"
	def format_duration(self, milliseconds):
		seconds=(milliseconds/1000)%60
		seconds = int(seconds)
		minutes=(milliseconds/(1000*60))%60
		minutes = int(minutes)
		hours=(milliseconds/(1000*60*60))%24

		hours_string = ("%d hour, " % (hours)) if hours >=1 else ''
		if hours_string and hours >= 2:
			hours_string.replace('hour', 'hours')

		minutes_string = ("%d minutes" % (minutes))

		return hours_string + minutes_string

class Project(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	project_name = db.Column(db.String(50))
	project_hex_color = db.Column(db.String(7))
	entries = db.relationship('Entry', backref='project')

