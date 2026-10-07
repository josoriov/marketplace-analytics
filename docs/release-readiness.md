# Release verification log

Recorded 2026-10-07, with an independent review of the final release work.
Commands run from the repository root. This verifies a local Git clone of a
release-candidate snapshot containing the intended changes; the remote
repository will match only after the release commits are pushed.

## Fresh Compose and repeated ingestion

Verified using rootless Podman 6.1.3, `podman compose`, and the `podman-compose`
1.6.0 provider, now documented in README. Docker Compose itself was not available
and is not claimed as locally tested.

- Created an isolated Compose project from the clean clone, with a new database
  volume and independent localhost ports. The original services/database were
  left running. PostgreSQL became healthy and the app served HTTP.
- `/health` returned 200 and `/ready` returned 503 before ingestion.
- Two complete pipeline runs each passed **14 models + 45 dbt tests**. Counts and
  sample HTTP responses were identical after both runs. The only warnings were
  814 duplicate review IDs and the two sparse review-comment columns.

| Raw table | Rows |
| --- | --- |
| orders | 99,441 |
| order_items | 112,650 |
| order_payments | 103,886 |
| order_reviews | 99,224 |
| customers | 99,441 |
| products | 32,951 |
| sellers | 3,095 |
| category_translation | 71 |
| geolocation | 1,000,163 |

After refresh, `/ready` returned 200. All four business endpoints and OpenAPI
returned valid JSON, `limit=0` returned 422, and an unknown seller returned 404.
The seller/state example JSON in [analytics.md](analytics.md) matched live
responses exactly. The test project's containers and volume were then removed.

## Python checks, regression, and CI

A host `uv sync --locked` in the clean clone installed the environment from the
lockfile. Ruff passed. The full suite passed **42 tests** with a separate empty
PostgreSQL database and `METRICS_TEST_DATABASE_URL`. This includes the dbt/HTTP
metric regression, repeated builds, schema/lineage checks, and duplicate-item
failure. Without that URL the result is **41 passed, 1 skipped**.

The subsequent public-release audit reran Ruff and all 42 tests against a new
disposable PostgreSQL container. All passed, and the owned test container and
volume were removed afterward.

The workflow in `.github/workflows/ci.yml` pins uv 0.12.22 to match the image,
runs Python checks, and runs a second job with disposable PostgreSQL 16. Hosted
GitHub execution remains unverified until the changes are pushed; local results
are not presented as a GitHub CI run.

The exploratory notebook now explicitly selects the products file rather than
using directory order, runs from the root or `scripts/`, and participates in
Ruff. Its code cells were executed successfully from both directories, with
outputs and execution counts kept clear. The manual SQL example now addresses
`raw.orders` without assuming a database name.

## Query plans and image scan

[Query plans](query-plans.md) now include committed raw evidence, a warm-up and
three measurements per query/mode. The seller filter pushes down; normalized
identifier expressions do not match the ordinary raw-column indexes. No API
index speedup is claimed, and JIT overhead is recorded.

The final image was rebuilt and rescanned after all build-input changes. It
excludes pytest, Ruff, and pip; an offline check with the repository mounted
read-only verified the `/opt/venv` environment and liveness handler. The earlier
Compose run also verified that `uv run` does not reinstall dev dependencies.
The [scan](security-scan.md) still reports 0 critical and 44 high package findings
(8 distinct high CVEs), with no fixed trixie versions reported. These remain
known findings, not resolved issues. The image runs as root and this Compose
configuration is for local development; published ports now bind to localhost.
Existing running containers take the new bindings after Compose recreates them.

The subsequent audit confirmed the original running containers still published
PostgreSQL on `0.0.0.0:5432` and the API on `0.0.0.0:8000`. Recreate these services
to apply the committed localhost bindings before publication.

## Licensing, evidence, and history

Code is [MIT](../LICENSE). Olist-derived examples/findings and historical samples
are explicitly attributed to
[Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)
and covered by [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
Full CSVs, `.env`, keys, and generated dbt outputs are absent from the public file
snapshot; test data is synthetic.

Gitleaks 8.30.1 scanned all 20 reachable commits across local refs, 74 public
files, and all 189 stored blobs, including dangling objects, with full redaction
and no detector findings. Manual checks found no private keys; credential URLs
contained test or documentation values. A final release-file scan also covered
the subsequently added architecture SVG. These results complement inspection;
they do not prove absence of every possible credential.

A separate comparison found that the ignored local `.env` still reused a
historical Compose password default. Treat that password as publicly known and
rotate it in both PostgreSQL and `.env` before publication. Merely changing
`.env` does not change the password in an already initialized database. Password
rotation and recreation of the original services remain outstanding local
operational steps; this verification does not claim they were completed.

The runtime lockfile scan reported no vulnerabilities with the same Trivy
database used for the image report. All recorded image build-input hashes still
matched the reviewed files; the documented Debian findings remain unresolved.

History **does retain data**: commit `42b0612` contains five geolocation rows and
two product summaries in notebook outputs, cleared from the current file in
`3b37631`. Per the owner's explicit choice, history is retained and the excerpts
are attributed/licensed in README. No history rewrite was performed.

The lineage diagram now follows the actual model dependencies, including
`silver.order_items` as the source of the item summary. Default dbt v2 docs
generation was verified; it provides model lineage without column lineage.
All five example queries and the three findings were rerun against PostgreSQL:

- The true late-delivery rate is **7,826 / 96,470 = 8.11%**. The previous
  7,661 / 95,824 counts describe only eligible orders with reviews.
- Seller revenues are additive; seller order counts overlap. Top-10 revenue is
  **1,754,800.00**, or **13.27%** of delivered item revenue.
- MA's **19.67%** late rate is about **2.4×** the national rate; the reviewed-order
  denominator is not used as the national baseline.

Release artifacts in `docs/` are public; the local full pipeline/scan logs are
in `/tmp/marketplace-public-review-vz4p9xdk`. The remaining external verification
is the first hosted CI run and a Docker Compose run if independently claiming
Docker support as tested. Publishing the repository does not require deploying
this development configuration to the internet.
