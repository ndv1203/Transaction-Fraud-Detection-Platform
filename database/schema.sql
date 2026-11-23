-- =============================================================================
-- PostgreSQL 3-Tier Schema (raw, core, analytics)
-- Transaction Fraud Detection Platform (Sparkov Credit Card Fraud Dataset)
-- Reference: docs/04_database_design.md
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

-- =============================================================================
-- 1. RAW SCHEMA (Lineage, Quarantine & Reprocessing)
-- =============================================================================

CREATE TABLE IF NOT EXISTS raw.ingestion_batches (
    batch_id UUID PRIMARY KEY,
    source_name VARCHAR(128) NOT NULL,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    status VARCHAR(32) NOT NULL DEFAULT 'RUNNING'
        CHECK (status IN ('RUNNING', 'SUCCEEDED', 'FAILED', 'PARTIAL')),
    input_count BIGINT NOT NULL DEFAULT 0,
    accepted_count BIGINT NOT NULL DEFAULT 0,
    rejected_count BIGINT NOT NULL DEFAULT 0,
    error_summary JSONB
);

CREATE TABLE IF NOT EXISTS raw.raw_transactions (
    raw_id BIGSERIAL PRIMARY KEY,
    source_trans_num VARCHAR(64),
    source_name VARCHAR(128) NOT NULL,
    payload JSONB NOT NULL,
    is_valid BOOLEAN NOT NULL DEFAULT TRUE,
    validation_errors JSONB,
    batch_id UUID REFERENCES raw.ingestion_batches(batch_id) ON DELETE SET NULL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_tx_batch_id ON raw.raw_transactions (batch_id);
CREATE INDEX IF NOT EXISTS idx_raw_tx_source_trans_num ON raw.raw_transactions (source_trans_num);
CREATE INDEX IF NOT EXISTS idx_raw_tx_is_valid ON raw.raw_transactions (is_valid);

-- =============================================================================
-- 2. CORE SCHEMA (Normalized 3NF Entities, Features, Predictions & Alerts)
-- =============================================================================

CREATE TABLE IF NOT EXISTS core.cards (
    card_id BIGSERIAL PRIMARY KEY,
    cc_num VARCHAR(32) UNIQUE NOT NULL,
    gender VARCHAR(8),
    dob DATE,
    job VARCHAR(128),
    city VARCHAR(128),
    state_code VARCHAR(16),
    zip VARCHAR(16),
    lat NUMERIC(9, 6),
    lon NUMERIC(9, 6),
    city_pop INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.merchants (
    merchant_id BIGSERIAL PRIMARY KEY,
    merchant_name VARCHAR(255) UNIQUE NOT NULL,
    primary_category VARCHAR(64),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.transactions (
    transaction_id BIGSERIAL PRIMARY KEY,
    trans_num VARCHAR(64) UNIQUE NOT NULL,
    card_id BIGINT NOT NULL REFERENCES core.cards(card_id),
    merchant_id BIGINT NOT NULL REFERENCES core.merchants(merchant_id),
    category VARCHAR(64) NOT NULL,
    amt NUMERIC(18, 2) NOT NULL CHECK (amt > 0),
    event_time TIMESTAMPTZ NOT NULL,
    unix_time BIGINT NOT NULL,
    merch_lat NUMERIC(9, 6),
    merch_lon NUMERIC(9, 6),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processing_status VARCHAR(32) NOT NULL DEFAULT 'PROCESSED'
        CHECK (processing_status IN ('RAW', 'PROCESSED', 'SCORED')),
    batch_id UUID REFERENCES raw.ingestion_batches(batch_id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_core_tx_card_unixtime
    ON core.transactions (card_id, unix_time DESC);
CREATE INDEX IF NOT EXISTS idx_core_tx_event_time
    ON core.transactions (event_time);
CREATE INDEX IF NOT EXISTS idx_core_tx_category
    ON core.transactions (category);

CREATE TABLE IF NOT EXISTS core.transaction_labels (
    transaction_id BIGINT PRIMARY KEY REFERENCES core.transactions(transaction_id) ON DELETE CASCADE,
    actual_is_fraud BOOLEAN NOT NULL,
    label_source VARCHAR(64) NOT NULL DEFAULT 'SPARKOV_GROUND_TRUTH',
    labeled_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.transaction_features (
    transaction_id BIGINT PRIMARY KEY REFERENCES core.transactions(transaction_id) ON DELETE CASCADE,
    tx_count_1h INTEGER,
    tx_count_6h INTEGER,
    tx_count_24h INTEGER,
    amt_sum_1h NUMERIC(18, 2),
    amt_sum_24h NUMERIC(18, 2),
    amt_to_card_mean_ratio NUMERIC(12, 4),
    amt_to_cat_median_ratio NUMERIC(12, 4),
    unique_merchants_24h INTEGER,
    time_since_last_tx_sec BIGINT,
    dist_home_to_merch_km NUMERIC(10, 3),
    merch_to_merch_dist_km NUMERIC(10, 3),
    implied_speed_kmh NUMERIC(10, 2),
    hour_of_day SMALLINT,
    day_of_week SMALLINT,
    is_weekend BOOLEAN,
    is_night_tx BOOLEAN,
    customer_age NUMERIC(5, 2),
    feature_generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS core.fraud_predictions (
    prediction_id BIGSERIAL PRIMARY KEY,
    transaction_id BIGINT NOT NULL REFERENCES core.transactions(transaction_id) ON DELETE CASCADE,
    detection_method VARCHAR(32) NOT NULL
        CHECK (detection_method IN ('RULE_BASED', 'ML_MODEL', 'HYBRID')),
    risk_score NUMERIC(6, 5) NOT NULL CHECK (risk_score BETWEEN 0 AND 1),
    is_flagged BOOLEAN NOT NULL,
    risk_level VARCHAR(16) NOT NULL
        CHECK (risk_level IN ('LOW', 'MEDIUM', 'HIGH')),
    model_version VARCHAR(64),
    predicted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_core_pred_tx_id
    ON core.fraud_predictions (transaction_id);

CREATE TABLE IF NOT EXISTS core.fraud_alerts (
    alert_id BIGSERIAL PRIMARY KEY,
    prediction_id BIGINT NOT NULL REFERENCES core.fraud_predictions(prediction_id) ON DELETE CASCADE,
    transaction_id BIGINT NOT NULL REFERENCES core.transactions(transaction_id) ON DELETE CASCADE,
    alert_status VARCHAR(32) NOT NULL DEFAULT 'NEW'
        CHECK (alert_status IN ('NEW', 'INVESTIGATING', 'CONFIRMED_FRAUD', 'FALSE_POSITIVE')),
    alert_reason JSONB NOT NULL,
    reviewer_notes TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    reviewed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_core_alerts_status_created
    ON core.fraud_alerts (alert_status, created_at DESC);

-- =============================================================================
-- 3. ANALYTICS SCHEMA (Star Schema & Analytical Views)
-- =============================================================================

CREATE TABLE IF NOT EXISTS analytics.dim_time (
    time_key INTEGER PRIMARY KEY,             -- Format: YYYYMMDDHH
    date_actual DATE NOT NULL,
    year SMALLINT NOT NULL,
    month SMALLINT NOT NULL,
    day SMALLINT NOT NULL,
    hour_of_day SMALLINT NOT NULL CHECK (hour_of_day BETWEEN 0 AND 23),
    day_of_week SMALLINT NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
    day_name VARCHAR(16) NOT NULL,
    is_weekend BOOLEAN NOT NULL,
    is_night_window BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics.dim_cards (
    card_key BIGINT PRIMARY KEY REFERENCES core.cards(card_id),
    cc_num VARCHAR(32) UNIQUE NOT NULL,
    gender VARCHAR(8),
    age_group VARCHAR(16),
    city VARCHAR(128),
    state_code VARCHAR(16),
    city_pop INTEGER,
    job VARCHAR(128)
);

CREATE TABLE IF NOT EXISTS analytics.dim_merchants (
    merchant_key BIGINT PRIMARY KEY REFERENCES core.merchants(merchant_id),
    merchant_name VARCHAR(255) UNIQUE NOT NULL,
    primary_category VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS analytics.dim_categories (
    category_key SMALLSERIAL PRIMARY KEY,
    category_code VARCHAR(64) UNIQUE NOT NULL,
    is_online_channel BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS analytics.fact_transactions (
    transaction_id BIGINT PRIMARY KEY REFERENCES core.transactions(transaction_id) ON DELETE CASCADE,
    trans_num VARCHAR(64) UNIQUE NOT NULL,
    time_key INTEGER NOT NULL REFERENCES analytics.dim_time(time_key),
    card_key BIGINT NOT NULL REFERENCES analytics.dim_cards(card_key),
    merchant_key BIGINT NOT NULL REFERENCES analytics.dim_merchants(merchant_key),
    category_key SMALLINT NOT NULL REFERENCES analytics.dim_categories(category_key),
    amt NUMERIC(18, 2) NOT NULL,
    dist_home_to_merch_km NUMERIC(10, 3),
    implied_speed_kmh NUMERIC(10, 2),
    tx_count_24h INTEGER,
    risk_score NUMERIC(6, 5),
    risk_level VARCHAR(16),
    is_flagged BOOLEAN NOT NULL DEFAULT FALSE,
    is_confirmed_fraud BOOLEAN
);

CREATE INDEX IF NOT EXISTS idx_fact_tx_time_key ON analytics.fact_transactions (time_key);
CREATE INDEX IF NOT EXISTS idx_fact_tx_card_key ON analytics.fact_transactions (card_key);
CREATE INDEX IF NOT EXISTS idx_fact_tx_category_key ON analytics.fact_transactions (category_key);
CREATE INDEX IF NOT EXISTS idx_fact_tx_flags ON analytics.fact_transactions (is_flagged, is_confirmed_fraud);

-- Analytical Views for FastAPI & Dashboard
CREATE OR REPLACE VIEW analytics.agg_hourly_transactions AS
SELECT
    dt.time_key,
    dt.date_actual,
    dt.hour_of_day,
    COUNT(ft.transaction_id) AS total_transactions,
    COALESCE(SUM(ft.amt), 0)::NUMERIC(18, 2) AS total_amount,
    COUNT(*) FILTER (WHERE ft.is_flagged = TRUE) AS suspicious_transactions,
    COUNT(*) FILTER (WHERE ft.is_confirmed_fraud = TRUE) AS confirmed_fraud_transactions,
    COALESCE(SUM(ft.amt) FILTER (WHERE ft.is_flagged = TRUE), 0)::NUMERIC(18, 2) AS suspicious_amount,
    COALESCE(SUM(ft.amt) FILTER (WHERE ft.is_confirmed_fraud = TRUE), 0)::NUMERIC(18, 2) AS confirmed_fraud_amount
FROM analytics.dim_time dt
LEFT JOIN analytics.fact_transactions ft ON ft.time_key = dt.time_key
GROUP BY dt.time_key, dt.date_actual, dt.hour_of_day;

CREATE OR REPLACE VIEW analytics.agg_daily_fraud AS
SELECT
    dt.date_actual,
    COUNT(ft.transaction_id) AS total_transactions,
    COALESCE(SUM(ft.amt), 0)::NUMERIC(18, 2) AS total_amount,
    COUNT(*) FILTER (WHERE ft.is_flagged = TRUE) AS flagged_count,
    COUNT(*) FILTER (WHERE ft.is_confirmed_fraud = TRUE) AS confirmed_fraud_count,
    COALESCE(SUM(ft.amt) FILTER (WHERE ft.is_flagged = TRUE), 0)::NUMERIC(18, 2) AS flagged_amount,
    COALESCE(SUM(ft.amt) FILTER (WHERE ft.is_confirmed_fraud = TRUE), 0)::NUMERIC(18, 2) AS confirmed_fraud_amount,
    CASE
        WHEN COUNT(ft.transaction_id) > 0
        THEN ROUND(COUNT(*) FILTER (WHERE ft.is_flagged = TRUE)::NUMERIC / COUNT(ft.transaction_id), 6)
        ELSE 0
    END AS flagged_rate,
    CASE
        WHEN COUNT(ft.transaction_id) > 0
        THEN ROUND(COUNT(*) FILTER (WHERE ft.is_confirmed_fraud = TRUE)::NUMERIC / COUNT(ft.transaction_id), 6)
        ELSE 0
    END AS confirmed_fraud_rate
FROM analytics.dim_time dt
JOIN analytics.fact_transactions ft ON ft.time_key = dt.time_key
GROUP BY dt.date_actual;

CREATE OR REPLACE VIEW analytics.agg_category_metrics AS
SELECT
    dc.category_key,
    dc.category_code,
    dc.is_online_channel,
    COUNT(ft.transaction_id) AS total_transactions,
    COALESCE(AVG(ft.amt), 0)::NUMERIC(18, 2) AS avg_amt,
    COALESCE(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY ft.amt), 0)::NUMERIC(18, 2) AS median_amt,
    COUNT(*) FILTER (WHERE ft.is_flagged = TRUE) AS suspicious_count,
    COUNT(*) FILTER (WHERE ft.is_confirmed_fraud = TRUE) AS confirmed_fraud_count,
    CASE
        WHEN COUNT(ft.transaction_id) > 0
        THEN ROUND(COUNT(*) FILTER (WHERE ft.is_flagged = TRUE)::NUMERIC / COUNT(ft.transaction_id), 6)
        ELSE 0
    END AS suspicious_rate,
    CASE
        WHEN COUNT(ft.transaction_id) > 0
        THEN ROUND(COUNT(*) FILTER (WHERE ft.is_confirmed_fraud = TRUE)::NUMERIC / COUNT(ft.transaction_id), 6)
        ELSE 0
    END AS confirmed_fraud_rate
FROM analytics.dim_categories dc
LEFT JOIN analytics.fact_transactions ft ON ft.category_key = dc.category_key
GROUP BY dc.category_key, dc.category_code, dc.is_online_channel;
