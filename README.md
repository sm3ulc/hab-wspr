# hab-wspr

## High altittude ballon tracking via WSPR

The software webscrapes data from wsprnet.org, filter out calls from the balloons and decode additional telemetry. Currently the script supports upload to:

* habhub tracker ( https://tracker.habhub.org/ )
* aprs-fi ( https://aprs.fi ).

There are existing functions to load/save flightdata from csv/wsprnet-archive-files. ( http://wsprnet.org/drupal/downloads )

The protocol for the telemetry is described here:

* https://qrp-labs.com/flights/s4.html

# Installation

First clone the repo:

        git clone https://github.com/sm3ulc/hab-wspr

The package requires some extra modules that need to be installed via pip or similar

    apt install python-httplib2 python-requests python3-bs4
    
# Configuration

Edit balloon.ini and add aprs-is user etc. Add balloons on the format:

     [ habhub name, ham callsign for the balloon , band in mhz, channel ]

Uploads to APRS-IS is done by adding the SSID "-12" to the default balloon-callsign.


To run:

	python3 webscrape.py


The scripts work with a database in sqlite. It can be used to do all kinds of output/export like checking the last sent spots:

    sqlite3 wsprdb.db 'select * from sentspots order by time_sent desc limit 30'

