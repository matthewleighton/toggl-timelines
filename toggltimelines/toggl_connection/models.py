print('This is the toggl_connection/models.py file!')
from flask import current_app

class TogglConnection():

	def testfunc(self):
		print('This is the TogglConnection test function!')
		print(current_app.config['API_KEY'])

