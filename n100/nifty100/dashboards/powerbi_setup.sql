-- Suggested DAX measures for the financial warehouse

-- Total Sales = SUM(vw_powerbi_financials[sales])
-- Total Net Profit = SUM(vw_powerbi_financials[net_profit])
-- Average NPM % = AVERAGE(vw_powerbi_financials[net_profit_margin_pct])
-- Average Debt To Equity = AVERAGE(vw_powerbi_financials[debt_to_equity])
-- Free Cash Flow = SUM(vw_powerbi_financials[free_cash_flow])
-- Latest EPS = MAX(vw_powerbi_latest[eps])
