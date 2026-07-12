"""
Clean and standardize raw Nifty 100 source tables into warehouse-ready CSVs.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import numpy as np
import pandas as pd

RAW_FILES = {
    "companies": "companies.csv",
    "analysis": "analysis.csv",
    "balancesheet": "balancesheet.csv",
    "profitandloss": "profitandloss.csv",
    "cashflow": "cashflow.csv",
    "prosandcons": "prosandcons.csv",
    "documents": "documents.csv",
}

SECTOR_DEFAULTS = {
    "TCS": ("IT", "IT Services"),
    "INFY": ("IT", "IT Services"),
    "WIPRO": ("IT", "IT Services"),
    "HCLTECH": ("IT", "IT Services"),
    "TECHM": ("IT", "IT Services"),
    "HDFCBANK": ("Banking", "Private Bank"),
    "ICICIBANK": ("Banking", "Private Bank"),
    "SBIN": ("Banking", "PSU Bank"),
    "AXISBANK": ("Banking", "Private Bank"),
    "KOTAKBANK": ("Banking", "Private Bank"),
    "BANKBARODA": ("Banking", "PSU Bank"),
    "INDUSINDBK": ("Banking", "Private Bank"),
    "BAJFINANCE": ("NBFC", "Consumer Finance"),
    "BAJAJFINSV": ("NBFC", "Financial Services"),
    "SBILIFE": ("Insurance", "Life Insurance"),
    "HDFCLIFE": ("Insurance", "Life Insurance"),
    "ICICIPRULI": ("Insurance", "Life Insurance"),
    "RELIANCE": ("Energy", "Integrated Energy"),
    "ONGC": ("Energy", "Oil & Gas"),
    "BPCL": ("Energy", "Oil Marketing"),
    "IOC": ("Energy", "Oil Marketing"),
    "ADANIGREEN": ("Power", "Renewable Power"),
    "ADANIPOWER": ("Power", "Thermal Power"),
    "ATGL": ("Energy", "Gas Distribution"),
    "NTPC": ("Power", "Power Generation"),
    "POWERGRID": ("Power", "Transmission"),
    "COALINDIA": ("Energy", "Mining"),
    "BHARTIARTL": ("Telecom", "Telecom Services"),
    "ASIANPAINT": ("Paint", "Decorative Paints"),
    "BERGEPAINT": ("Paint", "Decorative Paints"),
    "ULTRACEMCO": ("Cement", "Cement"),
    "AMBUJACEM": ("Cement", "Cement"),
    "SHREECEM": ("Cement", "Cement"),
    "SUNPHARMA": ("Healthcare", "Pharma"),
    "CIPLA": ("Healthcare", "Pharma"),
    "DRREDDY": ("Healthcare", "Pharma"),
    "DIVISLAB": ("Healthcare", "Pharma"),
    "APOLLOHOSP": ("Healthcare", "Hospitals"),
    "TITAN": ("Consumer Goods", "Lifestyle"),
    "NESTLEIND": ("Consumer Goods", "FMCG"),
    "HINDUNILVR": ("Consumer Goods", "FMCG"),
    "ITC": ("Consumer Goods", "FMCG"),
    "DABUR": ("Consumer Goods", "FMCG"),
    "BRITANNIA": ("Consumer Goods", "FMCG"),
    "MARUTI": ("Auto", "Passenger Vehicles"),
    "M&M": ("Auto", "Diversified Auto"),
    "TATAMOTORS": ("Auto", "Auto OEM"),
    "BAJAJ-AUTO": ("Auto", "Two Wheelers"),
    "HEROMOTOCO": ("Auto", "Two Wheelers"),
    "EICHERMOT": ("Auto", "Two Wheelers"),
    "LT": ("Infrastructure", "Engineering"),
    "ADANIPORTS": ("Ports", "Ports & Logistics"),
    "PIDILITIND": ("Consumer Goods", "Specialty Chemicals"),
}

SYMBOL_ALIASES = {
    "AGTL": "ATGL",
}


def read_raw_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, dtype=str)
    df = df.replace({"NULL": np.nan, "Null": np.nan, "null": np.nan, "": np.nan})
    df.columns = [col.strip().lower() for col in df.columns]
    return df


def rename_first_match(df: pd.DataFrame, target: str, candidates: list[str]) -> pd.DataFrame:
    for candidate in candidates:
        if candidate in df.columns:
            return df.rename(columns={candidate: target})
    return df


def to_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(
        series.astype(str).str.replace(",", "", regex=False).str.replace("%", "", regex=False),
        errors="coerce",
    )


def normalize_symbol_value(value: object) -> str:
    symbol = str(value).strip().upper()
    return SYMBOL_ALIASES.get(symbol, symbol)


def parse_year_label(value: object) -> dict[str, object]:
    raw = "" if pd.isna(value) else str(value).strip()
    if not raw:
        return {
            "year_label": None,
            "fiscal_year": None,
            "quarter": None,
            "is_ttm": False,
            "is_half_year": False,
            "sort_order": None,
        }
    if raw.upper() == "TTM":
        return {
            "year_label": "TTM",
            "fiscal_year": None,
            "quarter": "TTM",
            "is_ttm": True,
            "is_half_year": False,
            "sort_order": 999999,
        }

    decimal_match = re.fullmatch(r"(\d{4})\.5", raw)
    if decimal_match:
        year = int(decimal_match.group(1))
        return {
            "year_label": f"Sep {year}",
            "fiscal_year": year,
            "quarter": "Q2",
            "is_ttm": False,
            "is_half_year": False,
            "sort_order": year * 10 + 2,
        }

    match = re.match(r"(?P<mon>[A-Za-z]{3})[-\s]?(?P<year>\d{2,4})", raw)
    if match:
        mon = match.group("mon").title()
        year = int(match.group("year"))
        if year < 100:
            year += 2000
        quarter_map = {"Mar": "Q4", "Jun": "Q1", "Sep": "Q2", "Dec": "Q3"}
        is_half = (
            mon in {"Sep", "Mar"}
            and raw.lower().startswith(("sep", "mar"))
            and "half" in raw.lower()
        )
        return {
            "year_label": f"{mon} {year}",
            "fiscal_year": year,
            "quarter": quarter_map.get(mon),
            "is_ttm": False,
            "is_half_year": is_half,
            "sort_order": year * 10 + {"Jun": 1, "Sep": 2, "Dec": 3, "Mar": 4}.get(mon, 9),
        }

    if re.fullmatch(r"\d{4}", raw):
        year = int(raw)
        return {
            "year_label": f"Mar {year}",
            "fiscal_year": year,
            "quarter": "Q4",
            "is_ttm": False,
            "is_half_year": False,
            "sort_order": year * 10 + 4,
        }

    return {
        "year_label": raw,
        "fiscal_year": None,
        "quarter": None,
        "is_ttm": False,
        "is_half_year": False,
        "sort_order": None,
    }


def build_year_dimension(frames: list[pd.DataFrame]) -> pd.DataFrame:
    labels: dict[str, dict[str, object]] = {}
    for frame in frames:
        if "year" not in frame.columns:
            continue
        for value in frame["year"].dropna().unique():
            parsed = parse_year_label(value)
            if parsed["year_label"] and parsed["year_label"] not in labels:
                labels[parsed["year_label"]] = parsed

    year_df = pd.DataFrame(labels.values())
    if year_df.empty:
        return pd.DataFrame(
            columns=[
                "year_id",
                "year_label",
                "fiscal_year",
                "quarter",
                "is_ttm",
                "is_half_year",
                "sort_order",
            ]
        )
    year_df = year_df.sort_values(["sort_order", "year_label"], na_position="last").reset_index(
        drop=True
    )
    year_df["year_id"] = np.arange(1, len(year_df) + 1)
    return year_df[
        ["year_id", "year_label", "fiscal_year", "quarter", "is_ttm", "is_half_year", "sort_order"]
    ]


def attach_year_id(df: pd.DataFrame, dim_year: pd.DataFrame) -> pd.DataFrame:
    if "year" not in df.columns:
        return df
    parsed = df["year"].apply(parse_year_label).apply(pd.Series)
    df = pd.concat([df.drop(columns=["year"]), parsed], axis=1)
    df = df.merge(dim_year, on=["year_label"], how="left", suffixes=("", "_dim"))
    for col in ["fiscal_year", "quarter", "is_ttm", "is_half_year", "sort_order"]:
        dim_col = f"{col}_dim"
        if dim_col in df.columns:
            df[col] = df[dim_col].combine_first(df[col])
            df = df.drop(columns=[dim_col])
    return df


def normalize_companies(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = rename_first_match(df, "symbol", ["company_id", "symbol", "ticker", "id"])
    df = rename_first_match(df, "company_name", ["company_name", "name"])
    df = rename_first_match(df, "company_logo", ["company_logo", "logo", "company_logo_url"])
    df = rename_first_match(df, "nse_url", ["nse_url", "nse_profile", "nse_link"])
    df = rename_first_match(df, "bse_url", ["bse_url", "bse_profile", "bse_link"])
    df = rename_first_match(df, "about_company", ["about_company", "about"])
    df = rename_first_match(df, "roce", ["roce", "roce_pct", "roce_percentage"])
    df = rename_first_match(df, "roe", ["roe", "roe_pct", "roe_percentage"])
    for col in ["face_value", "book_value", "roce", "roe"]:
        if col in df.columns:
            df[col] = to_numeric(df[col])
    df["symbol"] = df["symbol"].apply(normalize_symbol_value)
    df["company_name"] = (
        df["company_name"].astype(str).str.replace(r"[\r\n]+", " ", regex=True).str.strip()
    )
    mapping_rows = []
    sectors = []
    subsectors = []
    for symbol in df["symbol"]:
        sector, sub_sector = SECTOR_DEFAULTS.get(symbol, ("Other", "Other"))
        sectors.append(sector)
        subsectors.append(sub_sector)
        mapping_rows.append({"symbol": symbol, "sector": sector, "sub_sector": sub_sector})
    df["sector"] = sectors
    df["sub_sector"] = subsectors
    mapping_df = pd.DataFrame(mapping_rows).drop_duplicates().sort_values("symbol")
    keep = [
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
    ]
    return df[[col for col in keep if col in df.columns]].drop_duplicates("symbol"), mapping_df


def normalize_profit_loss(
    df: pd.DataFrame, dim_year: pd.DataFrame, total_assets_map: pd.DataFrame | None
) -> pd.DataFrame:
    df = rename_first_match(df, "symbol", ["company_id", "symbol", "ticker"])
    df = rename_first_match(df, "opm_pct", ["opm_pct", "opm_percentage"])
    df = rename_first_match(df, "tax_pct", ["tax_pct", "tax_percentage"])
    df = rename_first_match(df, "dividend_payout_pct", ["dividend_payout_pct", "dividend_payout"])
    value_cols = [
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
    ]
    for col in value_cols:
        if col in df.columns:
            df[col] = to_numeric(df[col])
    df["symbol"] = df["symbol"].apply(normalize_symbol_value)
    df = attach_year_id(df, dim_year)
    if total_assets_map is not None:
        df = df.merge(total_assets_map, on=["symbol", "year_id"], how="left")
    df["net_profit_margin_pct"] = np.where(
        df["sales"] > 0, df["net_profit"] / df["sales"] * 100, np.nan
    )
    df["expense_ratio_pct"] = np.where(df["sales"] > 0, df["expenses"] / df["sales"] * 100, np.nan)
    df["interest_coverage"] = np.where(
        df["interest"] > 0, df["operating_profit"] / df["interest"], np.nan
    )
    df["asset_turnover"] = np.where(
        df["total_assets"] > 0, df["sales"] / df["total_assets"], np.nan
    )
    df["return_on_assets"] = np.where(
        df["total_assets"] > 0, df["net_profit"] / df["total_assets"] * 100, np.nan
    )
    keep = [
        "symbol",
        "year_id",
        "year_label",
        "sort_order",
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
    ]
    out = df[[col for col in keep if col in df.columns]]
    return out.drop_duplicates(subset=["symbol", "year_id"], keep="first")


def normalize_balance_sheet(
    df: pd.DataFrame, dim_year: pd.DataFrame, companies: pd.DataFrame
) -> pd.DataFrame:
    df = rename_first_match(df, "symbol", ["company_id", "symbol", "ticker"])
    df = rename_first_match(df, "other_assets", ["other_assets", "other_asset"])
    value_cols = [
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
    ]
    for col in value_cols:
        if col in df.columns:
            df[col] = to_numeric(df[col])
    df["symbol"] = df["symbol"].apply(normalize_symbol_value)
    df = attach_year_id(df, dim_year)
    df = df.merge(companies[["symbol", "face_value"]], on="symbol", how="left")
    net_worth = df["equity_capital"].fillna(0) + df["reserves"].fillna(0)
    shares_outstanding = np.where(
        df["face_value"] > 0, df["equity_capital"] / df["face_value"], np.nan
    )
    df["debt_to_equity"] = np.where(net_worth > 0, df["borrowings"] / net_worth, np.nan)
    df["equity_ratio"] = np.where(df["total_assets"] > 0, net_worth / df["total_assets"], np.nan)
    df["book_value_per_share"] = np.where(
        shares_outstanding > 0, net_worth / shares_outstanding, np.nan
    )
    keep = [
        "symbol",
        "year_id",
        "year_label",
        "sort_order",
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
    ]
    out = df[[col for col in keep if col in df.columns]]
    return out.drop_duplicates(subset=["symbol", "year_id"], keep="first")


def normalize_cash_flow(
    df: pd.DataFrame, dim_year: pd.DataFrame, net_profit_map: pd.DataFrame | None
) -> pd.DataFrame:
    df = rename_first_match(df, "symbol", ["company_id", "symbol", "ticker"])
    value_cols = ["operating_activity", "investing_activity", "financing_activity", "net_cash_flow"]
    for col in value_cols:
        if col in df.columns:
            df[col] = to_numeric(df[col])
    df["symbol"] = df["symbol"].apply(normalize_symbol_value)
    df = attach_year_id(df, dim_year)
    if net_profit_map is not None:
        df = df.merge(net_profit_map, on=["symbol", "year_id"], how="left")
    df["free_cash_flow"] = df["operating_activity"].fillna(0) + df["investing_activity"].fillna(0)
    df["cash_conversion_ratio"] = np.where(
        df["net_profit"] != 0, df["operating_activity"] / df["net_profit"], np.nan
    )
    keep = [
        "symbol",
        "year_id",
        "year_label",
        "sort_order",
        "operating_activity",
        "investing_activity",
        "financing_activity",
        "net_cash_flow",
        "free_cash_flow",
        "cash_conversion_ratio",
    ]
    out = df[[col for col in keep if col in df.columns]]
    return out.drop_duplicates(subset=["symbol", "year_id"], keep="first")


def normalize_analysis(df: pd.DataFrame) -> pd.DataFrame:
    df = rename_first_match(df, "symbol", ["company_id", "symbol", "ticker"])
    df["symbol"] = df["symbol"].apply(normalize_symbol_value)
    metric_aliases = {
        "compounded_sales_growth": "compounded_sales_growth_pct",
        "compounded_profit_growth": "compounded_profit_growth_pct",
        "stock_price_cagr": "stock_price_cagr_pct",
        "roe": "roe_pct",
    }
    for source, target in metric_aliases.items():
        if source in df.columns:
            df[target] = (
                df[source].astype(str).str.extract(r"([-+]?\d+(?:\.\d+)?)").iloc[:, 0].astype(float)
            )
    if "period_label" not in df.columns:
        if "period" in df.columns:
            period_source = df["period"].astype(str)
        else:
            period_source = df["compounded_sales_growth"].astype(str).fillna("")
        extracted = period_source.str.extract(r"(?i)(10|5|3)\s*years?")[0]
        df["period_label"] = extracted.map({"10": "10Y", "5": "5Y", "3": "3Y"})
        df.loc[period_source.str.contains("TTM", case=False, na=False), "period_label"] = "TTM"
    keep = [
        "symbol",
        "period_label",
        "compounded_sales_growth_pct",
        "compounded_profit_growth_pct",
        "stock_price_cagr_pct",
        "roe_pct",
    ]
    return (
        df[[col for col in keep if col in df.columns]]
        .dropna(subset=["symbol", "period_label"])
        .drop_duplicates()
    )


def normalize_pros_cons(df: pd.DataFrame) -> pd.DataFrame:
    df = rename_first_match(df, "symbol", ["company_id", "symbol", "ticker"])
    df["symbol"] = df["symbol"].apply(normalize_symbol_value)
    rows = []
    for _, row in df.iterrows():
        for is_pro, source_col in [(True, "pros"), (False, "cons")]:
            if source_col not in df.columns or pd.isna(row.get(source_col)):
                continue
            parts = [
                item.strip(" -")
                for item in re.split(r"\r?\n|;|[|]", str(row[source_col]))
                if item.strip()
            ]
            for text in parts:
                rows.append(
                    {
                        "symbol": row["symbol"],
                        "is_pro": is_pro,
                        "category": row.get("category"),
                        "text": text,
                        "source": "MANUAL",
                        "confidence": 100.0,
                        "generated_at": pd.NaT,
                    }
                )
    return pd.DataFrame(rows)


def normalize_documents(df: pd.DataFrame) -> pd.DataFrame:
    df = rename_first_match(df, "symbol", ["company_id", "symbol", "ticker"])
    df = rename_first_match(
        df, "document_url", ["document_url", "annual_report_url", "annual_report", "url"]
    )
    df["symbol"] = df["symbol"].apply(normalize_symbol_value)
    if "year" in df.columns:
        df["year_label"] = df["year"].apply(lambda value: parse_year_label(value)["year_label"])
    elif "year_label" not in df.columns:
        df["year_label"] = np.nan
    out = df[[col for col in ["symbol", "year_label", "document_url"] if col in df.columns]].dropna(
        subset=["symbol", "document_url"]
    )
    return out.drop_duplicates()


def build_dim_sector(mapping_df: pd.DataFrame) -> pd.DataFrame:
    sectors = mapping_df[["sector"]].drop_duplicates().sort_values("sector").reset_index(drop=True)
    sectors["sector_id"] = np.arange(1, len(sectors) + 1)
    sectors["sector_code"] = (
        sectors["sector"].str.upper().str.replace(r"[^A-Z0-9]+", "_", regex=True).str.strip("_")
    )
    sectors["description"] = sectors["sector"] + " sector"
    sectors = sectors.rename(columns={"sector": "sector_name"})
    return sectors[["sector_id", "sector_name", "sector_code", "description"]]


def run(raw_dir: Path, clean_dir: Path) -> None:
    clean_dir.mkdir(parents=True, exist_ok=True)
    raw_frames = {
        name: read_raw_csv(raw_dir / filename)
        for name, filename in RAW_FILES.items()
        if (raw_dir / filename).exists()
    }

    if "companies" not in raw_frames:
        raise FileNotFoundError(
            "companies.csv is required in data/raw. Run 01_extract_from_mysql.py first."
        )

    year_sources = [
        raw_frames[name]
        for name in ["balancesheet", "profitandloss", "cashflow"]
        if name in raw_frames
    ]
    dim_year = build_year_dimension(year_sources)
    companies, sector_mapping = normalize_companies(raw_frames["companies"])
    all_symbols = set(companies["symbol"])
    for name, frame in raw_frames.items():
        symbol_col = (
            "company_id"
            if "company_id" in frame.columns
            else "id" if name == "companies" and "id" in frame.columns else None
        )
        if symbol_col:
            all_symbols |= set(frame[symbol_col].dropna().apply(normalize_symbol_value))
    missing_symbols = sorted(all_symbols - set(companies["symbol"]))
    if missing_symbols:
        stub_rows = []
        stub_mapping = []
        for symbol in missing_symbols:
            sector, sub_sector = SECTOR_DEFAULTS.get(symbol, ("Other", "Other"))
            stub_rows.append(
                {
                    "symbol": symbol,
                    "company_name": symbol,
                    "sector": sector,
                    "sub_sector": sub_sector,
                    "company_logo": np.nan,
                    "website": np.nan,
                    "nse_url": np.nan,
                    "bse_url": np.nan,
                    "face_value": np.nan,
                    "book_value": np.nan,
                    "about_company": np.nan,
                    "roce": np.nan,
                    "roe": np.nan,
                }
            )
            stub_mapping.append({"symbol": symbol, "sector": sector, "sub_sector": sub_sector})
        companies = pd.concat([companies, pd.DataFrame(stub_rows)], ignore_index=True)
        sector_mapping = pd.concat(
            [sector_mapping, pd.DataFrame(stub_mapping)], ignore_index=True
        ).drop_duplicates("symbol")
    companies = companies.drop_duplicates("symbol").sort_values("symbol").reset_index(drop=True)
    sector_mapping = (
        sector_mapping.drop_duplicates("symbol").sort_values("symbol").reset_index(drop=True)
    )
    dim_sector = build_dim_sector(sector_mapping)

    balance_sheet = (
        normalize_balance_sheet(raw_frames.get("balancesheet", pd.DataFrame()), dim_year, companies)
        if "balancesheet" in raw_frames
        else pd.DataFrame()
    )
    total_assets_map = (
        balance_sheet[["symbol", "year_id", "total_assets"]] if not balance_sheet.empty else None
    )
    profit_loss = (
        normalize_profit_loss(
            raw_frames.get("profitandloss", pd.DataFrame()), dim_year, total_assets_map
        )
        if "profitandloss" in raw_frames
        else pd.DataFrame()
    )
    net_profit_map = (
        profit_loss[["symbol", "year_id", "net_profit"]] if not profit_loss.empty else None
    )
    cash_flow = (
        normalize_cash_flow(raw_frames.get("cashflow", pd.DataFrame()), dim_year, net_profit_map)
        if "cashflow" in raw_frames
        else pd.DataFrame()
    )
    analysis = (
        normalize_analysis(raw_frames.get("analysis", pd.DataFrame()))
        if "analysis" in raw_frames
        else pd.DataFrame()
    )
    pros_cons = (
        normalize_pros_cons(raw_frames.get("prosandcons", pd.DataFrame()))
        if "prosandcons" in raw_frames
        else pd.DataFrame()
    )
    documents = (
        normalize_documents(raw_frames.get("documents", pd.DataFrame()))
        if "documents" in raw_frames
        else pd.DataFrame()
    )

    outputs = {
        "dim_company.csv": companies,
        "dim_year.csv": dim_year,
        "dim_sector.csv": dim_sector,
        "sector_mapping.csv": sector_mapping,
        "fact_balance_sheet.csv": balance_sheet,
        "fact_profit_loss.csv": profit_loss,
        "fact_cash_flow.csv": cash_flow,
        "fact_analysis.csv": analysis,
        "fact_pros_cons.csv": pros_cons,
        "documents.csv": documents,
    }
    for filename, frame in outputs.items():
        frame.to_csv(clean_dir / filename, index=False)
        print(f"{filename:24s} rows={len(frame):5d}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", default="data/raw", help="Folder containing extracted raw CSVs")
    parser.add_argument("--out", default="data/clean", help="Folder for cleaned warehouse CSVs")
    args = parser.parse_args()
    run(Path(args.raw), Path(args.out))
