import os.path
from os import path

print('__init__.py')

from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///toggl_timelines.db'

db = SQLAlchemy(app)



from app import helpers

from app import models

from app import home
from app import timeline
from app import comparison
from app import frequency

if not path.exists("app/toggl_timelines.db"):
	print('Creating database.')
	db.create_all()
else:
	print('Database already exists!')

