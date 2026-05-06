"""
Extract Nifty 100 tables from a MariaDB/MySQL SQL dump.

The script reads INSERT INTO statements from the dump and writes one CSV per
raw source table to data/raw/.
"""

from __future__ import annotations

import argparse
import csv
import re
from io import StringIO
from pathlib import Path

import pandas as pd

TABLES = [
    "companies",
    "analysis",
    "balancesheet",
    "profitandloss",
    "cashflow",
    "prosandcons",
    "documents",
]


INSERT_RE = re.compile(
    r"INSERT\s+INTO\s+`?(?P<table>\w+)`?\s*\((?P<columns>.*?)\)\s*VALUES\s*(?P<values>.*?);",
    re.IGNORECASE | re.DOTALL,
)


def split_value_groups(blob: str) -> list[str]:
    groups: list[str] = []
    depth = 0
    in_quote = False
    escape = False
    start = None
    for idx, char in enumerate(blob):
        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == "'":
            in_quote = not in_quote
            continue
        if in_quote:
            continue
        if char == "(":
            if depth == 0:
                start = idx + 1
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and start is not None:
                groups.append(blob[start:idx])
    return groups


def parse_row(row_blob: str) -> list[object]:
    reader = csv.reader(StringIO(row_blob), delimiter=",", quotechar="'", escapechar="\\")
    values = next(reader)
    parsed: list[object] = []
    for value in values:
        item = value.strip()
        if item.upper() == "NULL":
            parsed.append(None)
        else:
            parsed.append(item.replace("\\r", "\r").replace("\\n", "\n"))
    return parsed


def extract_tables(sql_text: str) -> dict[str, pd.DataFrame]:
    frames: dict[str, list[pd.DataFrame]] = {table: [] for table in TABLES}
    for match in INSERT_RE.finditer(sql_text):
        table = match.group("table").lower()
        if table not in frames:
            continue
        columns = [col.strip().strip("`") for col in match.group("columns").split(",")]
        rows = [parse_row(group) for group in split_value_groups(match.group("values"))]
        frames[table].append(pd.DataFrame(rows, columns=columns))

    output: dict[str, pd.DataFrame] = {}
    for table, parts in frames.items():
        output[table] = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    return output


def run(sql_path: Path, out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    sql_text = sql_path.read_text(encoding="utf-8", errors="ignore")
    extracted = extract_tables(sql_text)

    for table, df in extracted.items():
        output_path = out_dir / f"{table}.csv"
        df.to_csv(output_path, index=False)
        print(f"{table:14s} rows={len(df):5d} columns={list(df.columns)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sql", required=True, help="Path to the MySQL/MariaDB dump file")
    parser.add_argument("--out", default="data/raw", help="Folder to write raw CSVs")
    args = parser.parse_args()
    run(Path(args.sql), Path(args.out))
