from flask import current_app

from toggltimelines import db

class Book(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(200))
	fiction = db.Column(db.Boolean)
	readthroughs = db.relationship('Readthrough', backref='book')


class Readthrough(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	book_id = db.Column(db.Integer, db.ForeignKey('book.id'))
	book_format = db.Column(db.String(10))
	first_page = db.Column(db.Integer)
	last_page = db.Column(db.Integer)
	current_position = db.Column(db.Integer)

	start_date = db.Column(db.DateTime(timezone=True))
	end_date = db.Column(db.DateTime(timezone=True))
	target_end_date = db.Column(db.DateTime(timezone=True))

