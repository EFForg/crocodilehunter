#!/usr/bin/env python3
from database import db_session, Tower, init_db
from sqlalchemy import func, text

class Watchdog:

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

    @classmethod
    def start_daemon(cls):
        print(f"\b* Starting Watchdog")

    @classmethod
    def shutdown(cls):
        print(f"\b* Stopping Watchdog")


if __name__ == "__main__":
    dog = Watchdog()
    print("last 10 unique towers seen")
    dog.last_ten()
    print("top ten readings by strength")
    dog.strongest()

