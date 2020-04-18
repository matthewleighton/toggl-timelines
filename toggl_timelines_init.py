first_init = True
import csv, pytz, time
from datetime import datetime, date, timedelta

import toggl_timelines as toggl_timelines
from toggl_timelines import db, Entry



def populate_database():
	import_complete = False
	days_per_request = 50

	start_days_ago = days_per_request
	end_days_ago = 0

	i = 0

	while not import_complete:
		entries_added = toggl_timelines.update_database(start_days_ago, end_days_ago)
		
		end_days_ago = start_days_ago
		start_days_ago += days_per_request

		i += 1

		#if (i > 3):
		#	import_complete = True

		print('Import loop: {0}'.format(i))
		print('Start: {0}'.format(start_days_ago))

		if len(entries_added) == 0:
			import_complete = True

db.create_all()

populate_database()
