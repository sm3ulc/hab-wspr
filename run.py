#!/usr/bin/env python3

import configparser
import csv
import datetime
import getopt
import os
import requests
import sqlite3
import sys
import time
import psycopg2

from balloon import *
from telemetry import *

def to_list(tuple):
    return list(tuple)

def getspots (nrspots):
    # The connection credentials are public, i.e. https://inductivestep.github.io/WSPR-analysis/
    try:
        conn = psycopg2.connect("host=logs2.wsprdaemon.org dbname=wsprnet user=wdread password=JTWSPR2008")
    except psycopg2.OperationalError as err:
        logging.error("PostgreSQL connect error: " + err)
        conn = None
    cursor = conn.cursor()
    cursor.execute('SELECT "wd_time", "CallSign", "MHz", "dB", "Drift", "Grid", "Power", "Reporter", "ReporterGrid", "distance" FROM spots ORDER BY "wd_time" DESC LIMIT ' + str(nrspots))
    sqldata = cursor.fetchall()
    tabledata = map(to_list, sqldata)
    conn.close()
    return list(tabledata)

# 
# Dump new spots to db. Note stripping of redundant fields
#
# 2018-05-28 05:50,OM1AI,7.040137,-15,0,JN88,+23,DA5UDI,JO30qj,724
def dumpnewdb(spotlist):
    con = None
    data = None
    
    try:
        con = sqlite3.connect('wsprdb.db')
        cur = con.cursor()
        cur.execute('create table if not exists newspots(timestamp varchar(20), tx_call varchar(10), freq real, snr integer, drift integer, tx_loc varchar(6), power integer, rx_call varchar(10), rx_loc varchar(6), distance integer)')
        for row in spotlist:
            cur.execute("INSERT INTO newspots VALUES(?,?,?,?,?,?,?,?,?,?)", (row))
            data = cur.fetchall()

        if not data:
            con.commit()
    except sqlite3.Error as e:
        print("Database error: %s" % e)
    except Exception as e:
        print("Exception in _query: %s" % e)
    finally:
        if con:
            con.close()
    return

# Fitler out only calls from balloons and telemetrypackets
def balloonfilter(spots,balloons):
    filtered = []
    calls = []
    for b in balloons:
        calls.append(b[1])

    for row in spots:
        for c in calls:
            if row[1] == c:

                # Remove selfmade WSPR tranmissions
                if len(row[5]) == 4:
                    filtered.append(row)
                else:
                    row[5] = row[5][0:4]
                    filtered.append(row)

        if re.match('(^0|^1|^Q).[0-9].*', row[1]):
            filtered.append(row)

#    for r in filtered:
#        logging.info("filtered out",r)

    return filtered

# 2018-05-28 05:50,OM1AI,7.040137,-15,0,JN88,+23,DA5UDI,JO30qj,724
def deduplicate(spotlist):
    pre=len(spotlist)
    
    rc = 0
    rc_max = len(spotlist)-1
    if rc_max > 1:
        while rc < rc_max:
            if (spotlist[rc][0] == spotlist[rc+1][0]) and (spotlist[rc][1] == spotlist[rc+1][1]):
#                logging.info("Duplicate entry")
                del spotlist[rc]
                rc_max -= 1
            else:
                rc += 1

#    print("Deduplicate:",pre, len(spotlist))
    return spotlist


# Setup logging

level    = logging.INFO
format   = '%(asctime)s - %(message)s'
handlers = [logging.FileHandler('logging.txt','a'), logging.StreamHandler()]
logging.basicConfig(level = level, format = format, handlers = handlers, datefmt='%y-%m-%d %H:%M:%S')

#
# Some options
# 

verbose = False
archive_file = ''
csv_file = ''
conf_file = 'balloon.ini'
dry_run = False

#print("ARGV      :", sys.argv[1:])

try:
      options, remainder = getopt.getopt(
            sys.argv[1:],
            'c:f:v',
                ['archive=',
                 'csv=',
                 'conf=',
                ])

except getopt.GetoptError as err:
    print('ERROR:', err)
    sys.exit(1)


#logging.info("OPTIONS   : %s", str(options))
      
for opt, arg in options:
    if opt in ('--archive'):
        archive_file = arg
    if opt in ('--csv'):
        csv_file = arg
    if opt in ('--conf'):
        conf_file = arg
    if opt in ('--dry_run'):
        dry_run = True
    elif opt in ('-v', '--verbose'):
        verbose = True

config = configparser.ConfigParser()
config.read(conf_file)
push_habhub = config['main'].getboolean('push_habhub')
push_aprs = config['main'].getboolean('push_aprs')
push_html = config['main'].getboolean('push_html')

balloons = json.loads(config.get('main','balloons'))
            
