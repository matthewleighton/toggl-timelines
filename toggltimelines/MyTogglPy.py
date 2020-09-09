from toggl.TogglPy import Toggl

class MyTogglPy(Toggl):
	# The version of this function in the original class uses a POST request, and returns a 400 error.
	def currentRunningTimeEntry(self):
		'''Gets the Current Time Entry'''

		response = self.request("https://www.toggl.com/api/v8/time_entries/current")

		return response['data']