# Testing and failure behavior

Run from the repository root with Python 3.13 and uv:

```powershell
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run python -m scripts.check_repository
uv run pytest --cov --cov-report=term-missing --cov-report=xml
uv run python -m build --no-isolation
```

Unit tests cover environment parsing and rejection, inventory validation and conflicts, concurrent ID allocation, lifecycle state, safe logging, scanner policy, exact/expiring exceptions, failed-readiness cleanup, digest validation, source/run/staging identity, evidence freshness, artifact checksums, refusal to overwrite semantic tags, and source-tag ownership. API tests exercise real FastAPI startup/shutdown, readiness dependency failure, metadata, inventory creation/listing, HTTP status codes, safe errors, and docs. A separate integration test starts Uvicorn on a loopback port and runs the staging HTTP checks against that real process.

CI executes unit and API integration tests separately, combines coverage, and enforces at least 90% branch-aware coverage of `src/pipeline_demo_api`. That metric does not claim full coverage of delivery scripts, Docker, or external services. JUnit and coverage XML reports are uploaded. Formatting, lint, types, package build, Docker build, functional smoke, and scanner checks have no mandatory-gate error bypasses.

Container verification runs on Docker-enabled GitHub Ubuntu runners and can also run locally using `scripts.container_smoke`. It checks the expected non-root user, OCI source label, runtime build ID, environment, deterministic inventory, readiness within 45 seconds, and zero exit code on graceful shutdown. Resources are removed in a `finally` block; cleanup failures fail validation.

## Controlled failing workflows

```powershell
gh workflow run failure-demo.yml --repo gig0d/enterprise-cicd-pipeline --ref main -f scenario=quality
gh workflow run failure-demo.yml --repo gig0d/enterprise-cicd-pipeline --ref main -f scenario=security
```

These manual demonstrations are **expected to conclude with failure**. The quality fixture runs an actual isolated failing Pytest assertion. The security fixture sends a synthetic CRITICAL advisory to the real policy implementation without installing a vulnerable dependency. In both cases the dependent Docker build must be skipped. A final observer records the actual failed/skipped job results; it does not convert the failed gate to success. Ordinary CI never collects the synthetic failing test.

`rollback.yml` demonstrates a failed readiness check and recovery. Release preflight and its unit tests reject invalid digests before Docker execution. A manual release with an invalid digest can be used to observe a failed preflight and skipped simulation, without publishing or starting a container.

Tests use no public business APIs or paid services. Scanners and dependency installation require public package/advisory/registry services. If a restricted execution sandbox cannot use the system temporary directory, select an owned writable test directory with `uv run pytest --basetemp=reports/pytest-temp`; do not delete unrelated temporary files or disable gates.
