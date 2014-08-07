#!/usr/bin/python
from flask import Flask, request, redirect
import twilio.twiml
import requests

app = Flask(__name__)

def log_text_message(phone_number, content):
	"""Function to abstract away logging. Right now this function will POST
	against a Google Form URL to log text messages.
	"""
	form_url = 'https://docs.google.com/forms/d/1C9G06CyX-wHf4NeMSsqSqi-VWcqh-0--lUHszd0SdHA/formResponse'
	params = {}
	params['entry.1533669412'] = phone_number
	params['entry.2016774916'] = content
	log_request = requests.post(form_url, params=params)

	print 'Request logged as coming from %s and saying "%s"' % (phone_number, content)

def handle_text_message(content):
	"""Function that ensures the text message can be processed and if not
	gives the user a relevant error.
	"""

	return content

carto_db_url = 'http://localfreeweb-cartodb-com-gwqynjms41pa.runscope.net/api/v2/sql?q=%s'
#carto_db_url = 'http://localfreeweb.cartodb.com/api/v2/sql?q=%s'

def get_stop_gps(stop_id):
	carto_action = 'SELECT stop_lat, stop_lon FROM stops WHERE stop_id = %s' % stop_id
	response = requests.get(carto_db_url % carto_action)

	return response

def get_locations_near_stop(stop_id):
	"""Function to get the responses from the DB and return them from a valid
	stop_id.
	"""

	stop_gps_request = get_stop_gps(stop_id)

	if stop_gps_request.status_code == 200:
		stop_gps = stop_gps_request.json()
		print stop_gps

		if stop_gps['total_rows'] != 0:
			geo_lat = stop_gps['rows'][0]['stop_lat']
			geo_long = stop_gps['rows'][0]['stop_lon']
			carto_action = """SELECT bizname, address, zip, phone,
			ST_Distance(the_geom::geography,
			ST_PointFromText('POINT(%s %s)', 4326)::geography)
			AS distance FROM freeweb ORDER BY distance ASC LIMIT 3
			""" % (geo_long, geo_lat)

			locations_response = requests.get(carto_db_url % carto_action)

			if locations_response.status_code == 200:
				return locations_response.json()['rows']
			else:
				return None
		else:
			return None
	else:
		return None

def generate_response_text(locations):
	"""Function to send the proper response back to Twilio
	"""

	error_message = "We apologize for the inconvenience, we are unable to "
	error_message += "determine the closest 'free internet'. "
	error_message += "Please try another Stop ID. Thank you!"

	if locations == None:
		resp = twilio.twiml.Response()
		resp.message(error_message)
		return str(resp)
	else:
		results = []
		for location in locations:
			print location
			results.append('%s @ %s' % (location['bizname'], location['address']))

		resp = twilio.twiml.Response()
		resp.message("Ask for 'free internet' at these places:" + ' ;'.join(results))
		return str(resp)

@app.route("/",methods=["GET","POST"])
def receive_text():
	"""Function that performs main functionality of app ie;
	logs received text message information to a Google Spreadsheet and replys
	with a text message that states the name and address of the 3 closest
	locations for 'free internet' from the bus stop that corresponds to the
	recieved ID.
	"""

	phone_number = request.values.get("From")
	sms_body = request.values.get("Body", False)

	#log_text_message(phone_number, sms_body)

	stop_id = handle_text_message(sms_body)

	if stop_id == None:
		locations = None
		response_text = generate_response_text(locations)
	else:
		locations = get_locations_near_stop(stop_id)
		response_text = generate_response_text(locations)

	return response_text

if __name__ == "__main__":
    app.run(debug=True)
