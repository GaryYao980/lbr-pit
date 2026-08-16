-- lbr-pit schema
-- Two time axes throughout: "valid time" (what period/date a value describes)
-- and "transaction time" (when that value became knowable / was published).
-- See README.md for the as-of query this schema exists to serve, and app/queries.py
-- for the one function that serves every table.

CREATE TABLE IF NOT EXISTS cot_obs (
  report_date  DATE        NOT NULL,   -- valid time:       the Tuesday (usually) positions were held
  release_ts   TIMESTAMPTZ NOT NULL,   -- transaction time: when it became knowable
  series       TEXT        NOT NULL,   -- 'mm_net' | 'comm_net' | 'oi' | 'nonc_net' | ...
  value        DOUBLE PRECISION NOT NULL,
  revision     INT         NOT NULL DEFAULT 0,
  PRIMARY KEY (report_date, series, revision)
);

CREATE TABLE IF NOT EXISTS futures_settle (
  trade_date     DATE   NOT NULL,
  contract_month TEXT   NOT NULL,      -- display label only, e.g. 'SEP26'
  contract_start DATE   NOT NULL,      -- sort key, 'SEP26' -> 2026-09-01.
                                       -- TEXT does not sort chronologically. Every curve
                                       -- query orders by THIS column, never by the label.
  settle         DOUBLE PRECISION,
  volume         BIGINT,
  open_interest  BIGINT,
  no_trade_flag  BOOLEAN NOT NULL DEFAULT FALSE,  -- exchange-computed settle, not a real trade
  note           TEXT,
  PRIMARY KEY (trade_date, contract_month)
);

-- ALFRED-style vintage-aware fundamentals. Same as-of shape as cot_obs --
-- one function serves both (see app/queries.py:as_of_query).
CREATE TABLE IF NOT EXISTS fundamental_obs (
  series_id TEXT NOT NULL,          -- 'HOUST', 'HOUST1F', 'PERMIT', 'MORTGAGE30US', 'WPU081', 'DEXCAUS'
  obs_date  DATE NOT NULL,          -- valid time:       the period described
  vintage   DATE NOT NULL,          -- transaction time: ALFRED realtime_start
  value     DOUBLE PRECISION,
  PRIMARY KEY (series_id, obs_date, vintage)
);

-- the physical leg: real schema, zero rows by design. Nothing public prices it,
-- and inventing rows here would undo the point of the whole repo.
CREATE TABLE IF NOT EXISTS physical_price (
  quote_date DATE NOT NULL,
  region     TEXT NOT NULL,
  species    TEXT NOT NULL,
  dimension  TEXT NOT NULL,
  basis      TEXT NOT NULL,            -- 'delivered' | 'fob-mill'
  price      DOUBLE PRECISION NOT NULL,
  source     TEXT NOT NULL,
  PRIMARY KEY (quote_date, region, species, dimension, basis)
);

CREATE INDEX IF NOT EXISTS idx_cot_obs_release_ts ON cot_obs (release_ts);
CREATE INDEX IF NOT EXISTS idx_fundamental_obs_vintage ON fundamental_obs (vintage);
CREATE INDEX IF NOT EXISTS idx_futures_settle_curve ON futures_settle (trade_date, contract_start);
CREATE INDEX IF NOT EXISTS idx_futures_settle_leg   ON futures_settle (contract_month, trade_date);
