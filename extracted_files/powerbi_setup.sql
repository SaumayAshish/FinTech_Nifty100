-- ============================================================
-- Power BI Setup Guide — NIFTY 100 Financial Analytics
-- ============================================================
-- This file documents:
--   1. PostgreSQL views to connect Power BI to
--   2. DAX measures to create in Power BI Desktop
--   3. Suggested dashboard layout
-- ============================================================


-- ================================================================
-- STEP 1: PostgreSQL views optimised for Power BI DirectQuery
-- ================================================================

SET search_path TO dw;

-- Flat wide table — easiest for Power BI Import mode
CREATE OR REPLACE VIEW vw_powerbi_flat AS
SELECT
    c.company_id,
    c.company_name,
    c.roce_pct                  AS company_roce,
    c.roe_pct                   AS company_roe,
    c.book_value,
    -- P&L
    pl.date_key,
    pl.sales,
    pl.expenses,
    pl.operating_profit,
    pl.opm_pct,
    pl.net_profit,
    pl.net_profit_margin        AS net_margin_pct,
    pl.ebitda,
    pl.eps,
    pl.dividend_payout_pct,
    pl.interest,
    pl.depreciation,
    -- Balance Sheet
    bs.equity_capital,
    bs.reserves,
    bs.borrowings,
    bs.total_assets,
    bs.net_worth,
    bs.debt_to_equity,
    bs.fixed_assets,
    bs.investments,
    -- Cash Flow
    cf.operating_activity,
    cf.investing_activity,
    cf.financing_activity,
    cf.net_cash_flow,
    cf.free_cash_flow,
    -- Date dimension
    dd.year,
    dd.month,
    dd.quarter,
    dd.fiscal_year
FROM dim_company c
LEFT JOIN fact_profit_loss  pl ON c.company_id = pl.company_id
LEFT JOIN fact_balance_sheet bs ON c.company_id = bs.company_id AND pl.date_key = bs.date_key
LEFT JOIN fact_cash_flow     cf ON c.company_id = cf.company_id AND pl.date_key = cf.date_key
LEFT JOIN dim_date           dd ON pl.date_key = dd.date_key;


-- Latest-year snapshot view (for KPI cards)
CREATE OR REPLACE VIEW vw_powerbi_latest AS
SELECT DISTINCT ON (company_id) *
FROM vw_powerbi_flat
ORDER BY company_id, date_key DESC;


-- Sector summary (after you populate company → sector mapping)
CREATE OR REPLACE VIEW vw_powerbi_sector AS
SELECT
    dd.fiscal_year,
    COUNT(DISTINCT pl.company_id)        AS company_count,
    SUM(pl.sales)                        AS total_sales,
    SUM(pl.net_profit)                   AS total_net_profit,
    AVG(pl.net_profit_margin)            AS avg_net_margin,
    AVG(bs.debt_to_equity)               AS avg_debt_equity,
    SUM(cf.free_cash_flow)               AS total_fcf
FROM fact_profit_loss pl
LEFT JOIN fact_balance_sheet bs ON pl.company_id = bs.company_id AND pl.date_key = bs.date_key
LEFT JOIN fact_cash_flow     cf ON pl.company_id = cf.company_id AND pl.date_key = cf.date_key
LEFT JOIN dim_date           dd ON pl.date_key = dd.date_key
GROUP BY dd.fiscal_year;


-- ================================================================
-- STEP 2: Power BI Connection Settings
-- ================================================================
/*
  In Power BI Desktop:
  1. Home → Get Data → PostgreSQL database
  2. Server:   localhost  (or your host)
     Database: nifty100_dw
  3. Data Connectivity mode: Import  (recommended for datasets < 500MB)
     Or DirectQuery for real-time.
  4. Select tables/views:
       dw.vw_powerbi_flat       ← main fact table
       dw.vw_powerbi_latest     ← KPI cards
       dw.dim_company           ← slicer table
       dw.vw_powerbi_sector     ← sector aggregates
  5. In Model view, verify relationships:
       dim_company[company_id] → vw_powerbi_flat[company_id]  (1:Many)
*/


-- ================================================================
-- STEP 3: DAX Measures (paste into Power BI DAX editor)
-- ================================================================

