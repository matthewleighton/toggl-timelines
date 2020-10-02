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

from datetime import datetime, date, timedelta

bp = Blueprint("sync", __name__)

@bp.route("/sync")
def sync_home():

	end = date.today()
	start = end - timedelta(days=7)

	data = {
		'start': start,
		'end': end
	}

	print(data)

	response = make_response(render_template('sync/index.html', data=data))

	return response

@bp.route("/sync/run_sync", methods=['POST'])
def run_sync():
	data = request.json

	date_format = '%Y-%m-%d'
	start = datetime.strptime(data['sync-start'], date_format)
	end = datetime.strptime(data['sync-end'], date_format)

	all_entries = []

	target_start = start
	target_end = start
	increment = 100

	while target_end < end:
		target_end += timedelta(days=increment)

		if target_end > end:
			target_end = end

		new_entries = helpers.toggl_sync(target_start, target_end)

		target_start += timedelta(days=increment)

		all_entries += new_entries

	message = f"{len(all_entries):,} entries synced"

	return jsonify(
		message=message
	)