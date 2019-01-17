#!/usr/bin/env python3
import os
import socketserver
from threading import Thread

from database import Tower, init_db
import gpsd
import numpy
from sqlalchemy import func, text

class Watchdog():
    SOCK = f"/tmp/croc.sock"

    def __init__(self):
        self.db_session = init_db()

    def last_ten(self):
        for row in Tower.query.group_by(Tower.cid).order_by(Tower.timestamp.desc())[0:10]:
            print(row)

    def strongest(self):
        for row in Tower.query.filter(Tower.rsrp != 0.0).filter(Tower.rsrp.isnot(None)).order_by(Tower.rsrp.desc())[0:10]:
            if row is None:
                continue
            print(f"{row}, power: {row.rsrp}")

    def count(self):
        num_rows = Tower.query.count()
        num_towers = Tower.query.with_entities(Tower.cid).distinct().count()
        print(f"Found {num_towers} towers a total of {num_rows} times")

    def process_tower(self, data):
        print(f"server recd: {data}")
        data = data.split(",")
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
        self.count()

    def calculate_all(self):
        towers = self.db_session.query(Tower).all()
        for tower in towers:
            self.calculate_suspiciousness(tower)
            print(tower)

    def check_mcc(self, tower):
        """ In case mcc isn't a standard value."""
        if tower.mcc not in (310, 311):
            tower.suspiciousness += 20

    def check_mnc(self, tower):
        """ In case mnc isn't a standard value."""
        continue

    def calculate_suspiciousness(self, tower):
        check_mcc(tower)

        # 2: if same tower is in the db but suddenly has much stronger signal
        # select power where not null and get avg and std deviation and add suspisciousness based on how much of a deviation we observe above the average
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

        # 3: if it exists but tac has changed
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

        # 4. also if it's the first time we've seen it in a given location +/- some threshold
        # find average/center point, then check if we're outside the average more than the avg
        # plus the std deviation.
        # TODO: ask someone who knows a thing
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

        if abs(tower.lat) > abs(center_point[0] + center_point_std_dev[0]) or \
           abs(tower.lat) < abs(center_point[0] - center_point_std_dev[0]) or \
           abs(tower.lon) > abs(center_point[1] + center_point_std_dev[1]) or \
           abs(tower.lon) < abs(center_point[1] - center_point_std_dev[1]):
              tower.suspiciousness += 5 * 1000 * (abs(tower.lat - center_point[0]) - abs(tower.lon - center_point[1]))

        # 5. if it has power stronger than some arbitrary threshold (against all the towers)
        existing_towers = self.db_session.query(Tower).filter(Tower.rsrp.isnot(None)).all()
        rsrps = [x.rsrp for x in existing_towers]
        if tower.rsrp is not None and len(rsrps) > 3:
            rsrp_mean = numpy.mean(rsrps)
            rsrp_std = numpy.std(rsrps)

            if tower.rsrp > rsrp_mean + rsrp_std:
                tower.suspiciousness += tower.rsrp - rsrp_mean


        # if not in Wigle db
        # use ML
        #TODO: try to understand rsrq/power levels.

    def start_daemon(self):
        print(f"\b* Starting Watchdog")
        print(f"\b* Creating socket {Watchdog.SOCK}")
        self.server = ThreadedUnixServer(Watchdog.SOCK, RequestHandler)

        server_thread = Thread(target=self.server.serve_forever)
        server_thread.setDaemon(True)
        server_thread.start()
        print("Watchdog server running")

    def shutdown(self):
        print(f"\b* Stopping Watchdog")
        if hasattr(self, 'server') and self.server:
            os.remove(Watchdog.SOCK)
            self.server.shutdown()

class ThreadedUnixServer(socketserver.UnixStreamServer):
    pass

class RequestHandler(socketserver.BaseRequestHandler):
    def handle(self):
        data = str(self.request.recv(1024), 'ascii')
        self.request.sendall(b"OK")
        wd = Watchdog()
        wd.process_tower(data)


if __name__ == "__main__":
    dog = Watchdog()
    dog.start_daemon()
    dog.strongest()
    dog.calculate_all()
    def signal_handler(sig, frame):
        print(f"You pressed Ctrl+C!")
        dog.shutdown()
    while True:
        continue

