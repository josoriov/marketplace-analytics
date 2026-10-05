Yes — here is the full `TODO.md` content pasted in chat.

The CSVs come from the **Olist Brazilian E-Commerce Public Dataset** on Kaggle. The dataset page is here, and the direct data tab lets you download/select the CSVs for the pipeline. Kaggle snippets also indicate the dataset includes multiple CSV files, including the standard Olist customer, seller, review, order-item, and geolocation tables. ([Kaggle][1])

---

# TODO.md

# Marketplace Seller Analytics API — Interview Project TODO

## Project goal

Build a small end-to-end **data product** using:

* **Python** for ingestion, cleaning, loading, and API logic
* **SQL** for schema design, transformations, analytical marts, and performance tuning
* **Docker / Docker Compose** for reproducible local setup
* **PostgreSQL** as the main database

The final product should:

* ingest raw CSVs into Postgres
* transform them into analytics-ready tables/views
* expose business insights through a small Python API
* be easy to run locally with one command
* be easy to explain in a technical interview

---

## Dataset source

Use the **Brazilian E-Commerce Public Dataset by Olist** on Kaggle. Download it from the main dataset page or from the data tab where the CSVs can be selected individually. ([Kaggle][1])

### Main dataset link

* `https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce`

### CSVs to download first

At minimum, use these core files for the pipeline:

* `olist_orders_dataset.csv`
* `olist_order_items_dataset.csv`
* `olist_order_payments_dataset.csv`
* `olist_order_reviews_dataset.csv`
* `olist_customers_dataset.csv`
* `olist_products_dataset.csv`
* `olist_sellers_dataset.csv`
* `product_category_name_translation.csv`

Optional but useful later:

* `olist_geolocation_dataset.csv`

These are the standard Olist CSV tables commonly used with the dataset. ([Kaggle][2])

### Where to place the CSVs locally

Create this folder:

* `data/raw/`

Put all downloaded CSVs inside it.

---

## Final expected output

By the end of the project, the repo should contain:

* Dockerized Postgres
* Python ETL pipeline
* SQL schema + transformations
* FastAPI service with analytics endpoints
* tests
* README with setup + architecture explanation

---

## Suggested repo structure

* `marketplace-analytics/`

  * `app/`

    * `api/`

      * `main.py`
      * `routes/`

        * `health.py`
        * `sellers.py`
        * `categories.py`
        * `geography.py`
    * `etl/`

      * `extract.py`
      * `transform.py`
      * `load.py`
      * `pipeline.py`
      * `validators.py`
    * `db/`

      * `schema.sql`
      * `marts.sql`
      * `indexes.sql`
      * `seed.sql`
    * `core/`

      * `config.py`
      * `logging.py`
      * `database.py`
    * `models/`

      * `schemas.py`
  * `data/`
    * `raw/`
  * `tests/`
    * `test_transformations.py`
    * `test_api.py`
    * `test_validators.py`
  * `Dockerfile`
  * `docker-compose.yml`
  * `.env.example`
  * `requirements.txt`
  * `README.md`

---

# Ordered TODOs

## 1 — Create the repository and initialize the project

### Tasks

* Create a new folder called `marketplace-analytics`
* Initialize a git repository
* Add a `.gitignore`
* Create the base folder structure shown above
* Create an empty `README.md`

### Done when

- [x] Repo exists
- [x] Folder structure exists
- [x] Git is initialized
- [x] README exists

---

## 2 — Download the dataset CSVs

### Tasks

- [x] Download the Olist dataset from Kaggle
- [x] Place the core CSV files in `data/raw/`
- [x] Do not rename files yet
- [x] Verify the files open correctly and have headers

### Checks

- [x] Confirm every CSV loads in a spreadsheet or pandas
- [x] Confirm there are no broken or empty files
- [x] Confirm filenames are consistent with your code expectations

### Done when

- [x] All CSVs are present in `data/raw/`
- [x] You can list them from the terminal
- [x] At least one can be read successfully with Python

---

## 3 — Define the local architecture

### Tasks

Decide the initial architecture:

- [x] `db` container → PostgreSQL
- [x] `app` container → Python ETL + API
- [x] (Decided not to) optional `adminer` container → DB inspection

### Deliverable

Add a short architecture section to the README:

- [x] what each container does
- [x] how data flows from raw CSV to API response

### Done when

- [x] You can explain the architecture in 4–5 sentences

---

## 4 — Create `docker-compose.yml`

### Tasks

Create a Docker Compose setup with:

#### Service 1: `db`

