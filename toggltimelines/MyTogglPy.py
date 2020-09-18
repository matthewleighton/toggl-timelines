from toggl.TogglPy import Toggl
from toggl.TogglPy import Endpoints

class MyTogglPy(Toggl):
	# The version of this function in the original class uses a POST request, and returns a 400 error.
	def currentRunningTimeEntry(self):
		'''Gets the Current Time Entry'''

		response = self.request("https://www.toggl.com/api/v8/time_entries/current")

		return response['data']

	# The version in the original class uses a POST request, but the API documentation asks to use PUT.
	def stopTimeEntry(self, entryid):
		'''Stop the time entry'''
		response = self.postRequest(Endpoints.STOP_TIME(entryid), method='PUT')
		return self.decodeJSON(response)