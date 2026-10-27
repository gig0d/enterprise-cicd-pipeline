# Troubleshooting

| Symptom | Resolution |
| --- | --- |
| Python/uv is unavailable | Install Python 3.13, reopen PowerShell, verify the interpreter, and install the hash-pinned bootstrap from the README. |
| Locked sync/export fails | Review the dependency change, update the lock/export together, audit, and commit under the owner identity. Do not remove `--locked` in CI. |
| Formatting/types fail | Inspect Ruff/MyPy output and fix the source; do not weaken mandatory checks. |
| Tests cannot import `scripts` | Run from the repository root with the committed Pytest configuration and a fresh locked sync. |
| Restricted temp/cache permissions | Select an owned path: `uv run pytest --basetemp=reports/pytest-temp -o cache_dir=reports/pytest-cache`. Do not delete unrelated system temp files. |
| Docker is unavailable | Install/start Docker Desktop with Linux containers. Inspect `docker version` and `docker info`. Distinguish local availability from verified GitHub runner checks. |
| Port 8000 is occupied | Stop the owning development process or choose another host port. Smoke tests allocate a random loopback port. |
| Readiness times out | Inspect saved logs/JSON, startup configuration, image revision, networking, and resource limits. Liveness is insufficient. |
| Container port is missing | Use a dedicated standard bridge with loopback publishing; internal Docker networks may not create that mapping. |
| Trivy blocks an image | Inspect blocking advisories/fixes, update dependencies/base digest or remove unnecessary tools, then rerun. Keep complete reports and use only reviewed exact expiring exceptions. |
| Advisory/database download fails | Treat it as a failed check and retry after service recovery. An absent report is not a clean scan. |
| Publishing is skipped | Check repository/ref/event conditions and the owner-approved `ENABLE_GHCR_PUBLISH` variable. |
| GHCR denies access | Verify package linkage/Actions access, scoped job permission, and login. Never print tokens or grant broad default write access. |
| Release rejects evidence | Check successful trusted CI, matching records, run attempt, digest, SHA, version, timestamps, and artifact expiry. |
| Release waits for review | The authorized owner must review the production deployment. The workflow cannot bypass approval rules. |
| Draft rejects a source tag | Use an annotated tag at the exact candidate revision with the required owner name/email. Do not move existing tags or create source commits in CI. |
| Push is rejected | Inspect protection, use a feature branch and PR, preserve checks, and never force push. |

Regenerate the production export after a reviewed lock update:

```powershell
uv export --frozen --no-dev --no-emit-project --no-header --quiet --output-file requirements.txt
uv run python -m scripts.check_repository
```

Inspect the specific failed Actions job and its evidence before rerunning. A successful dispatch, push, registry upload, or workflow startup does not prove full pipeline or deployment success.
