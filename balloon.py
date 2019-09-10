
# from datetime import datetime,timedelta
import datetime
import sqlite3
import csv
import sys


def balloonstodb(balloons):
        con = None

        print("Writing balloons do db")
        try:
            con = sqlite3.connect('wsprdb.db')
            cur = con.cursor()
            cur.execute('drop table if exists balloons')
            cur.execute('create table if not exists balloons(name varchar(20), call varchar(10), freq integer, channel integer)')
            for row in balloons:
                cur.execute("INSERT INTO balloons VALUES(?,?,?,?)", (row))
                print(row)
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


def readballoonsdb():
    con = None
    balloons = []
    data = []

    print("Reading balloons from db")
    try:
        con = sqlite3.connect('wsprdb.db')
        cur = con.cursor()
        cur.execute('select * from balloons')
        data = cur.fetchall()
        for row in data:
            print(row)
            balloons.append(list(row))

        if not data:
            con.commit()
    except sqlite3.Error as e:
        print("Database error: %s" % e)
    except Exception as e:
        print("Exception in _query: %s" % e)
    finally:
        if con:
            con.close()
#    print("Loaded balloons:", len(balloons))
    return balloons

# Dumps all spots to csv-file
def dumpcsv(spotlist):
    with open('spots.csv', 'a', newline='') as csvfile:
        spotswriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)

        for row in spotlist:
            row[0] = datetime.datetime.strftime(row[0], '%Y-%m-%d %H:%M')
            spotswriter.writerow(row)

        csvfile.close()



#  Date Call Frequency SNR Drift Grid dBm W reporter locator dist-km dist-mi 
# 2018-05-21 19:04,F6HCO,10.140216,-11,1,J19bg,+33,1.995,SM0EPX/RX2,JO89si,1495,929

# 2018-05-03 13:06:00, QA5IQA, 7.040161, -8, JO53, 27, DH5RAE, JN68qv, 537
# 0                    1       2         3   4     5   6       7       8 

# 2018-06-14 09:08,QA5IQB,5.288761,-26,0,JO22,+20,DL0HT,JO43jb,266
# 0                1      2         3  4 5    6   7     8      9


def readcsv():
    spots = []
    with open('spots.csv', newline='') as csvfile:
	    spotsreader = csv.reader(csvfile, delimiter=',', quotechar='|')

	    for row in spotsreader:


		    row[0] = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M')
		    row[3] = int(row[3])
		    row[4] = int(row[4])
		    # Strip "+" from dB
		    row[6] = int(row[6].replace('+',''))
		    row[9] = int(row[9])

#		    print(row)
		    spots.append(row)

    csvfile.close()
#       print(spotsreader)
    print("Loaded spots:", len(spots))
    print("First",spots[1:][0])
    print("Last",spots[-1:][0])

    return spots
