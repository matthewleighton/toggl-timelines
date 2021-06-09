from toggl.TogglPy import Toggl
from toggl.TogglPy import Endpoints
import math
import time


class Endpoints():
	WORKSPACES = "https://api.track.toggl.com/api/v8/workspaces"
	CLIENTS = "https://api.track.toggl.com/api/v8/clients"
	PROJECTS = "https://api.track.toggl.com/api/v8/projects"
	TASKS = "https://api.track.toggl.com/api/v8/tasks"
	REPORT_WEEKLY = "https://api.track.toggl.com/reports/api/v2/weekly"
	REPORT_DETAILED = "https://toggl.com/reports/api/v2/details"
	REPORT_SUMMARY = "https://api.track.toggl.com/reports/api/v2/summary"
	START_TIME = "https://api.track.toggl.com/api/v8/time_entries/start"
	TIME_ENTRIES = "https://api.track.toggl.com/api/v8/time_entries"
	CURRENT_RUNNING_TIME = "https://api.track.toggl.com/api/v8/time_entries/current"

	@staticmethod
	def STOP_TIME(pid):
		return "https://api.track.toggl.com/api/v8/time_entries/" + str(pid) + "/stop"

# 12/5/2021: I've pulled more of the functions from the base class into here.
# This was because Toggl have changed their api endpoint, but the TogglPy library hasn't been updated.
# Feels like there should be a better way of doing this, but unless I basically rewrite the functions below,
# it pulls from the original Endpoints class instead of my new one.
class MyTogglPy(Toggl):
	
	# The version of this function in the original class uses a POST request, and returns a 400 error.
	def currentRunningTimeEntry(self):
		'''Gets the Current Time Entry'''
		response = self.request("https://api.track.toggl.com/api/v8/time_entries/current")

		return response['data']

	def getDetailedReportPages(self, data):
		'''return detailed report data from all pages for a user'''
		pages_index = 1
		data['page'] = pages_index
		pages = self.request(Endpoints.REPORT_DETAILED, parameters=data)
		try:
			pages_number = math.ceil(pages.get('total_count', 0) / pages.get('per_page', 0))
		except ZeroDivisionError:
			pages_number = 0
		for pages_index in range(2, pages_number + 1):
			time.sleep(1)  # There is rate limiting of 1 request per second (per IP per API token).
			data['page'] = pages_index
			pages['data'].extend(self.request(Endpoints.REPORT_DETAILED, parameters=data).get('data', []))
		return pages

	# The version in the original class uses a POST request, but the API documentation asks to use PUT.
	def stopTimeEntry(self, entryid):
		'''Stop the time entry'''
		response = self.postRequest(Endpoints.STOP_TIME(entryid), method='PUT')
		return self.decodeJSON(response)

	def startTimeEntry(self, description, pid=None, tid=None):
		'''starts a new Time Entry'''

		data = {
			"time_entry": {
				"created_with": self.user_agent,
				"description": description
			}
		}
		if pid:
			data["time_entry"]["pid"] = pid

		if tid:
			data["time_entry"]["tid"] = tid

		response = self.postRequest(Endpoints.START_TIME, parameters=data)
		return self.decodeJSON(response)