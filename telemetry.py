#!/usr/bin/python3.6

from base64 import b64encode
import configparser
import csv
import datetime
from datetime import datetime,timedelta
import gzip
import hashlib
import httplib2
import logging
import json
import re
import requests
import sqlite3
import sys
import time

from pprint import pformat

import maidenhead

from balloon import *
from sonde_to_aprs import * 

# Power to decixmal conversion table 
pow2dec = {0:0,3:1,7:2,10:3,13:4,17:5,20:6,23:7,27:8,30:9,33:10,37:11,40:12,43:13,47:14,50:15,53:16,57:17,60:18}

config = configparser.ConfigParser()
config.read('balloon.ini')
habhub_callsign = config['main']['habhub_callsign']

def trim(spots):
    # Clean out old spots
    if len(spots) > 0:
        print(spots[-1:])
        time_last = 8
        spotc = 0
        splitspotc = 0
        for r in spots:
            spotc += 1
            if time_last < r:
                if splitspotc == 0:
                    splitspotc = spotc

        l = len(spots)
        spots = spots[splitspotc:]
        print("Split pre",l,"splitc",spotc,"after:",len(spots))
        
    return spots

# Read new spots from database
def readnewspotsdb():
    spots = []
    con = None
    data = None
    
    try:
        con = sqlite3.connect('wsprdb.db')
        cur = con.cursor()
        cur.execute('select * from newspots')
        data = cur.fetchall()

        for row in data:
#            print(row)'
            row[0] = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M')
            spots.append(list(row))
#            sys.exit(0)

        if not data:
            con.commit()
    except sqlite3.Error as e:
        print("Database error: %s" % e)
    except Exception as e:
        print("Exception in _query: %s" % e)
    finally:
        if con:
            con.close()
    print("Loaded spots:", len(spots))
    return spots


#
# Specs of the wspr-db format
#
# 1  Spot ID - A unique integer. Used as primary key in the database table. Not all spot numbers exist, and the files may not be in spot number order
# 2  Timestamp - The time of the spot in unix time() format (seconds since 1970-01-01 00:00 UTC).
# 3  Reporter - The station reporting the spot. Maximum of 10 characters.
# 4  Reporter's Grid - Maidenhead grid locator of the reporting station, in 4- or 6-character format.
# 5  SNR - Signal to noise ratio in dB as reported by the receiving software.
# 6  Frequency - Frequency of the received signal in MHz
# 7  Call Sign - Call sign of the transmitting station. 
# 8  Grid - Maidenhead grid locator of transmitting station, in 4- or 6-character format.
# 9  Power - Power, as reported by transmitting station in the transmission. 
# 10 Drift - The measured drift of the transmitted signal as seen by the receiver, in Hz/minute. 
# 11 Distance - Approximate distance between transmitter and receiver
# 12 Azimuth - Approximate direction, in degrees, from transmitting station to receiving station.
# 13 Band - Band of operation, computed from frequency as an index for faster retrieval. 
# 14 Version - Version string of the WSPR software in use by the receiving station. 
# 15 Code - Archives generated after 22 Dec 2010 have an additional integer Code field

# 1130358407,1522540800,DC0DX/MW2,JO31lk,-28,0.137553,2E0ILY,IO82qv,23,0,673,100,-1,,0

# 2018-05-28 05:50,OM1AI,7.040137,-15,0,JN88,+23,DA5UDI,JO30qj,724
# timestamp, tx_call , freq, snr , drift , tx_loc , power , rx_call, rx_loc, distance 
# 0          1         2     3     4       5        6       7        8       9



