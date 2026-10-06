# Marketplace Analytics

Load the [Olist dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
into PostgreSQL, build analytics views with dbt v2, and run a FastAPI service.
The API provides seller, category, and state metrics, with interactive contracts
at `/docs`. Remaining release work lives in [TODO.md](TODO.md).

## How it works

```text
CSV files → Python/Polars validation → PostgreSQL raw tables
                                     → dbt silver views → analytics views
FastAPI → analytics queries → JSON metrics
```

Two services: PostgreSQL 16 stores the data; the Python 3.12 app runs ingestion,
dbt, and FastAPI. uv locks the Python packages and the official dbt v2 binary
(currently 2.0.6). No separate transformation service or ORM is needed.

- `raw`: nine typed source tables. Python normalizes headers and parses numbers;
  PostgreSQL parses timestamps and validates enums. Source strings and every
  review/payment record are retained. Keep the original CSVs in `data/raw/`.
- `silver`: six views clean order/item identifiers, normalize category mappings,
  and aggregate items, reviews, and payments by order.
- `analytics`: three cleaned, deterministically deduplicated dimensions, two facts,
  and three business marts, all views. Order/item duplicates fail dbt tests.
  Missing dimensions are allowed.

## Run with Docker Compose

Copy `.env.example` to `.env`, set local credentials, and download these files
into `data/raw/`:

```text
olist_orders_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_customers_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
olist_geolocation_dataset.csv
```

```bash
cp .env.example .env                  # Edit credentials before starting.
docker compose up --build -d
docker compose exec app uv run --locked python -m app.etl.pipeline
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl 'http://localhost:8000/sellers/top?limit=10'
```

Compose connects the app to `db:5432`; host commands use `POSTGRES_HOST` and the
published `POSTGRES_PORT` in `.env`. Database files persist in `postgres_data`.
Use `docker compose down` to stop services; adding `-v` deletes the database.
Python edits reload automatically. Rebuild after dependency or Dockerfile changes.
The container environment lives in `/opt/venv` so the `/app` bind mount cannot hide it.

## Run locally

Install [uv](https://docs.astral.sh/uv/) and the native PostgreSQL client library
required by dbt v2 (`libpq.so.5` on Linux). The image already includes it.

```bash
# Debian/Ubuntu:
sudo apt-get install libpq5
# Arch/CachyOS:
sudo pacman -S --needed postgresql-libs
# macOS:
brew install libpq
```

For macOS, make Homebrew's libpq library directory available to the dynamic loader
if it is outside its default search paths. Install PostgreSQL client libraries
for your platform when using Windows.

```bash
uv sync --locked
uv run --locked dbt --version        # Must be >=2.0.0; project rejects v1.
uv run --locked python -m app.etl.pipeline
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start PostgreSQL first, using Compose or your own instance. The pipeline checks
connectivity, applies `app/db/schema.sql`, reads and validates all nine CSVs,
reloads raw tables, applies `app/db/indexes.sql`, then runs `dbt build`.
Missing columns, negative money, or invalid review scores stop loading. Duplicate
keys, reversed delivery dates, sparse columns, and empty CSVs produce warnings.

Each table reload is one transaction: a failed insert restores its previous
contents. Tables commit separately, and dbt commits models separately. A failed
refresh can leave earlier tables/models updated. Run a successful full build
before consuming refreshed analytics.

## dbt commands and editor

The wrapper loads the repository `.env`, validates connection settings, and
runs the dbt v2 binary installed in the active Python environment:

```bash
uv run --locked python -m app.etl.transform debug
uv run --locked python -m app.etl.transform build
uv run --locked python -m app.etl.transform test
uv run --locked python -m app.etl.transform docs generate
uv run --locked python -m app.etl.transform docs serve --port 8080
```

Run the same commands after `docker compose exec app` inside the container.
For the direct CLI, run from the repository root:

```bash
uv run --locked dbt build --project-dir dbt --profiles-dir dbt
```

PostgreSQL is experimental in dbt v2. `.env.example` and the image enable
`DBT_ALLOW_EXPERIMENTAL_ADAPTERS=true`. The profile uses environment variables;
exported values override `.env`. Schemas use the exact names `silver` and
`analytics`; use a separate database for each environment/developer.

The [dbt extension](https://docs.getdbt.com/docs/configure-dbt-extension#about-env-file-support)
reads `.env` from its project directory. On Linux/macOS, share the root file:

```bash
ln -s ../.env dbt/.env                # Run once, if the link does not exist.
```

On Windows, create a corresponding file link or configure `dbt.environmentVariables`
in local editor settings. Select `.venv` as the Python interpreter and run
**Developer: Reload Window**. Credentials and generated `dbt/target`, `dbt/logs`,
and `dbt/dbt_packages` files are ignored. The `.env` paths are excluded from image builds.

## Metrics

| View | Grain |
| --- | --- |
| `dim_customers`, `dim_products`, `dim_sellers` | customer, product, seller |
| `fact_orders` | order |
| `fact_order_items` | order + item |
| `mart_seller_performance` | seller |
| `mart_category_performance` | category |
| `mart_geography_sales` | customer state + city |

All views are in `analytics`. Facts retain every order status. Sales marts include
only delivered orders with items.

| Metric | Definition |
| --- | --- |
| `total_orders` | Distinct delivered orders in the group |
| `total_items_sold` | Item rows in those orders and the seller/category |
| `total_revenue` | Sum of item prices, excluding freight |
| Seller `avg_order_value`, `avg_freight_value` | Mean seller/order price and freight totals |
| Category `avg_price` | Mean non-null item price, weighted by item |
| Geography `avg_ticket` | Mean full order price + freight |
| `avg_review_score` | Mean of per-order mean non-null review scores, weighted equally by reviewed order |
| Seller `avg_delivery_delay_days` | Mean signed fractional delay, weighted by eligible seller/order |
| `late_delivery_rate` | Late / eligible orders, weighted by seller/order or category/order |

Delivery eligibility requires delivered status and both actual/estimated
timestamps; no eligible outcomes yields NULL. Missing reviews do not remove sales.
Category labels prefer English, fall back to Portuguese, then `unknown` for
missing products/categories. Seller/geography marts exclude unmatched sellers/customers.
Multi-seller/category order counts are not globally additive. Money and averages
are rounded to two decimals; rates are fractions rounded to four decimals.
Whole-order payment totals repeat on item rows and must not be summed across items.

## Business API

| GET endpoint | Result |
| --- | --- |
| `/sellers/top?limit=10` | Seller metrics ranked by delivered item revenue |
| `/sellers/{seller_id}/performance` | The same metrics for one seller |
| `/categories/performance?limit=100` | Category metrics ranked by delivered item revenue |
| `/geography/states?limit=100` | Customer state metrics ranked by delivered item revenue |
| `/health` | Application liveness, without a database query |
| `/ready` | Database connectivity and query access to the business sources |

Lists accept an integer `limit` from 1 through 100; invalid values return 422.
Revenue ties break by seller ID, category name, or state (NULL states last).
An empty list returns `[]`. Seller IDs accept 1–32 characters; a seller absent
from the delivered-sales mart returns 404, including sellers without delivered
items. All caller values use SQL bind parameters. Database failures or unbuilt
analytics return 503 with `{"detail":"Database analytics unavailable"}`.
Empty but queryable views pass readiness.

Decimal metrics serialize as JSON strings, preserving database precision and
scale, for example `"235.00"` revenue or `"0.5000"` late-delivery rate. Counts
are JSON integers; SQL NULL values remain JSON `null`, including missing
reviews, ineligible delivery outcomes, and missing locations. `/openapi.json`
specifies response fields, nullability, input bounds, and error responses.

State results use matched customer orders with delivered items, including a
NULL-state group. Revenue excludes freight; `avg_ticket` averages full order
price plus freight, and `avg_review_score` averages reviewed orders equally.
These metrics are calculated from order facts and order item totals, rather
than averaging the city mart's rounded averages.

Endpoint review: these routes cover seller ranking and investigation, category
mix, and regional sales. No additional business endpoint has a current consumer.
Add a global summary when a dashboard needs it; its distinct order counts must
come from facts because seller/category counts overlap.

When upgrading an existing database, rebuild first, then remove the obsolete
`silver.customers`, `silver.products`, and `silver.sellers` views. The gold
dimensions now clean their raw sources directly; dbt does not delete old views.

## Checks

```bash
uv run --locked pytest -q
# Include the dbt metric regression using an empty disposable database:
METRICS_TEST_DATABASE_URL=postgresql://user:password@localhost:5432/metrics_test \
  uv run --locked pytest -q
```

The regression refuses existing `raw`, `silver`, or `analytics` schemas, loads
synthetic edge cases, repeats builds, checks exact KPIs/schema names/lineage,
and verifies a duplicate-item failure. It also checks HTTP results against real
views, readiness before/after dbt, and state averages across unequal city and
review counts. It drops its own schemas on exit. The database-free HTTP check
uses Uvicorn and Python's HTTP client to verify serialization, input validation,
parameter binding, empty results, 404/503 responses, and OpenAPI contracts.
Without the test URL it skips explicitly. The 45 dbt tests check grains,
nonempty facts, bounds, and independent source-revenue reconciliation.

## Files

- `app/core`: environment settings, cached database engine, SQL runner.
- `app/etl`: CSV mapping, extraction, validation, loading, pipeline, dbt wrapper.
- `app/db`: raw DDL and indexes.
- `dbt`: source/model SQL, descriptions, macros, and data tests.
- `tests`: Python checks and the PostgreSQL metric regression.
- `scripts`: manual SQL initialization and analytics row-count checks.

Write SQL in lowercase, preserving case-sensitive string literals and quoted identifiers.

Full reloads and ordinary views are sufficient for this dataset. Add incremental
loads or materialization when measured load/query costs justify them.
