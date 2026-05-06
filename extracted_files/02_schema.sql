-- ============================================================
-- NIFTY 100 Financial Data Warehouse — Star Schema DDL
-- ============================================================
-- Run with: psql -U postgres -d nifty100_dw -f sql/02_schema.sql
-- ============================================================

-- ----------------------------------------------------------------
-- 0. Housekeeping
-- ----------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

DROP SCHEMA IF EXISTS dw CASCADE;
CREATE SCHEMA dw;
SET search_path TO dw;


-- ================================================================
-- DIMENSION TABLES
-- ================================================================

-- dim_company: one row per NIFTY 100 company
CREATE TABLE dim_company (
    company_id          VARCHAR(30)  PRIMARY KEY,
    company_name        TEXT         NOT NULL,
    website             TEXT,
    nse_profile_url     TEXT,
    bse_profile_url     TEXT,
    company_logo_url    TEXT,
    about_company       TEXT,
    face_value          NUMERIC(10,2),
    book_value          NUMERIC(10,2),
    roce_pct            NUMERIC(6,2),   -- Return on Capital Employed
    roe_pct             NUMERIC(6,2),   -- Return on Equity
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_dim_company_name ON dim_company (company_name);


-- dim_date: one row per fiscal period (year-month grain)
CREATE TABLE dim_date (
    date_key        VARCHAR(10) PRIMARY KEY,  -- e.g. '2014-03', '2024'
    year            SMALLINT,
    month           SMALLINT,                 -- NULL when only year is known
    quarter         SMALLINT,                 -- 1-4
    fiscal_year     VARCHAR(10),              -- '2013-14' (Apr-Mar Indian FY)
    is_annual       BOOLEAN DEFAULT TRUE
);
CREATE INDEX idx_dim_date_year ON dim_date (year);


-- dim_sector: industry classification (can be enriched via NSE data)
CREATE TABLE dim_sector (
    sector_id   SERIAL PRIMARY KEY,
    sector_name VARCHAR(100) NOT NULL UNIQUE,
    industry    VARCHAR(100)
);
INSERT INTO dim_sector (sector_name, industry) VALUES
    ('Banking & Finance',       'Financials'),
    ('Information Technology',  'Technology'),
    ('Oil & Gas',               'Energy'),
    ('Pharmaceuticals',         'Healthcare'),
    ('Automotive',              'Consumer Discretionary'),
    ('Consumer Goods',          'Consumer Staples'),
    ('Infrastructure',          'Industrials'),
    ('Metals & Mining',         'Materials'),
    ('Telecom',                 'Communication Services'),
    ('Real Estate',             'Real Estate'),
    ('Others',                  'Diversified');


-- dim_metric: lookup for computed financial KPIs (for EAV fact table)
CREATE TABLE dim_metric (
    metric_id       SERIAL PRIMARY KEY,
    metric_name     VARCHAR(80)  NOT NULL UNIQUE,
    category        VARCHAR(40),    -- Profitability | Leverage | Liquidity | Growth | Valuation
    unit            VARCHAR(20),    -- '%', 'INR Cr', 'x', 'ratio'
    higher_is_better BOOLEAN
);
INSERT INTO dim_metric (metric_name, category, unit, higher_is_better) VALUES
    ('net_profit_margin',       'Profitability', '%',     TRUE),
    ('opm_pct',                 'Profitability', '%',     TRUE),
    ('ebitda_margin',           'Profitability', '%',     TRUE),
    ('roe_pct',                 'Profitability', '%',     TRUE),
    ('roce_pct',                'Profitability', '%',     TRUE),
    ('debt_to_equity',          'Leverage',      'x',     FALSE),
    ('interest_coverage',       'Leverage',      'x',     TRUE),
    ('debt_to_assets',          'Leverage',      'ratio', FALSE),
    ('free_cash_flow',          'Liquidity',     'INR Cr',TRUE),
    ('operating_cash_ratio',    'Liquidity',     'ratio', TRUE),
    ('capex_intensity',         'Liquidity',     '%',     FALSE),
    ('sales_growth_cagr_3y',    'Growth',        '%',     TRUE),
    ('profit_growth_cagr_5y',   'Growth',        '%',     TRUE),
    ('stock_price_cagr_10y',    'Growth',        '%',     TRUE),
    ('eps',                     'Valuation',     'INR',   TRUE),
    ('dividend_payout_pct',     'Valuation',     '%',     NULL);


-- ================================================================
-- FACT TABLES
-- ================================================================

-- fact_profit_loss: annual P&L data (one row per company per period)
CREATE TABLE fact_profit_loss (
    id                  SERIAL PRIMARY KEY,
    company_id          VARCHAR(30) NOT NULL REFERENCES dim_company(company_id),
    date_key            VARCHAR(10) NOT NULL REFERENCES dim_date(date_key),
    sales               NUMERIC(15,2),   -- INR Crores
    expenses            NUMERIC(15,2),
    operating_profit    NUMERIC(15,2),
    opm_pct             NUMERIC(6,2),
    other_income        NUMERIC(15,2),
    interest            NUMERIC(15,2),
    depreciation        NUMERIC(15,2),
    profit_before_tax   NUMERIC(15,2),
    tax_pct             NUMERIC(6,2),
    net_profit          NUMERIC(15,2),
    eps                 NUMERIC(10,2),
    dividend_payout_pct NUMERIC(6,2),
    -- Derived / computed columns
    ebitda              NUMERIC(15,2) GENERATED ALWAYS AS
                            (operating_profit + depreciation) STORED,
    net_profit_margin   NUMERIC(8,4) GENERATED ALWAYS AS
                            (CASE WHEN sales > 0 THEN net_profit / sales * 100 ELSE NULL END) STORED,
    UNIQUE (company_id, date_key)
);
CREATE INDEX idx_fpl_company ON fact_profit_loss (company_id);
CREATE INDEX idx_fpl_date    ON fact_profit_loss (date_key);


-- fact_balance_sheet: annual balance sheet data
CREATE TABLE fact_balance_sheet (
    id                  SERIAL PRIMARY KEY,
    company_id          VARCHAR(30) NOT NULL REFERENCES dim_company(company_id),
    date_key            VARCHAR(10) NOT NULL REFERENCES dim_date(date_key),
    equity_capital      NUMERIC(15,2),
    reserves            NUMERIC(15,2),
    borrowings          NUMERIC(15,2),
    other_liabilities   NUMERIC(15,2),
    total_liabilities   NUMERIC(15,2),
    fixed_assets        NUMERIC(15,2),
    cwip                NUMERIC(15,2),   -- Capital Work in Progress
    investments         NUMERIC(15,2),
    other_assets        NUMERIC(15,2),
    total_assets        NUMERIC(15,2),
    -- Derived
    net_worth           NUMERIC(15,2) GENERATED ALWAYS AS
                            (equity_capital + reserves) STORED,
    debt_to_equity      NUMERIC(10,4) GENERATED ALWAYS AS
                            (CASE WHEN (equity_capital + reserves) > 0
                             THEN borrowings / (equity_capital + reserves)
                             ELSE NULL END) STORED,
    UNIQUE (company_id, date_key)
);
CREATE INDEX idx_fbs_company ON fact_balance_sheet (company_id);
CREATE INDEX idx_fbs_date    ON fact_balance_sheet (date_key);


-- fact_cash_flow: annual cash flow statement
CREATE TABLE fact_cash_flow (
    id                  SERIAL PRIMARY KEY,
    company_id          VARCHAR(30) NOT NULL REFERENCES dim_company(company_id),
    date_key            VARCHAR(10) NOT NULL REFERENCES dim_date(date_key),
    operating_activity  NUMERIC(15,2),
    investing_activity  NUMERIC(15,2),
    financing_activity  NUMERIC(15,2),
    net_cash_flow       NUMERIC(15,2),
    -- Derived
    free_cash_flow      NUMERIC(15,2) GENERATED ALWAYS AS
                            (operating_activity + investing_activity) STORED,
    UNIQUE (company_id, date_key)
);
CREATE INDEX idx_fcf_company ON fact_cash_flow (company_id);
CREATE INDEX idx_fcf_date    ON fact_cash_flow (date_key);


-- fact_metrics: pre-computed KPIs (wide analytical table)
CREATE TABLE fact_metrics (
    id              SERIAL PRIMARY KEY,
    company_id      VARCHAR(30) NOT NULL REFERENCES dim_company(company_id),
    date_key        VARCHAR(10) NOT NULL REFERENCES dim_date(date_key),
    -- Profitability
    net_profit_margin   NUMERIC(8,4),
    opm_pct             NUMERIC(6,2),
    ebitda_margin       NUMERIC(8,4),
    roe_pct             NUMERIC(6,2),
    roce_pct            NUMERIC(6,2),
    -- Leverage
    debt_to_equity      NUMERIC(10,4),
    interest_coverage   NUMERIC(10,4),
    debt_to_assets      NUMERIC(10,4),
    -- Cash
    free_cash_flow      NUMERIC(15,2),
    operating_cash_ratio NUMERIC(10,4),
    capex_intensity     NUMERIC(8,4),
    -- Growth
    sales_growth_1y     NUMERIC(8,4),
    profit_growth_1y    NUMERIC(8,4),
    -- Valuation
    eps                 NUMERIC(10,2),
    dividend_payout_pct NUMERIC(6,2),
    UNIQUE (company_id, date_key)
);
CREATE INDEX idx_fm_company ON fact_metrics (company_id);
CREATE INDEX idx_fm_date    ON fact_metrics (date_key);


-- dim_documents: annual report links
CREATE TABLE dim_documents (
    id                  SERIAL PRIMARY KEY,
    company_id          VARCHAR(30) NOT NULL REFERENCES dim_company(company_id),
    report_year         SMALLINT,
    annual_report_url   TEXT
);


-- dim_pros_cons: qualitative analysis text
CREATE TABLE dim_pros_cons (
    id          SERIAL PRIMARY KEY,
    company_id  VARCHAR(30) NOT NULL REFERENCES dim_company(company_id),
    pros        TEXT,
    cons        TEXT
);


-- ================================================================
-- VIEWS — pre-built analytical queries
-- ================================================================

-- vw_company_latest: most recent financials per company
CREATE VIEW vw_company_latest AS
SELECT
    c.company_id,
    c.company_name,
    c.roce_pct,
    c.roe_pct,
    c.book_value,
    pl.date_key,
    pl.sales,
    pl.net_profit,
    pl.net_profit_margin,
    pl.eps,
    pl.opm_pct,
    bs.borrowings,
    bs.net_worth,
    bs.debt_to_equity,
    cf.free_cash_flow
FROM dim_company c
LEFT JOIN LATERAL (
    SELECT * FROM fact_profit_loss fpl
    WHERE fpl.company_id = c.company_id
    ORDER BY date_key DESC LIMIT 1
) pl ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM fact_balance_sheet fbs
    WHERE fbs.company_id = c.company_id
    ORDER BY date_key DESC LIMIT 1
) bs ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM fact_cash_flow fcf
    WHERE fcf.company_id = c.company_id
    ORDER BY date_key DESC LIMIT 1
) cf ON TRUE;


-- vw_sector_avg: sector-level averages (requires sector mapping table)
CREATE VIEW vw_financial_trends AS
SELECT
    pl.company_id,
    pl.date_key,
    pl.sales,
    pl.net_profit,
    pl.net_profit_margin,
    pl.eps,
    bs.debt_to_equity,
    cf.free_cash_flow,
    cf.operating_activity
FROM fact_profit_loss pl
LEFT JOIN fact_balance_sheet bs
    ON pl.company_id = bs.company_id AND pl.date_key = bs.date_key
LEFT JOIN fact_cash_flow cf
    ON pl.company_id = cf.company_id AND pl.date_key = cf.date_key;
