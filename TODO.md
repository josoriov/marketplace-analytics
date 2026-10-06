# Remaining work

The current project ingests nine Olist CSVs, builds 14 PostgreSQL views with
locked dbt v2, and serves business metrics plus `/health` and `/ready`.
Metric definitions and runnable commands live in [README.md](README.md).

## Business API

- [x] Add `/sellers/top?limit=10`, `/sellers/{seller_id}/performance`,
  `/categories/performance`, and `/geography/states`.
- [x] Bound list inputs, parameterize queries, return clear 404s, and specify
  decimal/null serialization. Compute state metrics at their proper grain.
- [x] Add database readiness and HTTP success/error/OpenAPI checks.
- [x] Verify and decide if the creation of some other endpoints might add value to this project

No additional business routes are needed now. README records when a global
summary would help and how to avoid overlapping seller/category order counts.

## Verification and release

- [ ] Verify a fresh Compose setup and repeated ingestion-to-HTTP runs;
  document the Podman Compose provider if supporting Podman.
- [ ] Add CI with Python checks and the disposable PostgreSQL regression.
- [ ] Record query plans before claiming index speedups.
- [ ] Rescan the final image and review remaining relevant vulnerabilities.
- [ ] Verify a clean clone using README, choose a code license, and confirm
  dataset attribution/redistribution terms.
- [ ] Add a useful model lineage example, five example queries, and two or
  three verified findings with their assumptions and sample API output.
- [ ] Review files/history for secrets and raw data before publishing the repo.

Keep one PostgreSQL database and one app service. Add a frontend, orchestration,
caching, incremental models, materialization, or cloud hosting only when needed.