def readgz(balloons, gzfile):
    logging.info("Reading gz: %s", gzfile)

    rows = 0
    spots = []
    calls = []
    for b in balloons:
        calls.append(b[1])

    with gzip.open(gzfile, "rt") as csvfile:
        spotsreader = csv.reader(csvfile, delimiter=',', quotechar='|')

        for row in spotsreader:
            rows += 1
            # print(row)
            # Select correct fields in correct order
            row = [row[1], row[6], row[5], row[4], row[9], row[7], row[8],row[2],row[3],row[10]]

            # print(', '.join(row))
            for c in calls:
                if row[1] == c:
                    # Remove selfmade WSPR tranmissions
                    if len(row[5]) == 4:
                        row[0] = datetime.datetime.fromtimestamp(int(row[0]))
                        row[3] = int(row[3])
                        row[4] = int(row[4])

                        # Strip "+" from dB
                        row[6] = int(row[6].replace('+',''))
                        row[9] = int(row[9])
                        # print("Found", c, row)
                        spots.append(row)

            if re.match('(^0|^Q).[0-9].*', row[1]):
                row[0] = datetime.datetime.fromtimestamp(int(row[0]))
                
                row[3] = int(row[3])
                row[4] = int(row[4])
                        
                # Strip "+" from dB
                row[6] = int(row[6].replace('+',''))
                row[9] = int(row[9])
 
                spots.append(row)
                # sys.exit(0)

        print("Total rows", rows, "Nr-calls+telem:", len(spots))
        csvfile.close()

    return spots


def posdata_cmp(spot1, spot2):
    if [spot1[1],spot1[5],spot1[6]] == [spot2[1],spot2[5],spot2[6]]:
        print("lika")
        return True
    else:
        print("olika")
        return False

#  ['2018-05-15 18:14', 'SA6BSS', '14.097165', '-21', '0', 'AN84', '+13', '0.020', 'AI6VN/KH6', 'BL10rx', '2681', '1666']
#  [datetime.datetime(2018, 5, 15, 18, 16), 'Q11DCN', '14.097184', '-25', '1', 'FB18', '+30', '1.000', 'JH1HRJ', 'PM95pi', '15479', '9618']

# [datetime.datetime(2018, 6, 1, 5, 44), 'SA6BSS', '14.097174', -19, 1, 'MO15', 13, 'LA9JO', 'JP99gb', 2659] 
#  [datetime.datetime(2018, 6, 1, 5, 46), 'QK1TKY', '14.097174', -22, 0, 'FB17', 50, 'LA9JO', 'JP99gb', 17160]

# 2018-05-03 13:06:00, QA5IQA, 7.040161, -8, JO53, 27, DH5RAE, JN68qv, 537
# 0                    1       2         3   4     5   6       7       8 

def decode_telemetry(spot_pos, spot_tele):
#    print("Decoding!\n",spot_pos,"\n",spot_tele)

    spot_pos_time = spot_pos[0]
    spot_pos_call = spot_pos[1]
    spot_pos_loc = spot_pos[5]
    spot_pos_power = spot_pos[6]
    spot_tele_call = spot_tele[1]
    spot_tele_loc = spot_tele[5]
    spot_tele_power = spot_tele[6]
    
    # Convert call to numbers
    c1 = spot_tele_call[1]
 #   print("C1=",c1)
    if c1.isalpha():
        c1=ord(c1)-55
    else:
        c1=ord(c1)-48

    c2=ord(spot_tele_call[3])-65
    c3=ord(spot_tele_call[4])-65
    c4=ord(spot_tele_call[5])-65

    # Convert locator to numbers
    l1=ord(spot_tele_loc[0])-65
    l2=ord(spot_tele_loc[1])-65
    l3=ord(spot_tele_loc[2])-48
    l4=ord(spot_tele_loc[3])-48

    #
    # Convert power
    #

    p=pow2dec[spot_tele_power]
    sum1=c1*26*26*26
    sum2=c2*26*26
    sum3=c3*26
    sum4=c4
    sum1_tot=sum1+sum2+sum3+sum4

    sum1=l1*18*10*10*19
    sum2=l2*10*10*19
    sum3=l3*10*19
    sum4=l4*19
    sum2_tot=sum1+sum2+sum3+sum4+p
    # print("sum_tot1/2:", sum1_tot,sum2_tot)

    # 24*1068
    lsub1=int(sum1_tot/25632)
    lsub2_tmp=sum1_tot-lsub1*25632
    lsub2=int(lsub2_tmp/1068)

    # print("lsub1/2",lsub1,lsub2)

    alt=(lsub2_tmp-lsub2*1068)*20

    # Handle bogus altitudes
    if  alt > 14000:
 #       print("Bogus packet. Too high altitude!! locking to 9999")
        alt=9999
        
    if alt == 2760:
 #       print("Bogus packet. 2760 m  locking to 9998")
        alt=9998

    if alt == 0:
