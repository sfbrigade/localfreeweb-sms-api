#!/usr/bin/python

from flask import Flask, request, redirect
import urllib, json as simplejson
import urllib2
from urllib2 import Request, urlopen, URLError
import twilio.twiml
import gdata.spreadsheet.service
import gdata.service
import atom.service
import gdata.spreadsheet
import atom
import arrow
import re
import os


#Global Variables
#gdata variables
email_address = os.environ.get('SF_BRIGADE_EMAIL')
password = os.environ.get('SF_BRIGADE_EMAIL_PASS')
spreadsheet_key = os.environ.get('LOCALFREEWEB_DATA_KEY')
apikey = os.environ.get('CARTO_DB_API_KEY')
worksheet_ID = 'od6'
#cartoDB variables
url = 'http://localfreeweb.cartodb.com/api/v2/sql'
SELECT_url = 'http://localfreeweb.cartodb.com/api/v2/sql?q=SELECT '
day = 'day' + str(arrow.now('US/Pacific').weekday())

error_message = "We apologize for the inconvenience, we are unable to "
error_message += "determine the closest 'free internet'. "
error_message += "Please try another Stop ID. Thank you!"

app = Flask(__name__)

@app.route("/",methods=["GET","POST"])
  
def receive_text():
    """Performs main functionality of app ie;
    logs received text message information to a Google Spreadsheet and replys
    with a text message that states the name and address of the 3 closest
    locations for 'free internet' from the bus stop that corresponds to the
    recieved ID.
    """
    #10 + 390 10 + 913 130 + 913
    #Create list of all numbers in text message
    stop_ID = re.findall('\d+', request.values.get("Body"))
    phone_number = request.values.get("From")
    #Stop IDs are either FIVE or SIX digits
    if len(stop_ID) > 0 and len(stop_ID[0]) > 4:
        #If Stop ID is 5 digits, remove the leading digit
        if len(stop_ID[0]) == 5:
            #Handle special cases
            if stop_ID[0] == '10390':
                database_ID = '390'
            elif stop_ID[0] == '10913':
                database_ID = '913'
            #Handle generic case
            else: 
                database_ID = stop_ID[0][1:]
            stop_gps_resp_dict = get_stop_gps(database_ID)
        #If Stop ID is 6 digits, remove the first TWO leading digits
        elif len(stop_ID[0]) == 6:
            #Handle special case
            if stop_ID[0] == '130913':
                database_ID = '913'
            #Handle generic case    
            else:
                database_ID = stop_ID[0][2:]
            stop_gps_resp_dict = get_stop_gps(database_ID)
        else:
            return generate_text_message(error_message)
        #When total_rows is 0 there are no results    
        if stop_gps_resp_dict['total_rows'] == 0:
            return generate_text_message(error_message)
        else:
            log_text_message(stop_ID[0], phone_number)
            stop_request_count = stop_gps_resp_dict['rows'][0]['net_reqs']
            increment_request_count(stop_request_count, database_ID)
    else:
        return generate_text_message(error_message)
    
    internet_resp_dict = get_closest_internet(stop_gps_resp_dict)
    return generate_response_text(internet_resp_dict)


def log_text_message(stop_ID, phone_number):    
    """Logs the incoming text sender's phone number & the stop ID into a Google
    Spreadsheet.
    
    In args:           stop_ID, phone_number
    Global vars in:    email_address, password, spreadsheet_key, worksheet_ID
    """
    spr_client = gdata.spreadsheet.service.SpreadsheetsService()
    spr_client.email = email_address
    spr_client.password = password
    spr_client.source = 'localfreeweb-sms-api'
    spr_client.ProgrammaticLogin()
    entry = spr_client.InsertRow(build_data_dict(stop_ID, phone_number),
                                 spreadsheet_key, worksheet_ID)


def increment_request_count(stop_request_count, database_ID):
    """Updates request count of Stop ID by incrementing it by 1.
    
    Global var in:    UPDATE_url
    In args:    stop_gps_resp_dict, database_ID
    """
    #UPDATE stops SET net_reqs=0 WHERE stop_id=390
    update_statement = 'UPDATE stops SET net_reqs = ' + stop_request_count
    #update_statement += ' WHERE stop_id = ' + database_ID
    
    #make_request(update_statement)


def make_request(sql_statement):
    """Builds and opens url for SQL statement to modify/add entry in database.
    
    Global vars in:    api_key, url
    In arg:            sql_statement
    """
    params = {
        'api_key' : apikey, # our account apikey, don't share!
        'q'       : sql_statement  # our SQL statement above
    }
    data = urllib.urlencode(params)
    print 'Encoded:', data
    
    try:
        response = urllib2.urlopen(url + '?' + data)
        
    except urllib2.HTTPError, e:
        
        print e.code
        print e.msg
        print e.headers
        print e.fp.read()    
    

def build_data_dict(stop_ID, phone_number):
    """Builds a dictionary that includes the date, time, phone_number and
    stop_ID of received text message.
    
    In args:    stop_ID, phone_number
    Out arg:    dict
    """
    dict = {}
    dict['date'] = arrow.now('US/Pacific').format('MM/DD/YYYY')
    dict['time'] = arrow.now('US/Pacific').format('hh:mm:ss A')
    dict['phone'] = phone_number
    dict['stop'] = stop_ID
    return dict
    
    
def get_stop_gps(database_ID):    
    """Requests GPS coordinates of Bus stop based on Stop ID.
    
    Global var in:    SELECT_url
    In arg:           database_ID
    Out arg:          response_dict
    """
    geo_url = SELECT_url + 'net_reqs, stop_lat, stop_lon FROM stops WHERE'
    geo_url += ' stop_id = ' + database_ID
    response = urllib.urlopen(geo_url)
    for line in response:
        response_dict = simplejson.loads(line)
    return response_dict


def generate_text_message(msg_body):
    """Helper function that creates text message.
    
    In arg:    msg_body
    Out arg:   resp
    """
    resp = twilio.twiml.Response()
    resp.message(msg_body)
    return str(resp)


def get_closest_internet(stop_gps_resp_dict):
    """Creates url to request 3 closest internet locations asking for the
    business name, address, hours for current day and phone number. Then
    makes the request.
    
    Global var in:     SELECT_url
    In arg:            stop_gps_resp_dict
    Out arg:           response_dict
    """
    geo_lat = str(stop_gps_resp_dict['rows'][0]['stop_lat'])
    geo_long = str(stop_gps_resp_dict['rows'][0]['stop_lon'])
    
    free_net_url = SELECT_url + 'bizname, address, ' + day + ', phone, '
    free_net_url += 'ST_Distance(the_geom::geography, ST_PointFromText('
    free_net_url += '\'POINT('+ geo_long + ' ' + geo_lat + ')\', 4326)'
    free_net_url += '::geography) AS distance FROM freeweb ORDER BY distance '
    free_net_url += 'ASC LIMIT 3'
    response = urllib.urlopen(free_net_url)
    for line in response:
        response_dict = simplejson.loads(line)
    return response_dict    


def generate_response_text(internet_resp_dict):
    """Generates text message to be sent back to the user.
    
    In arg:      internet_resp_dict
    Out arg:     resp
    """
    results = ""
        
    for i in internet_resp_dict['rows']:
        results += str(i['bizname']) + " "
        results += str(i['address']) + " "
        results += str(i['phone']) + " today's hrs:"
        results += str(i[day]).strip() + " | "        
    
    results = "Ask for 'free internet' at these places: " + results
    return generate_text_message(results[:-3])


if __name__ == "__main__":
    app.run(debug=True)

