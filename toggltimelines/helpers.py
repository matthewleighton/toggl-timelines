from flask import current_app

from datetime import datetime, timedelta

from toggltimelines.timelines.models import Entry
from toggltimelines.timelines.models import Project
from toggltimelines import db


def toggl_sync(start_date, end_date):
	entries = get_entries_from_toggl(start_date, end_date)

	current_entry = get_current_toggl_entry()
	entries.append(current_entry)

	local_projects = get_all_projects_from_database()

	#print(local_projects[0].project_name)

	#TODO-NEXT: Overwrite entries when they already exist.

	for entry in entries:
		print(entry)
		print('')

		project_id = entry['pid']
		db_project = get_database_project_by_id(project_id, local_projects)

		if not db_project:
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

		db_entry = create_entry({
			'id': 		   entry['id'],
			'description': entry['description'],
			'start': 	   start_datetime,
			'end': 		   end_datetime,
			'dur': 		   entry['dur'],
			'client': 	   entry['client'],
			'utc_offset':  2, #TODO
			'user_id': 	   entry['uid'],
			'db_project':  db_project #TODO: Need case for if there is no project
		})

	db.session.commit()

# Save a new entry to the database
def create_entry(entry_data):
	db_entry = Entry(
		id 				  = entry_data['id'],
		description 	  = entry_data['description'],
		start 			  = entry_data['start'],
		end 			  = entry_data['end'],
		dur 			  = entry_data['dur'],
		client 			  = entry_data['client'],
		utc_offset 		  = entry_data['utc_offset'],
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
		project_list = get_projects_from_database()
		#TODO: Instead of getting the whole list here, this should just be a query for the particular project.

	db_project = False

	for project in project_list:
		if project.id == project_id:
			db_project = project
			break

	return db_project

def get_entries_from_toggl(start_date, end_date):
	request_data = {
		'workspace_id': current_app.config['WORKSPACE_ID'],
		'since': start_date,
		'until': end_date
	}

	entries = current_app.toggl.getDetailedReportPages(request_data)['data']

	return entries

def get_current_toggl_entry():
	current_entry = current_app.toggl.currentRunningTimeEntry()


	start_datetime = timestamp_to_datetime(current_entry['start'])
	utc_now = datetime.utcnow()

	time_since_entry_start = utc_now - start_datetime.replace(tzinfo=None)

	end_datetime = start_datetime + timedelta(seconds = time_since_entry_start.seconds)

	current_entry['dur'] = time_since_entry_start.seconds * 1000 # Duration is in milliseconds
	current_entry['end'] = datetime_to_timestamp(end_datetime)

	return current_entry

def get_user_toggl_data():
	user_data = current_app.toggl.request("https://www.toggl.com/api/v8/me?with_related_data=true")['data']

	projects = user_data['projects']
	clients = user_data['clients']

	print(projects)

def save_toggl_entries_to_database(entries):
	for entry in entries:
		print(entry)
		print('')



def get_all_projects_from_database():
	print('get_projects_from_database')
	projects = Project.query.all()

	return projects

# Convert a timestamp string to a datetime object.
def timestamp_to_datetime(timestamp, string_format='%Y-%m-%dT%H:%M:%S%z'):
	timestamp = remove_colon_from_timezone(timestamp)
	return datetime.strptime(timestamp, string_format)

def datetime_to_timestamp(dt, string_format='%Y-%m-%dT%H:%M:%S%z'):
	return remove_colon_from_timezone(datetime.strftime(dt, string_format))

# The datetime strings we receive from toggl have a colon in the timezone. We need to remove this.
def remove_colon_from_timezone(timestamp):
	if timestamp[-3] == ':':
		return timestamp[:-3] + timestamp[-2:]
	else:
		return timestamp