#        print("Zero alt detected. Locking to 10000")
        alt=10000

    # Sublocator
    lsub1=lsub1+65
    lsub2=lsub2+65
    subloc=(chr(lsub1)+chr(lsub2)).lower()

    # Temperature
    # 40*42*2*2
    temp_1=int(sum2_tot/6720)
    temp_2=temp_1*2+457
    temp_3=temp_2*5/1024
    temp=(temp_2*500/1024)-273

    # print("Temp: %5.2f %5.2f %5.2f %5.2f" % (temp_1, temp_2, temp_3, temp))
    
    #
    # Battery
    #
    # =I7-J7*(40*42*2*2)
    batt_1=int(sum2_tot-temp_1*6720)
    batt_2=int(batt_1/168)
    batt_3=batt_2*10+614

    # 5*M8/1024
    batt=batt_3*5/1024

    #
    # Speed / GPS / Sats
    #
    # =I7-J7*(40*42*2*2)
    # =INT(L7/(42*2*2))
    t1=sum2_tot-temp_1*6720
    t2=int(t1/168)
    t3=t1-t2*168
    t4=int(t3/4)
    speed=t4*2
    r7=t3-t4*4
    gps=int(r7/2)
    sats=r7%2

    # print("T1-4,R7:",t1, t2, t3, t4, r7)

    #
    # Calc lat/lon from loc+subbloc
    #
    loc=spot_pos_loc+subloc
    lat,lon = (maidenhead.toLoc(loc))
    
    pstr =    ("Spot %s Call: %6s Latlon: %10.5f %10.5f Loc: %6s Alt: %5d Temp: %4.1f Batt: %5.2f Speed: %3d GPS: %1d Sats: %1d" %
          (  spot_pos_time, spot_pos_call, lat, lon, loc, alt, temp, batt, speed, gps, sats ))
    logging.info(pstr)

    telemetry = {'time':spot_pos_time, "call":spot_pos_call, "lat":lat, "lon":lon, "loc":loc, "alt": alt,
                 "temp":round(temp,1), "batt":round(batt,3), "speed":speed, "gps":gps, "sats":sats }

    return telemetry

# Check if sencence is in history of sent spots
def checkifsentdb(sentence):
    con = None
    try:
        con = sqlite3.connect('wsprdb.db')
        cur = con.cursor()
        cur.execute('select * from sentspots where sentstr=?', (sentence,))
        data = cur.fetchall()

#        for row in data:
#            print("found", row)
        if len(data) > 0:
            if con:
                con.close()
            return True
        if not data:
            con.commit()
    except sqlite3.Error as e:
        print("Database error: %s" % e)
    except Exception as e:
        print("Exception in _query: %s" % e)
    finally:
        if con:
            con.close()

    return False


def addsentdb(name, time_rec, sentence):
    con = None
    time_sent = datetime.datetime.now()
    
    try:
        con = sqlite3.connect('wsprdb.db')
        cur = con.cursor()
#         cur.execute('drop table if exists sentspots')
        cur.execute('create table if not exists sentspots(name varchar(15),time_sent varchar(20), time_received varchar(20), sentstr varchar(50))')
        cur.execute("INSERT INTO sentspots VALUES(?,?,?,?)", (name, time_sent, time_rec, sentence))
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




def send_tlm_to_habitat2(sentence, callsign):
    result = call(["python2","./send_tlm_to_habitat.py", sentence,"sm0ulc"])
    return

def send_tlm_to_habitat(sentence, callsign, spot_time):
    input=sentence

    logging.info("Pushing data to habhub")


    if not sentence.endswith('\n'):
        sentence += '\n'
    sentence = sentence.encode("utf-8")
    sentence2 = b64encode(sentence)
    sentence = str(sentence2,'utf-8')

