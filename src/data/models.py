# src/data/models.py

from sqlalchemy import Column, String, Date, Boolean, Numeric, BigInteger, TIMESTAMP, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Instrument(Base):
    __tablename__ = "instruments"
    symbol = Column(String, primary_key=True)
    cusip = Column(String)
    name = Column(String)
    primary_exchange = Column(String)
    is_active = Column(Boolean)
    first_seen = Column(Date)
    last_seen = Column(Date)
    sector = Column(String)
    industry = Column(String)

class Bars1d(Base):
    __tablename__ = "bars_1d"
    symbol = Column(String, primary_key=True)
    t = Column(TIMESTAMP, primary_key=True)
    o = Column(Numeric)
    h = Column(Numeric)
    l = Column(Numeric)
    c = Column(Numeric)
    v = Column(BigInteger)
    adj_o = Column(Numeric)
    adj_h = Column(Numeric)
    adj_l = Column(Numeric)
    adj_c = Column(Numeric)
    adj_v = Column(BigInteger)
    vendor = Column(String)

