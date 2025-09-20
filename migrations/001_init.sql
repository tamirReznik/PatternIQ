-- migrations/001_init.sql

CREATE TABLE instruments (
    symbol TEXT PRIMARY KEY,
    cusip TEXT,
    name TEXT,
    primary_exchange TEXT,
    is_active BOOL,
    first_seen DATE,
    last_seen DATE,
    sector TEXT,
    industry TEXT
);

CREATE TABLE universe_membership (
    symbol TEXT,
    universe TEXT,
    effective_from DATE,
    effective_to DATE,
    PRIMARY KEY(symbol, universe, effective_from)
);

CREATE TABLE corporate_actions (
    symbol TEXT,
    action_date DATE,
    type TEXT,
    ratio NUMERIC,
    cash_amount NUMERIC
);

CREATE TABLE bars_1d (
    symbol TEXT,
    t TIMESTAMP,
    o NUMERIC,
    h NUMERIC,
    l NUMERIC,
    c NUMERIC,
    v BIGINT,
    adj_o NUMERIC,
    adj_h NUMERIC,
    adj_l NUMERIC,
    adj_c NUMERIC,
    adj_v BIGINT,
    vendor TEXT,
    PRIMARY KEY(symbol, t)
);

CREATE TABLE fundamentals_snapshot (
    symbol TEXT,
    asof DATE,
    market_cap NUMERIC,
    ttm_eps NUMERIC,
    ttm_revenue NUMERIC,
    pe NUMERIC,
    ps NUMERIC
);

CREATE TABLE earnings (
    symbol TEXT,
    event_time TIMESTAMP,
    period TEXT,
    consensus NUMERIC,
    actual NUMERIC,
    surprise NUMERIC,
    before_after TEXT
);

CREATE TABLE features_daily (
    symbol TEXT,
    d DATE,
    feature_name TEXT,
    value NUMERIC,
    PRIMARY KEY(symbol, d, feature_name)
);

CREATE TABLE signals_daily (
    symbol TEXT,
    d DATE,
    signal_name TEXT,
    score NUMERIC,
    rank INT,
    explain JSONB
);

CREATE TABLE backtests (
    run_id UUID PRIMARY KEY,
    created_at TIMESTAMP,
    universe TEXT,
    start_date DATE,
    end_date DATE,
    cost_bps NUMERIC,
    slippage_bps NUMERIC,
    labeling TEXT
);

CREATE TABLE backtest_positions (
    run_id UUID,
    symbol TEXT,
    d DATE,
    weight NUMERIC,
    price_entry NUMERIC,
    price_exit NUMERIC,
    pnl NUMERIC
);

CREATE TABLE reports (
    report_id UUID PRIMARY KEY,
    period TEXT,
    path TEXT,
    summary JSONB
);

