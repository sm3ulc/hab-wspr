# hab-wspr

## High altittude ballon tracking via WSPR

The software fetches data from WsprDaemon TimescaleDB, filters out calls from the balloons and decodes additional telemetry. Currently the script supports upload to:

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
python3 -m venv venv/
source venv/bin/activate
pip install -r requirements.txt
</pre>

# Configuration

Edit balloon.ini and add aprs-is user etc. Add balloons on the format:

<pre>
[ habhub name, aprs-wspr-call, band in mhz, channel, timeslot, datetime, html_push, aprs-ssid, aprs_comment]
</pre>


**habhub name** = fancy name to use on habhub

**aprs-wspr-call** = call to use for aprs data

**band in mhz** - band to use, i.e 20m band is 14 Mhz

**channel** - channelnumber 0 to 15

**timeslot** - 0 to disable use of timeslots. 1-5, use correspondent slot 00, 02, 04 etc.

**datetime** - starttime in isoformat to calculate duration

**html_push** 1 to push html page otherwise 0, ONLY for one balloon

**aprs-ssid** - the ssid to use with aprs-call

**aprs_comment** - comment to use for comment in aprs-packet


To run on linux: (with default config file balloon.ini)

<pre>
python3 run.py
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
python3 run.py --archive wsprspots-2019-12.csv.gz  --conf test.ini
</pre>

Read csv-file from spots.csv and process. 

<pre>
python3 run.py --csv spots.csv
</pre>





