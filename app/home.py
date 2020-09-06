from app import app
from flask import make_response, render_template

@app.route('/')
def home_page():
	response = make_response(render_template('home.html'))

	return response