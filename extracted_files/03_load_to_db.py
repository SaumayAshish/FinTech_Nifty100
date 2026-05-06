"""
Phase 3 — ETL Loader: Clean CSVs → PostgreSQL Data Warehouse
=============================================================
Usage:
    python etl/03_load_to_db.py --clean data/clean --db postgresql://user:pass@localhost/nifty100_dw

Dependencies:
    pip install pandas sqlalchemy psycopg2-binary
"""

import argparse
import re
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_engine(db_url: str):
    engine = create_engine(db_url, echo=False)
    return engine


def build_date_keys(df: pd.DataFrame, year_col: str = "year") -> set:
    """Collect all unique date_key values that need to exist in dim_date."""
    return set(df[year_col].dropna().unique())


def upsert_dim_date(engine, date_keys: set):
    """Insert date dimension rows (skip duplicates)."""
    rows = []
    for dk in date_keys:
        dk = str(dk).strip()
        if re.fullmatch(r"\d{4}", dk):
            year, month = int(dk), None
            quarter = None
            fy = f"{year-1}-{str(year)[2:]}" if month is None else None
        else:
            m = re.fullmatch(r"(\d{4})-(\d{2})", dk)
            if m:
                year, month = int(m.group(1)), int(m.group(2))
                quarter = (month - 1) // 3 + 1
                fy_start = year if month >= 4 else year - 1
                fy = f"{fy_start}-{str(fy_start + 1)[2:]}"
            else:
                year, month, quarter, fy = None, None, None, None

        rows.append({
            "date_key": dk,
            "year": year,
            "month": month,
            "quarter": quarter,
            "fiscal_year": fy,
            "is_annual": True,
        })

    dim_df = pd.DataFrame(rows).drop_duplicates("date_key")
    with engine.begin() as conn:
        for _, row in dim_df.iterrows():
            conn.execute(text("""
                INSERT INTO dw.dim_date (date_key, year, month, quarter, fiscal_year, is_annual)
                VALUES (:date_key, :year, :month, :quarter, :fiscal_year, :is_annual)
                ON CONFLICT (date_key) DO NOTHING
            """), row.to_dict())
    print(f"    dim_date: {len(dim_df)} date keys upserted")


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_companies(clean_dir: Path, engine):
    df = pd.read_csv(clean_dir / "companies.csv")
    keep = [
        "company_id", "company_name", "website", "nse_profile", "bse_profile",
        "company_logo_url", "about_company", "face_value", "book_value",
        "roce_pct", "roe_pct"
    ]
    df = df[[c for c in keep if c in df.columns]]
    df = df.rename(columns={
        "nse_profile": "nse_profile_url",
        "bse_profile": "bse_profile_url"
    })
    df.to_sql(
        "dim_company", engine, schema="dw", if_exists="append",
        index=False, method="multi",
    )
    print(f"    dim_company: {len(df)} rows loaded")


def load_pros_cons(clean_dir: Path, engine):
    df = pd.read_csv(clean_dir / "pros_cons.csv")
    df = df[["company_id", "pros", "cons"]]
    df.to_sql(
        "dim_pros_cons", engine, schema="dw", if_exists="append",
        index=False, method="multi",
    )
    print(f"    dim_pros_cons: {len(df)} rows loaded")


def load_documents(clean_dir: Path, engine):
    df = pd.read_csv(clean_dir / "documents.csv")
    df = df.rename(columns={"year": "report_year", "annual_report_url": "annual_report_url"})
    df.to_sql(
        "dim_documents", engine, schema="dw", if_exists="append",
        index=False, method="multi",
    )
    print(f"    dim_documents: {len(df)} rows loaded")


def load_profit_loss(clean_dir: Path, engine):
    df = pd.read_csv(clean_dir / "profit_loss.csv")
    df = df.rename(columns={"year": "date_key"})
    upsert_dim_date(engine, build_date_keys(df, "date_key"))
    keep = [
        "company_id", "date_key", "sales", "expenses", "operating_profit",
        "opm_pct", "other_income", "interest", "depreciation",
        "profit_before_tax", "tax_pct", "net_profit", "eps", "dividend_payout_pct"
    ]
    df = df[[c for c in keep if c in df.columns]]
    df.to_sql(
        "fact_profit_loss", engine, schema="dw", if_exists="append",
        index=False, method="multi",
    )
    print(f"    fact_profit_loss: {len(df)} rows loaded")


def load_balance_sheet(clean_dir: Path, engine):
    df = pd.read_csv(clean_dir / "balance_sheet.csv")
    df = df.rename(columns={"year": "date_key"})
    upsert_dim_date(engine, build_date_keys(df, "date_key"))
    keep = [
        "company_id", "date_key", "equity_capital", "reserves", "borrowings",
        "other_liabilities", "total_liabilities", "fixed_assets", "cwip",
        "investments", "other_assets", "total_assets"
    ]
    df = df[[c for c in keep if c in df.columns]]
    df.to_sql(
        "fact_balance_sheet", engine, schema="dw", if_exists="append",
        index=False, method="multi",
    )
    print(f"    fact_balance_sheet: {len(df)} rows loaded")


