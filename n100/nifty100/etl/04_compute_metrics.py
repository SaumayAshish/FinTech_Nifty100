"""
Compute lightweight health scores from cleaned fact CSVs.

This step is optional but useful for populating fact_ml_scores later.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def bounded_score(series: pd.Series, higher_is_better: bool = True) -> pd.Series:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.dropna().empty:
        return pd.Series([np.nan] * len(series), index=series.index)
    lo = numeric.quantile(0.05)
    hi = numeric.quantile(0.95)
    clipped = numeric.clip(lower=lo, upper=hi)
    scaled = (
        (clipped - lo) / (hi - lo) * 100
        if hi != lo
        else pd.Series([50.0] * len(series), index=series.index)
    )
    return scaled if higher_is_better else 100 - scaled


def health_label(score: float) -> str | None:
    if pd.isna(score):
        return None
    if score >= 80:
        return "EXCELLENT"
    if score >= 60:
        return "GOOD"
    if score >= 40:
        return "AVERAGE"
    if score >= 20:
        return "WEAK"
    return "POOR"


def run(clean_dir: Path, out_path: Path) -> None:
    pl = pd.read_csv(clean_dir / "fact_profit_loss.csv")
    bs = pd.read_csv(clean_dir / "fact_balance_sheet.csv")
    cf = pd.read_csv(clean_dir / "fact_cash_flow.csv")

    latest_pl = pl.sort_values("sort_order").groupby("symbol").tail(1)
    latest_bs = bs.sort_values("sort_order").groupby("symbol").tail(1)
    latest_cf = cf.sort_values("sort_order").groupby("symbol").tail(1)

    merged = latest_pl.merge(latest_bs, on=["symbol", "year_id"], how="left", suffixes=("", "_bs"))
    merged = merged.merge(latest_cf, on=["symbol", "year_id"], how="left", suffixes=("", "_cf"))

    merged["profitability_score"] = bounded_score(merged["net_profit_margin_pct"])
    merged["growth_score"] = bounded_score(merged["asset_turnover"])
    merged["leverage_score"] = bounded_score(merged["debt_to_equity"], higher_is_better=False)
    merged["cashflow_score"] = bounded_score(merged["free_cash_flow"])
    merged["dividend_score"] = bounded_score(merged["dividend_payout_pct"])
    merged["trend_score"] = bounded_score(merged["return_on_assets"])

    score_cols = [
        "profitability_score",
        "growth_score",
        "leverage_score",
        "cashflow_score",
        "dividend_score",
        "trend_score",
    ]
    merged["overall_score"] = merged[score_cols].mean(axis=1, skipna=True).round(2)
    merged["health_label"] = merged["overall_score"].apply(health_label)
    merged["computed_at"] = datetime.now(timezone.utc).isoformat()

    out = merged[["symbol", "computed_at", "overall_score"] + score_cols + ["health_label"]]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print(f"ml_scores rows={len(out)} written to {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clean", default="data/clean", help="Folder containing cleaned fact CSVs")
    parser.add_argument("--out", default="data/clean/fact_ml_scores.csv", help="Output CSV path")
    args = parser.parse_args()
    run(Path(args.clean), Path(args.out))