* image: postgres
* exposed port: `5432`
* environment variables:
  * `POSTGRES_DB`
  * `POSTGRES_USER`
  * `POSTGRES_PASSWORD`
* mounted volume for persistence

#### Service 2: `app`

- [x] built from your `Dockerfile`
- [x] mounted source code for local development
- [x] environment variables for DB connection
- [x] depends on `db`

#### Optional Service 3: `adminer` (won't do)

- [x] useful for visually inspecting tables

### Done when

- [x] `docker compose up` starts the services without crashing

---

## 5 — Create the Python app environment

### Tasks

Create uv files or requirements.txt to manage the packages inside the container with the next python packages:

* `fastapi`
* `uvicorn`
* `pandas` or `polars`
* `sqlalchemy`
* `psycopg2-binary`
* `pydantic`
* `python-dotenv`
* `pytest`

Optional:

* `alembic`
* `httpx`

### Done when

- [x] Dependencies install successfully inside the app container

---

## 6 — Create the `Dockerfile`

### Tasks

Build a Python image that:

- [x] uses a slim Python base image
- [x] sets a working directory
- [x] copies `requirements.txt`
- [x] installs dependencies
- [x] copies app code
- [x] starts FastAPI with `uvicorn`

### Done when

- [x] The `app` container builds successfully
- [x] The container starts without import errors

---

## 7 — Create environment configuration

### Tasks

Create:

- [x] `.env.example`
* `app/core/config.py`

Add the following environment variables:

* `POSTGRES_HOST`
* `POSTGRES_PORT`
* `POSTGRES_DB`
* `POSTGRES_USER`
* `POSTGRES_PASSWORD`

### Done when

- [x] The Python app can read DB credentials from environment variables

---

## 8 — Design the raw database schema

### Goal

Load CSVs into raw tables first with minimal transformation.

### Tasks

Create `app/db/schema.sql` with a `raw` schema and these tables:

* `raw.orders`
* `raw.order_items`
* `raw.order_payments`
* `raw.order_reviews`
* `raw.customers`
* `raw.products`
* `raw.sellers`
* `raw.category_translation`
* optional: `raw.geolocation`

### Important columns to define carefully

#### `raw.orders`

- [x] `order_id` (varchar(32))
- [x] `customer_id` (varchar(32))
- [x] `order_status` (enum ['unavailable','shipped','approved','processing','delivered','canceled','invoiced','created'])
- [x] `order_purchase_timestamp` (timestamp)
- [x] `order_approved_at` (timestamp)
- [x] `order_delivered_carrier_date` (timestamp)
- [x] `order_delivered_customer_date` (timestamp)
- [x] `order_estimated_delivery_date` (timestamp)

#### `raw.order_items`

- [x] `order_id` (varchar(32))
- [x] `order_item_id` (int(64))
- [x] `product_id` (varchar(32))
- [x] `seller_id` (varchar(32))
- [x] `shipping_limit_date` (timestamp)
- [x] `price` (numeric(8))
- [x] `freight_value` (numeric(8))

#### `raw.order_payments`

- [x] `order_id` (varchar(32))
- [x] `payment_sequential` (integer)
- [x] `payment_type` (enum ['not_defined','boleto','credit_card','voucher','debit_card'])
- [x] `payment_installments` (integer)
- [x] `payment_value` (numeric(8))

#### `raw.order_reviews`

- [x] `review_id` (varchar(32))
- [x] `order_id` (varchar(32))
- [x] `review_score` (smallint CHECK (review_score BETWEEN 1 AND 5))
- [x] `review_creation_date` (timestamp)
- [x] `review_answer_timestamp` (timestamp)
- [x] `review_comment_title` (varchar)
- [x] `review_comment_message` (varchar)

#### `raw.customers`

- [x] `customer_id` (varchar(32))
- [x] `customer_unique_id` (varchar(32))
- [x] `customer_zip_code_prefix` (integer)
- [x] `customer_city` (varchar)
- [x] `customer_state` (varchar(2))

#### `raw.products`

- [x] `product_id` (varchar(32))
- [x] `product_category_name` (varchar)
- [x] `product_name_lenght` (smallint)
- [x] `product_description_lenght` (smallint)
- [x] `product_photos_qty` (smallint)
- [x] `product_weight_g` (integer)
- [x] `product_length_cm` (integer)
- [x] `product_height_cm` (integer)
- [x] `product_width_cm` (integer)

#### `raw.sellers`

- [x] `seller_id` (varchar(32))
- [x] `seller_zip_code_prefix` (integer)
- [x] `seller_city` (varchar)
- [x] `seller_state` (varchar(2))

