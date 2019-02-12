import os
import time

from sqlalchemy import Table, Column, Integer, Float, DateTime, MetaData, create_engine, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy_utils import create_database, database_exists

Base = declarative_base()

def init_db(project_name):
    MYSQL_PATH = f"mysql://root:toor@localhost:3306"
    DB_PATH = f"{MYSQL_PATH}/{project_name}"

    if not database_exists(DB_PATH):
        create_database(DB_PATH)

    engine = create_engine(DB_PATH)
    db_session = scoped_session(sessionmaker(bind=engine, autoflush=False))

    Base.query = db_session.query_property()
    Base.metadata.create_all(bind=engine)
    return db_session

class Tower(Base):
    __tablename__ = "tower_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    mcc = Column(Integer)
    mnc = Column(Integer)
    tac = Column(Integer)
    cid = Column(Integer)
    phyid = Column(Integer)
    earfcn = Column(Integer)
    lat = Column(Float)
    lon = Column(Float)
    timestamp = Column(Integer)
    rsrp = Column(Float, nullable=True)
    suspiciousness = Column(Integer, default=0)

    def __repr__(self):
        return f"<Tower: {self.mcc}-{self.mnc}-{self.cid} with TAC {self.tac} spotted at {self.lat}, {self.lon} on {time.ctime(self.timestamp)} with suspiciousness {self.suspiciousness}>"

    def params(self):
        return [str(t).replace('tower_data.','') for t in Tower.__table__.columns]

    def get_frequency(self):
        band_list = [
                {'band': 1, 'dl_low': 2110, 'min_earfcn':0, 'max_earfcn' : 599},
                {'band': 2, 'dl_low': 1930, 'min_earfcn': 600, 'max_earfcn' : 1199},
                {'band': 3, 'dl_low': 1805,  'min_earfcn': 1200, 'max_earfcn': 1949},
                {'band': 4, 'dl_low': 2110, 'min_earfcn': 1950, 'max_earfcn': 2399},
                {'band': 5, 'dl_low': 869, 'min_earfcn': 2400, 'max_earfcn': 2649},
                {'band': 6, 'dl_low': 875, 'min_earfcn': 2650, 'max_earfcn': 2749},
                {'band': 7, 'dl_low': 2620, 'min_earfcn': 2750, 'max_earfcn': 3449},
                {'band': 8, 'dl_low': 925, 'min_earfcn': 3450, 'max_earfcn': 3799},
                {'band': 9, 'dl_low': 1844.9, 'min_earfcn': 3800, 'max_earfcn': 4149},
                {'band': 10, 'dl_low': 2110, 'min_earfcn': 4150, 'max_earfcn': 4749},
                {'band': 11, 'dl_low': 1475.9, 'min_earfcn': 4750, 'max_earfcn': 4949},
                {'band': 12, 'dl_low': 729, 'min_earfcn': 5010, 'max_earfcn': 5179},
                {'band': 13, 'dl_low': 746, 'min_earfcn': 5180, 'max_earfcn': 5279},
                {'band': 14, 'dl_low': 758, 'min_earfcn': 5280, 'max_earfcn': 5379}
                ]

        for band in band_list:
            if self.earfcn >= band['min_earfcn'] and self.earfcn <= band['max_earfcn']:
                return band['dl_low'] + 0.1 * (self.earfcn - band['min_earfcn'])

    def get_enodeb_id(self):
        pass

    def get_sector_id(self):
        pass
