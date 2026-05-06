# NIFTY 100 Financial Analytics System

Full data pipeline: raw xlsx → clean CSVs → PostgreSQL star schema → financial metrics → REST API → Power BI dashboard.

---

## Project Structure

```
nifty100/
├── data/
│   ├── raw/               ← place your 7 xlsx files here
│   └── clean/             ← auto-generated clean CSVs + metrics.csv
├── etl/
│   ├── 01_clean_raw_data.py    Phase 1: clean & transform
│   ├── 03_load_to_db.py        Phase 3: load into PostgreSQL
│   └── 04_compute_metrics.py   Phase 4: compute all KPIs
├── sql/
│   ├── 02_schema.sql           Phase 2: PostgreSQL star schema DDL
│   └── powerbi_setup.sql       Power BI views + DAX reference
├── api/                        Phase 5: Django REST API
│   ├── nifty100_project/
│   │   ├── settings.py
│   │   └── urls.py
│   └── core/
│       ├── models.py
│       ├── serializers.py
│       ├── views.py
│       └── urls.py
├── dashboards/
│   └── powerbi_setup.sql
└── requirements.txt
```

---

## Prerequisites

- Python 3.10+
- PostgreSQL 14+
- Power BI Desktop (Windows, free)

---

## Step-by-Step Run Guide

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

---

### 2. Phase 1 — Clean raw data

Copy your 7 xlsx files into `data/raw/`, then run:

```bash
python etl/01_clean_raw_data.py --src data/raw --out data/clean
```

Output: 7 clean CSVs in `data/clean/`

---

### 3. Phase 2 — Create PostgreSQL schema

```bash
# Create the database
psql -U postgres -c "CREATE DATABASE nifty100_dw;"

# Run the DDL
psql -U postgres -d nifty100_dw -f sql/02_schema.sql
```

---

### 4. Phase 3 — Load data into PostgreSQL

```bash
python etl/03_load_to_db.py \
  --clean data/clean \
  --db postgresql://postgres:password@localhost:5432/nifty100_dw
```

---

### 5. Phase 4 — Compute financial metrics

```bash
python etl/04_compute_metrics.py --clean data/clean --out data/clean/metrics.csv
```

Output: `data/clean/metrics.csv` with 33 KPI columns for 1,551 company-year rows.

---

### 6. Phase 5 — Run the Django API

```bash
cd api

# Set env vars (or edit settings.py directly for dev)
export DB_NAME=nifty100_dw
export DB_USER=postgres
export DB_PASSWORD=password
export DJANGO_SECRET_KEY=your-secret-key

# Install Django dependencies
pip install django djangorestframework django-filter django-cors-headers

# Start server
python manage.py runserver
```

---

## API Endpoints

| Method | URL | Description |
|--------|-----|-------------|
| GET | `/api/companies/` | List all 92 companies |
| GET | `/api/companies/HDFCBANK/` | Full profile + docs + pros/cons |
| GET | `/api/financials/profit-loss/?company_id=TCS` | P&L history |
| GET | `/api/financials/balance-sheet/?company_id=TCS` | Balance sheet history |
| GET | `/api/financials/cash-flow/?company_id=TCS` | Cash flow history |
| GET | `/api/metrics/?company_id=INFY&ordering=-roce_pct` | DB-backed KPIs |
| GET | `/api/metrics/csv/?company_id=ABB` | CSV-backed KPIs (no DB needed) |
| GET | `/api/snapshot/RELIANCE/` | One-call full snapshot with trend |
| GET | `/api/top/?metric=net_profit_margin_pct&limit=10` | Top 10 companies by metric |

### Example curl calls

```bash
# Top 10 companies by EBITDA margin
curl "http://localhost:8000/api/top/?metric=ebitda_margin_pct&limit=10"

# Full snapshot for TCS
curl "http://localhost:8000/api/snapshot/TCS/"

# HDFC Bank P&L history, sorted by year
curl "http://localhost:8000/api/financials/profit-loss/?company_id=HDFCBANK&ordering=date_key"

# All companies sorted by ROE descending
curl "http://localhost:8000/api/companies/?ordering=-roe_pct"
```

---

## Power BI Connection

1. Open Power BI Desktop → **Get Data** → **PostgreSQL**
2. Server: `localhost`, Database: `nifty100_dw`
3. Import these views:
   - `dw.vw_powerbi_flat` — main fact table
   - `dw.vw_powerbi_latest` — KPI cards
   - `dw.dim_company` — company slicer
4. Copy DAX measures from `dashboards/powerbi_setup.sql`
5. Build pages as described in the dashboard layout section

---

## Key Financial Metrics Computed

| Category | Metric | Formula |
|----------|--------|---------|
| Profitability | Net Profit Margin | `net_profit / sales × 100` |
| Profitability | EBITDA Margin | `(operating_profit + depreciation) / sales × 100` |
| Profitability | OPM % | from raw data |
| Profitability | ROE | `net_profit / net_worth × 100` |
| Profitability | ROCE | `EBIT / capital_employed × 100` |
| Leverage | Debt-to-Equity | `borrowings / net_worth` |
| Leverage | Interest Coverage | `EBITDA / interest` |
| Leverage | Debt-to-Assets | `borrowings / total_assets` |
| Liquidity | Free Cash Flow | `operating_CF + investing_CF` |
| Liquidity | Operating Cash Ratio | `operating_CF / sales` |
| Liquidity | Capex Intensity | `|investing_CF| / sales × 100` |
| Growth | Sales CAGR 3Y/5Y | Rolling window CAGR |
| Growth | Profit CAGR 3Y/5Y | Rolling window CAGR |
| Growth | YoY Sales/Profit | `pct_change()` |
| Valuation | EPS | from raw data |
| Valuation | Dividend Payout % | from raw data |

---

## Data Coverage

| File | Table | Rows | Companies |
|------|-------|------|-----------|
| companies.xlsx | dim_company | 92 | 92 |
| profitandloss.xlsx | fact_profit_loss | 1,276 | ~90 |
| balancesheet.xlsx | fact_balance_sheet | 1,312 | ~90 |
| cashflow.xlsx | fact_cash_flow | 1,187 | ~88 |
| documents.xlsx | dim_documents | 1,585 | 92 |
| prosandcons.xlsx | dim_pros_cons | 16 | 8 |
| analysis.xlsx | (unpivoted) | 80 | 20 |
