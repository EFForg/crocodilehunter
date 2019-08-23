#!/usr/bin/env python3

import os
import math
from math import radians, cos, sin, asin, sqrt
import socketserver
from threading import Thread
from datetime import datetime

import gpsd
import numpy
from sqlalchemy import func, text
from scipy.optimize import minimize

from database import Tower, init_db
from wigle import Wigle

class Watchdog():
    SOCK = f"/tmp/croc.sock"

    def __init__(self, args):
        self.project_name = args.project_name
        self.db_session = init_db(self.project_name)
        self.disable_wigle = args.disable_wigle
        self.debug = args.debug
        self.disable_gps = args.disable_gps
        self.logger = args.logger
        self.config = args.config
        if not self.disable_wigle:
            self.wigle = Wigle(self.config['general']['wigle_name'],
                               self.config['general']['wigle_key'])

    def last_ten(self):
        return self.db_session.query(Tower.id, Tower, func.max(Tower.timestamp)).group_by(Tower.cid).order_by(Tower.timestamp.desc())[0:10]

    def get_unique_enodebs(self):
        return self.db_session.query(Tower.id, Tower, func.max(Tower.timestamp)).group_by(Tower.enodeb_id).order_by(Tower.id.desc())

    def strongest(self):
        for row in Tower.query.filter(Tower.rssi != 0.0).filter(Tower.rssi.isnot(None)).order_by(Tower.rssi.desc())[0:10]:
            if row is None:
                continue
            self.logger.debug(f"{row}, power: {row.rssi}")

    def get_row_by_id(self, row_id):
        return Tower.query.get(row_id)

    def get_similar_towers(self, tower):
        """ Gets towers with similar mnc, mcc, and tac."""
        return Tower.query.filter(Tower.mnc == tower.mnc).filter(Tower.mcc == tower.mcc).filter(Tower.enodeb_id == tower.enodeb_id)

    def get_towers_by_cid(self, cid):
        return Tower.query.filter(Tower.cid == cid)

    def count(self):
        num_rows = Tower.query.count()
        num_towers = Tower.query.with_entities(Tower.enodeb_id).distinct().count()
        self.logger.verbose(f"Found {num_towers} towers a total of {num_rows} times")

    def get_gps(self):
        if self.disable_gps:
            gps = self.config['general']['gps_default'].split(',')
            packet = type('Packet', (object,), {'lat': float(gps[0]), 'lon': float(gps[1])})()
        else:
            gpsd.connect()
            packet = gpsd.get_current()
            while packet.lat == 0.0 and packet.lon == 0.0:
                packet = gpsd.get_current()

        return packet

    def process_tower(self, data):
        self.logger.debug(f"server recd: {data}")
        data = data.split(",")
        packet = self.get_gps()
        new_tower = Tower(
                mcc = int(data[0]),
                mnc = int(data[1]),
                tac = int(data[2]),
                cid = int(data[3]),
                phyid = int(data[4]),
                earfcn = int(data[5]),
                rssi = float(data[6]),
                frequency = float(data[7]),
                enodeb_id = float(data[8]),
                sector_id = float(data[9]),
                cfo = float(data[10]),
                rsrq = float(data[11]),
                snr = float(data[12]),
                raw_sib1 = data[13],
                timestamp = datetime.fromtimestamp(int(data[14])),
                lat = packet.lat,
                lon = packet.lon,
                )

        new_tower.est_distance()
        self.logger.success(f"Adding a new tower: {new_tower}")
        self.db_session.add(new_tower)
        self.db_session.commit()
        self.calculate_suspiciousness(new_tower)
        self.count()

    def check_all(self):
        towers = self.db_session.query(Tower).all()
        for tower in towers:
            self.calculate_suspiciousness(tower)

    def get_all_by_suspicioussnes(self):
        towers = self.db_session.query(Tower).all()
        towers.sort(key=lambda t: t.suspiciousness, reverse=True)
        return towers

    def check_mcc(self, tower):
        """ In case mcc isn't a standard value."""
        if tower.mcc not in (310, 311, 316):
            tower.suspiciousness += 30

    def check_mnc(self, tower):
        """ In case mnc isn't a standard value."""
        known_mncs = [410,260,480]
        """
        known_mncs = [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 20, 23, 24,
                25, 26, 30, 31, 32, 34, 38, 40, 46, 50, 60, 70, 80, 90, 100, 110, 120, 130,
                140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260, 270, 280,
                290, 300, 310, 311, 320, 330, 340, 350, 360, 370, 380, 390, 400, 410, 420,
                430, 440, 450, 460, 470, 480, 490, 500, 510, 520, 530, 540, 550, 560, 570,
                580, 590, 600, 610, 620, 630, 640, 650, 660, 670, 680, 690, 700, 710, 720,
                730, 740, 750, 760, 770, 780, 790, 800, 810, 820, 830, 840, 850, 860, 870,
                880, 890, 900, 910, 920, 930, 940, 950, 960, 970, 980, 990]
        """
        # TODO: the above are all known MNCs in the USA from cell finder's db, but do we really
        # want to include all of them?
        if tower.mnc not in known_mncs:
            tower.suspiciousness += 20

    def check_existing_rssi(self, tower):
        """ If the same tower has been previously recorded but is suddenly
        recorded at a much higher power level."""
        existing_towers = self.db_session.query(Tower).filter(
                Tower.mcc == tower.mcc,
                Tower.mnc == tower.mnc,
                Tower.tac == tower.tac,
                Tower.cid == tower.cid,
                Tower.phyid == tower.phyid,
                Tower.earfcn == tower.earfcn,
                Tower.rssi.isnot(None)
                ).all()
        rssi_levels = [x.rssi for x in existing_towers]
        if tower.rssi is not None and len(rssi_levels) > 3:
            std = numpy.std(rssi_levels)
            mean = numpy.mean(rssi_levels)

            # TODO: think about this some more.
            if tower.rssi is None or tower.rssi > mean + std:
                tower.suspiciousness += (tower.rssi - mean)

    def check_changed_tac(self, tower):
        """ If the tower already exists but with a different tac."""
        existing_tower = self.db_session.query(Tower).filter(
                Tower.mcc == tower.mcc,
                Tower.mnc == tower.mnc,
                Tower.cid == tower.cid,
                Tower.phyid == tower.phyid,
                Tower.earfcn == tower.earfcn,
                ).first()

        if existing_tower is not None:
            if existing_tower.tac != tower.tac:
                tower.suspiciousness += 10

    def get_centroid(self, towers):
        lats = numpy.unique([x.lat for x in towers])
        lons = numpy.unique([x.lon for x in towers])
        return (numpy.mean(lats), numpy.mean(lons))



    def check_new_location(self, tower):
        """ If it's the first time we've seen a tower in a given
        location (+- some threshold)."""
        # TODO: ask someone who has thought about this
        # pymcmc
        # bayseian statistics for hackers
        # distribution of points
        # calculate distribution of findability  probability of distance x that i will fidn a tower
        # what is the probability that the given point is part of thatd distribution
        # exponential lamdax

        existing_towers = self.db_session.query(Tower).filter(
                Tower.mcc == tower.mcc,
                Tower.mnc == tower.mnc,
                Tower.enodeb_id == tower.enodeb_id,
                ).all()

        lats = numpy.unique([x.lat for x in existing_towers])
        lons = numpy.unique([x.lon for x in existing_towers])
        if abs(max(lats) - min(lats)) < 0.01 or abs(max(lons) - min(lons)) < 0.01:
            # Skip calculation until diameter is of a certain size ... half of 1/100th of a lat or lon.
            return

        center_point = (numpy.mean(lats), numpy.mean(lons))
        center_point_std_dev = (numpy.std(lats), numpy.std(lons))
        border_point = (center_point[0] + center_point_std_dev[0], center_point[1] + center_point_std_dev[1])

        self.logger.info(f"tower: {tower.lat}, {tower.lon}")
        self.logger.info(f"center_point: {center_point}")

        radius = self._get_point_distance(center_point, border_point)
        self.logger.info(f"radius: {radius}")
        distance = self._get_point_distance(center_point, [tower.lat, tower.lon])
        self.logger.info(f"distance: {distance}")

        if int(distance * 10000) > int(radius * 10000):
            s_coeff = (10 * distance - radius) ** 2
            self.logger.info('tower outside expected range')
            self.logger.info(f'increasing suspiciousness by {s_coeff}')

            tower.suspiciousness += s_coeff

    def _get_point_distance(self, centerpoint, outpoint):
        a = abs(abs(centerpoint[0]) - abs(outpoint[0]))
        b = abs(abs(centerpoint[1]) - abs(outpoint[1]))
        return math.sqrt(a*a + b*b)


    def check_rssi(self, tower):
        """ If a given tower has a power signal significantly stronger than we've ever seen."""
        # TODO: maybe we should modify this to be anything over a certain threshold, like -50 db or something.
        existing_towers = self.db_session.query(Tower).filter(Tower.rssi.isnot(None)).all()
        rssis = [x.rssi for x in existing_towers]
        if tower.rssi is not None and len(rssis) > 3:
            rssi_mean = numpy.mean(rssis)
            rssi_std = numpy.std(rssis)

            if tower.rssi > rssi_mean + rssi_std:
                tower.suspiciousness += tower.rssi - rssi_mean

    def check_wigle(self, tower):
        if self.disable_wigle:
            self.logger.warning("Wigle API access disabled locally!")
        else:
            #self.wigle.cell_search(tower.lat, tower.lon, 0.0001, tower.cid, tower.tac)
            resp = self.wigle.cell_search(tower.lat, tower.lon, 0.1, tower.cid, tower.tac)
            self.logger.debug("conducting a cell search: " + str(resp))
            if resp["resultCount"] < 1:
                tower.suspiciousness += 20

    def calculate_suspiciousness(self, tower):
        tower.suspiciousness = 0
        # TODO: let's try some ML?
        self.check_mcc(tower)
        self.check_mnc(tower)
        self.check_existing_rssi(tower)
        self.check_changed_tac(tower)
        self.check_new_location(tower)
        self.check_rssi(tower)
        self.check_wigle(tower)
        self.db_session.commit()

    def trilaterate_enodeb_location(self, tower):
        """
        perform trilateration on tower readings and distance estimates to estimate location of enodeb
        return - tuple (est_lat, est_lon, confidence)
        """
        towers = Tower.query.filter(Tower.mnc == tower.mnc).filter(Tower.mcc == tower.mcc).filter(Tower.enodeb_id == tower.enodeb_id).group_by(func.concat(Tower.lat, Tower.lon))
        centroid = self.get_centroid(towers)
        print(f"count: {towers.count()}")
        if towers.count() < 3:
            return (centroid[0],centroid[1])

        # locations: [ (lat1, long1), ... ]
        # distances: [ distance1,     ... ]
        locations = [(t.lat, t.lon) for t in towers]
        distances = [t.est_dist for t in towers]

        def _great_circle_distance(lat1, lon1, lat2, lon2):
            """
            Calculate the great circle distance between two points
            on the earth (specified in decimal degrees)
            """
            # convert decimal degrees to radians
            lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

            # haversine formula
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * asin(sqrt(a))
            r = 6371088 # Radius of earth in meters
            return c * r

        # trilaterate(towers(lat, lon, est_dist))
        def _mse(x, locations, distances):
            mse = 0.0
            for location, distance in zip(locations, distances):
                distance_calculated = _great_circle_distance(x[0], x[1], location[0], location[1])
                mse += math.pow(distance_calculated - distance, 2.0)
            return mse / len(locations)

        result = minimize(
            _mse,                         # The error function
            centroid,            # The initial guess
            args=(locations, distances), # Additional parameters for mse
            method='L-BFGS-B',           # The optimisation algorithm
            options={
                'ftol':1e-7,         # Tolerance
                'maxiter': 1e+7      # Maximum iterations
            })
        location = result.x
        print(f"result {result}")
        self.logger.debug(f"location: {location}")
        return location

    def start_daemon(self):
        self.logger.debug(f"Starting Watchdog")
        self.logger.debug(f"Creating socket {Watchdog.SOCK}")
        if os.path.isfile(Watchdog.SOCK):
            os.remove(Watchdog.SOCK)
        RequestHandlerClass = self.create_request_handler_class(self)
        self.server = ThreadedUnixServer(Watchdog.SOCK, RequestHandlerClass)

        server_thread = Thread(target=self.server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()
        self.logger.success("Watchdog server running")

    def create_request_handler_class(self, wd_inst):
        class RequestHandler(socketserver.BaseRequestHandler):
            def handle(self):
                data = str(self.request.recv(1024), 'ascii')
                self.request.sendall(b"OK")
                wd_inst.process_tower(data)
        return RequestHandler


    def shutdown(self):
        self.logger.warning(f"Stopping Watchdog")
        if hasattr(self, 'server') and self.server:
            os.remove(Watchdog.SOCK)
            self.server.shutdown()

class ThreadedUnixServer(socketserver.UnixStreamServer):
    pass


if __name__ == "__main__":
    class Args:
        disable_gps = False
        disable_wigle = False
        debug = False
        project_name = "test"
    dog = Watchdog(Args)
    dog.start_daemon()
    dog.strongest()
    dog.check_all()
    while True:
        continue

