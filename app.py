#!/usr/bin/python

from flask import Flask, request, redirect
import urllib, simplejson
import twilio.twiml

error_message = "We apologize for the inconvenience, we are unable to "
error_message += "determine the closest 'free internet'. "
error_message += "Please try another Stop ID. Thank you!"

app = Flask(__name__)

@app.route("/",methods=["GET","POST"])
def receive_text():
	"""Function that performs main functionality of app ie;
	logs received text message information to a Google Spreadsheet and replys
	with a text message that states the name and address of the 3 closest
	locations for 'free internet' from the bus stop that corresponds to the
	recieved ID.
	"""
	results = ""
	stop_ID = request.values.get("Body")
	phone_number = request.values.get("From")
	#log_text_message(stop_ID, phone_number)

	get_geo_url = 'http://localfreeweb.cartodb.com/api/v2/sql?q=SELECT '
	get_geo_url += 'stop_lat, stop_lon FROM stops WHERE stop_id = '
	get_geo_url += stop_ID
	response = urllib.urlopen(get_geo_url)
	for line in response:
		response_dict = simplejson.loads(line)

	if response_dict['total_rows'] == 0:
		resp = twilio.twiml.Response()
		resp.message(error_message)
		return str(resp)

	geo_lat = str(response_dict['rows'][0]['stop_lat'])
	geo_long = str(response_dict['rows'][0]['stop_lon'])
	lat_long = [geo_lat, geo_long]

	free_net_url = 'http://localfreeweb.cartodb.com/api/v2/sql?q=SELECT'
	free_net_url += ' bizname, address, zip, phone, '
	free_net_url += 'ST_Distance(the_geom::geography, ST_PointFromText('
	free_net_url += '\'POINT('+ geo_long + ' ' + geo_lat + ')\', 4326)'
	free_net_url += '::geography) AS distance FROM freeweb ORDER BY distance '
	free_net_url += 'ASC LIMIT 3'
	response = urllib.urlopen(free_net_url)
	for line in response:
		response_dict = simplejson.loads(line)

	for i in range(0, 3):
	    results += " " + response_dict['rows'][i]['bizname'] + " @ "
	    results += response_dict['rows'][i]['address'] + ";"
	# 	print 'Phone number: ' + str(response_dict['rows'][i]['phone'])
	resp = twilio.twiml.Response()
	resp.message("Ask for 'free internet' at these places:" + results)
	return str(resp)



if __name__ == "__main__":
    app.run(debug=True)
