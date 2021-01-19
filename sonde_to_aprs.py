#!/usr/bin/python
# Oh wait, you'll usually be running this on Windows :-)
#
# Sondemonitor to APRS bridge
# Copyright (C) 2014 Mark Jessop <vk5qi@rfhead.net>

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

import configparser
import time, datetime, urllib3, sys
import logging
from socket import *

# APRS-IS login info
serverHost = 'euro.aprs2.net' # Pick a local server if you like
serverPort = 14580

config = configparser.ConfigParser()
config.read('balloon.ini')
aprsUser = config['main']['aprsUser']
aprsPass = config['main']['aprsPass']

# APRS packet Settings
# This is the callsign the object comes from. Doesn't necessarily have to be the same as your APRS-IS login. 
callsign = config['main']['aprsCallsign']

def get_sonde():
        sonde_data = {}
        sonde_data["lat"] = str(sys.argv[2])
        sonde_data["lon"] = str(sys.argv[3])
        sonde_data["alt"] = "10000"
        sonde_data["id"] = str(sys.argv[1])
        sonde_data["speed"] = "0"
        sonde_data["temp"] = "0"
        sonde_data["batt"] = "0"
        sonde_data["comment"] = str(sys.argv[8])
        return sonde_data

# Push a Radiosonde data packet to APRS as an object.
def push_balloon_to_aprs(sonde_data):
        # Pad or limit the sonde ID to 9 characters.
        object_name = sonde_data["id"]
        if len(object_name) > 9:
       	        object_name = object_name[:9]
        elif len(object_name) < 9:
                object_name = object_name + " "*(9-len(object_name))
	
        # Convert float latitude to APRS format (DDMM.MM)
        lat = float(sonde_data["lat"])
        lat_degree = abs(int(lat))
        lat_minute = abs(lat - int(lat)) * 60.0
        lat_min_str = ("%02.2f" % lat_minute).zfill(5)
        lat_dir = "S"
        if lat>0.0:
                lat_dir = "N"
                
        lat_str = "%02d%s" % (lat_degree,lat_min_str) + lat_dir
	
        # Convert float longitude to APRS format (DDDMM.MM)
        lon = float(sonde_data["lon"])
        lon_degree = abs(int(lon))
        lon_minute = abs(lon - int(lon)) * 60.0
        lon_min_str = ("%02.2f" % lon_minute).zfill(5)
        lon_dir = "E"
        if lon<0.0:
                lon_dir = "W"
        lon_str = "%03d%s" % (lon_degree,lon_min_str) + lon_dir

        # Convert Alt (in metres) to feet
        alt = int(float(sonde_data["alt"])/0.3048)

        # Convert Speed (in metres) to feet
        speed = round(float(sonde_data["speed"]))

	#if speed < 1:
	#	speed = 1;

        temp = round(float(sonde_data["temp"]),1)
        batt = round(float(sonde_data["batt"]),2)
        object_comment = sonde_data["comment"]

        
        # Produce the APRS object string.
        #out_str = ";%s*111111z%s/%sO000/000/A=%06d Balloon" % (object_name,lat_str,lon_str,alt)
        # print(out_str)
        out_str = ";%s*111111z%s/%sO000/%03d/A=%06dTemp=%sC Solar=%sV %s" % (object_name,lat_str,lon_str,speed,alt,temp,batt,object_comment)
        logging.info('\033[33m' + "APRS: %s" + '\033[0m' , out_str)

	# Connect to an APRS-IS server, login, then push our object position in.	
	# create socket & connect to server
        sSock = socket(AF_INET, SOCK_STREAM)
        sSock.connect((serverHost, serverPort))
	# logon
        sSock.send(b'user %s pass %s vers VK5QI-Python 0.01\n' % (aprsUser.encode('utf-8'), aprsPass.encode('utf-8')) )
	# send packet
        sSock.send(b'%s>APRS:%s\n' % (callsign.encode('utf-8'), out_str.encode('utf-8')) )

	# close socket
        sSock.shutdown(0)
        sSock.close()

