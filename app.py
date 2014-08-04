#!/usr/bin/python

from flask import Flask, request, redirect
import urllib, simplejson
import twilio.twiml
import gdata.spreadsheet.service
import gdata.service
import atom.service
import gdata.spreadsheet
import atom
import arrow
import re


#Global Variables
#gdata variables
email_address = 'sfbrigade@gmail.com'
password = 'hack4change'
spreadsheet_key = '1S4jHX9__Drog_qqGsDJYFuO7KvRP9BUD8A95xQ5kkQU'
worksheet_ID = 'od6'

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
	error = False
	results = ""
	stop_ID = re.findall('\d+', request.values.get("Body"))
	phone_number = request.values.get("From")
	
	if len(stop_ID) > 0:
		log_text_message(stop_ID[0], phone_number)
		get_geo_url = 'http://localfreeweb.cartodb.com/api/v2/sql?q=SELECT '
		get_geo_url += 'stop_lat, stop_lon FROM stops WHERE stop_id = '
		get_geo_url += stop_ID[0]
	else if len(stop_ID) == 0:
		error = True
	response = urllib.urlopen(get_geo_url)
	for line in response:
		response_dict = simplejson.loads(line)
		
	if response_dict['total_rows'] == 0:
		error = True
	if error:
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


def log_text_message(stop_ID, phone_number):	
	"""Function that logs the incoming text sender's phone number & the stop ID
	into a Google Spreadsheet.
	In args:           stop_ID, phone_number
	Global vars in:    email_address, password, spreadsheet_key, worksheet_ID
	"""
	spr_client = gdata.spreadsheet.service.SpreadsheetsService()
	spr_client.email = email_address
	spr_client.password = password
	spr_client.source = 'LocalFreeWeb text message app'
	spr_client.ProgrammaticLogin()
	entry = spr_client.InsertRow(build_data_dict(stop_ID, phone_number),
	                             spreadsheet_key, worksheet_ID)


def build_data_dict(stop_ID, phone_number):
    """Function that builds a dictionary that includes the date, time,
    phone_number and stop_ID of received text message
    In args:    stop_ID, phone_number
    Out arg:    dict
    """
    dict = {}
    dict['date'] = arrow.now('US/Pacific').format('MM/DD/YYYY')
    dict['time'] = arrow.now('US/Pacific').format('hh:mm:ss A')
    dict['phone'] = phone_number
    dict['stop'] = stop_ID
    return dict


if __name__ == "__main__":
    app.run(debug=True)

