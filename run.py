from __future__ import print_function
from os.path import abspath, dirname, join
from flask import flash, Flask, Markup, redirect, render_template, url_for, request, session
from flask.ext.sqlalchemy import SQLAlchemy

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired, Email
#from wtforms.ext.sqlalchemy.fields import QuerySelectField
#from util.validators import Unique
from wtforms.validators import ValidationError

import os
import googlemaps
from datetime import datetime
import json
import sys

from sqlalchemy.ext.hybrid import hybrid_property
from flask_bcrypt import Bcrypt

_cwd = dirname(abspath(__file__))

SECRET_KEY = os.urandom(24)
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + join(_cwd, 'TripLogger.db')
SQLALCHEMY_ECHO = True
WTF_CSRF_SECRET_KEY = SECRET_KEY

app = Flask(__name__)
app.config.from_object(__name__)

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class Unique(object):
    def __init__(self, model, field, message=u'This element already exists.'):
        self.model = model
        self.field = field

    def __call__(self, form, field):
        check = self.model.query.filter(self.field == field.data).first()
        if check:
            raise ValidationError(self.message)

# Models
class Trip(db.Model):
	__tablename__ = 'trips'

	id = db.Column(db.Integer, primary_key=True)
	trip_name = db.Column(db.String, unique=True)
	origin = db.Column(db.String)
	destination = db.Column(db.String)
	waypoints = db.Column(db.String) #SEE IF ANOTHER DATA TYPE IS BETTER- IDEALLY WANT TO STORE LIST OF STRINGS

	def __init__(self, trip_name, origin, destination, waypoints):
		self.trip_name = trip_name
		self.origin = origin
		self.destination = destination
		self.waypoints = waypoints

	def __repr__(self):
		return '<Trip %r(name = %r, origin = %r, destination = %r)>' % (self.id, self.trip_name, self.origin, self.destination)

	def __str__(self):
		return self.trip_name

class User(db.Model):
	__tablename__ = 'users'

	id = db.Column(db.Integer, primary_key=True)
	user_first_name = db.Column(db.String)
	user_last_name = db.Column(db.String)
	user_email = db.Column(db.String, unique=True)
	_user_password = db.Column(db.String)

	def __init__(self, user_first_name, user_last_name, user_email, user_password):
		self.user_first_name = user_first_name
		self.user_last_name = user_last_name
		self.user_email = user_email
		self._user_password = user_password

	def __repr__(self):
		return "<User %r(name = %r %r, email = %r, password = %r)>" % (self.id, self.user_first_name, self.user_last_name, self.user_email, self.user_password)

	def __str__(self):
		return self.user_first_name + self.user_last_name

	@hybrid_property
	def user_password(self):
		return self._user_password

	@user_password.setter
	def user_password(self, plaintext):
		self._user_password = bcrypt.generate_password_hash(plaintext)

	def is_correct_password(self, plaintext):
		return bcrypt.check_password_hash(self._user_password, plaintext)

# Forms
#CONSIDER CUSTOM VALIDATOR TO ENSURE THAT TRIP_NAME IS UNIQUE FOR A SPECIFIC USER/ACCOUNT
class TripForm(FlaskForm): 
	trip_name = StringField('Trip Name', validators=[DataRequired()])
	origin = StringField('Origin', validators=[DataRequired()])
	destination = StringField('Destination', validators=[DataRequired()])
	waypoints = StringField('Waypoint')

class SignInForm(FlaskForm):
	email_address = StringField('E-mail Address', validators=[Email(), DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])

class SignUpForm(FlaskForm):
	first_name = StringField("First Name", validators=[DataRequired()])
	last_name = StringField("Last Name", validators=[DataRequired()])
	email_address = StringField("E-mail Address", validators=[Email(), DataRequired(),
		Unique(
			User,
			User.user_email,
			message="Another account with this e-mail address is already registered. Please use a different e-mail address.")])
	password = PasswordField("Password", validators=[DataRequired()])


# Views
@app.route("/", methods = ["GET", "POST"])
def index():
    trip_form = TripForm(request.form)
    if trip_form.validate_on_submit():
		print("Submitted new trip form, now redirecting to /finalize_new_trip to render map...", file=sys.stderr)
		return redirect(url_for("complete_trip", trip_name = trip_form.trip_name.data, origin = trip_form.origin.data, destination = trip_form.destination.data, waypoints = trip_form.waypoints.data))
    return render_template("index.html", trip_form = trip_form)

