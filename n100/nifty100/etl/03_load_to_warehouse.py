"""
Load cleaned warehouse CSVs into PostgreSQL using idempotent upserts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


UPSERTS = {
    "dim_sector": (
        ["sector_name", "sector_code", "description"],
        "sector_code",
        "sector_name = EXCLUDED.sector_name, description = EXCLUDED.description",
    ),
    "dim_company": (
        ["symbol", "company_name", "sector", "sub_sector", "company_logo", "website", "nse_url", "bse_url", "face_value", "book_value", "about_company", "roce", "roe"],
        "symbol",
        "company_name = EXCLUDED.company_name, sector = EXCLUDED.sector, sub_sector = EXCLUDED.sub_sector, company_logo = EXCLUDED.company_logo, website = EXCLUDED.website, nse_url = EXCLUDED.nse_url, bse_url = EXCLUDED.bse_url, face_value = EXCLUDED.face_value, book_value = EXCLUDED.book_value, about_company = EXCLUDED.about_company, roce = EXCLUDED.roce, roe = EXCLUDED.roe",
    ),
    "dim_year": (
        ["year_id", "year_label", "fiscal_year", "quarter", "is_ttm", "is_half_year", "sort_order"],
        "year_id",
        "year_label = EXCLUDED.year_label, fiscal_year = EXCLUDED.fiscal_year, quarter = EXCLUDED.quarter, is_ttm = EXCLUDED.is_ttm, is_half_year = EXCLUDED.is_half_year, sort_order = EXCLUDED.sort_order",
    ),
    "fact_balance_sheet": (
        ["symbol", "year_id", "equity_capital", "reserves", "borrowings", "other_liabilities", "total_liabilities", "fixed_assets", "cwip", "investments", "other_assets", "total_assets", "debt_to_equity", "equity_ratio", "book_value_per_share"],
        "symbol, year_id",
        "equity_capital = EXCLUDED.equity_capital, reserves = EXCLUDED.reserves, borrowings = EXCLUDED.borrowings, other_liabilities = EXCLUDED.other_liabilities, total_liabilities = EXCLUDED.total_liabilities, fixed_assets = EXCLUDED.fixed_assets, cwip = EXCLUDED.cwip, investments = EXCLUDED.investments, other_assets = EXCLUDED.other_assets, total_assets = EXCLUDED.total_assets, debt_to_equity = EXCLUDED.debt_to_equity, equity_ratio = EXCLUDED.equity_ratio, book_value_per_share = EXCLUDED.book_value_per_share",
    ),
    "fact_profit_loss": (
        ["symbol", "year_id", "sales", "expenses", "operating_profit", "opm_pct", "other_income", "interest", "depreciation", "profit_before_tax", "tax_pct", "net_profit", "eps", "dividend_payout_pct", "net_profit_margin_pct", "expense_ratio_pct", "interest_coverage", "asset_turnover", "return_on_assets"],
        "symbol, year_id",
        "sales = EXCLUDED.sales, expenses = EXCLUDED.expenses, operating_profit = EXCLUDED.operating_profit, opm_pct = EXCLUDED.opm_pct, other_income = EXCLUDED.other_income, interest = EXCLUDED.interest, depreciation = EXCLUDED.depreciation, profit_before_tax = EXCLUDED.profit_before_tax, tax_pct = EXCLUDED.tax_pct, net_profit = EXCLUDED.net_profit, eps = EXCLUDED.eps, dividend_payout_pct = EXCLUDED.dividend_payout_pct, net_profit_margin_pct = EXCLUDED.net_profit_margin_pct, expense_ratio_pct = EXCLUDED.expense_ratio_pct, interest_coverage = EXCLUDED.interest_coverage, asset_turnover = EXCLUDED.asset_turnover, return_on_assets = EXCLUDED.return_on_assets",
    ),
    "fact_cash_flow": (
        ["symbol", "year_id", "operating_activity", "investing_activity", "financing_activity", "net_cash_flow", "free_cash_flow", "cash_conversion_ratio"],
        "symbol, year_id",
        "operating_activity = EXCLUDED.operating_activity, investing_activity = EXCLUDED.investing_activity, financing_activity = EXCLUDED.financing_activity, net_cash_flow = EXCLUDED.net_cash_flow, free_cash_flow = EXCLUDED.free_cash_flow, cash_conversion_ratio = EXCLUDED.cash_conversion_ratio",
    ),
    "fact_analysis": (
        ["symbol", "period_label", "compounded_sales_growth_pct", "compounded_profit_growth_pct", "stock_price_cagr_pct", "roe_pct"],
        "symbol, period_label",
        "compounded_sales_growth_pct = EXCLUDED.compounded_sales_growth_pct, compounded_profit_growth_pct = EXCLUDED.compounded_profit_growth_pct, stock_price_cagr_pct = EXCLUDED.stock_price_cagr_pct, roe_pct = EXCLUDED.roe_pct",
    ),
    "fact_pros_cons": (
        ["symbol", "is_pro", "category", "text", "source", "confidence", "generated_at"],
        "symbol, is_pro, text",
        "category = EXCLUDED.category, source = EXCLUDED.source, confidence = EXCLUDED.confidence, generated_at = EXCLUDED.generated_at",
    ),
    "documents": (
        ["symbol", "year_label", "document_url"],
        "symbol, year_label, document_url",
        "year_label = EXCLUDED.year_label",
    ),
    "fact_ml_scores": (
        ["symbol", "computed_at", "overall_score", "profitability_score", "growth_score", "leverage_score", "cashflow_score", "dividend_score", "trend_score", "health_label_id"],
        "symbol, computed_at",
        "overall_score = EXCLUDED.overall_score, profitability_score = EXCLUDED.profitability_score, growth_score = EXCLUDED.growth_score, leverage_score = EXCLUDED.leverage_score, cashflow_score = EXCLUDED.cashflow_score, dividend_score = EXCLUDED.dividend_score, trend_score = EXCLUDED.trend_score, health_label_id = EXCLUDED.health_label_id",
    ),
}


FILES = {
    "dim_sector": "dim_sector.csv",
    "dim_company": "dim_company.csv",
    "dim_year": "dim_year.csv",
    "fact_balance_sheet": "fact_balance_sheet.csv",
    "fact_profit_loss": "fact_profit_loss.csv",
    "fact_cash_flow": "fact_cash_flow.csv",
    "fact_analysis": "fact_analysis.csv",
    "fact_pros_cons": "fact_pros_cons.csv",
    "documents": "documents.csv",
    "fact_ml_scores": "fact_ml_scores.csv",
}


def load_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path).replace({pd.NA: None, float("nan"): None})


def transform_ml_scores(engine, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    if "health_label" in df.columns and "health_label_id" not in df.columns:
        with engine.begin() as conn:
            rows = conn.execute(text("SELECT label_id, label_name FROM dim_health_label")).fetchall()
        mapping = {row[1]: row[0] for row in rows}
        df["health_label_id"] = df["health_label"].map(mapping)
    return df


def upsert_dataframe(engine, table: str, df: pd.DataFrame) -> None:
    if df.empty:
        print(f"{table:20s} skipped (0 rows)")
        return
    columns, conflict_target, updates = UPSERTS[table]
    cols = [col for col in columns if col in df.columns]
    placeholders = ", ".join([f":{col}" for col in cols])
    sql = text(
        f"""
        INSERT INTO {table} ({", ".join(cols)})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_target}) DO UPDATE
        SET {updates}
        """
    )
    records = df[cols].where(pd.notna(df[cols]), None).to_dict(orient="records")
    with engine.begin() as conn:
        conn.execute(sql, records)
    print(f"{table:20s} upserted {len(records):5d} rows")


def run_quality_checks(engine) -> None:
    checks = {
        "orphan_profit_loss": "SELECT COUNT(*) FROM fact_profit_loss fp LEFT JOIN dim_company dc ON fp.symbol = dc.symbol WHERE dc.symbol IS NULL",
        "orphan_balance_sheet": "SELECT COUNT(*) FROM fact_balance_sheet fb LEFT JOIN dim_company dc ON fb.symbol = dc.symbol WHERE dc.symbol IS NULL",
        "orphan_cash_flow": "SELECT COUNT(*) FROM fact_cash_flow fc LEFT JOIN dim_company dc ON fc.symbol = dc.symbol WHERE dc.symbol IS NULL",
        "missing_year_dim": "SELECT COUNT(*) FROM fact_profit_loss fp LEFT JOIN dim_year dy ON fp.year_id = dy.year_id WHERE dy.year_id IS NULL",
    }
    with engine.begin() as conn:
        for label, sql in checks.items():
            value = conn.execute(text(sql)).scalar_one()
            print(f"quality {label:20s} = {value}")


def run(clean_dir: Path, db_url: str) -> None:
    engine = create_engine(db_url)
    for table in ["dim_sector", "dim_company", "dim_year", "fact_balance_sheet", "fact_profit_loss", "fact_cash_flow", "fact_analysis", "fact_pros_cons", "documents", "fact_ml_scores"]:
        csv_path = clean_dir / FILES[table]
        if not csv_path.exists():
            print(f"{table:20s} missing file {csv_path.name}")
            continue
        df = load_csv(csv_path)
        if table == "fact_ml_scores":
            df = transform_ml_scores(engine, df)
        upsert_dataframe(engine, table, df)
    run_quality_checks(engine)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", default="data/clean", help="Folder containing cleaned warehouse CSVs")
    parser.add_argument("--db", default="postgresql+psycopg2://postgres:password@localhost:5432/nifty100_dw", help="SQLAlchemy PostgreSQL URL")
    args = parser.parse_args()
    run(Path(args.clean), args.db)
