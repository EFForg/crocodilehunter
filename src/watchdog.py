#!/usr/bin/env python3

import os
import math
from math import radians, cos, sin, asin, sqrt
import socketserver
from threading import Thread
from datetime import datetime
from geopy.distance import vincenty
from types import SimpleNamespace
from collections import namedtuple

import gpsd
import numpy
from sqlalchemy import func, text
from scipy.optimize import minimize


from database import Tower, KnownTower, init_db, TowerClassification, ExternalTowers
from wigle import Wigle
import ocid

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
        return self.db_session.query(Tower).group_by(func.concat(Tower.mnc, Tower.mcc, Tower.tac, Tower.enodeb_id)).order_by(Tower.id.desc())

    def get_unique_cids(self):
        return self.db_session.query(Tower).group_by(func.concat(Tower.mnc, Tower.mcc, Tower.tac, Tower.cid)).order_by(Tower.id.desc())

    def get_enodeb(self, enodeb_id):
        return self.db_session.query(Tower).filter(Tower.enodeb_id == enodeb_id).first()

    def get_cid(self, cid):
        return self.db_session.query(Tower).filter(Tower.cid == cid).first()

    def get_unique_phyids(self):
        return self.db_session.query(Tower.id, Tower, func.max(Tower.timestamp)).group_by(func.concat(Tower.mnc, Tower.mcc, Tower.tac, Tower.phyid)).order_by(Tower.id.desc())

    def get_sightings_for_enodeb(self, t):
        return self.db_session.query(Tower).filter(Tower.mnc == t.mnc, Tower.mcc == t.mcc, Tower.tac == t.tac, Tower.enodeb_id == t.enodeb_id)

    def get_sightings_for_cid(self, t):
        return self.db_session.query(Tower).filter(Tower.mnc == t.mnc, Tower.mcc == t.mcc, Tower.tac == t.tac, Tower.cid == t.cid)

    def get_cells_count_for_enodebid(self, t):
        return self.get_sightings_for_enodeb(t).group_by(Tower.cid).count()

    def get_max_column_by_enodeb(self, t, colname):
        row = self.get_sightings_for_enodeb(t).add_columns(func.max(getattr(Tower, colname))).first()
        return row[1]

    def get_min_column_by_enodeb(self, t, colname):
        row = self.get_sightings_for_enodeb(t).add_columns(func.min(getattr(Tower, colname))).first()
        return row[1]

    def get_max_column_by_cid(self, t, colname):
        row = self.get_sightings_for_cid(t).add_columns(func.max(getattr(Tower, colname))).first()
        return row[1]

    def get_min_column_by_cid(self, t, colname):
        row = self.get_sightings_for_cid(t).add_columns(func.min(getattr(Tower, colname))).first()
        return row[1]

    def get_suspicious_percentage_by_enodeb(self, t):
        hits = self.get_sightings_for_enodeb(t)
        return self._calcPercent(hits)

    def get_suspicious_percentage_by_cid(self, t):
        hits = self.get_sightings_for_cid(t)
        return self._calcPercent(hits)

    def _calcPercent(self, hits):
        cnt = hits.count()
        scnt = hits.filter(Tower.classification == TowerClassification.suspicious).count()
        return int((scnt / cnt) * 100)

    def reclassify_tower(self, id, classification, batch=False):
        tower = self.db_session.query(Tower).get(id)
        tower.classification = getattr(TowerClassification, classification)
        if not batch:
            self.db_session.commit()


    def closest_known_tower(self, lat, lon):
        r = 6371088 # Radius of earth in meters
        stmt = text(f" \
            SELECT id, ( {r} * acos(cos(radians({lat})) * cos(radians(known_towers.lat))\
            * cos(radians(known_towers.lon) - radians({lon})) + sin(radians({lat}))\
            * sin(radians(known_towers.lat )))) AS dist FROM known_towers ORDER BY\
            dist")
        q = self.db_session.query(KnownTower).from_statement(stmt)
        kt = q.first()
        if kt is None:
            return('None')
        dist = self._great_circle_distance(lat, lon, kt.lat, kt.lon)

        return(dist)

    def strongest(self):
        for row in Tower.query.filter(Tower.rssi != 0.0).filter(Tower.rssi.isnot(None)).order_by(Tower.rssi.desc())[0:10]:
            if row is None:
                continue
            self.logger.debug(f"{row}, power: {row.rssi}")

    def get_row_by_id(self, row_id):
        return Tower.query.get(row_id)

    def get_similar_towers(self, tower):
        return Tower.query.filter(Tower.mnc == tower.mnc).filter(Tower.mcc == tower.mcc).filter(Tower.phyid == tower.phyid).filter(Tower.tac == tower.tac)
        #towers = self.get_towers_by_enodeb(tower.mnc, tower.mcc, tower.enodeb_id)
        #return towers

    def get_towers_by_enodeb(self, mnc, mcc, enodeb_id):
        """ Gets towers with similar mnc, mcc, and tac."""
        return Tower.query.filter(Tower.mnc == mnc).filter(Tower.mcc == mcc).filter(Tower.enodeb_id == enodeb_id)

    def get_towers_by_cid(self, mnc, mcc, cid):
        return Tower.query.filter(Tower.mnc == mnc).filter(Tower.mcc == mcc).filter(Tower.cid == cid)

    def get_rough_trilateration_points(self):
        points = []
        enbys = self.get_unique_enodebs()
        for enb in enbys:
            towers = self.get_sightings_for_enodeb(enb).group_by(func.concat(func.round(Tower.lat,3), Tower.lon))
            if towers.count() > 3:
                res = self.trilaterate_enodeb_location(towers)
                points.append((res[0], res[1], enb.enodeb_id))

        return points

    def get_trilateration_points(self):
        points = []
        cells = {}
        enbys = Tower.query.group_by(func.concat(Tower.mcc, Tower.mnc, Tower.cid))
        for enb in enbys:
            enbid = enb.enodeb_id
            if not enbid in cells:
                cells[enbid] = []
            towers = Tower.query.filter(Tower.mnc == enb.mnc).filter(Tower.mcc == enb.mcc).filter(Tower.cid == enb.cid)
            towers = towers.group_by(func.concat(func.round(Tower.lat,3), Tower.lon))
            if towers.count() > 3:
                res = self.trilaterate_enodeb_location(towers)
                cells[enbid].append(SimpleNamespace(lat=res[0], lon=res[1], est_dist=50, sus_pct=self.get_suspicious_percentage_by_enodeb(towers[0])))

        for i in cells:
            if len(cells[i]) > 0:
                res = self.trilaterate_enodeb_location(cells[i], False)
                points.append({
                    'trilat': (res[0], res[1]),
                    'enodeb_id': i,
                    'max_suspiciousness': cells[i][0].sus_pct,
                    "closest_tower": self.closest_known_tower(res[0], res[1]),
                    "unique_cells": "NA", #self.get_cells_count_for_enodebid(cells[i]),
                    "sightings": "NA", #self.get_sightings_for_enodeb(cells[i]).count(),
                    "first_seen": "NA", #str(self.get_min_column_by_enodeb(cells[i], 'timestamp')),
                    "last_seen": "NA" #str(self.get_max_column_by_enodeb(cells[i], 'timestamp'))
                    })

        return points

    def get_known_towers(self):
        return self.db_session.query(KnownTower).order_by(KnownTower.id.desc())

    def add_known_tower(self, lat, lon, desc):
        kt = KnownTower(
            lat = lat,
            lon = lon,
            description = desc
        )
        self.db_session.add(kt)
        self.db_session.commit()
        return kt

    def delete_known_tower(self, id):
        kt = KnownTower.query.get(id)
        self.db_session.delete(kt)
        self.db_session.commit()

    def count(self):
        num_rows = Tower.query.count()
        num_towers = Tower.query.with_entities(Tower.enodeb_id).distinct().count()
        self.logger.verbose(f"Found {num_towers} towers a total of {num_rows} times")

    def get_ocid_location(self):
        Packet = namedtuple("Packet", ("lat", "lon"))
        ocid_key = self.config.get('general', 'ocid_key')
        if ocid_key:
            resp = ocid.ocid_get_location(ocid_key)
            self.logger.debug(resp)
            if 'lat' in resp:
                packet = Packet(float(resp['lat']), float(resp['lon']))
                return packet

        return None

    def get_gps(self):
        if self.disable_gps:
            packet = self.get_ocid_location()
            if packet:
                return packet
            Packet = namedtuple("Packet", ("lat", "lon"))
            gps = self.config['general']['gps_default'].split(',')
            packet = Packet(float(gps[0]), float(gps[1]))
        else:
            gpsd.logger.setLevel("WARNING")
            gpsd.connect()
            packet = gpsd.get_current()
            tries = 1
            while packet.mode < 2:
                # After every 10 tries try to get a packet from ocid
                if not tries % 10:
                    packet = self.get_ocid_location()
                    if packet:
                        return packet
                tries += 1
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
                rsrp = float(data[13]),
                tx_pwr = float(data[14]),
                raw_sib1 = data[15],
                timestamp = datetime.fromtimestamp(int(data[16])),
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

    def get_all_towers_after(self, starting_id):
        return self.db_session.query(Tower).filter(Tower.id > starting_id).all()

    def check_mcc(self, tower):
        """ In case mcc isn't a standard value."""
        if tower.mcc not in (310, 311, 316):
            tower.suspiciousness += 30

    def check_mnc(self, tower):
        """ In case mnc isn't a standard value."""
        known_mncs = [410,260,480,120]
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
        precache = self.db_session.query(Tower).filter(Tower.mcc == tower.mcc, Tower.mnc == tower.mnc, Tower.tac == tower.tac, Tower.cid == tower.cid, Tower.external_db != ExternalTowers.unknown).all()

        if len(precache) > 0 and tower.external_db == ExternalTowers.unknown:
            self.logger.info(f"Marking external DB tower as {precache[0].external_db} based on existing db records")
            tower.external_db = precache[0].external_db
            if tower.classification == TowerClassification.unknown:
                tower.classification = precache[0].classification

        elif tower.external_db == ExternalTowers.unknown:
            # Check CID in Wigle
            resp = self.wigle.cell_search(tower.lat, tower.lon, 0.1, tower.cid, tower.tac)
            self.logger.debug("conducting a cell search in wigle: " + str(resp))

            if resp["success"] == False:
                self.logger.error(f"wigle connection failed: {resp}")
                return

            if resp["resultCount"] < 1:
                tower.external_db = ExternalTowers.not_present
            else:
                tower.external_db = ExternalTowers.wigle

        if tower.external_db == ExternalTowers.not_present:
            self.logger.warning(f"Tower not externally confirmed {tower}")
            tower.suspiciousness += 30
            tower.classification = TowerClassification.suspicious
        elif tower.external_db in [ExternalTowers.wigle, ExternalTowers.opencellid]:
            self.logger.warning(f"Tower externally confirmed {tower}")

        self.logger.info(f"saving tower {tower.external_db}, {tower.classification} score: {tower.suspiciousness}")
        self.db_session.commit()

    def calculate_suspiciousness(self, tower):
        tower.suspiciousness = 0
        # TODO: let's try some ML?
        self.check_mcc(tower)
        self.check_mnc(tower)
        self.check_existing_rssi(tower)
        self.check_changed_tac(tower)
        self.check_new_location(tower)
        self.check_rssi(tower)
        if not self.disable_wigle:
            self.check_wigle(tower)

        if tower.suspiciousness >= 20:
            tower.classification = TowerClassification.suspicious
        else:
            tower.classification = TowerClassification.unknown
        self.db_session.commit()

    def trilaterate_enodeb_location(self, towers, run_checks=True):
        """
        perform trilateration on tower readings and distance estimates to estimate location of enodeb
        return - tuple (est_lat, est_lon, confidence)
        """
        centroid = self.get_centroid(towers)
        if run_checks:
            towers = towers.group_by(func.concat(func.round(Tower.lat,3), Tower.lon)).all()
            if len(towers) < 3:
                return (centroid[0],centroid[1])

        # locations: [ (lat1, long1), ... ]
        # distances: [ distance1,     ... ]
        locations = [(t.lat, t.lon) for t in towers]
        distances = [t.est_dist for t in towers]

        # trilaterate(towers(lat, lon, est_dist))
        def _mse(x, locations, distances):
            mse = 0.0
            for location, distance in zip(locations, distances):
                distance_calculated = self._great_circle_distance(x[0], x[1], location[0], location[1])
                mse += math.pow(distance_calculated - distance, 2.0)
            return mse / len(locations)


        result = minimize(
            _mse,                         # The error function
            centroid,            # The initial guess
            args=(locations, distances), # Additional parameters for mse
            method='L-BFGS-B',           # The optimisation algorithm
            options={
                'ftol':1e-5,         # Tolerance
                'maxiter': 1000      # Maximum iterations
            })
        #print(f"result {result}")
        location = result.x
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

    @staticmethod
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


class ThreadedUnixServer(socketserver.UnixStreamServer):
    pass


if __name__ == "__main__":
    class Args:
        disable_gps = True
        disable_wigle = False
        debug = True
        project_name = "test"
    dog = Watchdog(Args)
    dog.start_daemon()
    dog.strongest()
    dog.check_all()
    while True:
        continue

