import os
import time

from sqlalchemy import Table, Column, Integer, Float, DateTime, MetaData, create_engine, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

DB_PATH = f"sqlite:///{os.path.dirname(os.path.abspath(__file__))}/../data/cell_data.db"

engine = create_engine(DB_PATH)
db_session = scoped_session(sessionmaker(bind=engine))

Base = declarative_base()
Base.query = db_session.query_property()

def init_db():
    Base.metadata.create_all(bind=engine)
    return db_session

class Tower(Base):
    __tablename__ = "tower_data"

    id = Column(Integer, primary_key=True)
    mcc = Column(Integer)
    mnc = Column(Integer)
    tac = Column(Integer)
    cid = Column(Integer)
    phyid = Column(Integer)
    earfcn = Column(Integer)
    lat = Column(Float)
    lon = Column(Float)
    timestamp = Column(Integer)
    rsrp = Column(Float)
    suspiciousness = Column(Integer, default=0)

    def __repr__(self):
        return f"<Tower: {self.mcc}-{self.mnc}-{self.cid} spotted at {self.lat}, {self.lon} on {time.ctime(self.timestamp)}>"
