"""
Phase 4 — Financial Metrics Computation
========================================
Reads clean CSVs, computes all key financial KPIs, exports metrics CSV.
Can run standalone (no DB needed) or after Phase 3.

Metrics computed:
  Profitability : net margin, OPM, EBITDA margin, ROE, ROCE
  Leverage      : debt-to-equity, interest coverage, debt-to-assets
  Liquidity     : free cash flow, operating cash ratio, capex intensity
  Growth        : YoY, 3Y CAGR, 5Y CAGR for sales & profit
  Valuation     : EPS, dividend payout

Usage:
    python etl/04_compute_metrics.py --clean data/clean --out data/clean/metrics.csv
"""

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=RuntimeWarning)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_all(clean_dir: Path):
    pl  = pd.read_csv(clean_dir / "profit_loss.csv")
    bs  = pd.read_csv(clean_dir / "balance_sheet.csv")
    cf  = pd.read_csv(clean_dir / "cash_flow.csv")
    co  = pd.read_csv(clean_dir / "companies.csv")
    return pl, bs, cf, co


# ---------------------------------------------------------------------------
# CAGR helper
# ---------------------------------------------------------------------------

def cagr(start, end, n_years):
    """Compound Annual Growth Rate. Returns NaN on bad inputs."""
    try:
        if pd.isna(start) or pd.isna(end) or start <= 0 or n_years <= 0:
            return np.nan
        return ((end / start) ** (1 / n_years) - 1) * 100
    except Exception:
        return np.nan


# ---------------------------------------------------------------------------
# Merge fact tables
# ---------------------------------------------------------------------------

def build_merged(pl, bs, cf, co):
    key = ["company_id", "year"]

    merged = (
        pl.merge(bs, on=key, how="outer", suffixes=("_pl", "_bs"))
          .merge(cf, on=key, how="outer", suffixes=("", "_cf"))
    )

    # Bring in company-level cols
    co_slim = co[["company_id", "roce_pct", "roe_pct", "book_value", "face_value"]].copy()
    merged = merged.merge(co_slim, on="company_id", how="left")

    merged = merged.sort_values(["company_id", "year"])
    return merged


# ---------------------------------------------------------------------------
# Metric computation
# ---------------------------------------------------------------------------

