# Fintech Nifty100

Financial analytics project for NIFTY 100 company data with ETL pipelines, a Django REST API, and a Power BI dashboard.

## Repository Layout

`n100/nifty100/`
Core project folder containing ETL scripts, SQL schema/view scripts, cleaned data, API code, and Python dependencies.

`BluestockNifty100.pbix`
Power BI Desktop report file.

`Assets/BlueStock_Analytics_Final.png`
Dashboard screenshot for documentation/submission use.

## Main Components

### ETL

Located in `n100/nifty100/etl/`.

- `01_extract_from_xlsx.py`
- `02_clean_and_transform.py`
- `03_load_to_warehouse.py`
- `04_compute_metrics.py`

### Database

Located in `n100/nifty100/sql/`.

- `02_schema.sql` creates the warehouse tables.
- `powerbi_setup.sql` creates Power BI helper views:
  - `vw_powerbi_financials`
  - `vw_powerbi_latest`

### API

Located in `n100/nifty100/api/`.

Base routes are exposed under `/api/`:

- `/api/companies/`
- `/api/companies/<symbol>/`
- `/api/financials/profit-loss/`
- `/api/financials/balance-sheet/`
- `/api/financials/cash-flow/`
- `/api/analysis/`
- `/api/ml-scores/`
- `/api/metrics/csv/`
- `/api/snapshot/<symbol>/`

## Local Setup

### Install dependencies

```powershell
pip install -r n100/nifty100/requirements.txt
```

### Run the Django API

```powershell
cd n100/nifty100/api
python manage.py runserver
```

By default the API uses SQLite. To use PostgreSQL instead, set:

- `USE_POSTGRES=true`
- `DB_NAME`
- `DB_USER`
- `DB_PASSWORD`
- `DB_HOST`
- `DB_PORT`

## Power BI Dashboard

The Power BI report file is `BluestockNifty100.pbix`.

If the report should read from PostgreSQL, first apply:

```powershell
psql -U postgres -d nifty100_dw -f n100/nifty100/sql/02_schema.sql
psql -U postgres -d nifty100_dw -f n100/nifty100/sql/powerbi_setup.sql
```

Then open `BluestockNifty100.pbix` in Power BI Desktop and connect it to the same database used by the warehouse.

Expected Power BI helper views:

- `vw_powerbi_financials`
- `vw_powerbi_latest`

Reference screenshot:

- `Assets/BlueStock_Analytics_Final.png`

## Notes

- The repository currently contains source datasets and some generated artifacts for convenience.
- `extracted_files/` is reference material and not part of the active app path.
