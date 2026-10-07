# Container image vulnerability scan

Rescanned 2026-10-07 after rebuilding the corrected `Dockerfile` with Trivy
0.75.0 and its vulnerability database updated at 07:38:55 UTC that day.
Image ID: `sha256:11f41c2fcc8147cbc9f33a12ae1c8ae00aeda7e6ff3c41090528261de2a15683`.
The image uses Python 3.12-slim-trixie / Debian 13.7, applies available apt
upgrades, removes pip, and installs only locked runtime dependencies. `UV_NO_DEV=1`
also prevents documented `uv run` commands from reinstalling dev packages.

[Scan evidence](security-scan.json) records image and source hashes, the scanner
database timestamp, counts, and high-severity findings. The complete local
report is `/tmp/marketplace-public-review-vz4p9xdk/final-security-scan.json`.

| Severity | Findings | Distinct CVEs |
| --- | --- | --- |
| Critical | 0 | 0 |
| High | 44 | 8 |
| Medium | 58 | 29 |
| Low | 82 | 42 |
| Unknown | 2 | 2 |

## Remaining findings

All 186 reported findings are in Debian packages; Python dependency and uv
scanner targets reported none. This is a scanner result, not proof that the
Python runtime or application has no vulnerabilities.

No finding lists a fixed package version available for **Debian trixie** in the
scan database. This does not mean no upstream fix exists: Debian lists newer
fixed versions in unstable for
[CVE-2026-76642](https://security-tracker.debian.org/tracker/CVE-2026-76642)
and [CVE-2026-9538](https://security-tracker.debian.org/tracker/CVE-2026-9538),
while trixie remains affected. Debian classifies these two as minor issues;
Trivy's high labels use severity information from other vendors.

The 44 high findings consist of:

- `CVE-2026-76642`, `CVE-2026-78408`, `CVE-2026-78409`, `CVE-2026-78410`: util-linux (9 package records each), involving local mount/namespace operations.
- `CVE-2025-69720`: ncurses (4 records), involving the `infocmp` command.
- `CVE-2026-16742`: systemd (2 records), involving `systemd-homed`.
- `CVE-2026-54369`: libacl1, involving pathname-based ACL operations.
- `CVE-2026-9538`: perl-base, involving Perl tar parsing.

The business handlers query PostgreSQL and do not invoke those operations.
That lowers their apparent exposure through HTTP routes; it is not an
exploitability assessment of every installed library or dbt execution path.

## Scope and follow-up

Compose does not request privileged mode, but **the image runs as root inside the
container**, mounts the working tree for reload, and uses the database owner for
ingestion and queries. Both published ports now bind to localhost. This is a
local portfolio demonstration, not an internet deployment configuration.

Rebuild and rescan when base packages or dependencies change. Keep the local
binding and avoid privileged mode. An internet deployment would also need a
non-root runtime, a read-only API database role, and separate ingestion access.
No report findings are suppressed or called resolved merely because a patch is
unavailable in the selected distribution.

Reproduce with Docker (or substitute Podman), and an installed Trivy:

```bash
docker build --pull -t marketplace-analytics:review .
docker save --output /tmp/marketplace-review-image.tar marketplace-analytics:review
trivy image --input /tmp/marketplace-review-image.tar --scanners vuln --format json --output /tmp/marketplace-review-scan.json
```

Mutable base tags and a changing vulnerability database can change the results.
