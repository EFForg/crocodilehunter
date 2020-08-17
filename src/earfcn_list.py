#!/usr/bin/env python3
import argparse
import configparser
from wigle import Wigle

def main(args, config):
    wigle = Wigle(config['wigle_name'], config['wigle_key'])
    print("searching earfcns...")
    earfcn_list = ",".join(map(str, wigle.earfcn_search(args.lat, args.lon, args.radius)))
    print(f"earfcns = {earfcn_list}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Get an earfcn list from two gps coordinates")
    parser.add_argument('lat', help="Lattitude", type=float, action='store')
    parser.add_argument('lon', help="Longitude", type=float, action='store')
    parser.add_argument('-r', '--radius', dest="radius", help="radius to search", type=float, default=0.2, action='store')
    args = parser.parse_args()

    config = configparser.ConfigParser()
    config.read('config.ini')

    main(args, config["general"])