/*
-- ─── Profitability ───────────────────────────────────────────────

Net Profit Margin % =
    DIVIDE(SUM(vw_powerbi_flat[net_profit]),
           SUM(vw_powerbi_flat[sales]), 0) * 100

EBITDA Margin % =
    DIVIDE(SUM(vw_powerbi_flat[ebitda]),
           SUM(vw_powerbi_flat[sales]), 0) * 100

OPM % =
    DIVIDE(SUM(vw_powerbi_flat[operating_profit]),
           SUM(vw_powerbi_flat[sales]), 0) * 100

-- ─── Leverage ────────────────────────────────────────────────────

Avg Debt to Equity =
    AVERAGEX(DISTINCT(vw_powerbi_flat[company_id]),
        CALCULATE(AVERAGE(vw_powerbi_flat[debt_to_equity])))

Interest Coverage =
    DIVIDE(SUM(vw_powerbi_flat[ebitda]),
           SUM(vw_powerbi_flat[interest]), BLANK())

-- ─── Cash ────────────────────────────────────────────────────────

Total Free Cash Flow =
    SUM(vw_powerbi_flat[free_cash_flow])

FCF Margin % =
    DIVIDE(SUM(vw_powerbi_flat[free_cash_flow]),
           SUM(vw_powerbi_flat[sales]), 0) * 100

-- ─── Growth (YoY requires date intelligence) ─────────────────────

Sales YoY % =
VAR currentYear = SELECTEDVALUE(vw_powerbi_flat[year])
VAR prevSales   = CALCULATE(SUM(vw_powerbi_flat[sales]),
                    vw_powerbi_flat[year] = currentYear - 1)
RETURN DIVIDE(SUM(vw_powerbi_flat[sales]) - prevSales, prevSales, BLANK()) * 100

Profit YoY % =
VAR currentYear  = SELECTEDVALUE(vw_powerbi_flat[year])
VAR prevProfit   = CALCULATE(SUM(vw_powerbi_flat[net_profit]),
                     vw_powerbi_flat[year] = currentYear - 1)
RETURN DIVIDE(SUM(vw_powerbi_flat[net_profit]) - prevProfit, prevProfit, BLANK()) * 100

-- ─── Ranking ─────────────────────────────────────────────────────

Company Rank by Net Margin =
RANKX(ALL(dim_company[company_name]),
      [Net Profit Margin %], , DESC, DENSE)

Company Rank by FCF =
RANKX(ALL(dim_company[company_name]),
      [Total Free Cash Flow], , DESC, DENSE)
*/


-- ================================================================
-- STEP 4: Suggested Dashboard Layout
-- ================================================================
/*
  PAGE 1 — Executive Overview
  ┌──────────────────────────────────────────────────────┐
  │  [Slicer: Company]   [Slicer: Fiscal Year]           │
  ├────────┬────────┬────────┬────────┬─────────────────┤
  │ Sales  │Net P.  │OPM%   │D/E     │FCF              │
  │ ₹ Cr  │ ₹ Cr  │  %    │  x     │  ₹ Cr          │
  ├────────┴────────┴────────┴────────┴─────────────────┤
  │  [Line: Sales & Net Profit trend 10Y]                │
  ├──────────────────────┬───────────────────────────────┤
  │  [Bar: Top 10 by     │  [Bar: Top 10 by ROE %]       │
  │   Net Margin %]      │                               │
  └──────────────────────┴───────────────────────────────┘

  PAGE 2 — P&L Deep Dive
  - Waterfall: Sales → Gross Profit → EBITDA → Net Profit
  - Line chart: OPM % trend vs net margin trend
  - Table: All companies sorted by net margin (latest year)

  PAGE 3 — Balance Sheet & Leverage
  - Scatter: Debt-to-Equity vs ROCE (bubble = Market Cap if available)
  - Stacked bar: Equity vs Borrowings by company
  - KPI card: Companies with D/E > 1 (high leverage alert)

  PAGE 4 — Cash Flow
  - Clustered bar: Operating / Investing / Financing CF per year
  - Line: FCF trend per company
  - Matrix: FCF Margin % heat map (companies × years)

  PAGE 5 — Screening Tool
  - All slicers (OPM > X%, D/E < Y, FCF positive)
  - Conditional formatting table ranking all companies
*/
