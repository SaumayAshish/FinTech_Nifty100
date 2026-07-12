"""
Load cleaned warehouse CSVs into PostgreSQL using idempotent upserts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

# table -> (columns, conflict_target). The SET clause for each upsert is
# derived from `columns` (see _build_update_clause) instead of being
# hand-duplicated, so the two can't drift out of sync.
UPSERTS = {
    "dim_sector": (["sector_name", "sector_code", "description"], "sector_code"),
    "dim_company": (
        [
            "symbol",
            "company_name",
            "sector",
            "sub_sector",
            "company_logo",
            "website",
            "nse_url",
            "bse_url",
            "face_value",
            "book_value",
            "about_company",
            "roce",
            "roe",
        ],
        "symbol",
    ),
    "dim_year": (
        ["year_id", "year_label", "fiscal_year", "quarter", "is_ttm", "is_half_year", "sort_order"],
        "year_id",
    ),
    "fact_balance_sheet": (
        [
            "symbol",
            "year_id",
            "equity_capital",
            "reserves",
            "borrowings",
            "other_liabilities",
            "total_liabilities",
            "fixed_assets",
            "cwip",
            "investments",
            "other_assets",
            "total_assets",
            "debt_to_equity",
            "equity_ratio",
            "book_value_per_share",
        ],
        "symbol, year_id",
    ),
    "fact_profit_loss": (
        [
            "symbol",
            "year_id",
            "sales",
            "expenses",
            "operating_profit",
            "opm_pct",
            "other_income",
            "interest",
            "depreciation",
            "profit_before_tax",
            "tax_pct",
            "net_profit",
            "eps",
            "dividend_payout_pct",
            "net_profit_margin_pct",
            "expense_ratio_pct",
            "interest_coverage",
            "asset_turnover",
            "return_on_assets",
        ],
        "symbol, year_id",
    ),
    "fact_cash_flow": (
        [
            "symbol",
            "year_id",
            "operating_activity",
            "investing_activity",
            "financing_activity",
            "net_cash_flow",
            "free_cash_flow",
            "cash_conversion_ratio",
        ],
        "symbol, year_id",
    ),
    "fact_analysis": (
        [
            "symbol",
            "period_label",
            "compounded_sales_growth_pct",
            "compounded_profit_growth_pct",
            "stock_price_cagr_pct",
            "roe_pct",
        ],
        "symbol, period_label",
    ),
    "fact_pros_cons": (
        ["symbol", "is_pro", "category", "text", "source", "confidence", "generated_at"],
        "symbol, is_pro, text",
    ),
    "documents": (
        ["symbol", "year_label", "document_url"],
        "symbol, year_label, document_url",
    ),
    "fact_ml_scores": (
        [
            "symbol",
            "computed_at",
            "overall_score",
            "profitability_score",
            "growth_score",
            "leverage_score",
            "cashflow_score",
            "dividend_score",
            "trend_score",
            "health_label_id",
        ],
        "symbol, computed_at",
    ),
}


def _build_update_clause(columns: list[str], conflict_target: str) -> str:
    conflict_cols = {c.strip() for c in conflict_target.split(",")}
    return ", ".join(f"{c} = EXCLUDED.{c}" for c in columns if c not in conflict_cols)


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
            rows = conn.execute(
                text("SELECT label_id, label_name FROM dim_health_label")
            ).fetchall()
        mapping = {row[1]: row[0] for row in rows}
        df["health_label_id"] = df["health_label"].map(mapping)
    return df


def upsert_dataframe(engine, table: str, df: pd.DataFrame) -> None:
    if df.empty:
        print(f"{table:20s} skipped (0 rows)")
        return
    columns, conflict_target = UPSERTS[table]
    cols = [col for col in columns if col in df.columns]
    placeholders = ", ".join([f":{col}" for col in cols])
    updates = _build_update_clause(cols, conflict_target)
    # If every insertable column is part of the conflict target (e.g.
    # `documents`), there's nothing left to update on conflict.
    on_conflict = f"DO UPDATE SET {updates}" if updates else "DO NOTHING"
    sql = text(f"""
        INSERT INTO {table} ({", ".join(cols)})
        VALUES ({placeholders})
        ON CONFLICT ({conflict_target}) {on_conflict}
        """)
    records = df[cols].where(pd.notna(df[cols]), None).to_dict(orient="records")
    with engine.begin() as conn:
        conn.execute(sql, records)
    print(f"{table:20s} upserted {len(records):5d} rows")


def run_quality_checks(engine) -> None:
    checks = {
        "orphan_profit_loss": (
            "SELECT COUNT(*) FROM fact_profit_loss fp "
            "LEFT JOIN dim_company dc ON fp.symbol = dc.symbol "
            "WHERE dc.symbol IS NULL"
        ),
        "orphan_balance_sheet": (
            "SELECT COUNT(*) FROM fact_balance_sheet fb "
            "LEFT JOIN dim_company dc ON fb.symbol = dc.symbol "
            "WHERE dc.symbol IS NULL"
        ),
        "orphan_cash_flow": (
            "SELECT COUNT(*) FROM fact_cash_flow fc "
            "LEFT JOIN dim_company dc ON fc.symbol = dc.symbol "
            "WHERE dc.symbol IS NULL"
        ),
        "missing_year_dim": (
            "SELECT COUNT(*) FROM fact_profit_loss fp "
            "LEFT JOIN dim_year dy ON fp.year_id = dy.year_id "
            "WHERE dy.year_id IS NULL"
        ),
    }
    with engine.begin() as conn:
        for label, sql in checks.items():
            value = conn.execute(text(sql)).scalar_one()
            print(f"quality {label:20s} = {value}")


def run(clean_dir: Path, db_url: str) -> None:
    engine = create_engine(db_url)
    for table in [
        "dim_sector",
        "dim_company",
        "dim_year",
        "fact_balance_sheet",
        "fact_profit_loss",
        "fact_cash_flow",
        "fact_analysis",
        "fact_pros_cons",
        "documents",
        "fact_ml_scores",
    ]:
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
    parser.add_argument(
        "--clean", default="data/clean", help="Folder containing cleaned warehouse CSVs"
    )
    parser.add_argument(
        "--db",
        default="postgresql+psycopg2://postgres:password@localhost:5432/nifty100_dw",
        help="SQLAlchemy PostgreSQL URL",
    )
    args = parser.parse_args()
    run(Path(args.clean), args.db)
