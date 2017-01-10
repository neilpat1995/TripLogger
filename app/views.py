from app import app
from flask import render_template

@app.route('/')
@app.route('/index')
def index():
	return 'Hello, World'

@app.route('/signin')
def sign_in():


@app.route('/signup')
def sign_up():

# View previous trip info
@app.route('/trips')
def view_trips():
	return render_template('view_trips.html')