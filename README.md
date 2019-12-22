# hab-wspr

## High altittude ballon tracking via WSPR

The software webscrapes data from wsprnet.org, filter out calls from the balloons and decode additional telemetry. Currently the script supports upload to:

* habhub tracker ( https://tracker.habhub.org/ )
* aprs-fi ( https://aprs.fi ).

There are existing functions to load/save flightdata from csv/wsprnet-archive-files.
( http://wsprnet.org/drupal/downloads )

The protocol for the telemetry is described here:

* https://qrp-labs.com/flights/s4.html


# Installation

First clone the repo:

<pre>
git clone https://github.com/sm3ulc/hab-wspr
</pre>

The package requires some extra modules that need to be installed via pip or similar

<pre>
apt install python-httplib2 python-requests python3-bs4
</pre>


For windows users install anaconda with python 3.

<pre>
pip install httplib2
pip install bs4
</pre>

# Configuration

Edit balloon.ini and add aprs-is user etc. Add balloons on the format:

<pre>
[ habhub name, ham callsign for the balloon , band in mhz, channel, timeslot ]
</pre>

timeslot = 0 to disable use of timeslots. 1-5, use correspondent slot 00, 02, 04 etc.


Uploads to APRS-IS is done by adding the SSID "-12" to the default balloon-callsign.


To run on linux: (with default config file balloon.ini)

<pre>
python3 webscrape.py
</pre>


The scripts work with a database in sqlite. It can be used to do all kinds of output/export like checking the last sent spots:

<pre>
sqlite3 wsprdb.db 'select * from sentspots order by time_sent desc limit 30'
</pre>

# Testing

Adjust your balloon.ini or other configfile like test.ini.

Goto http://wsprnet.org/drupal/downloads or

<pre>
wget http://wsprnet.org/archive/wsprspots-2019-12.csv.gz
</pre>

Extract data from archive and append filtered spots to spots.csv in and then process. 

<pre>
python3 webscrape.py --archive wsprspots-2019-12.csv.gz  --conf test.ini	 
</pre>

Read csv-file from spots.csv and process. 

<pre>
python3 webscrape.py --csv spots.csv
</pre>





