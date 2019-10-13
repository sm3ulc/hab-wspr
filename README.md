# hab-wspr

## High altittude ballon tracking via WSPR

The software webscrapes data from wsprnet.org, filter out calls from the balloons and decode additional telemetry.

The protocol for the telemetry is described here:

https://qrp-labs.com/flights/s4.html


# Installation

	git clone https://github.com/sm3ulc/hab-wspr

The package requires some extra modules that need to be installed via pip or similar

    apt install python-httplib2 python-requests python3-bs4
    
# Configuration

Edit balloon.ini and add aprs-is user, callsigns, balloons etc


To run:

	python3 webscrape.py
