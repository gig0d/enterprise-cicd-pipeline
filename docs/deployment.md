# Deployment and ephemeral staging

This project validates containers on isolated GitHub-hosted runners. It does not provide a persistent server or a public staging URL. Each run creates a dedicated bridge network and a container with a randomly allocated port bound only to `127.0.0.1`. The container uses UID/GID 10001, a read-only filesystem, a bounded temporary filesystem, no Linux capabilities, no-new-privileges, and explicit resource limits.

`ci.yml` publishes only when `ENABLE_GHCR_PUBLISH` is `true`, the repository is exactly `gig0d/enterprise-cicd-pipeline`, the ref is `main`, and the event is a trusted push or manual dispatch. Quality, dependency, secret, Docker, and container-security gates must succeed first. The publishing job requests package write permission; workflows default to read-only. The owner authorized this scoped publication and activation was verified on 2026-10-27. No service is publicly deployed.

The registry candidate is built with a source-SHA tag, OCI revision/version/time labels, BuildKit provenance, and an SPDX SBOM. The published image is pulled by digest, smoke-tested again, and scanned again. Only then is `build-record.json` uploaded. This separate registry build is the delivery candidate; the earlier PR-compatible container build is validation only. After this candidate is built, staging, release, and rollback use it without rebuilding.

The reusable `staging.yml` retrieves the build record from the same CI run. `scripts.stage` verifies its digest, revision, run ID, and attempt before pulling the image by digest. HTTP checks verify liveness, real store readiness, version/source/environment metadata, deterministic seed data, creation, listing, duplicate rejection, validation errors, and API docs. Shutdown must exit with code zero. Logs and JSON diagnostics are collected and owned resources are removed even when readiness fails. Successful staging writes a second record bound to the same image and source identity.

## Local PowerShell verification

Install Docker Desktop, switch to Linux containers, start the engine, and install Python 3.13 and uv. No Make installation is required.

```powershell
uv sync --locked
$revision = git rev-parse HEAD
docker build --build-arg "VCS_REF=$revision" -t pipeline-demo-api:local .
uv run python -m scripts.container_smoke --image pipeline-demo-api:local --revision $revision --environment staging
```

For an interactive development container:

```powershell
$env:BUILD_ID = git rev-parse HEAD
docker compose up --build --wait
Invoke-RestMethod http://127.0.0.1:8000/health/ready
docker compose down
```

The local image tag identifies a development build, not a validated registry candidate. For a published private image, authenticate with `docker login ghcr.io` using an appropriately scoped credential via stdin, then pass the exact `ghcr.io/gig0d/enterprise-cicd-pipeline@sha256:...` reference and matching source SHA to `scripts.container_smoke`. Never paste a credential into a shell command or documentation.

GitHub Environments are metadata and policy boundaries. A job's `environment: staging` declaration does not prove reviewer or source restrictions were configured. See `github-setup.md` for verified settings and manual configuration.
