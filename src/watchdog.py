#!/usr/bin/env python3
import os
import time
from sqlalchemy import Table, Column, Integer, Float, MetaData, create_engine, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Watchdog:
    def __init__(self, db_path):
        engine = create_engine(db_path)
        Base.metadata.create_all(engine)
        self.Session = sessionmaker(bind=engine)

    def start_daemon(self):
        print(f"\b* Starting Watchdog")

    def shutdown(self):
        print(f"\b* Stopping Watchdog")

    def last_ten(self):
        session = self.Session()
        for row in session.query(Tower).group_by(Tower.cid).order_by(Tower.datetime.desc())[0:10]:
            print(row)

    def strongest(self):
        session = self.Session()
        for row in session.query(Tower).filter(Tower.rsrp != 0.0).order_by(Tower.rsrp.desc())[0:10]:
            print(f"{row}, power: {row.rsrp}")
        num_rows = session.query(Tower).count()
        num_towers = session.query(func.count(text('DISTINCT cid'))).select_from(Tower).scalar()
        print(f"Found {num_towers} towers a total of {num_rows} times")

class Tower(Base):
    __tablename__ = "sib1_data"

    mcc = Column(Integer)
    mnc = Column(Integer)
    tac = Column(Integer)
    cid = Column(Integer, primary_key=True)
    phyid = Column(Integer)
    earfcn = Column(Integer)
    lat = Column(Float)
    lon = Column("long", Float)
    datetime = Column(Integer, primary_key=True)
    rsrp = Column(Float)

    def __repr__(self):
        return f"<Tower: {self.mcc}-{self.mnc}-{self.cid} spotted at {self.lat}, {self.lon} on {time.ctime(self.datetime)}>"

if __name__ == "__main__":
    path = f"{os.path.dirname(os.path.abspath(__file__))}/../data/cell_data.db"
    dog = Watchdog(f"sqlite:///{path}")
    print("last 10 unique towers seen")
    dog.last_ten()
    print("top ten readings by strength")
    dog.strongest()

