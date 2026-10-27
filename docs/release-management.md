# Release management

Releases use stable semantic identifiers (`vMAJOR.MINOR.PATCH`), source-SHA image tags, and immutable registry digests. `latest` is never a release identity. The validated registry image is built once; staging and production simulation pull that digest. Semantic tagging copies the existing image index, including its attestations, and verifies the resulting digest without rebuilding.

## Authorization and evidence

`release.yml` accepts only manual dispatches on `main` initiated and rerun by `gig0d`. The default operation is an isolated production simulation with read-only package access. Before the production job, and again after any environment-approval wait, it:

1. Validates the digest format and version identifier.
2. Queries GitHub for a completed successful `ci.yml` run from this repository's `main`, triggered by push or manual dispatch.
3. Retrieves exactly one unexpired build record and staging record from that run and verifies the SHA-256 checksum of each artifact archive against GitHub's metadata.
4. Matches revision, image repository, digest, version, run ID, run attempt, and staging identity.
5. Rejects evidence older than seven days or implausibly in the future.

The production job rescans the exact image with a current vulnerability database and runs the functional smoke suite in a loopback-only container using `APP_ENVIRONMENT=production`. It records the source, digest, originating CI run, release workflow run, version, timestamp, and actual verification outcome. No persistent/public production service is created.

`environment: production` allows GitHub reviewer rules to apply when configured. Without those rules, the authorization mechanism is owner-only manual dispatch; this is **not** GitHub-enforced reviewer approval. See `github-setup.md` for the observed configuration and approval setup steps. The workflow never approves its own pending deployment through the API.

The owner-approved production reviewer rule and main-only source restriction were configured and read back on 2026-10-27, after the initial successful simulation. Subsequent production jobs require that review. The historical run is documented with the control that actually existed at execution time.

## Run a simulation (PowerShell)

Select a successful CI run that contains both `build-record` and `staging-record`. Download its records, inspect the source and digest, and use those exact values:

```powershell
gh run list --repo gig0d/enterprise-cicd-pipeline --workflow ci.yml
$ciRun = '<successful-run-id>'
gh run download $ciRun --repo gig0d/enterprise-cicd-pipeline --name build-record --dir reports/candidate
gh run download $ciRun --repo gig0d/enterprise-cicd-pipeline --name staging-record --dir reports/candidate
$build = Get-Content reports/candidate/build-record.json -Raw | ConvertFrom-Json
gh workflow run release.yml --repo gig0d/enterprise-cicd-pipeline --ref main -f "ci_run_id=$ciRun" -f "digest=$($build.digest)" -f "version=v$($build.version)"
```

Inspect the new run and `release-evidence` artifact; dispatch acceptance does not prove release success. An invalid digest, failed run, absent staging record, stale evidence, or version mismatch must stop preflight and skip simulation.

## Explicit semantic promotion

After reviewing the candidate and authorizing package write access for the manual promotion job, dispatch the same workflow with `-F publish_tag=true`. `ENABLE_GHCR_PUBLISH` must already be enabled. The semantic-tag job uses the production environment and revalidates the candidate. It refuses to overwrite a tag pointing at a different digest. An identical existing tag is an idempotent success.

## Git tags and GitHub draft releases

Prepare a new application version by updating `pyproject.toml`, `src/pipeline_demo_api/__init__.py`, Docker/Compose version defaults, and relevant API expectations together. Run the full pipeline before selecting that version's validated image. Do not relabel an old application version as a different semantic release.

Source tags must be created by the owner, never by a CI bot. After inspecting the validated source revision and effective Git identity:

```powershell
git var GIT_AUTHOR_IDENT
git var GIT_COMMITTER_IDENT
$revision = $build.revision
git tag -a "v$($build.version)" $revision -m "Release v$($build.version)"
git show --no-patch "v$($build.version)"
git push origin "refs/tags/v$($build.version)"
```

Do not reuse or move an existing release tag. The optional `-F create_draft=true` dispatch input explicitly authorizes the separate contents-write job to create a GitHub **draft** release after simulation. It verifies the annotated source tag, source revision, and tagger name/email against the required owner identity. It attaches the release record and notes. It does not create source commits or tags. Publishing the draft publicly remains an owner action.

BuildKit provenance and SPDX SBOM metadata are attached to the registry image and copied into CI artifacts. These are BuildKit attestations; the project does not claim an independently verified GitHub/Sigstore signature. Reports expire after 30 days for CI and 90 days for release/recovery; archive evidence externally if longer retention is needed.