#### `raw.geolocation`

- [x] `geolocation_zip_code_prefix` (integer)
- [x] `geolocation_lat` (numeric)
- [x] `geolocation_lng` (numeric)
- [x] `geolocation_city` (varchar)
- [x] `geolocation_state` (varchar(2))

### Done when

- [x] You can run the schema script and create all raw tables

---

## 9 — Add database connection utilities in Python

### Tasks

Create `app/core/database.py` to:

- [x] open a SQLAlchemy engine
- [x] create reusable DB sessions or connections
- [x] support running SQL scripts

### Done when

- [x] A simple script can connect to Postgres and run `SELECT 1`

---

## 10 — Create an ingestion config

### Tasks

Create a central mapping for:

- [x] CSV filename
- [x] destination table
- [x] expected columns
- [x] columns to parse as dates
- [x] primary key logic if needed

Example concept:

* `olist_orders_dataset.csv` → `raw.orders`
* `olist_order_items_dataset.csv` → `raw.order_items`

### Done when

- [x] You can change one config file instead of hardcoding table behavior everywhere

---

## 11 — Implement CSV extraction

### Tasks

Create `app/etl/extract.py` to:

- [x] read CSVs from `data/raw/`
- [x] validate that files exist
- [x] load them into polars DataFrames
- [x] standardize column names to lowercase
- [x] optionally trim whitespace from string columns

### Data quality checks

- [x] fail if a required CSV is missing
- [x] warn if a CSV is empty
- [x] warn if unexpected columns appear

### Done when

- [x] Each CSV can be loaded independently through a function call

---

## 12 — Implement basic validation logic

### Tasks

Create `app/etl/validators.py` with checks for:

- [x] missing required columns
- [x] duplicate primary-key-like rows where appropriate
- [x] impossible date relationships where obvious
- [x] negative monetary values
- [x] null-heavy fields that should be monitored

### Examples

- [x] `price < 0` should fail
- [x] `freight_value < 0` should fail
- [x] `review_score` should be between valid bounds
- [x] `order_delivered_customer_date` earlier than `order_purchase_timestamp` should be flagged

### Done when

- [x] Validation runs before load and produces a clear report

---

## 13 — Load raw tables into Postgres

### Tasks

Create `app/etl/load.py` to:

- [x] truncate raw tables during early development
- [x] insert CSV data into Postgres
- [x] use chunked inserts for larger files
- [x] log row counts loaded per table

### Recommended approach

- [x] start with full refresh loads
- [x] keep load logic idempotent for repeated local runs

### Done when

- [x] You can run one command and populate all raw tables

---

## 14 — Create a pipeline entrypoint

### Tasks

Create `app/etl/pipeline.py` that orchestrates:

1. DB connection
2. schema creation
3. CSV extraction
4. validation
5. raw table load
6. SQL transformation execution

### CLI behavior

- [x] Support a command like:

* `python -m app.etl.pipeline`

### Done when

- [x] One command runs the whole pipeline end to end

---

## TODO 15 — Create the analytics schema

### Tasks

Create an `analytics` schema in SQL for transformed models

Suggested tables/views:

- [x] `analytics.dim_customers`
- [x] `analytics.dim_products`
- [x] `analytics.dim_sellers`
- [x] `analytics.fact_orders`
- [x] `analytics.fact_order_items`
- [x] `analytics.mart_seller_performance`
- [x] `analytics.mart_category_performance`
- [x] `analytics.mart_geography_sales`

### Done when

- [x] Raw data and analytics outputs are clearly separated

---

## TODO 16 — Build dimension models

### Tasks

- [x] In `app/db/marts.sql`, create dimensions:

### `analytics.dim_customers`

Include:

* customer_id
* customer_unique_id
* customer_city
* customer_state

### `analytics.dim_products`

Include:

* product_id
* translated category name if available
* size/weight attributes

### `analytics.dim_sellers`

Include:

* seller_id
* seller_city
* seller_state

### Done when

- [x] You have clean, reusable dimension tables for joins

---

## TODO 17 — Build fact tables

### Tasks

Create:

### `analytics.fact_orders`

Include:

* order_id
* customer_id
* order_status
* purchase timestamp
* approved timestamp
* delivered timestamp
* estimated delivery date
* derived delivery delay metrics

### `analytics.fact_order_items`

Include:

* order_id
* order_item_id
* product_id
* seller_id
* price
* freight_value
* payment summary fields if useful

### Important derived fields

Add computed fields such as:

