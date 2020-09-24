#!/usr/bin/python3

"""
This is a replacement for a shell script from README.md that can be used to generate FCC tower
data CSV files. This script will produce a filed called fccinfo-towers.csv which can be ingested
using add_known_tower.py. It leverages GPSD, or if GPSD is not working it uses location data from
config.ini.
By ThreeSixes 23 Sep, 2020
"""

import configparser
import csv
from pprint import pprint
import re
import urllib3

import gpsd

latlon = []
lines = []

http = urllib3.PoolManager()
lines_match = re.compile(r"^[ ]+<coordinates>([0-9\-\.]+),([0-9\-\.]+),[0-9]+</coordinates>$")

config_fp = 'config.ini'
config = configparser.ConfigParser()
config.read(config_fp)

try:
    packet = gpsd.get_current()
    tries = 1
    while tries < 4:
        # After every 3 tries get the location from config.
        if tries == 3:
            raise AttributeError("No GPS coords.")

        if packet.mode < 1:
            latlon = [packet.lat, packet.lon]
            break

        tries += 1
        packet = gpsd.get_current()

except AttributeError:
    latlon = config['general']['gps_default'].split(", ")

print("Geting towers around: %s, %s" %(latlon[0], latlon[1]))

# TODO: Figure out how to make the radius configurable.
target_url = "http://ge.fccinfo.com/googleEarthASR.php?LOOK=%s,%s,50915.07,0,60.7" \
        %(latlon[1], latlon[0])

http = urllib3.PoolManager()
r = http.request('GET', target_url)

# Bytes->UTF8 string, UTF8 string->List
page_content = r.data.decode("utf-8")
lines = page_content.splitlines()

with open('fccinfo-towers.csv', 'w') as csvfile:
    csv_file = csv.writer(csvfile, delimiter=',')
    for line in lines:
        matches = re.match(lines_match, line)
        if matches:
            match_groups = matches.groups()
            csv_file.writerow([match_groups[1], match_groups[0], "imported from ge.fccinfo.com"])