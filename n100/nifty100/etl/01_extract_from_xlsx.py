"""
Extract the 7 Nifty 100 source workbooks into normalized raw CSVs.

The source files have a banner row followed by headers on row 2.
This step preserves the original table shape and prepares data/raw/*.csv
for 02_clean_and_transform.py.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


FILE_MAP = {
    "companies.xlsx": "companies.csv",
    "analysis.xlsx": "analysis.csv",
    "balancesheet.xlsx": "balancesheet.csv",
    "profitandloss.xlsx": "profitandloss.csv",
    "cashflow.xlsx": "cashflow.csv",
    "prosandcons.xlsx": "prosandcons.csv",
    "documents.xlsx": "documents.csv",
}


def read_workbook(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, header=1)
    df = df.dropna(how="all").dropna(axis=1, how="all")
    df.columns = [str(col).strip().lower() for col in df.columns]
    return df


def run(src_dir: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for source_name, output_name in FILE_MAP.items():
        path = src_dir / source_name
        if not path.exists():
            print(f"skip {source_name}: file not found")
            continue
        df = read_workbook(path)
        df.to_csv(out_dir / output_name, index=False)
        print(f"{source_name:18s} -> {output_name:18s} rows={len(df):5d} cols={list(df.columns)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", default=".", help="Directory containing the 7 source xlsx files")
    parser.add_argument("--out", default="data/raw", help="Output directory for raw CSVs")
    args = parser.parse_args()
    run(Path(args.src), Path(args.out))
