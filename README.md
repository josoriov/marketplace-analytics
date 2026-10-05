# Marketplace Seller Analytics API

End-to-end data product that ingests the **Olist Brazilian E-Commerce** dataset,
transforms it into analytics-ready models inside PostgreSQL, and exposes
business insights through a FastAPI service.

## Stack

| Layer | Technology |
|-------|-----------|
| Database | PostgreSQL 16 |
| ETL / API | Python 3.12, Polars, SQLAlchemy, FastAPI |
| Containerisation | Docker & Docker Compose |

## Architecture

```
data/raw/*.csv
      │
      ▼
┌──────────┐   extract    ┌──────────┐   validate   ┌──────────┐
│  CSV     │ ──────────►  │  Polars  │ ──────────►  │  Polars  │
│  files   │              │  DFs     │              │  DFs     │
└──────────┘              └──────────┘              └─────┬────┘
                                                         │ load
                                                         ▼
                                                  ┌──────────────┐
                                                  │  PostgreSQL  │
                                                  │  raw.*       │
                                                  └──────┬───────┘
                                                         │ SQL transforms
                                                         ▼
                                                  ┌──────────────┐
                                                  │  analytics.* │
                                                  │  dims/facts/ │
                                                  │  marts       │
                                                  └──────┬───────┘
                                                         │
                                                         ▼
                                                  ┌──────────────┐
                                                  │  FastAPI     │
                                                  │  /health     │
                                                  └──────────────┘
```

The **`db`** container runs PostgreSQL and stores both the raw ingested tables
and the analytics models.  The **`app`** container runs the Python ETL pipeline
and the FastAPI server.  Data flows from raw CSVs into `raw.*` tables, then SQL
views build dimensions (`analytics.dim_*`), facts (`analytics.fact_*`), and
business marts (`analytics.mart_*`).  The API reads from those transformed
views so request handling stays fast and predictable.

## Dataset source

**Brazilian E-Commerce Public Dataset by Olist** — <https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce>

Download the CSVs and place them in `data/raw/`.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and
  [Docker Compose](https://docs.docker.com/compose/install/) (v2)
- (Optional, for local development) [uv](https://docs.astral.sh/uv/) — used to manage the Python virtual environment

## Quick start

```bash
# 1. Clone the repository
git clone <repo-url> && cd marketplace-analytics

# 2. Place the Olist CSV files inside data/raw/
ls data/raw/
# olist_orders_dataset.csv  olist_order_items_dataset.csv  ...

# 3. Build and start all services
docker compose up --build -d

# 4. Run the full ETL pipeline (extract → validate → load → transform → verify)
docker compose exec app python -m app.etl.pipeline

# 5. Verify the API is running
curl http://localhost:8000/health
```

The API is available at **http://localhost:8000** and the auto-generated
OpenAPI docs at **http://localhost:8000/docs**.

### Stopping the services

```bash
docker compose down          # stop containers, keep data volume
docker compose down -v       # stop containers AND delete the database volume
```

### Rebuilding after code changes

```bash
docker compose up --build -d
```

Local code is bind-mounted into the container, so most Python changes are
picked up automatically by Uvicorn's `--reload` flag.  Only `requirements.txt`
or `Dockerfile` changes require a rebuild.

## Pipeline steps

| Step | Description |
|------|-------------|
| 1 | Test database connectivity |
| 2 | Apply raw schema (`app/db/schema.sql`) |
| 3 | Extract CSVs from `data/raw/` into Polars DataFrames |
| 4 | Validate data quality (column presence, bounds, monetary signs, date logic) |
| 5 | Load validated data into `raw.*` tables (truncate + insert) |
| 6 | Create performance indexes (`app/db/indexes.sql`) |
| 7 | Build analytics views — dimensions, facts, marts (`app/db/marts.sql`) |
| 8 | Run sanity checks on the analytics layer (`app/db/sanity_checks.sql`) |

## Analytics models

### Dimensions

| View | Grain | Key columns |
|------|-------|-------------|
| `analytics.dim_customers` | customer_id | city, state |
| `analytics.dim_products` | product_id | translated category, size/weight |
| `analytics.dim_sellers` | seller_id | city, state |

### Facts

| View | Grain | Key columns |
|------|-------|-------------|
| `analytics.fact_orders` | order_id | status, timestamps, `delivery_delay_days`, `is_late_delivery` |
| `analytics.fact_order_items` | order_id + order_item_id | price, freight, `item_total_value` |

### Business marts

| View | Grain | Key metrics |
|------|-------|-------------|
| `analytics.mart_seller_performance` | seller_id | revenue, avg review score, late delivery rate |
| `analytics.mart_category_performance` | product_category | revenue, avg price, late delivery rate |
| `analytics.mart_geography_sales` | state + city | revenue, avg ticket, avg review score |

## Local development (optional)

If you want to run code outside Docker (e.g. tests, linting):

```bash
# Create and activate a virtual environment with uv
uv venv
source .venv/bin/activate

# Install dependencies
uv pip install -r requirements.txt
```

## Running tests

```bash
# Inside the container
docker compose exec app python -m pytest tests/ -v

# Or locally with uv
source .venv/bin/activate
pytest tests/ -v
```

## Project structure

```
marketplace-analytics/
├── app/
│   ├── main.py              # FastAPI application
│   ├── core/
│   │   ├── config.py        # Environment-based settings
│   │   └── database.py      # SQLAlchemy engine, sessions, SQL runner
│   ├── db/
│   │   ├── schema.sql       # Raw table DDL
│   │   ├── indexes.sql      # Performance indexes
│   │   ├── marts.sql        # Analytics views (dims, facts, marts)
│   │   └── sanity_checks.sql# Post-transform validation
│   └── etl/
│       ├── config.py        # CSV → table mapping
│       ├── extract.py       # CSV reader
│       ├── load.py          # Postgres loader
│       ├── pipeline.py      # Orchestrator
│       └── validators.py    # Pre-load data checks
├── data/raw/                # Olist CSV files (not committed)
├── tests/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Assumptions and trade-offs

- **Full refresh** — Every pipeline run truncates and reloads all raw tables.
  Acceptable at interview scale; production would use incremental loads.
- **Views, not materialized views** — Analytics models are plain views so the
  schema rebuild is idempotent and instant. For heavier traffic, materializing
  the marts and refreshing them on a schedule would be the next step.
- **Revenue = sum of item prices** — `total_revenue` in the marts sums
  `order_items.price`. Freight is tracked separately.
- **Late delivery** — An order is late when `delivered_customer_date >
  estimated_delivery_date`. Orders without both dates are not counted.
- **PostgreSQL is sufficient** — The dataset fits comfortably in a single
  Postgres instance; no distributed compute is needed.
