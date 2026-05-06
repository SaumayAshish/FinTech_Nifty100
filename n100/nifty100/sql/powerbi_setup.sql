-- Power BI helper views for the Nifty 100 warehouse

CREATE OR REPLACE VIEW vw_powerbi_financials AS
SELECT
    dc.symbol,
    dc.company_name,
    dc.sector,
    dc.sub_sector,
    dy.year_id,
    dy.year_label,
    dy.fiscal_year,
    dy.quarter,
    dy.is_ttm,
    pl.sales,
    pl.net_profit,
    pl.net_profit_margin_pct,
    pl.opm_pct,
    pl.eps,
    pl.dividend_payout_pct,
    pl.interest_coverage,
    bs.total_assets,
    bs.borrowings,
    bs.debt_to_equity,
    bs.equity_ratio,
    cf.operating_activity,
    cf.investing_activity,
    cf.free_cash_flow,
    cf.cash_conversion_ratio
FROM dim_company dc
LEFT JOIN fact_profit_loss pl
    ON dc.symbol = pl.symbol
LEFT JOIN dim_year dy
    ON pl.year_id = dy.year_id
LEFT JOIN fact_balance_sheet bs
    ON pl.symbol = bs.symbol AND pl.year_id = bs.year_id
LEFT JOIN fact_cash_flow cf
    ON pl.symbol = cf.symbol AND pl.year_id = cf.year_id;

CREATE OR REPLACE VIEW vw_powerbi_latest AS
SELECT *
FROM (
    SELECT
        vpf.*,
        ROW_NUMBER() OVER (PARTITION BY symbol ORDER BY sort_year DESC) AS rn
    FROM (
        SELECT
            vw_powerbi_financials.*,
            COALESCE(year_id, 0) AS sort_year
        FROM vw_powerbi_financials
    ) vpf
) ranked
WHERE rn = 1;