* `delivery_delay_days`
* `is_delivered`
* `is_late_delivery`
* `order_total_item_value`
* `order_total_freight_value`

### Done when

- [x] You can answer most business questions from the fact tables

---

## TODO 18 — Create `mart_seller_performance`

### Goal

- [x] This is the main interview-ready business mart.

### Fields to include

* `seller_id`
* `seller_city`
* `seller_state`
* `total_orders`
* `total_items_sold`
* `total_revenue`
* `avg_order_value`
* `avg_freight_value`
* `avg_review_score`
* `avg_delivery_delay_days`
* `late_delivery_rate`

### Business logic notes

* define clearly what counts as revenue
* define clearly what counts as late delivery
* define the review aggregation grain

### Done when

* Querying this mart returns top seller rankings

---

## TODO 19 — Create `mart_category_performance`

### Fields to include

* `product_category`
* `total_orders`
* `total_items_sold`
* `total_revenue`
* `avg_price`
* `avg_review_score`
* `late_delivery_rate`

### Done when

* You can compare category quality and sales performance

---

## TODO 20 — Create `mart_geography_sales`

### Fields to include

* `customer_state`
* `customer_city`
* `total_orders`
* `total_revenue`
* `avg_ticket`
* `avg_review_score`

### Done when

* You can expose geography-based analytics through the API

---

## TODO 21 — Add indexes for performance

### Tasks

- [x] Create `app/db/indexes.sql`

- [x] Add indexes on likely join/filter columns such as:

* `order_id`
* `customer_id`
* `product_id`
* `seller_id`
* purchase timestamp
* customer state
* seller state

### Done when

- [x] Key analytical queries improve measurably
- [x] You can explain why you indexed each column

---

## TODO 22 — Validate transformation outputs with SQL sanity checks

### Tasks

Write SQL checks such as:

* row counts are non-zero
* no duplicate `order_id` where grain should be unique
* late delivery rate is between `0` and `1`
* average review score is in valid bounds
* revenue is non-negative

### Done when

* Transformation layer has basic trust checks

---

## TODO 23 — Build the FastAPI app skeleton

### Tasks

Create `app/api/main.py`

Add:

* FastAPI app initialization
* route registration
* health endpoint
* simple startup logging

### Done when

* The API starts and responds locally

---

## TODO 24 — Implement the health endpoint

### Endpoint

* `GET /health`

### Response

Return:

* API status
* DB connectivity status

### Done when

* You can prove the app and DB are both alive

---

## TODO 25 — Implement seller analytics endpoints

### Endpoints

* `GET /sellers/top?limit=10`
* `GET /sellers/{seller_id}/performance`

### Expected behavior

#### `/sellers/top`

* returns top sellers ordered by revenue
* supports `limit`

#### `/sellers/{seller_id}/performance`

* returns one seller’s KPI summary

### Done when

* You can demonstrate a business-facing API query live

---

## TODO 26 — Implement category analytics endpoints

### Endpoints

* `GET /categories/performance`
* optional filter: `?min_orders=...`

### Done when

* You can query category-level analytics from the mart

---

## TODO 27 — Implement geography analytics endpoints

### Endpoints

* `GET /geography/states`
* optional `GET /geography/cities?state=SP`

### Done when

* Geography summaries are queryable and cleanly formatted

---

## TODO 28 — Add response schemas with Pydantic

### Tasks

Create `app/models/schemas.py`

Define response models for:

* health
* seller performance
* top seller list
* category performance
* geography summary

### Done when

* API responses are typed and documented automatically

---

## TODO 29 — Add logging

### Tasks

Create `app/core/logging.py`

Log:

* pipeline start/end
* rows loaded per table
* validation warnings
* transformation execution
* API startup

### Done when

* The app logs enough to debug failures during demo

---

## TODO 30 — Add unit tests for transformations

### Tasks

Create `tests/test_transformations.py`

Test:

* delivery delay calculation
* late delivery flag logic
* revenue aggregation logic
* category translation joins

### Done when

* Core business logic is covered by tests

---

## TODO 31 — Add API tests

### Tasks

Create `tests/test_api.py`

Test:

* `/health`
* `/sellers/top`
* `/categories/performance`

### Done when

* Your most important endpoints have basic coverage

---

## TODO 32 — Add validation tests

### Tasks

Create `tests/test_validators.py`

Test:

* missing columns
* negative price rejection
* invalid review score rejection
* invalid timestamp relationships

### Done when

* Validation layer is testable and defendable in interview discussion

---

## TODO 33 — Write the README properly

### Sections to include

