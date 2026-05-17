CREATE TABLE IF NOT EXISTS market_bars (
    time TIMESTAMPTZ NOT NULL,
    instrument_key TEXT NOT NULL,
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    oi BIGINT,
    vwap DOUBLE PRECISION,
    PRIMARY KEY (time, instrument_key)
);

SELECT create_hypertable('market_bars', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS thesis_outcomes (
    time TIMESTAMPTZ NOT NULL,
    thesis_id UUID,
    symbol TEXT,
    direction TEXT,
    setup_type INT,
    regime INT,
    sector INT,
    time_bucket INT,
    hit BOOLEAN,
    gross_return_pct DOUBLE PRECISION,
    net_return_pct DOUBLE PRECISION,
    mfe_pct DOUBLE PRECISION,
    mae_pct DOUBLE PRECISION,
    r_multiple DOUBLE PRECISION,
    time_to_trigger_min INT,
    time_to_exit_min INT,
    confluence_score INT,
    score_at_creation INT,
    liquidity_quality TEXT
);

SELECT create_hypertable('thesis_outcomes', 'time', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS instruments (
    symbol TEXT PRIMARY KEY,
    instrument_key TEXT NOT NULL,
    segment TEXT,
    isin TEXT,
    lot_size INT,
    tick_size DOUBLE PRECISION,
    fo_eligible BOOLEAN DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS nse_flags (
    symbol TEXT NOT NULL,
    date DATE NOT NULL,
    fo_ban BOOLEAN DEFAULT FALSE,
    mwpl_status TEXT,
    earnings_flag TEXT,
    circuit_limit TEXT,
    PRIMARY KEY (symbol, date)
);

CREATE TABLE IF NOT EXISTS volume_seasonality (
    symbol TEXT NOT NULL,
    time_bucket INT NOT NULL,
    avg_volume_10d DOUBLE PRECISION,
    std_volume_10d DOUBLE PRECISION,
    PRIMARY KEY (symbol, time_bucket)
);

CREATE TABLE IF NOT EXISTS session_calendar (
    date DATE PRIMARY KEY,
    is_trading_day BOOLEAN DEFAULT TRUE,
    is_expiry BOOLEAN DEFAULT FALSE,
    event_flag TEXT
);