logging.info("Tracking these balloons:")
for b in balloons:
      logging.info("%s", str(b))

if dry_run:
    logging.info("Dru run. No uploads")
    push_habhub = False
    push_aprs = False
      
spots = []

#
# Load and process spots from archive-file - default append to csv
#

if archive_file:
      logging.info("Archive-mode")

      # Read archivefile and filter out balloondata
      spots = readgz(balloons, archive_file)
      # logging.info(spots[0])
      spots.sort(reverse=False)

      # Do a crude trimetrim 
      # temp_spots = []
      #for s in spots:
      #      if s[0] > datetime.datetime(2018, 5, 15, 0, 0) and s[0] > datetime.datetime(2018, 5, 15, 0, 0):
      #            temp_spots.append(s)
      # spots = temp_spots
      
      dumpcsv(spots)

      if len(spots) > 1:
            logging.info("Spots: %s", str(len(spots)))
            spots = process_telemetry(spots, balloons,habhub_callsign, push_habhub, push_aprs)
      else:
            logging.info("No spots!")
            
      logging.info("Done")
      sys.exit(0)

#
# Load and process spots from csv-file
#
      
if csv_file:
      push_habhub = False
      push_aprs = False

      spots = readcsv()

      # Do a crude trimetrim 
      # temp_spots = []
      # for s in spots:
      #     if s[0] > datetime.datetime(2019, 12, 18, 11, 0) and s[0] < datetime.datetime(2019, 12, 18, 12, 30):
      #         # print(s)
      #         temp_spots.append(s)
      # spots = temp_spots

      
      if len(spots) > 1:
            logging.info("Spots: %s", str(len(spots)))
            spots = process_telemetry(spots, balloons,habhub_callsign, push_habhub, push_aprs)
      else:
            logging.info("No spots!")

      logging.info("Done")
      sys.exit(0)
            
# Spots to pullfrom wsprnet
nrspots_pull= 2000
spotcache = []

logging.info("Preloading cache from WsprDaemon...")
spotcache = getspots(10000)
logging.info("Fspots1: %d",len(spotcache))
spotcache = balloonfilter(spotcache ,balloons)
logging.info("Fspots2: %s", len(spotcache))

spots = spotcache
cache_max = 10000
new_max = 0
only_balloon=False
sleeptime = 75

logging.info("Entering pollingloop.")
while 1==1:
    tnow = datetime.datetime.now() 

    dbspots = getspots(nrspots_pull)
    dbspots = balloonfilter(dbspots ,balloons)
    newspots = [] 

    # Sort in case some spots arrived out of order
    spotcache.sort(reverse=False)   
    spotcache = timetrim(spotcache,120)

    src_cc = 0 

    # Loop trough cache and check for new spots
    for row in dbspots:
        old = 0
        for srow in spotcache:
            # print("testing:",row, "\nagainst:", srow)
            src_cc += 1
            if row == srow:
                # print("Found",row)
                old = 1
                break

        if old == 0:
            # logging.info("New",str(row))
            logging.info("New spot: %s",row)
            
            # Insert in beginning for cache
            spotcache.insert(0, row)


 #           for w in spotcache:
 #               print("cache2:", w)

            # Add last for log
            newspots.append(row)

#     spotcache.sort(reverse=True)
#    print("first:",spotcache[0][0]," last: ",spotcache[-1:][0][0])
#    print("DATA:\n")
#    for row in newspots:
#        print("Newspots:",row)

#    dumpcsv(newspots)
    dumpnewdb(newspots)

    spots = spots + newspots
    spots.sort(reverse=False)   
    spots = deduplicate(spots) # needs sorted list
    # Filter out all spots newer that x minutes
    spots = timetrim(spots,7)

    if len(spots) > 1:
        logging.info("pre-tele: %d",len(spots))
        spots = process_telemetry(spots, balloons,habhub_callsign, push_habhub, push_aprs, push_html)
        logging.info("pro-tele: %s", str(len(spots)))

    if new_max < len(newspots):
#  and len(newspots) != nrspots_pull:
        new_max = len(newspots)

    if len(newspots) == nrspots_pull:
        logging.info("Hit max spots. Increasing set to fetch")
        nrspots_pull += 100

    printstr = ("Spots: %5d Cache: %6d New: %5d (max: %5d) Nrspots: %5d Looptime: %s Checks: %8d" % 
          (len(spots), len(spotcache), len(newspots), new_max, nrspots_pull, str(datetime.datetime.now() - tnow).split(":")[2], src_cc)) 
    logging.info(printstr)
    
    spotcache = spotcache[:cache_max]

    sleeping = sleeptime - time.time() % sleeptime
#     logging.info("Sleep:", sleeping)
    time.sleep(sleeping)







        
