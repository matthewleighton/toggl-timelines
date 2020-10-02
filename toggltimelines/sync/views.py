from flask import Blueprint
from flask import flash
from flask import g
from flask import redirect
from flask import render_template
from flask import request
from flask import url_for
from flask import current_app
from flask import make_response
from flask import jsonify

from toggltimelines import db
from toggltimelines.reading.models import Book, Readthrough
from toggltimelines.timelines.models import Project
from toggltimelines import helpers

bp = Blueprint("sync", __name__)

@bp.route("/sync")
def sync_home():

	page_data = {}

	response = make_response(render_template('sync/index.html', data=page_data))

	return response