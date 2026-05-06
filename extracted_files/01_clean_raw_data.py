"""
Phase 1 — Clean & Transform Raw NIFTY 100 Data
================================================
Reads the 7 source xlsx files, fixes malformed headers, coerces types,
parses messy year strings, and exports clean CSVs ready for DB load.

Usage:
    python etl/01_clean_raw_data.py --src /path/to/xlsx_folder --out data/clean
"""

import argparse
import re
import pandas as pd
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_xlsx(path: Path, header_row: int = 1) -> pd.DataFrame:
    """Read an xlsx where row 0 is a banner and row 1 is the real header."""
    df = pd.read_excel(path, header=header_row)
    # Drop fully empty rows/cols
    df = df.dropna(how="all").dropna(axis=1, how="all")
    # Rename columns: strip whitespace
    df.columns = [str(c).strip() for c in df.columns]
    return df


def to_numeric_cols(df: pd.DataFrame, cols: list) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def normalize_year(val) -> str | None:
    """
    Convert messy year strings to a consistent 'YYYY-MM' or 'MMM-YY' form.
    Examples:
        'Mar 2014'   -> '2014-03'
        'Mar-13'     -> '2013-03'
        'Dec 2012'   -> '2012-12'
        '2024'       -> '2024'
    """
    if pd.isna(val):
        return None
    s = str(val).strip()

    # Already clean: YYYY
    if re.fullmatch(r"\d{4}", s):
        return s

    # 'Mon YYYY' -> '2014-03'
    m = re.fullmatch(r"([A-Za-z]{3})\s+(\d{4})", s)
    if m:
        month_map = {v: str(i).zfill(2) for i, v in enumerate(
            ["Jan","Feb","Mar","Apr","May","Jun",
             "Jul","Aug","Sep","Oct","Nov","Dec"], 1)}
        mon = m.group(1).capitalize()
        return f"{m.group(2)}-{month_map.get(mon, '00')}"

    # 'Mon-YY' -> '20YY-MM'  (assume 20xx for 2-digit years)
    m = re.fullmatch(r"([A-Za-z]{3})-(\d{2})", s)
    if m:
        month_map = {v: str(i).zfill(2) for i, v in enumerate(
            ["Jan","Feb","Mar","Apr","May","Jun",
             "Jul","Aug","Sep","Oct","Nov","Dec"], 1)}
        mon = m.group(1).capitalize()
        year = "20" + m.group(2)
        return f"{year}-{month_map.get(mon, '00')}"

    return s  # return as-is if nothing matched


def extract_first_pct(val) -> float | None:
    """Extract first numeric value from strings like '10 Years: 21%'."""
    if pd.isna(val):
        return None
    m = re.search(r"([\d.]+)%", str(val))
    return float(m.group(1)) if m else None


def extract_first_years(val) -> int | None:
    """Extract the year horizon from strings like '10 Years: 21%'."""
    if pd.isna(val):
        return None
    m = re.search(r"(\d+)\s*[Yy]ears?", str(val))
    return int(m.group(1)) if m else None


# ---------------------------------------------------------------------------
# Per-table cleaners
# ---------------------------------------------------------------------------

def clean_companies(path: Path) -> pd.DataFrame:
    df = load_xlsx(path)
    rename = {
        df.columns[0]: "company_id",
        df.columns[1]: "company_logo_url",
        df.columns[2]: "company_name",
        df.columns[3]: "chart_link",
        df.columns[4]: "about_company",
        df.columns[5]: "website",
        df.columns[6]: "nse_profile",
        df.columns[7]: "bse_profile",
        df.columns[8]: "face_value",
        df.columns[9]: "book_value",
        df.columns[10]: "roce_pct",
        df.columns[11]: "roe_pct",
    }
    df = df.rename(columns=rename)
    df = to_numeric_cols(df, ["face_value", "book_value", "roce_pct", "roe_pct"])
    df["company_id"] = df["company_id"].str.strip()
    df = df.dropna(subset=["company_id"])
    return df


def clean_prosandcons(path: Path) -> pd.DataFrame:
    df = load_xlsx(path)
    df.columns = ["id", "company_id", "pros", "cons"]
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df = df.dropna(subset=["company_id"])
    df["company_id"] = df["company_id"].str.strip()
    return df


def clean_documents(path: Path) -> pd.DataFrame:
    df = load_xlsx(path)
    df.columns = ["id", "company_id", "year", "annual_report_url"]
    df["id"] = pd.to_numeric(df["id"], errors="coerce")
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    df["company_id"] = df["company_id"].str.strip()
    return df


