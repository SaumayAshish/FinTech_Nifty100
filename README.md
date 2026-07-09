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

## API Access

All `/api/` endpoints are public and read-only (NIFTY 100 company financials,
no per-user data), so there is no authentication layer. Anonymous requests
are rate-limited (`API_ANON_THROTTLE_RATE`, default `120/min`) to guard
against scraping/abuse.

## Local Setup

### Install dependencies

```powershell
pip install -r n100/nifty100/requirements.txt
```

### Configure environment

```powershell
cd n100/nifty100/api
copy .env.example .env
```

See `.env.example` for all supported variables (Django secret/debug/hosts,
Postgres connection, admin bootstrap, throttle rate). By default the API
uses SQLite. To use PostgreSQL instead, set `USE_POSTGRES=true` plus
`DB_NAME`/`DB_USER`/`DB_PASSWORD`/`DB_HOST`/`DB_PORT`.

### Run the Django API

```powershell
cd n100/nifty100/api
python manage.py runserver
```

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

## Running with Docker

`n100/nifty100/docker-compose.yml` runs the API against a real Postgres
container, loading `sql/02_schema.sql` on first start:

```powershell
cd n100/nifty100
docker compose up --build
```

The API is served at `http://localhost:8000/api/`. This brings up the
warehouse schema only — it does not run the ETL pipeline or copy `data/`
into the image, so endpoints backed by flat CSVs (`/api/metrics/csv/`,
`/api/snapshot/<symbol>/`) will return 503 until ETL output is provided
separately. Override any variable in `docker-compose.yml`'s `environment:`
blocks via a `.env` file in `n100/nifty100/` (e.g. `DJANGO_SECRET_KEY`,
`DB_PASSWORD`).

## Notes

- The repository currently contains source datasets and some generated artifacts for convenience.
