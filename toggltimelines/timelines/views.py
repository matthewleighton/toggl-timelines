from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import current_app
from werkzeug.exceptions import abort

from toggltimelines import db

from toggltimelines.timelines.models import Entry

bp = Blueprint("timelines", __name__)

@bp.route("/")
def index():
	return render_template("index.html")

@bp.route("/timelines")
def timelines_page():
	print(current_app.config['TESTING'])
	return render_template("timelines/timelines.html")