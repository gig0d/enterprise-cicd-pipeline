# Verification evidence

Verified on **2026-10-27**. These are observed executions, not projected results. Workflow artifacts provide detailed logs, scanner reports, records, and checksums. Intentional failure demonstrations are expected to appear red.

## Local checks

Python 3.13.18: **51 tests passed**. Measured branch-aware coverage of `src/pipeline_demo_api` was **100%**, above the enforced 90% minimum. This does not claim 100% delivery-script or infrastructure coverage. Ruff format/lint, strict MyPy, actionlint, production-export/workflow invariants, and locked wheel/source builds passed. pip-audit reported no known vulnerabilities for the applicable locked runtime/development dependency set at audit time.

A separate fresh Python 3.13 environment installed only hashed production dependencies and the non-editable wheel. Uvicorn ran outside the source directory and passed the complete HTTP smoke suite, confirming that application imports did not depend on the editable development checkout. The source distribution and wheel were inspected; local tools, virtual environments, Git internals, and `.env` files were excluded. Relative documentation links and evidence JSON were also checked.

Docker was unavailable on the development machine. Docker build, runtime, HTTP, shutdown, scanning, registry, staging, and recovery results below were verified on actual GitHub Ubuntu runners. The local integration suite also started Uvicorn and exercised real loopback HTTP.

## Observed GitHub runs

| Verification | Actual result | Evidence |
| --- | --- | --- |
| Complete first registry candidate | Success: quality, security, Docker, published-image verification, staging | [CI 40465250945](https://github.com/gig0d/enterprise-cicd-pipeline/actions/runs/40465250945) |
| Complete second registry candidate | Success, including hash-pinned bootstrap/build tooling | [CI 40466321010](https://github.com/gig0d/enterprise-cicd-pipeline/actions/runs/40466321010) |
| Production release simulation | Success using the first candidate's unchanged digest; semantic tag/draft jobs skipped | [Release 40466351814](https://github.com/gig0d/enterprise-cicd-pipeline/actions/runs/40466351814) |
| Controlled test failure | Expected failure: real assertion failed, dependent Docker build skipped, observer passed | [Quality failure 40466354461](https://github.com/gig0d/enterprise-cicd-pipeline/actions/runs/40466354461) |
| Controlled security-policy failure | Expected failure: synthetic CRITICAL advisory blocked, dependent build skipped, observer passed | [Security failure 40466357029](https://github.com/gig0d/enterprise-cicd-pipeline/actions/runs/40466357029) |
| Invalid digest | Expected failure in preflight before Docker; simulation/tag/draft jobs skipped | [Invalid candidate 40466703896](https://github.com/gig0d/enterprise-cicd-pipeline/actions/runs/40466703896) |
| Isolated rollback | Success: newer candidate rejected on readiness timeout; older digest rescanned and recovered | [Rollback 40466738100](https://github.com/gig0d/enterprise-cicd-pipeline/actions/runs/40466738100) |

The release simulation ran under the owner-only manual-dispatch control before required production reviewers were configured. Afterward, the owner explicitly authorized the environment rules below, and the API confirmed them. This report does not claim that earlier execution passed a reviewer rule which did not yet exist.

## Validated immutable candidates

Repository: `ghcr.io/gig0d/enterprise-cicd-pipeline`; application version: `0.1.0` for both candidates.

| Role in recovery demonstration | Source revision | Image digest |
| --- | --- | --- |
| Previously validated recovery image | `792647766b5440b064a7a6239c2bbd3f2b1d8c02` | `sha256:d44f97b24e4def3de43978d32e7c1ffe12f9d2679a014f90bafb4c2636fe3cac` |
| Newer candidate subjected to controlled readiness failure | `0cd0939ffcb8dc97a265010e755e964c0b92bcea` | `sha256:127b7f57bae0a57102fad903939dd6b0422c2d44f1739ec855409d1acd2991e4` |

[Saved build/staging records](evidence/validated-candidates.json) were copied from actual artifacts and schema-validated for matching run, attempt, revision, version, digest, and time ordering. Release preflight was also run against the real GitHub artifact archives and verified their checksums. Nonempty provenance and SBOM JSON were inspected in `published-image-evidence`. These reference candidates remain historical evidence; new releases must independently satisfy the seven-day freshness policy and current scanner gates.

## Settings verified through GitHub's API

| Setting | Observed state |
| --- | --- |
| Default workflow token | Read-only; workflow PR creation/approval disabled |
| GHCR activation | Owner-authorized `ENABLE_GHCR_PUBLISH=true`, read back after setting |
| Staging environment | Only branch `main`; administrator bypass disabled |
| Production environment | Only branch `main`; required reviewer `gig0d`; administrator bypass disabled; owner self-review allowed |
| `main` branch protection/rulesets | Not configured; precise recommendations and setup steps are documented, not claimed active |
| GitHub Releases/source tags | None created during verification; optional draft and semantic-tag flows are implemented but were not exercised |

The [environment snapshot](evidence/environment-settings.json) contains sanitized API read-back data, not credentials. See [GitHub setup](github-setup.md) for configuration details and limitations.

All development commits created by the implementation were inspected for the exact author and committer `Giovanny Alvarado Barrantes <gioab0411@gmail.com>`, Conventional Commit messages, and absence of AI coauthor trailers. Pushes were verified against `origin/main`. An automatically generated dependency PR was closed without merging; automatic version-update commits were disabled. No history was force-pushed or rewritten.

Staging, release, and recovery were isolated temporary containers. No persistent/public service, paid infrastructure, performance improvement, uptime, or real production rollback is claimed.