# Route to display trip on map (in future, to modify trip details, e.g. waypoints)
@app.route("/finalize_new_trip/<trip_name>/<origin>/<destination>/<waypoints>", methods=["GET"])
def complete_trip(trip_name, origin, destination, waypoints):
	return render_template("finish_new_trip.html", trip_name = trip_name, origin = origin, destination = destination, waypoints = waypoints, GOOGLE_API_KEY=os.environ["GOOGLE_API_KEY"])

# Store new trip data in database
@app.route("/store_trip", methods=["POST"])
def store_trip():
	print("Now in /store_trip endpoint!", file=sys.stderr)
	trip_data_json = request.json
	print("Now making Trip object and storing in DB", file=sys.stderr)
	new_trip = Trip(trip_data_json["trip_name"], trip_data_json["origin"], trip_data_json["destination"], trip_data_json["waypoints"])
	print("name: " + trip_data_json["trip_name"], file=sys.stderr)
	print("origin: " + trip_data_json["origin"], file=sys.stderr)
	print("destination: " + trip_data_json["destination"], file=sys.stderr)
	print("waypoints: " + trip_data_json["waypoints"], file=sys.stderr)
	db.session.add(new_trip)
	db.session.commit()
	print("Trip Data after storing new trip: ", file=sys.stderr)
	print(Trip.query.all(), file=sys.stderr)
	flash("Your new trip was successfully added!")
	return redirect(url_for("index"))



@app.route("/log_in", methods=["GET", "POST"])
def log_in():
	log_in_form = SignInForm(request.form)
	if log_in_form.validate_on_submit():
		print("Submitted log-in form, now verifying...", file=sys.stderr)
		# VALIDATE USER LOGIN


	return render_template("log_in.html", log_in_form=log_in_form)



@app.route("/create_account", methods= ["GET", "POST"])
def create_account():
	sign_up_form = SignUpForm(request.form)
	if (sign_up_form.validate_on_submit()):
		print("Submitted sign-up form", file=sys.stderr)
		new_user = User(sign_up_form.first_name.data, sign_up_form.last_name.data, sign_up_form.email_address.data, sign_up_form.password.data)
		db.session.add(new_user)
		db.session.commit()
	return render_template("sign_up.html", sign_up_form=sign_up_form)

@app.route("/view_trips", methods= ["GET", "POST"])
def view_trips():
	return "Post request made in /view_trips!"


# @app.route("/site", methods=("POST", ))
# def add_site():
#     form = SiteForm()
#     if form.validate_on_submit():
#         site = Site()
#         form.populate_obj(site)
#         db.session.add(site)
#         db.session.commit()
#         flash("Added site")
#         return redirect(url_for("index"))
#     return render_template("validation_error.html", form=form)


# @app.route("/visit", methods=("POST", ))
# def add_visit():
#     form = VisitForm()
#     if form.validate_on_submit():
#         visit = Visit()
#         form.populate_obj(visit)
#         visit.site_id = form.site.data.id
#         db.session.add(visit)
#         db.session.commit()
#         flash("Added visit for site " + form.site.data.base_url)
#         return redirect(url_for("index"))
#     return render_template("validation_error.html", form=form)


# @app.route("/sites")
# def view_sites():
#     query = Site.query.filter(Site.id >= 0)
#     data = query_to_list(query)
#     data = [next(data)] + [[_make_link(cell) if i == 0 else cell for i, cell in enumerate(row)] for row in data]
#     return render_template("data_list.html", data=data, type="Sites")


# _LINK = Markup('<a href="{url}">{name}</a>')


# def _make_link(site_id):
#     url = url_for("view_site_visits", site_id=site_id)
#     return _LINK.format(url=url, name=site_id)


# @app.route("/site/<int:site_id>")
# def view_site_visits(site_id=None):
#     site = Site.query.get_or_404(site_id)
#     query = Visit.query.filter(Visit.site_id == site_id)
#     data = query_to_list(query)
#     title = "visits for " + site.base_url
# 	  return render_template("data_list.html", data=data, type=title)


def query_to_list(query, include_field_names=True):
    """Turns a SQLAlchemy query into a list of data values."""
    column_names = []
    for i, obj in enumerate(query.all()):
        if i == 0:
            column_names = [c.name for c in obj.__table__.columns]
            if include_field_names:
                yield column_names
        yield obj_to_list(obj, column_names)


def obj_to_list(sa_obj, field_order):
    """Takes a SQLAlchemy object - returns a list of all its data"""
    return [getattr(sa_obj, field_name, None) for field_name in field_order]

if __name__ == "__main__":
    app.debug = True
    db.create_all()
    app.run()