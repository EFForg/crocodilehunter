import os
import time

from sqlalchemy import Table, Column, Integer, Float, DateTime, MetaData, create_engine, func, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

Base = declarative_base()

def init_db(project_path):
    DB_PATH = os.path.join(project_path, 'cell_data.db')
    DB_PATH = f"sqlite:///{DB_PATH}"
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
    rsrp = Column(Float)
    suspiciousness = Column(Integer, default=0)

    def __repr__(self):
        return f"<Tower: {self.mcc}-{self.mnc}-{self.cid} with TAC {self.tac} spotted at {self.lat}, {self.lon} on {time.ctime(self.timestamp)} with suspiciousness {self.suspiciousness}>"

    def params(self):
        return [str(t).replace('tower_data.','') for t in Tower.__table__.columns]
