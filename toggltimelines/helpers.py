from flask import current_app

from datetime import datetime, timedelta
import pytz
import csv

from toggltimelines.timelines.models import Entry
from toggltimelines.timelines.models import Project
from toggltimelines import db


def toggl_sync(start_date, end_date=False):

	if not end_date:
		end_date = datetime.utcnow()


	entries = get_entries_from_toggl(start_date, end_date)

	current_entry = get_current_toggl_entry()
	if current_entry:
		entries.append(current_entry)

	local_projects = get_all_projects_from_database()

	# Remove database entries which already exist in the sync window.
	existing_db_entries = get_db_entries(start_date, end_date)
	for db_entry in existing_db_entries:
		db.session.delete(db_entry)


	for entry in entries:
		project_id = entry['pid']
		db_project = get_database_project_by_id(project_id, local_projects)


		if not db_project: # Create the database project if it doesn't exist.

			if not 'project' in entry.keys(): # If the project name isn't given in the entry details, we ask Toggl for details about all projects
											  # (This is the case for currently running projects).
				toggl_projects = get_user_toggl_data()['projects']

				for toggl_project in toggl_projects:
					toggl_project_id = toggl_project['id']

					if toggl_project_id == project_id:
						entry['project'] = toggl_project['name']
						entry['project_hex_color'] = toggl_project['hex_color']


			db_project = create_project({
				'project_id': 		 project_id,
				'project_name': 	 entry['project'],
				'project_hex_color': entry['project_hex_color']
			})

			local_projects.append(db_project)


		start_datetime = timestamp_to_datetime(entry['start'])
		end_datetime = timestamp_to_datetime(entry['end'])


		if not 'client' in entry.keys():
			entry['client'] = None #TODO: This is temporary. Need to check how clients are actually working.


		location = get_entry_location(start_datetime)

		db_entry = create_entry({
			'id': 		   entry['id'],
			'description': entry['description'],
			'start': 	   start_datetime,
			'end': 		   end_datetime,
			'dur': 		   entry['dur'],
			'client': 	   entry['client'],
			'location':	   location,
			'user_id': 	   entry['uid'],
			'db_project':  db_project #TODO: Need case for if there is no project
		})

	db.session.commit()

def get_entry_location(entry_datetime):
	with open('location_history.csv', 'r') as file:
		reader = csv.DictReader(file)

		timestamp_format = '%Y-%m-%dT%H:%M'

		location = current_app.config['DEFAULT_LOCATION']

		for row in reader:
			location_start_datetime = datetime.strptime(row['start'], timestamp_format).astimezone(tz=pytz.utc)
			location_end_datetime = datetime.strptime(row['end'], timestamp_format).astimezone(tz=pytz.utc)

			if location_start_datetime <= entry_datetime <= location_end_datetime:
				location = row['location']

	return location

def get_db_entries(start_datetime=False, end_datetime=False, projects=False, clients=False, description=False):
	query = Entry.query.join(Entry.project, aliased=True)

	if start_datetime:
		query.filter(Entry.start >= start_datetime)

	if end_datetime:
		query.filter(Entry.end <= end_datetime)

	if projects:
		query.filter(Project.project_name.in_(projects))

	if clients:
		query = query.filter(Entry.client.in_(clients))

	if description:
		query = query.filter(func.lower(Entry.description).contains(description.lower()))


	entries = query.order_by(Entry.start).all()

	# Entries are timezone naive when we retreive them.
	# Need to make them aware that they are in UTC.
	for entry in entries:
		entry.tzinfo_to_utc()

	return entries

# Save a new entry to the database
def create_entry(entry_data):
	db_entry = Entry(
		id 				  = entry_data['id'],
		description 	  = entry_data['description'],
		start 			  = entry_data['start'],
		end 			  = entry_data['end'],
		dur 			  = entry_data['dur'],
		client 			  = entry_data['client'],
		location 		  = entry_data['location'],
		user_id 		  = entry_data['user_id']
	)

	if entry_data['db_project']:
		db_entry.project = entry_data['db_project']

	db.session.add(db_entry)

	return db_entry

# Save a new project to the database
def create_project(project_data):
	db_project = Project(
		id 				  = project_data['project_id'],
		project_name 	  = project_data['project_name'],
		project_hex_color = project_data['project_hex_color']
	)

	db.session.add(db_project)

	return db_project

# Given a project ID, return the project object from the database.
# Can provide a project list, to avoid unneeded database queries.
def get_database_project_by_id(project_id, project_list = None):
	if not project_list:
		project_list = get_all_projects_from_database()
		#TODO: Instead of getting the whole list here, this should just be a query for the particular project.

	db_project = False

	for project in project_list:
		if project.id == project_id:
			db_project = project
			break

	return db_project

# Get entries between two dates from the Toggl API.
# Will NOT include an entry which is currently being tracked.
def get_entries_from_toggl(start_date, end_date):
	request_data = {
		'workspace_id': current_app.config['WORKSPACE_ID'],
		'since': start_date,
		'until': end_date
	}

	entries = current_app.toggl.getDetailedReportPages(request_data)['data']

	return entries

# Note: current entries are returned from Toggl in UTC,
# while past entries are returned in the user's assigned timezone.
def get_current_toggl_entry():
	current_entry = current_app.toggl.currentRunningTimeEntry()

	if not current_entry:
		return False


	start_datetime = timestamp_to_datetime(current_entry['start'])

	utc_now = datetime.utcnow().replace(tzinfo=pytz.utc)

	time_since_entry_start = utc_now - start_datetime

	end_datetime = start_datetime + timedelta(seconds = time_since_entry_start.seconds)

	current_entry['dur'] = time_since_entry_start.seconds * 1000 # Duration is in milliseconds
	current_entry['end'] = datetime_to_timestamp(end_datetime)

	return current_entry

def get_user_toggl_data():
	user_data = current_app.toggl.request("https://www.toggl.com/api/v8/me?with_related_data=true")['data']

	projects = user_data['projects']
	clients = user_data['clients']

	return user_data

def get_all_projects_from_database():
	#print('get_projects_from_database')
	projects = Project.query.all()

	return projects

# Convert a timestamp string to a datetime object.
def timestamp_to_datetime(timestamp, string_format='%Y-%m-%dT%H:%M:%S%z'):
	timestamp = remove_colon_from_timezone(timestamp)
	utc = pytz.timezone('UTC')
	dt = datetime.strptime(timestamp, string_format).astimezone(tz=utc)

	return dt

def datetime_to_timestamp(dt, string_format='%Y-%m-%dT%H:%M:%S%z'):
	return remove_colon_from_timezone(datetime.strftime(dt, string_format))

# The datetime strings we receive from toggl have a colon in the timezone. We need to remove this.
def remove_colon_from_timezone(timestamp):
	if timestamp[-3] == ':':
		return timestamp[:-3] + timestamp[-2:]
	else:
		return timestamp