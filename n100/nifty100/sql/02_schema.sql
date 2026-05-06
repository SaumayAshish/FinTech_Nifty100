-- Nifty 100 Financial Intelligence Warehouse
-- PostgreSQL 15 compatible star schema

CREATE TABLE IF NOT EXISTS dim_sector (
    sector_id SERIAL PRIMARY KEY,
    sector_name VARCHAR(100) NOT NULL UNIQUE,
    sector_code VARCHAR(20) NOT NULL UNIQUE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS dim_company (
    symbol VARCHAR(20) PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    sector VARCHAR(100),
    sub_sector VARCHAR(100),
    company_logo TEXT,
    website TEXT,
    nse_url TEXT,
    bse_url TEXT,
    face_value NUMERIC(12,2),
    book_value NUMERIC(12,2),
    about_company TEXT,
    roce NUMERIC(8,2),
    roe NUMERIC(8,2)
);

CREATE TABLE IF NOT EXISTS dim_year (
    year_id INT PRIMARY KEY,
    year_label VARCHAR(20) NOT NULL UNIQUE,
    fiscal_year INT,
    quarter VARCHAR(4),
    is_ttm BOOLEAN NOT NULL DEFAULT FALSE,
    is_half_year BOOLEAN NOT NULL DEFAULT FALSE,
    sort_order INT NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_health_label (
    label_id SERIAL PRIMARY KEY,
    label_name VARCHAR(20) NOT NULL UNIQUE,
    min_score NUMERIC(6,2) NOT NULL,
    max_score NUMERIC(6,2) NOT NULL,
    color_hex VARCHAR(7) NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_profit_loss (
    symbol VARCHAR(20) NOT NULL REFERENCES dim_company(symbol),
    year_id INT NOT NULL REFERENCES dim_year(year_id),
    sales NUMERIC(18,2),
    expenses NUMERIC(18,2),
    operating_profit NUMERIC(18,2),
    opm_pct NUMERIC(8,2),
    other_income NUMERIC(18,2),
    interest NUMERIC(18,2),
    depreciation NUMERIC(18,2),
    profit_before_tax NUMERIC(18,2),
    tax_pct NUMERIC(8,2),
    net_profit NUMERIC(18,2),
    eps NUMERIC(12,2),
    dividend_payout_pct NUMERIC(8,2),
    net_profit_margin_pct NUMERIC(10,4),
    expense_ratio_pct NUMERIC(10,4),
    interest_coverage NUMERIC(12,4),
    asset_turnover NUMERIC(12,4),
    return_on_assets NUMERIC(10,4),
    PRIMARY KEY (symbol, year_id)
);

CREATE TABLE IF NOT EXISTS fact_balance_sheet (
    symbol VARCHAR(20) NOT NULL REFERENCES dim_company(symbol),
    year_id INT NOT NULL REFERENCES dim_year(year_id),
    equity_capital NUMERIC(18,2),
    reserves NUMERIC(18,2),
    borrowings NUMERIC(18,2),
    other_liabilities NUMERIC(18,2),
    total_liabilities NUMERIC(18,2),
    fixed_assets NUMERIC(18,2),
    cwip NUMERIC(18,2),
    investments NUMERIC(18,2),
    other_assets NUMERIC(18,2),
    total_assets NUMERIC(18,2),
    debt_to_equity NUMERIC(12,4),
    equity_ratio NUMERIC(12,4),
    book_value_per_share NUMERIC(12,4),
    PRIMARY KEY (symbol, year_id)
);

CREATE TABLE IF NOT EXISTS fact_cash_flow (
    symbol VARCHAR(20) NOT NULL REFERENCES dim_company(symbol),
    year_id INT NOT NULL REFERENCES dim_year(year_id),
    operating_activity NUMERIC(18,2),
    investing_activity NUMERIC(18,2),
    financing_activity NUMERIC(18,2),
    net_cash_flow NUMERIC(18,2),
    free_cash_flow NUMERIC(18,2),
    cash_conversion_ratio NUMERIC(12,4),
    PRIMARY KEY (symbol, year_id)
);

CREATE TABLE IF NOT EXISTS fact_analysis (
    symbol VARCHAR(20) NOT NULL REFERENCES dim_company(symbol),
    period_label VARCHAR(10) NOT NULL,
    compounded_sales_growth_pct NUMERIC(10,2),
    compounded_profit_growth_pct NUMERIC(10,2),
    stock_price_cagr_pct NUMERIC(10,2),
    roe_pct NUMERIC(10,2),
    PRIMARY KEY (symbol, period_label)
);

CREATE TABLE IF NOT EXISTS fact_ml_scores (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES dim_company(symbol),
    computed_at TIMESTAMPTZ NOT NULL,
    overall_score NUMERIC(6,2) NOT NULL,
    profitability_score NUMERIC(6,2),
    growth_score NUMERIC(6,2),
    leverage_score NUMERIC(6,2),
    cashflow_score NUMERIC(6,2),
    dividend_score NUMERIC(6,2),
    trend_score NUMERIC(6,2),
    health_label_id INT REFERENCES dim_health_label(label_id),
    UNIQUE (symbol, computed_at)
);

CREATE TABLE IF NOT EXISTS fact_pros_cons (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES dim_company(symbol),
    is_pro BOOLEAN NOT NULL,
    category VARCHAR(100),
    text TEXT NOT NULL,
    source VARCHAR(20) NOT NULL DEFAULT 'MANUAL',
    confidence NUMERIC(6,2),
    generated_at TIMESTAMPTZ,
    UNIQUE (symbol, is_pro, text)
);

CREATE TABLE IF NOT EXISTS documents (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL REFERENCES dim_company(symbol),
    year_label VARCHAR(20),
    document_url TEXT NOT NULL,
    UNIQUE (symbol, year_label, document_url)
);

INSERT INTO dim_health_label (label_name, min_score, max_score, color_hex)
VALUES
    ('POOR', 0, 20, '#B91C1C'),
    ('WEAK', 20, 40, '#EA580C'),
    ('AVERAGE', 40, 60, '#CA8A04'),
    ('GOOD', 60, 80, '#15803D'),
    ('EXCELLENT', 80, 100, '#166534')
ON CONFLICT (label_name) DO NOTHING;

CREATE INDEX IF NOT EXISTS idx_company_sector ON dim_company(sector);
CREATE INDEX IF NOT EXISTS idx_year_sort_order ON dim_year(sort_order);
CREATE INDEX IF NOT EXISTS idx_profit_loss_year ON fact_profit_loss(year_id);
CREATE INDEX IF NOT EXISTS idx_balance_sheet_year ON fact_balance_sheet(year_id);
CREATE INDEX IF NOT EXISTS idx_cash_flow_year ON fact_cash_flow(year_id);
CREATE INDEX IF NOT EXISTS idx_ml_scores_symbol_time ON fact_ml_scores(symbol, computed_at DESC);
