# Marketplace Analytics

[![CI](https://github.com/josoriov/marketplace-analytics/actions/workflows/ci.yml/badge.svg)](https://github.com/josoriov/marketplace-analytics/actions/workflows/ci.yml)

A local analytics engineering project built on the
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
Python ingests and validates nine CSVs, dbt v2 builds a PostgreSQL warehouse,
and FastAPI exposes seller, category, and regional sales metrics.

The implementation combines Python 3.12, Polars, PostgreSQL 16, dbt, and uv.
The examples below come from the supplied historical dataset; the API serves
those analytics after a local refresh.

## Architecture

```mermaid
flowchart LR
    csv[Olist CSVs] --> etl[Python / Polars ETL]
    etl --> raw[raw tables]
    raw --> silver[silver views]
    silver --> analytics[analytics views]
    raw -->|dimensions| analytics
    etl -->|dbt build| dbt[dbt v2]
    dbt -->|build and test| silver
    dbt -->|build and test| analytics
    client[API consumer] -->|HTTP / JSON| api[FastAPI]
    api -->|SQL| analytics
```

[Interactive architecture diagram](docs/architecture/marketplace-analytics.html)
— open the downloaded HTML in a browser for source links, themes, and image exports.
The [diagram specification](docs/architecture/marketplace-analytics.architecture.json)
and [model lineage](docs/lineage.md) are included.

Two Compose services run the project: PostgreSQL stores the data, and the Python
app runs ingestion, dbt, and FastAPI. uv locks the Python packages and official
dbt v2 binary (2.0.6).

- **Raw:** nine typed tables retain source strings and every review/payment
  record. Python normalizes headers and parses numbers; PostgreSQL parses
  timestamps and validates enums.
- **Silver:** six views clean identifiers and category mappings, then aggregate
  items, reviews, and payments by order.
- **Analytics:** three deterministically deduplicated dimensions, two facts, and
  three business marts, all views. Duplicate order/item keys fail dbt tests;
  missing dimensions are allowed. Geolocation is loaded but unused by the models.

## Repository Layout

| Path | Description |
| --- | --- |
| `app/core/` | Environment settings, cached database engine, and SQL runner |
| `app/etl/` | CSV extraction, validation, transactional loading, and dbt wrapper |
| `app/db/` | Raw PostgreSQL schema and indexes |
| `app/main.py` | Business endpoints, liveness, and database readiness |
| `dbt/` | Sources, models, metric descriptions, and data tests |
| `tests/` | Python checks, HTTP contracts, and PostgreSQL metric regression |
| `scripts/` | Manual database checks and exploratory notebook |
| `docs/` | Findings, query plans, vulnerability evidence, and release verification |
| `docs/architecture/` | Interactive diagram, source specification, and validation receipt |
| `data/raw/` | Downloaded Olist CSVs; ignored by Git |

## Current Status

| Component | Status |
| --- | --- |
| Ingestion and warehouse | **Verified locally** — two full refreshes, 14 views, and 45 dbt tests per run |
| Business API | **Complete** — seller, category, and state metrics with documented HTTP contracts |
| Python checks | **Passing locally** — 42 tests with disposable PostgreSQL; 41 pass and one skips without it |
| Compose workflow | **Verified with Podman** — Docker Compose itself remains unverified locally |
| GitHub Actions | **Configured** — lint and PostgreSQL regression; first hosted run pending |
| Container scan | **Known findings** — 0 critical and 44 high package findings across 8 high-severity CVEs |

See the [release verification log](docs/release-readiness.md),
[image scan](docs/security-scan.md), and [TODO.md](TODO.md) for evidence and limits.
This is a local development setup: ports bind to localhost, the app runs as root
inside the container, and ingestion and API queries share the database owner.

## Example Results

Recorded on 2026-10-07 using the full Olist dataset:

- **Delivered sales:** 96,478 orders with items, 110,197 item rows, and
  13,221,498.11 in item revenue excluding freight.
- **Seller mix:** the top 10 of 2,970 sellers account for **13.27%** of delivered
  item revenue. Seller revenues are additive; seller order counts overlap.
- **Delivery and reviews:** **8.11%** of eligible orders arrived late. Among
  reviewed eligible orders, late deliveries average **2.57/5**, compared with
  **4.29/5** for on-time deliveries. This is an association, not a causal result.

[Example queries, assumptions, and API output](docs/analytics.md) explain how
these results were calculated.

## Prerequisites

- **Docker with Compose**, or **Podman with the `podman-compose` provider**.
  Podman 6.1.3 with `podman-compose` 1.6.0 was used for local verification.
- **Olist CSVs**, downloaded separately from Kaggle; see the license section.
- For host execution and tests: **Python 3.12**, [uv](https://docs.astral.sh/uv/),
  and the native PostgreSQL client library required by dbt v2.

## Quick Start

Run these commands from the repository root.

### 1. Prepare the environment and data

```bash
cp .env.example .env
mkdir -p data/raw
```

Edit `.env` to set your local database credentials. Download these nine files
into `data/raw/` and keep the original CSVs there:

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

### 2. Start services and build the warehouse

```bash
docker compose up --build -d
docker compose exec app uv run --locked python -m app.etl.pipeline
```

Compose connects the app to `db:5432`; host commands use `POSTGRES_HOST` and
`POSTGRES_PORT` from `.env`. The pipeline checks connectivity, applies the raw
schema, extracts and validates all files, reloads the tables, creates indexes,
and runs `dbt build`.

Missing columns, negative money, and invalid review scores stop loading.
Duplicate source keys, reversed delivery dates, sparse columns, and empty CSVs
produce warnings. Each table reload is one transaction; failed inserts restore
that table's previous contents. Tables and dbt models commit separately, so a
failed refresh can leave earlier objects updated. Complete a successful full
build before consuming refreshed analytics.

For Podman, substitute `podman compose` for `docker compose` in these commands.
Python edits reload automatically; rebuild after dependency or Dockerfile
changes. The image installs runtime dependencies in `/opt/venv`, which the
`/app` bind mount does not hide. Run lint and pytest on the host or in CI.

### 3. Verify the API

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl 'http://localhost:8000/sellers/top?limit=10'
```

Open [interactive API docs](http://localhost:8000/docs) after starting the app.
These URLs use the default `APP_PORT=8000`; adjust them if you change it.
`/ready` returns 503 until the analytics sources exist and can be queried.

Use `docker compose down` to stop services. Database files persist in
`postgres_data`; adding `-v` deletes that volume and its data.

## Run Locally

Prepare `.env` and the CSVs as above. Install the native PostgreSQL client
library (`libpq.so.5` on Linux); the container image already includes it:

```bash
# Debian/Ubuntu:
sudo apt-get install libpq5
# Arch/CachyOS:
sudo pacman -S --needed postgresql-libs
# macOS:
brew install libpq
```

On macOS, make Homebrew's libpq library directory available to the dynamic loader
if it is outside its search paths. On Windows, install the corresponding native
PostgreSQL client libraries.

Start PostgreSQL using Compose or your own instance, then run:

```bash
uv sync --locked
uv run --locked dbt --version        # Must be >=2.0.0; dbt v1 is rejected.
uv run --locked python -m app.etl.pipeline
uv run --locked uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## dbt Commands

The wrapper loads the repository `.env`, validates the connection settings, and
uses the dbt binary in the active Python environment:

```bash
uv run --locked python -m app.etl.transform debug
uv run --locked python -m app.etl.transform build
uv run --locked python -m app.etl.transform test
uv run --locked python -m app.etl.transform docs generate
uv run --locked python -m app.etl.transform docs serve --port 8080
```

Prefix these commands with `docker compose exec app` inside the container.
For the direct CLI, run from the repository root:

```bash
uv run --locked dbt build --project-dir dbt --profiles-dir dbt
```

PostgreSQL support is experimental in dbt v2; `.env.example` and the image enable
`DBT_ALLOW_EXPERIMENTAL_ADAPTERS=true`. Exported variables override `.env`.
Schemas use the exact names `silver` and `analytics`; use a separate database
for each environment or developer.

<details>
<summary>dbt editor setup</summary>

The [dbt extension](https://docs.getdbt.com/docs/configure-dbt-extension#about-env-file-support)
reads `.env` from its project directory. On Linux/macOS, share the root file:

```bash
ln -s ../.env dbt/.env                # Run once, if the link does not exist.
```

On Windows, create a corresponding file link or configure
`dbt.environmentVariables` in local editor settings. Select `.venv` as the
Python interpreter and run **Developer: Reload Window**. Credentials and
`dbt/target`, `dbt/logs`, `dbt/dbt_packages`, and `dbt/.user.yml` are ignored.
Both `.env` paths are excluded from image builds.

</details>

## Business API

| GET endpoint | Result |
| --- | --- |
| `/sellers/top?limit=10` | Sellers ranked by delivered item revenue |
| `/sellers/{seller_id}/performance` | Delivered-sales metrics for one seller |
| `/categories/performance?limit=100` | Categories ranked by delivered item revenue |
| `/geography/states?limit=100` | Customer states ranked by delivered item revenue |
| `/health` | Application liveness, without a database query |
| `/ready` | Database connectivity and access to the business query sources |

Lists accept an integer `limit` from 1 through 100; invalid values return 422.
Revenue ties break by seller ID, category name, or state, with NULL states last.
Empty lists return `[]`. Seller IDs accept 1–32 characters; sellers absent from
the delivered-sales mart, including those without delivered items, return 404.
All caller values use SQL bind parameters. Database failures or unbuilt analytics
return 503 with `{"detail":"Database analytics unavailable"}`. Empty queryable
views pass readiness.

Decimals serialize as JSON strings preserving precision and scale, such as
`"235.00"` revenue and `"0.5000"` late-delivery rate. Counts are integers; SQL NULL
values remain JSON `null`. `/openapi.json` describes fields, nullability,
input bounds, and error responses.

State results come from matched customer orders with delivered items, including
a NULL-state group. They use order facts and item totals to weight ticket and
review averages by order, rather than averaging rounded city-level averages.

## Metrics

All views below are in `analytics`. Facts retain every order status; sales
marts include only delivered orders with items.

| View | Grain |
| --- | --- |
| `dim_customers`, `dim_products`, `dim_sellers` | Customer, product, seller |
| `fact_orders` | Order |
| `fact_order_items` | Order + item |
| `mart_seller_performance` | Seller |
| `mart_category_performance` | Category |
| `mart_geography_sales` | Customer state + city |

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
timestamps; no eligible outcomes yields NULL. Missing reviews do not remove
sales. Category labels prefer English, fall back to Portuguese, then `unknown`
for missing products/categories. Seller/geography marts exclude unmatched
sellers/customers. Multi-seller/category order counts are not globally additive.
Money and averages round to two decimals; rates are fractions rounded to four.
Whole-order payment totals repeat on item rows and must not be summed across them.

## Run Tests

```bash
uv sync --locked
uv run --locked ruff check .
uv run --locked pytest -q
```

Include the metric regression with an empty disposable database:

```bash
METRICS_TEST_DATABASE_URL=postgresql://user:password@localhost:5432/metrics_test \
  uv run --locked pytest -q
```

The regression refuses existing `raw`, `silver`, or `analytics` schemas, loads
synthetic edge cases, repeats builds, checks exact KPIs and lineage, exercises
HTTP against real views, and verifies a duplicate-item failure. It drops its
own schemas on exit; without the URL it skips explicitly. Database-free HTTP
checks cover serialization, bounds, parameter binding, empty results, 404/503
responses, and OpenAPI. The 45 dbt tests check grains, nonempty facts, bounds,
and independent source-revenue reconciliation.

[GitHub Actions](.github/workflows/ci.yml) runs lint, Python checks, and the
PostgreSQL regression on pushes to `main` and pull requests.

## Validation and Scope

Full reloads and ordinary views are sufficient for this dataset. The
[query plans](docs/query-plans.md) support no index-speedup claim for the business
API. Add incremental loads, materialization, caching, or more endpoints when a
measured workload or consumer needs them. Global order counts must come from
facts because seller/category counts overlap.

When upgrading an older database, rebuild successfully before removing the
obsolete `silver.customers`, `silver.products`, and `silver.sellers` views.
The gold dimensions clean their raw sources directly; dbt does not delete old views.
Write SQL in lowercase, preserving case-sensitive literals and quoted identifiers.

## License and Data

The code is released under the [MIT License](LICENSE). Olist-derived data examples
and findings in `docs/`, plus the historical sample described below, are
attributed to Olist and shared under
[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
The analysis aggregates and transforms source data; MIT applies to the code.

The full CSVs are downloaded separately and `data/raw/` is ignored by Git.
History retains five geolocation rows and two product summaries in an old
`scripts/file_check.ipynb` output (commit `42b0612`); the current notebook has
no outputs. Those excerpts come from the same
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
and remain covered by its attribution, non-commercial, and share-alike terms.
This project is independent and is not affiliated with or endorsed by Olist.
