from datetime import datetime, time, timedelta
import calendar
from calendar import monthrange
import pytz
import csv
import getpass
from TogglPy import Toggl

import toggl_timelines_config as config







def get_local_utc_offset():
	local_hours = datetime.now().hour
	utc_hours = datetime.utcnow().hour

	utc_offset = local_hours - utc_hours

	return utc_offset

# Return a datetime for the current time in the user's current timezone.
def get_current_datetime_in_user_timezone():
	with open ('utc_offsets.csv', 'r') as file:
		reader = csv.DictReader(file)
		timezone_name = next(reader)['location']

	timezone = pytz.timezone(timezone_name)

	user_time = datetime.now(timezone)

	return user_time

