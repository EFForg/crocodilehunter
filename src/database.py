import os
import time
import math
import enum

import configparser

from sqlalchemy import Table, Column, Integer, Float, String, DateTime, MetaData, Text, create_engine, func, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy_utils import create_database, database_exists

Base = declarative_base()

def init_db(project_name):
    config_fp = 'config.ini'
    config = configparser.ConfigParser()
    config.read(config_fp)

    MYSQL_PATH = config['general']['mysql_path']
    DB_PATH = f"{MYSQL_PATH}/{project_name}"

    if not database_exists(DB_PATH):
        create_database(DB_PATH)

    engine = create_engine(DB_PATH)
    db_session = scoped_session(sessionmaker(bind=engine, autoflush=False))

    Base.query = db_session.query_property()
    Base.metadata.create_all(bind=engine)
    return db_session

class TowerClassification(enum.Enum):
    unknown = 1
    legitimate = 2
    small_cell = 3
    suspicious = 4
    CSS = 5

    def __str__(self):
        return self.name.title()

class ExternalTowers(enum.Enum):
    not_present=0
    unknown=1
    wigle=2
    opencellid=3

    def __str__(self):
        return self.name.title()

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
    timestamp = Column(DateTime, nullable=False)
    rssi = Column(Float, nullable=True)
    suspiciousness = Column(Integer, default=0)
    frequency = Column(Float)
    enodeb_id = Column(Integer)
    sector_id = Column(Integer)
    cfo = Column(Float)
    rsrq = Column(Float)
    snr = Column(Float)
    rsrp = Column(Float)
    tx_pwr = Column(Float)
    est_dist = Column(Float)
    raw_sib1 = Column(String(255))
    classification = Column(Enum(TowerClassification), default=TowerClassification.unknown, nullable=False)
    external_db = Column(Enum(ExternalTowers), default=ExternalTowers.unknown, nullable=False)

    def __repr__(self):
        repr = f"<Tower: {self.mcc}-{self.mnc}-{self.tac}-{self.enodeb_id}, loc: {self.lat}," + \
            f"{self.lon}, time: {self.timestamp}, freq: {self.frequency}>"
        return repr

    def params(self):
        return [str(t).replace('tower_data.','') for t in Tower.__table__.columns]

    def plmn(self):
        return f"{self.mcc}-{self.mnc}"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def est_distance(self):
        """
        calcluate distance in meters of enodeb from a reading using FSPL estimate
        (https://en.wikipedia.org/wiki/Free-space_path_loss#Free-space_path_loss_in_decibels)
        """
        #fspl = tx_pow + tx_gain + rx_gain - rx_pow - fade_margin
        tx_pow = 30 # standard transmit DBm for a tower
        rx_gain = -1# default gain setting for bladRF
        plc = 2.2 # path loss coefficient
        fspl = self.tx_pwr - self.rssi + rx_gain
        distance = 10 ** ((27.55 - ((10 * plc) * math.log10(self.frequency)) + fspl)/(10 * plc))
        self.est_dist = distance
        return distance


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
                {'band': 14, 'dl_low': 758, 'min_earfcn': 5280, 'max_earfcn': 5379},
                {'band': 17, 'dl_low': 734, 'min_earfcn': 5730, 'max_earfcn': 5849},
                {'band': 18, 'dl_low': 860, 'min_earfcn': 5850, 'max_earfcn': 5999},
                {'band': 19, 'dl_low': 875, 'min_earfcn': 6000, 'max_earfcn': 6149},
                {'band': 20, 'dl_low': 791, 'min_earfcn': 6150, 'max_earfcn': 6449},
                {'band': 21, 'dl_low': 1495.9, 'min_earfcn': 6450, 'max_earfcn': 6599},
                {'band': 22, 'dl_low': 3510, 'min_earfcn': 6600, 'max_earfcn': 7399},
                {'band': 23, 'dl_low': 2180, 'min_earfcn': 7500, 'max_earfcn': 7699},
                {'band': 24, 'dl_low': 1525, 'min_earfcn': 7700, 'max_earfcn': 8039},
                {'band': 25, 'dl_low': 1930, 'min_earfcn': 8040, 'max_earfcn': 8689},
                {'band': 26, 'dl_low': 859, 'min_earfcn': 8690, 'max_earfcn': 9039},
                {'band': 27, 'dl_low': 852, 'min_earfcn': 9040, 'max_earfcn': 9209},
                {'band': 28, 'dl_low': 758, 'min_earfcn': 9210, 'max_earfcn': 9659},
                {'band': 29, 'dl_low': 717, 'min_earfcn': 9660, 'max_earfcn': 9769},
                {'band': 30, 'dl_low': 2350, 'min_earfcn': 9770, 'max_earfcn': 9869}
                ]

        for band in band_list:
            if self.earfcn >= band['min_earfcn'] and self.earfcn <= band['max_earfcn']:
                return band['dl_low'] + 0.1 * (self.earfcn - band['min_earfcn'])

    def get_enodeb_id(self):
        # The first 24 bits make up the enodeb id.
        return self.cid >> 8

    def get_sector_id(self):
        # The last 8 bits are sector id.
        return self.cid & 255

class KnownTower(Base):
    __tablename__ = "known_towers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lat = Column(Float(32))
    lon = Column(Float(32))
    description = Column(Text)

    def __repr__(self):
        return f"{self.lat}, {self.lon}, {self.description}"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class EnodeB(Base):
    __tablename__ = "enodebs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    mcc = Column(Integer)
    mnc = Column(Integer)
    tac = Column(Integer)
    enodeb_id = Column(Integer)
    classification = Column(Enum(TowerClassification), default=1, nullable=False)

    def plmn(self):
        return f"{self.mcc}_{self.mnc}_{self.tac}"

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}

    def __repr__(self):
        return f"{self.plmn}_{self.enodeb_id}: {classification}"