* project overview
* architecture diagram in text
* stack used
* dataset source
* how to run locally
* pipeline flow
* API endpoints
* assumptions and tradeoffs
* future improvements

### Done when

* A reviewer can run the project from README instructions only

---

## TODO 34 — Add a “How to run” section

### Exact commands to support

* `docker compose up --build`
* pipeline run command
* API access URL
* optional docs URL

### Done when

* The project is runnable in a few commands

---

## TODO 35 — Add OpenAPI docs support

### Tasks

Use FastAPI’s autogenerated docs

### Demo URLs

* `/docs`
* `/redoc`

### Done when

* Interviewer can explore the API visually

---

## TODO 36 — Prepare sample SQL queries for interview discussion

### Write down 5 SQL examples you can explain

#### Example ideas

* top sellers by revenue
* average review score by seller
* percentage of late deliveries by category
* revenue by customer state
* monthly order trend

### Done when

* You can speak comfortably about joins, aggregates, and query logic

---

## TODO 37 — Prepare system design talking points

### You should be ready to answer:

#### If data volume becomes 100x larger

* partition fact tables by date
* add stronger indexing
* move to incremental ingestion
* separate raw and analytics workloads

#### If the API gets heavy traffic

* add caching
* use materialized views
* use read replicas
* paginate large result sets

#### If data arrives daily

* implement incremental loads
* use upserts
* track watermarks by timestamp

#### If quality becomes critical

* formalize validation checks
* reject bad rows into quarantine tables
* add monitoring and alerting

### Done when

* You can discuss scale, reliability, and tradeoffs clearly

---

## TODO 38 — Add explicit assumptions to the README

### Include assumptions like

* full refresh loads are acceptable for the initial version
* Postgres is sufficient for interview-scale data
* analytics are batch-computed, not real-time
* revenue is defined from order item price totals unless otherwise specified

### Done when

* Reviewers understand your design decisions and simplifications

---

## TODO 39 — Polish for interview presentation

### Tasks

* remove dead code
* ensure endpoint naming is clean
* ensure logs are readable
* ensure SQL is formatted
* ensure README screenshots or examples are present if possible

### Done when

* The repo looks deliberate and production-minded

---

## TODO 40 — Final demo checklist

Before considering the project complete, confirm:

* Docker starts cleanly
* Postgres is reachable
* pipeline runs end to end
* raw tables are populated
* marts are populated
* API starts
* `/health` works
* `/sellers/top` works
* `/categories/performance` works
* tests pass
* README is enough for someone else to run it

---

# Nice-to-have stretch tasks

## Stretch 1 — Add materialized views

Use materialized views for slow marts and discuss refresh strategy.

## Stretch 2 — Add Alembic migrations

Useful if you want to look more production-oriented.

## Stretch 3 — Add CI

Use GitHub Actions to:

* run tests
* lint code
* maybe build the Docker image

## Stretch 4 — Add simple data quality report

Generate a validation summary after pipeline execution.

## Stretch 5 — Add pagination and filtering

For example:

* seller filters by state
* category filters by minimum orders
* date-range filtering for summaries

---

# Suggested build order if time is tight

If the challenge is short, do this in priority order:

1. Docker Compose with Postgres
2. raw table schema
3. Python CSV load into Postgres
4. 1–2 transformed marts
5. FastAPI with 2–3 endpoints
6. basic README
7. a few tests
8. system design prep notes

---

# Minimum viable submission

If you need a smaller but strong version, submit:

* Dockerized Postgres + Python app
* raw CSV ingestion
* `mart_seller_performance`
* `mart_category_performance`
* `GET /health`
* `GET /sellers/top`
* `GET /categories/performance`
* README with architecture + tradeoffs

That is already enough for a solid technical discussion.

---

# Interview talking points to rehearse

Be ready to explain:

* why you used Postgres
* why you separated raw and analytics schemas
* why transformations live in SQL
* why FastAPI was chosen
* how Docker improves reproducibility
* how you would scale ingestion
* how you would improve data quality
* how you would support daily refreshes
* how you would optimize slow queries

---

# Definition of done

This project is done when:

* a reviewer can clone the repo
* start the stack with Docker
* run the pipeline
* query the API
* inspect transformed analytics
* understand your design choices from the README

---

If you want, I can turn this next into a **matching README.md** and also give you a **starter folder structure with the exact files and code skeletons**.

[1]: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce?utm_source=chatgpt.com "Brazilian E-Commerce Public Dataset by Olist"
[2]: https://www.kaggle.com/code/roruizf/olist-order-items-dataset?utm_source=chatgpt.com "olist_order_items_dataset"
