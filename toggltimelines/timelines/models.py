from toggltimelines import db

class Entry(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	description = db.Column(db.String(200))
	start = db.Column(db.DateTime(timezone=True))
	end = db.Column(db.DateTime(timezone=True))
	dur = db.Column(db.Integer)
	project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
	client = db.Column(db.String(50))
	project_hex_color = db.Column(db.String(7))
	#tags = db.relationship('Tag', secondary=tags, backref=db.backref('entries', lazy=True), lazy='select')
	user_id = db.Column(db.Integer)
	utc_offset = db.Column(db.Integer)

	def __repr__(self):
		return "<Entry (Description: " + self.description + ") (Start: " + str(self.get_local_start_time()) + ") (End: " + str(self.end) + ") (Duration: " + str(self.dur) + ") (ID: " + str(self.id) + ")"




class Project(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	project_name = db.Column(db.String(50))
	project_hex_color = db.Column(db.String(7))
	entries = db.relationship('Entry', backref='project')