#    callsign = sys.argv[2] if len(sys.argv) > 2 else "HABTOOLS"

    date_created = spot_time.isoformat("T") + "Z" 
    date = datetime.datetime.utcnow().isoformat("T") + "Z"


    data = {
        "type": "payload_telemetry",
        "data": {
            "_raw": sentence
            },
        "receivers": {
            callsign: {
                "time_created": date_created,
                "time_uploaded": date,
                },
            },
        }


    h = httplib2.Http("")

    resp, content = h.request(
        uri="http://habitat.habhub.org:/habitat/_design/payload_telemetry/_update/add_listener/%s" % hashlib.sha256(sentence2).hexdigest(),
        method='PUT',
        headers={'Content-Type': 'application/json; charset=UTF-8'},
        body=json.dumps(data),
    )

    print(resp['status'])
    if resp['status'] == '201':
        print("OK 201", input)
    elif resp['status'] == '403':
        print("Error 403 - already uploaded")

    return


#
# Trim off older spots. Assuming oldest first!
#
def timetrim(spots, m):
    if len(spots) == 0:
        return spots

#    print("First:", spots[0][0], "Last: ", spots[-1:][0])
    time_last = datetime.datetime.utcnow() - timedelta(minutes=m)
    spotc = 0
    splitspotc = 0

    # find splitpoint in list
    for r in spots:
        spotc += 1
#        print(r[0], "vs ", time_last)
        if r[0] < time_last:
            splitspotc = spotc

    l = len(spots)
    if splitspotc > 0:
        spots = spots[splitspotc:]
        
    return spots


