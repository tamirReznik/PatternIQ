# src/data/models.py

from sqlalchemy import Column, String, Date, Boolean, Numeric, BigInteger, TIMESTAMP, JSON, Text, Integer, DateTime
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

class UniverseMembership(Base):
    __tablename__ = "universe_membership"
    symbol = Column(String, primary_key=True)
    universe = Column(String, primary_key=True)
    effective_from = Column(Date, primary_key=True)
    effective_to = Column(Date)

class CorporateActions(Base):
    __tablename__ = "corporate_actions"
    symbol = Column(String, primary_key=True)
    action_date = Column(Date, primary_key=True)
    type = Column(String)  # 'split' | 'dividend'
    ratio = Column(Numeric)  # e.g., 4:1 split => 4.0
    cash_amount = Column(Numeric)  # dividend per share

class Bars1d(Base):
    __tablename__ = "bars_1d"
    symbol = Column(String, primary_key=True)
    t = Column(DateTime, primary_key=True)  # Use DateTime instead of TIMESTAMP for SQLite compatibility
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

class FundamentalsSnapshot(Base):
    __tablename__ = "fundamentals_snapshot"
    symbol = Column(String, primary_key=True)
    asof = Column(Date, primary_key=True)
    market_cap = Column(Numeric)
    ttm_eps = Column(Numeric)
    ttm_revenue = Column(Numeric)
    pe = Column(Numeric)
    ps = Column(Numeric)

class Earnings(Base):
    __tablename__ = "earnings"
    symbol = Column(String, primary_key=True)
    event_time = Column(TIMESTAMP, primary_key=True)
    period = Column(String)  # 'Q1 2025' etc.
    consensus = Column(Numeric)
    actual = Column(Numeric)
    surprise = Column(Numeric)
    before_after = Column(String)  # 'BMO'/'AMC'

class FeaturesDaily(Base):
    __tablename__ = "features_daily"
    symbol = Column(String, primary_key=True)
    d = Column(Date, primary_key=True)
    feature_name = Column(String, primary_key=True)
    value = Column(Numeric)

class SignalsDaily(Base):
    __tablename__ = "signals_daily"
    symbol = Column(String, primary_key=True)
    d = Column(Date, primary_key=True)
    signal_name = Column(String, primary_key=True)
    score = Column(Numeric)
    rank = Column(Integer)
    explain = Column(JSON)

class Backtests(Base):
    __tablename__ = "backtests"
    run_id = Column(String, primary_key=True)
    created_at = Column(TIMESTAMP)
    universe = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    cost_bps = Column(Numeric)
    slippage_bps = Column(Numeric)
    labeling = Column(String)

class BacktestPositions(Base):
    __tablename__ = "backtest_positions"
    run_id = Column(String, primary_key=True)
    symbol = Column(String, primary_key=True)
    d = Column(Date, primary_key=True)
    weight = Column(Numeric)
    price_entry = Column(Numeric)
    price_exit = Column(Numeric)
    pnl = Column(Numeric)

class Reports(Base):
    __tablename__ = "reports"
    report_id = Column(String, primary_key=True)
    period = Column(String)  # 'daily:2025-09-20'
    path = Column(String)  # pointer to rendered file (PDF/HTML)
    summary = Column(JSON)  # KPIs, top signals