def compute_profitability(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Net profit margin
    df["net_profit_margin_pct"] = np.where(
        df["sales"] > 0,
        df["net_profit"] / df["sales"] * 100,
        np.nan
    )

    # EBITDA = operating profit + depreciation
    df["ebitda"] = df["operating_profit"] + df["depreciation"].fillna(0)

    # EBITDA margin
    df["ebitda_margin_pct"] = np.where(
        df["sales"] > 0,
        df["ebitda"] / df["sales"] * 100,
        np.nan
    )

    # ROE and ROCE come from company master (already merged)
    # Re-derive net worth for cross-check
    df["net_worth"] = df["equity_capital"].fillna(0) + df["reserves"].fillna(0)

    # ROE from P&L + BS: net_profit / net_worth * 100
    df["roe_derived_pct"] = np.where(
        df["net_worth"] > 0,
        df["net_profit"] / df["net_worth"] * 100,
        np.nan
    )

    # ROCE: EBIT / Capital Employed
    df["capital_employed"] = df["total_assets"].fillna(0) - df["other_liabilities"].fillna(0)
    df["ebit"] = df["operating_profit"].fillna(0)
    df["roce_derived_pct"] = np.where(
        df["capital_employed"] > 0,
        df["ebit"] / df["capital_employed"] * 100,
        np.nan
    )

    return df


def compute_leverage(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Debt-to-Equity
    df["debt_to_equity"] = np.where(
        df["net_worth"] > 0,
        df["borrowings"] / df["net_worth"],
        np.nan
    )

    # Interest Coverage = EBITDA / Interest
    df["interest_coverage"] = np.where(
        df["interest"].fillna(0) > 0,
        df["ebitda"] / df["interest"],
        np.nan
    )

    # Debt-to-Assets
    df["debt_to_assets"] = np.where(
        df["total_assets"] > 0,
        df["borrowings"] / df["total_assets"],
        np.nan
    )

    return df


def compute_liquidity(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Free Cash Flow = Operating CF + Investing CF (capex is negative in investing)
    df["free_cash_flow"] = (
        df["operating_activity"].fillna(0) + df["investing_activity"].fillna(0)
    )

    # Operating Cash Ratio = Operating CF / Sales
    df["operating_cash_ratio"] = np.where(
        df["sales"] > 0,
        df["operating_activity"] / df["sales"],
        np.nan
    )

    # Capex Intensity = |Investing CF| / Sales  (proxy for capex)
    df["capex_intensity_pct"] = np.where(
        df["sales"] > 0,
        df["investing_activity"].abs() / df["sales"] * 100,
        np.nan
    )

    return df


def compute_growth(df: pd.DataFrame) -> pd.DataFrame:
    """YoY and multi-year CAGRs per company."""
    df = df.sort_values(["company_id", "year"])

    grp = df.groupby("company_id")

    # Year-over-year
    df["sales_yoy_pct"] = grp["sales"].pct_change() * 100
    df["profit_yoy_pct"] = grp["net_profit"].pct_change() * 100
    df["eps_yoy_pct"] = grp["eps"].pct_change() * 100

    # 3-year CAGR
    df["sales_cagr_3y"] = grp["sales"].transform(
        lambda s: s.rolling(4, min_periods=4).apply(
            lambda x: cagr(x.iloc[0], x.iloc[-1], 3), raw=False
        )
    )
    df["profit_cagr_3y"] = grp["net_profit"].transform(
        lambda s: s.rolling(4, min_periods=4).apply(
            lambda x: cagr(x.iloc[0], x.iloc[-1], 3), raw=False
        )
    )

    # 5-year CAGR
    df["sales_cagr_5y"] = grp["sales"].transform(
        lambda s: s.rolling(6, min_periods=6).apply(
            lambda x: cagr(x.iloc[0], x.iloc[-1], 5), raw=False
        )
    )
    df["profit_cagr_5y"] = grp["net_profit"].transform(
        lambda s: s.rolling(6, min_periods=6).apply(
            lambda x: cagr(x.iloc[0], x.iloc[-1], 5), raw=False
        )
    )

    return df


def compute_valuation(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # Earnings per Share is already in the P&L data
    # Payout ratio already present as dividend_payout_pct

    # Book value per share (from balance sheet)
    shares_outstanding = df["equity_capital"] / df["face_value"].replace(0, np.nan)
    df["book_value_per_share"] = np.where(
        shares_outstanding > 0,
        df["net_worth"] / shares_outstanding,
        np.nan
    )

    return df


# ---------------------------------------------------------------------------
# Final output columns
# ---------------------------------------------------------------------------

OUTPUT_COLS = [
    "company_id", "year",
    # Profitability
    "sales", "net_profit", "net_profit_margin_pct",
    "opm_pct", "ebitda", "ebitda_margin_pct",
    "roe_pct", "roe_derived_pct", "roce_pct", "roce_derived_pct",
    # Leverage
    "borrowings", "net_worth", "debt_to_equity",
    "interest_coverage", "debt_to_assets",
    # Liquidity / Cash
    "free_cash_flow", "operating_cash_ratio", "capex_intensity_pct",
    "operating_activity", "investing_activity", "financing_activity",
    # Growth
    "sales_yoy_pct", "profit_yoy_pct", "eps_yoy_pct",
    "sales_cagr_3y", "profit_cagr_3y",
    "sales_cagr_5y", "profit_cagr_5y",
    # Valuation
    "eps", "dividend_payout_pct", "book_value_per_share",
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def run(clean_dir: Path, out_path: Path):
    print("Loading clean CSVs...")
    pl, bs, cf, co = load_all(clean_dir)
    print(f"  P&L: {len(pl)} rows | BS: {len(bs)} rows | CF: {len(cf)} rows")

    print("Merging fact tables...")
    df = build_merged(pl, bs, cf, co)
    print(f"  Merged: {len(df)} rows across {df['company_id'].nunique()} companies")

    print("Computing metrics...")
    df = compute_profitability(df)
    df = compute_leverage(df)
    df = compute_liquidity(df)
    df = compute_growth(df)
    df = compute_valuation(df)

    # Keep only output columns that exist
    final_cols = [c for c in OUTPUT_COLS if c in df.columns]
    out_df = df[final_cols].copy()

    # Round all numeric columns to 4 decimal places
    num_cols = out_df.select_dtypes(include=[np.number]).columns
    out_df[num_cols] = out_df[num_cols].round(4)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(out_path, index=False)

    print(f"\nMetrics CSV written → {out_path}")
    print(f"  Shape: {out_df.shape[0]} rows × {out_df.shape[1]} columns")

    # Print a quick sample
    sample = out_df[out_df["company_id"] == out_df["company_id"].iloc[0]].tail(3)
    print(f"\nSample (last 3 rows for {sample['company_id'].iloc[0]}):")
    print(sample[["company_id","year","net_profit_margin_pct",
                  "debt_to_equity","free_cash_flow","sales_cagr_5y"]].to_string(index=False))

    return out_df


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", default="data/clean")
    parser.add_argument("--out",   default="data/clean/metrics.csv")
    args = parser.parse_args()
    run(Path(args.clean), Path(args.out))
