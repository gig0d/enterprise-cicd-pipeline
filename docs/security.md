# Security policy and threat model

The delivery system treats pull request source as untrusted. CI uses disposable GitHub-hosted runners, a read-only token, no repository secrets, and no `pull_request_target` trigger. Only the trusted `main` publishing job may request package write permission. Checkout never persists credentials. Workflow payloads enter commands through environment variables or discrete process arguments, never executable expression interpolation.

## Blocking policies

| Gate | Blocking behavior | Evidence |
| --- | --- | --- |
| Python dependency audit | Every known advisory in the locked production and development dependencies blocks, regardless of severity. Skipped dependencies, scanner errors, and missing reports fail closed. | `dependency-security-evidence/pip-audit.json` |
| Secrets | Any Gitleaks finding in checked-out history blocks; reports redact secret values. | `secret-security-evidence/gitleaks.json` |
| Container | HIGH or CRITICAL vulnerabilities with an available fixed version block. Unfixed and lower severity findings remain in the complete report for review. | `container-evidence/trivy.json` |
| Quality | Formatting, lint, strict types, functional tests, 90% application branch coverage, package build, Docker build, and container smoke checks block dependent jobs. | Quality and container artifacts |

The image is not claimed to be vulnerability-free. OS advisories without an available fix require monitoring; the owner should review all HIGH/CRITICAL findings before a release, even when the automated fixability policy allows them. Scanner databases and advisory services are live network dependencies; an outage is a failed check, not a clean scan. Re-run the complete pipeline when evidence is older than the release freshness limit.

## Exceptions

`security/exceptions.json` starts empty. A change requires owner review and an exact scanner (`pip-audit` or `trivy`), advisory `id`, `package`, nonempty `reason`, accountable `owner`, and ISO `expires` date. Wildcards and expired entries are rejected. All raw findings remain in reports. Remove an exception when fixed or before its expiry; never add broad scanner ignore flags. Gitleaks exceptions are not configured; rotate leaked credentials, remove the exposure through an owner-approved procedure, and investigate affected history.

Synthetic fixtures in tests use `DEMO-ADVISORY-*`, not real vulnerable dependencies. They verify the blocking policy without installing insecure packages.

## Supply-chain controls

Production dependencies are exported from `uv.lock` into fully pinned, hashed `requirements.txt`. `scripts.check_repository` rejects a stale export. Docker installs only matching binary wheels with `--require-hashes`, then removes pip and its bundled bootstrap copy from the runtime image. The official Python image is pinned by manifest digest. A weekly read-only audit checks current Python advisories; dependency, base-image, scanner, and Action updates are applied manually and validated under the required owner identity. Automated version-update PRs are intentionally disabled to avoid creating development commits under bot identities. Every external Action reference uses an upstream-verified 40-character commit SHA. Scanner binaries use official release assets and committed SHA-256 checksums in `tools.lock.json`; checksums protect against changed downloads but are not independent publisher signatures.

## Attack surfaces and residual risk

| Surface | Mitigation | Residual risk |
| --- | --- | --- |
| Malicious PR | No privileged credentials; separate jobs; publisher checks event, repository, and branch. | Untrusted code has runner network access and can forge its own logs. PR artifacts are never promotion evidence. |
| Compromised dependency or Action | Hashes, full commit pins, audit, reviewed updates, read-only defaults. | Scanners cannot identify every malicious package or zero-day. |
| Mutable tag or candidate substitution | Digest-only staging and release; source label and runtime revision checks; same-run build/staging records. | Repository writers can change workflow policy; branch protection is an owner-controlled setting. |
| Stale or forged release evidence | Verify repository, successful trusted CI run, run attempt, source SHA, artifact fields, and evidence freshness against GitHub. | GitHub and the owner's account are trust roots. |
| Container breakout | Non-root user, read-only filesystem, dropped capabilities, no-new-privileges, bounded memory/processes, loopback publishing, isolated network. | The Docker daemon remains privileged infrastructure on a disposable runner. |
| Log disclosure | No request bodies, headers, credentials, or environment dumps; route templates in request logs; redacted secret reports. | Review all artifacts before sharing them outside the repository. |

Repository settings are tracked separately in `docs/github-setup.md`. Workflow YAML does not prove branch protection, reviewer approval, or account security is enabled.

## Official references

- [GitHub secure use reference](https://docs.github.com/en/actions/reference/security/secure-use)
- [GitHub token permission configuration](https://docs.github.com/en/actions/how-tos/security-for-github-actions/security-guides/automatic-token-authentication)
- [Docker image build recommendations](https://docs.docker.com/build/building/best-practices/)
- [pip-audit](https://github.com/pypa/pip-audit)
- [Trivy vulnerability scanning](https://trivy.dev/latest/docs/scanner/vulnerability/)
- [Gitleaks](https://github.com/gitleaks/gitleaks)