#
# Main function - filter, process and upload of telemetry
#
def process_telemetry(spots, balloons, habhub_callsign, push_habhub, push_aprs):

    # Filter out telemetry-packets
    spots_tele = []
    for row in spots:
        # print(row)
        if re.match('(^0|^Q).[0-9].*', row[1]):
            #         print(', '.join(row))
            #if re.match('10\..*', row[2]) or re.match('14\..*', row[2]):
            spots_tele.append(row)

    # 2018-05-03 13:06:00, QA5IQA, 7.040161, -8, JO53, 27, DH5RAE, JN68qv, 537
    # 0                    1       2         3   4     5   6       7       8 

    for b in balloons:
        if len(spots) == 0:
            logging.info("out of spots in balloonloop. returning")
            return spots
            
        balloon_name = b[0]
        balloon_call = b[1]
        balloon_mhz = b[2]
        balloon_channel = b[3]
        balloon_timeslot = b[4]

        logging.info("Name: %-8s Call: %6s MHz: %2d Channel: %2d Slot: %d" % (balloon_name, balloon_call, balloon_mhz, balloon_channel, balloon_timeslot))

        # Filter out telemetry for active channel
        if balloon_channel < 10:
            telem = [element for element in spots_tele if re.match('^0.'+str(balloon_channel), element[1])]
        else:
            telem = [element for element in spots_tele if re.match('^Q.'+str(balloon_channel-10), element[1])]

        # Filter out only selected band
        telem = [element for element in telem if re.match(str(balloon_mhz)+'\..*', element[2])]

        # If timeslot is used. filter out correct slot
        if balloon_timeslot > 0:
            telem = [element for element in telem if balloon_timeslot == int(element[0].minute % 10 / 2)]
                                
        #if len(telem) > 0:
            # logging.info("time at top-tele spot: %s", str(telem[0]))

        # Loop through all spots and try to find matching telemetrypacket
        spot_last = spots[0]
        spot_oldtime = datetime.datetime(1970, 1, 1, 1, 1)
        bspots = []
        for row in spots:
            if balloon_call == row[1]:
                bspots.append(row)
                
        logging.info("Spots: %d  Telemetry: %d", len(bspots), len(telem))
        for row in bspots:
            # logging.info("B: %s",row)
            spot_call = row[1]
            
            if balloon_call == spot_call:
                spot_time = row[0]

                # Only check new uniq times
                if spot_time != spot_oldtime:

                    # [datetime.datetime(2019, 8, 1, 0, 22), 'YO3ICT', '14.097148', -23, -1, 'BM73', 10, 'ND7M', 'DM16', 2564]
                    pstr = "Call: %s Time: %s Fq: %s Loc: %s Power: %s Reporter: %s" %  (row[1], row[0], row[2], row[5], row[6], row[7])
                    logging.info(pstr)
                    spot_oldtime = spot_time
                    spot_fq = row[2]
                    spot_power = row[4]
                    spot_loc = row[5]
                    spot_reporter = row[6]        
                    spot_reporter_loc = row[7]
                    
                # Match positioningpacket with telemetrypackets
                    b_telem = []
                    for trow in telem:
                        # print("tdiff:",trow, spot_time, type(spot_time))
                        tdiff = trow[0] - spot_time
                        #                    print(tdiff)

                        if tdiff > timedelta(minutes=8):
                            logging.info("Too long interval, breaking %s", str(tdiff))
                            break
                        if tdiff > timedelta(minutes=0):
                            b_telem.append(trow)

                    # If suitable telemetry found, enter decoding!
                    if len(b_telem) > 0:
                        logging.info("Found suitable telemetry rows: %d",len(b_telem))

                        # print("call", spot_call,"time",spot_time,"fq",spot_fq,"loc", spot_loc,"power",spot_power,"reporter",spot_reporter)
                        #logging.info(pstr)
                        #logging.info("T: %s", b_telem[0])
                        telemetry = decode_telemetry(row, b_telem[0])
                        if len(telemetry) > 0:
                            # Delete spot and telemetryspot
                            try:
                                spots.remove(row)
                            except ValueError:
                                pass

                            for rt in b_telem:
                                pstr = "%s Time: %s Fq: %s Loc: %s Power: %s Reporter: %s" %  (rt[1], rt[0], rt[2], rt[5], rt[6], rt[7]) 
                                logging.info("Removing: %s", pstr)
                                try:
                                    spots.remove(rt)
                                except ValueError:
                                    pass

                                try:
                                    spots_tele.remove(rt)
                                except ValueError:
                                    pass

                                try:
                                    telem.remove(rt)
                                except ValueError:
                                    pass

                            # logging.info(telemetry)

                            # seqnr = int(((int(telemetry['time'].strftime('%s'))) / 120) % 100000)
                            seqnr = int(telemetry['time'].strftime('%s'))

                            # telemetry = [ spot_pos_time, spot_pos_call, lat, lon, loc, alt, temp, batt, speed, gps, sats ]
                            telestr = "%s,%d,%s,%.5f,%.5f,%d,%d,%.2f,%.2f,%d,%d" % (  
                                balloon_name, seqnr, telemetry['time'].strftime('%H:%M'), telemetry['lat'], telemetry['lon'],
                                telemetry['alt'], telemetry['speed'], telemetry['temp'], telemetry['batt'], telemetry['gps'], telemetry['sats'])

                            # Calculate and add XOR-checksum
                            i=0
                            checksum = 0
                            while i < len(telestr):
                                checksum = checksum ^ ord(telestr[i])
                                i+=1
                            telestr = "$$" + telestr + "*" + '{:x}'.format(int(checksum))
                            logging.info("Telemetry: %s", telestr)

                            # Check if string has been uploaded before and if not then add and upload
                            if not checkifsentdb(telestr):
                                # print("Unsent spot", telestr)

                                if push_habhub:
                                    # Send telemetry to habhub
                                    #                                send_tlm_to_habitat2(telestr, habhub_callsign)                            
                                    send_tlm_to_habitat(telestr, habhub_callsign, spot_time)                            

                                if push_aprs:
                                    # Prep and push basic data to aprs.fi
                                    sonde_data = {}
                                    sonde_data["id"] = spot_call + "-12"
                                    sonde_data["lat"] = telemetry['lat']
                                    sonde_data["lon"] = telemetry['lon']
                                    sonde_data["alt"] = telemetry['alt']
                                    logging.info("Pushing data to aprs.fi")
                                    push_balloon_to_aprs(sonde_data)


                                # Add sent string to history-db
                                addsentdb(balloon_name, row[0], telestr)

                            else:
                                logging.info("Already sent spot. Doing nothing")

    return spots



        
