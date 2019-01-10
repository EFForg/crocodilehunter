#!/usr/bin/env python3
import os
import socketserver
from threading import Thread

from database import db_session, Tower, init_db
import gpsd
from sqlalchemy import func, text

class Watchdog():
    SOCK = f"{os.path.dirname(os.path.abspath(__file__))}/../croc.sock"

    def __init__(self):
        init_db()

    def last_ten(self):
        for row in Tower.query.group_by(Tower.cid).order_by(Tower.timestamp.desc())[0:10]:
            print(row)

    def strongest(self):
        for row in Tower.query.filter(Tower.rsrp != 0.0).order_by(Tower.rsrp.desc())[0:10]:
            print(f"{row}, power: {row.rsrp}")
        num_rows = Tower.query.count()
        num_towers = Tower.query.with_entities(Tower.cid).distinct().count()
        print(f"Found {num_towers} towers a total of {num_rows} times")

    def process_tower(self, data):
        print(f"server recd: {data}")
        data = data.split(",")
        gpsd.connect()
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
        db_session.add(new_tower)
        db_session.commit()
        self.strongest()

    def start_daemon(self):
        print(f"\b* Starting Watchdog")
        print(f"\b* Creating socket {Watchdog.SOCK}")
        self.server = ThreadedUnixServer(Watchdog.SOCK, RequestHandler)
        with self.server:
            server_thread = Thread(target=self.server.serve_forever)
            server_thread.setDaemon(True)
            server_thread.start()
            print("Watchdog server running")
            while True:
                continue

    def shutdown(self):
        print(f"\b* Stopping Watchdog")
        os.remove(Watchdog.SOCK)
        if hasattr(self, 'server') and self.server:
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