def load_cash_flow(clean_dir: Path, engine):
    df = pd.read_csv(clean_dir / "cash_flow.csv")
    df = df.rename(columns={"year": "date_key"})
    upsert_dim_date(engine, build_date_keys(df, "date_key"))
    keep = [
        "company_id", "date_key", "operating_activity",
        "investing_activity", "financing_activity", "net_cash_flow"
    ]
    df = df[[c for c in keep if c in df.columns]]
    df.to_sql(
        "fact_cash_flow", engine, schema="dw", if_exists="append",
        index=False, method="multi",
    )
    print(f"    fact_cash_flow: {len(df)} rows loaded")


def compute_and_load_metrics(engine):
    """
    Compute fact_metrics from already-loaded fact tables.
    Runs entirely in SQL for performance.
    """
    sql = """
    INSERT INTO dw.fact_metrics (
        company_id, date_key,
        net_profit_margin, opm_pct, ebitda_margin, roe_pct, roce_pct,
        debt_to_equity, interest_coverage, debt_to_assets,
        free_cash_flow, operating_cash_ratio, capex_intensity,
        sales_growth_1y, profit_growth_1y,
        eps, dividend_payout_pct
    )
    SELECT
        pl.company_id,
        pl.date_key,
        -- Profitability
        CASE WHEN pl.sales > 0 THEN pl.net_profit / pl.sales * 100 END         AS net_profit_margin,
        pl.opm_pct,
        CASE WHEN pl.sales > 0
             THEN (pl.operating_profit + pl.depreciation) / pl.sales * 100 END AS ebitda_margin,
        c.roe_pct,
        c.roce_pct,
        -- Leverage
        bs.debt_to_equity,
        CASE WHEN pl.interest > 0
             THEN (pl.operating_profit + pl.depreciation) / pl.interest END     AS interest_coverage,
        CASE WHEN bs.total_assets > 0
             THEN bs.borrowings / bs.total_assets END                            AS debt_to_assets,
        -- Cash
        cf.free_cash_flow,
        CASE WHEN pl.sales > 0
             THEN cf.operating_activity / pl.sales END                           AS operating_cash_ratio,
        CASE WHEN pl.sales > 0
             THEN ABS(cf.investing_activity) / pl.sales END                      AS capex_intensity,
        -- Growth (YoY)
        CASE WHEN LAG(pl.sales) OVER w > 0
             THEN (pl.sales - LAG(pl.sales) OVER w) / LAG(pl.sales) OVER w * 100 END AS sales_growth_1y,
        CASE WHEN LAG(pl.net_profit) OVER w > 0
             THEN (pl.net_profit - LAG(pl.net_profit) OVER w)
                  / LAG(pl.net_profit) OVER w * 100 END                          AS profit_growth_1y,
        -- Valuation
        pl.eps,
        pl.dividend_payout_pct
    FROM dw.fact_profit_loss pl
    LEFT JOIN dw.fact_balance_sheet bs
        ON pl.company_id = bs.company_id AND pl.date_key = bs.date_key
    LEFT JOIN dw.fact_cash_flow cf
        ON pl.company_id = cf.company_id AND pl.date_key = cf.date_key
    LEFT JOIN dw.dim_company c ON pl.company_id = c.company_id
    WINDOW w AS (PARTITION BY pl.company_id ORDER BY pl.date_key)
    ON CONFLICT (company_id, date_key) DO UPDATE SET
        net_profit_margin   = EXCLUDED.net_profit_margin,
        opm_pct             = EXCLUDED.opm_pct,
        ebitda_margin       = EXCLUDED.ebitda_margin,
        debt_to_equity      = EXCLUDED.debt_to_equity,
        interest_coverage   = EXCLUDED.interest_coverage,
        free_cash_flow      = EXCLUDED.free_cash_flow,
        eps                 = EXCLUDED.eps;
    """
    with engine.begin() as conn:
        result = conn.execute(text(sql))
    print(f"    fact_metrics: {result.rowcount} rows upserted")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

LOADERS = [
    ("Companies",     load_companies),
    ("Pros & Cons",   load_pros_cons),
    ("Documents",     load_documents),
    ("Profit & Loss", load_profit_loss),
    ("Balance Sheet", load_balance_sheet),
    ("Cash Flow",     load_cash_flow),
]


def run(clean_dir: Path, db_url: str):
    engine = get_engine(db_url)
    print(f"\nConnected to: {db_url}")

    for name, loader in LOADERS:
        print(f"\n  Loading {name}...")
        try:
            loader(clean_dir, engine)
        except Exception as e:
            print(f"    ERROR: {e}")

    print("\n  Computing financial metrics...")
    try:
        compute_and_load_metrics(engine)
    except Exception as e:
        print(f"    ERROR in metrics: {e}")

    print("\nETL complete.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", default="data/clean")
    parser.add_argument(
        "--db",
        default="postgresql://postgres:password@localhost:5432/nifty100_dw",
        help="SQLAlchemy DB URL"
    )
    args = parser.parse_args()
    run(Path(args.clean), args.db)