def clean_profit_loss(path: Path) -> pd.DataFrame:
    df = load_xlsx(path)
    df.columns = [
        "id", "company_id", "year", "sales", "expenses",
        "operating_profit", "opm_pct", "other_income", "interest",
        "depreciation", "profit_before_tax", "tax_pct",
        "net_profit", "eps", "dividend_payout_pct"
    ]
    df["year_raw"] = df["year"].copy()
    df["year"] = df["year"].apply(normalize_year)
    num_cols = [
        "sales", "expenses", "operating_profit", "opm_pct", "other_income",
        "interest", "depreciation", "profit_before_tax", "tax_pct",
        "net_profit", "eps", "dividend_payout_pct"
    ]
    df = to_numeric_cols(df, num_cols)
    df["company_id"] = df["company_id"].str.strip()
    df = df.drop(columns=["year_raw"])
    return df


def clean_balance_sheet(path: Path) -> pd.DataFrame:
    df = load_xlsx(path)
    df.columns = [
        "id", "company_id", "year", "equity_capital", "reserves",
        "borrowings", "other_liabilities", "total_liabilities",
        "fixed_assets", "cwip", "investments", "other_assets", "total_assets"
    ]
    df["year"] = df["year"].apply(normalize_year)
    num_cols = [
        "equity_capital", "reserves", "borrowings", "other_liabilities",
        "total_liabilities", "fixed_assets", "cwip", "investments",
        "other_assets", "total_assets"
    ]
    df = to_numeric_cols(df, num_cols)
    df["company_id"] = df["company_id"].str.strip()
    return df


def clean_cashflow(path: Path) -> pd.DataFrame:
    df = load_xlsx(path)
    df.columns = [
        "id", "company_id", "year",
        "operating_activity", "investing_activity",
        "financing_activity", "net_cash_flow"
    ]
    df["year"] = df["year"].apply(normalize_year)
    num_cols = [
        "operating_activity", "investing_activity",
        "financing_activity", "net_cash_flow"
    ]
    df = to_numeric_cols(df, num_cols)
    df["company_id"] = df["company_id"].str.strip()
    return df


def clean_analysis(path: Path) -> pd.DataFrame:
    """
    Unpivots the wide analysis table into long format:
    (company_id, metric, horizon_years, value_pct)
    """
    df = load_xlsx(path)
    df.columns = [
        "id", "company_id",
        "compounded_sales_growth",
        "compounded_profit_growth",
        "stock_price_cagr",
        "roe"
    ]
    df["company_id"] = df["company_id"].str.strip()

    metrics = {
        "compounded_sales_growth": "sales_growth_cagr",
        "compounded_profit_growth": "profit_growth_cagr",
        "stock_price_cagr": "stock_price_cagr",
        "roe": "roe",
    }

    rows = []
    for _, row in df.iterrows():
        for raw_col, metric_name in metrics.items():
            val = row.get(raw_col)
            rows.append({
                "company_id": row["company_id"],
                "metric": metric_name,
                "horizon_years": extract_first_years(val),
                "value_pct": extract_first_pct(val),
            })

    return pd.DataFrame(rows).dropna(subset=["company_id"])


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

FILE_MAP = {
    "companies.xlsx":     (clean_companies,    "companies.csv"),
    "prosandcons.xlsx":   (clean_prosandcons,  "pros_cons.csv"),
    "documents.xlsx":     (clean_documents,    "documents.csv"),
    "profitandloss.xlsx": (clean_profit_loss,  "profit_loss.csv"),
    "balancesheet.xlsx":  (clean_balance_sheet,"balance_sheet.csv"),
    "cashflow.xlsx":      (clean_cashflow,     "cash_flow.csv"),
    "analysis.xlsx":      (clean_analysis,     "analysis.csv"),
}


def run(src_dir: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = []

    for filename, (cleaner, out_name) in FILE_MAP.items():
        src = src_dir / filename
        if not src.exists():
            print(f"  [SKIP] {filename} not found at {src}")
            continue

        print(f"  Processing {filename} ...", end=" ")
        df = cleaner(src)
        out_path = out_dir / out_name
        df.to_csv(out_path, index=False)
        summary.append({
            "source": filename,
            "rows": len(df),
            "columns": len(df.columns),
            "output": out_name,
            "null_pct": f"{df.isnull().mean().mean() * 100:.1f}%"
        })
        print(f"{len(df)} rows → {out_name}")

    print("\n--- Summary ---")
    for s in summary:
        print(f"  {s['source']:25s}  {s['rows']:>5} rows  {s['columns']:>2} cols  "
              f"null%={s['null_pct']}  → {s['output']}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=".", help="Folder containing xlsx files")
    parser.add_argument("--out", default="data/clean", help="Output folder for CSVs")
    args = parser.parse_args()
    run(Path(args.src), Path(args.out))
