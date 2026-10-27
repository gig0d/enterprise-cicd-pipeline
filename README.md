# Enterprise CI/CD Pipeline

A Python 3.13 inventory API used to demonstrate secure, reproducible delivery with GitHub Actions and Docker. The application is intentionally small; the delivery process is the focus.

Implementation and verification are in progress. See `AGENTS.md` for repository engineering rules. Completed architecture, setup, security, release, and rollback runbooks will be added as their implementations are validated.

## Local development (PowerShell)

Install Python 3.13 and [uv](https://docs.astral.sh/uv/getting-started/installation/), then:

```powershell
uv sync --locked
uv run uvicorn pipeline_demo_api.main:app --host 127.0.0.1 --port 8000 --no-access-log
```

Open http://127.0.0.1:8000/docs. The process-local inventory starts with two deterministic items and resets on restart. Run exactly one worker; stores are not shared across processes.

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov --cov-report=term-missing --cov-report=xml
```
