#!/usr/bin/env python3

import os
import socketserver
from threading import Thread

import gpsd
import numpy
from sqlalchemy import func, text

from database import Tower, init_db
from wigle import Wigle

class Watchdog():
    SOCK = f"/tmp/croc.sock"

    def __init__(self, args):
        self.project_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", args.project_name)
        self.db_session = init_db(self.project_path)
        self.project_name = args.project_name
        self.disable_wigle = args.disable_wigle
        self.debug = args.debug
        self.disable_gps = args.disable_gps
        if not self.disable_wigle:
            self.wigle = Wigle()

    def last_ten(self):
        return Tower.query.group_by(Tower.cid).order_by(Tower.timestamp.desc())[0:10]

    def strongest(self):
        for row in Tower.query.filter(Tower.rsrp != 0.0).filter(Tower.rsrp.isnot(None)).order_by(Tower.rsrp.desc())[0:10]:
            if row is None:
                continue
            print(f"{row}, power: {row.rsrp}")

    def get_row_by_id(self, row_id):
        return Tower.query.get(row_id)

    def get_towers_by_cid(self, cid):
        return Tower.query.filter(Tower.cid == cid)

    def count(self):
        num_rows = Tower.query.count()
        num_towers = Tower.query.with_entities(Tower.cid).distinct().count()
        print(f"Found {num_towers} towers a total of {num_rows} times")

    def process_tower(self, data):
        print(f"server recd: {data}")
        data = data.split(",")
        if self.disable_gps:
            packet = type('Packet', (object,), {'lat': 0.0, 'lon': 0.0})()
        else:
            gpsd.connect()
            packet = gpsd.get_current()
            while packet.lat == 0.0 and packet.lon == 0.0:
                packet = gpsd.get_current()

        new_tower = Tower(
                mcc = int(data[0]),
                mnc = int(data[1]),
                tac = int(data[2]),
                cid = int(data[3]),
                phyid = int(data[4]),
                earfcn = int(data[5]),
                lat = packet.lat,
                lon = packet.lon,
                timestamp = int(data[6]),
                rsrp = float(data[7])
                )
        print(f"Adding a new tower: {new_tower}")
        self.db_session.add(new_tower)
        self.db_session.commit()
        self.calculate_suspiciousness(new_tower)
        self.count()

    def calculate_all(self):
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
        known_mncs = [0, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 20, 23, 24,
                25, 26, 30, 31, 32, 34, 38, 40, 46, 50, 60, 70, 80, 90, 100, 110, 120, 130,
                140, 150, 160, 170, 180, 190, 200, 210, 220, 230, 240, 250, 260, 270, 280,
                290, 300, 310, 311, 320, 330, 340, 350, 360, 370, 380, 390, 400, 410, 420,
                430, 440, 450, 460, 470, 480, 490, 500, 510, 520, 530, 540, 550, 560, 570,
                580, 590, 600, 610, 620, 630, 640, 650, 660, 670, 680, 690, 700, 710, 720,
                730, 740, 750, 760, 770, 780, 790, 800, 810, 820, 830, 840, 850, 860, 870,
                880, 890, 900, 910, 920, 930, 940, 950, 960, 970, 980, 990]
        # TODO: the above are all known MNCs in the USA from cell finder's db, but do we really
        # want to include all of them?
        if tower.mnc not in known_mncs:
            tower.suspisciousness += 20

    def check_existing_rsrp(self, tower):
        """ If the same tower has been previously recorded but is suddenly
        recorded at a much higher power level."""
        existing_towers = self.db_session.query(Tower).filter(
                Tower.mcc == tower.mcc,
                Tower.mnc == tower.mnc,
                Tower.tac == tower.tac,
                Tower.cid == tower.cid,
                Tower.phyid == tower.phyid,
                Tower.earfcn == tower.earfcn,
                Tower.rsrp.isnot(None)
                ).all()
        rsrp_levels = [x.rsrp for x in existing_towers]
        if tower.rsrp is not None and len(rsrp_levels) > 3:
            std = numpy.std(rsrp_levels)
            mean = numpy.mean(rsrp_levels)

            # TODO: think about this some more.
            if tower.rsrp is None or tower.rsrp > mean + std:
                tower.suspiciousness += (tower.rsrp - mean)

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

    def check_new_location(self, tower):
        """ If it's the first time we've seen a tower in a given
        location (+- some threshold)."""
        # TODO: ask someone who has thought about this
        # TODO: skip calculation until diameter is of a certain size ... half of 1/100th of a lat or lon.
        existing_towers = self.db_session.query(Tower).filter(
                Tower.mcc == tower.mcc,
                Tower.mnc == tower.mnc,
                Tower.cid == tower.cid,
                Tower.phyid == tower.phyid,
                Tower.earfcn == tower.earfcn,
                ).all()

        lats = [x.lat for x in existing_towers]
        lons = [x.lon for x in existing_towers]
        center_point = (numpy.mean(lats), numpy.mean(lons))
        center_point_std_dev = (numpy.std(lats), numpy.std(lons))
        # pymcmc
        # bayseian statistics for hackers
        # distribution of points
        # calculate distribution of findability  probability of distance x that i will fidn a tower
        # what is the probability that the given point is part of thatd distribution
        # exponential lamdax

        if abs(tower.lat) > abs(center_point[0] + center_point_std_dev[0]) or \
           abs(tower.lat) < abs(center_point[0] - center_point_std_dev[0]) or \
           abs(tower.lon) > abs(center_point[1] + center_point_std_dev[1]) or \
           abs(tower.lon) < abs(center_point[1] - center_point_std_dev[1]):
              tower.suspiciousness += 5 * 1000 * (abs(tower.lat - center_point[0]) - abs(tower.lon - center_point[1]))

    def check_rsrp(self, tower):
        """ If a given tower has a power signal significantly stronger than we've ever seen."""
        # TODO: maybe we should modify this to be anything over a certain threshold, like -50 db or something.
        existing_towers = self.db_session.query(Tower).filter(Tower.rsrp.isnot(None)).all()
        rsrps = [x.rsrp for x in existing_towers]
        if tower.rsrp is not None and len(rsrps) > 3:
            rsrp_mean = numpy.mean(rsrps)
            rsrp_std = numpy.std(rsrps)

            if tower.rsrp > rsrp_mean + rsrp_std:
                tower.suspiciousness += tower.rsrp - rsrp_mean

    def check_wigle(self, tower):
        if self.disable_wigle:
            print("Wigle API access disabled locally!")
        else:
            #self.wigle.cell_search(tower.lat, tower.lon, 0.0001, tower.cid, tower.tac)
            resp = self.wigle.get_cell_detail(tower.mnc, tower.tac, tower.cid)
            print("getting cell detail: " + str(resp))
            resp = self.wigle.cell_search(tower.lat, tower.lon, 0.001, tower.cid, tower.tac)
            print("conducting a cell search: " + str(resp))

    def calculate_suspiciousness(self, tower):
        # TODO: let's try some ML?
        self.check_mcc(tower)
        self.check_mnc(tower)
        self.check_existing_rsrp(tower)
        self.check_changed_tac(tower)
        self.check_new_location(tower)
        self.check_rsrp(tower)
        self.check_wigle(tower)
        self.db_session.commit()

    def start_daemon(self):
        print(f"\b* Starting Watchdog")
        print(f"\b* Creating socket {Watchdog.SOCK}")
        RequestHandlerClass = self.create_request_handler_class(self)
        self.server = ThreadedUnixServer(Watchdog.SOCK, RequestHandlerClass)

        server_thread = Thread(target=self.server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()
        print("Watchdog server running")

    def create_request_handler_class(self, wd_inst):
        class RequestHandler(socketserver.BaseRequestHandler):
            def handle(self):
                data = str(self.request.recv(1024), 'ascii')
                self.request.sendall(b"OK")
                wd_inst.process_tower(data)
        return RequestHandler


    def shutdown(self):
        print(f"\b* Stopping Watchdog")
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
    dog = Watchdog(Args)
    dog.start_daemon()
    dog.strongest()
    dog.calculate_all()
#    def signal_handler(sig, frame):
#        print(f"You pressed Ctrl+C!")
#        dog.shutdown()
    while True:
        continue

