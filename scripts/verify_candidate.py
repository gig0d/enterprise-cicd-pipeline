"""Retrieve digest-bound evidence from a successful trusted CI run through GitHub's API."""

import argparse
import hashlib
import io
import json
import os
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from pydantic import TypeAdapter

from scripts.evidence import REPOSITORY, BuildRecord, Digest, StageRecord, verify_stage


def verify_run(
    run: dict[str, Any],
    build: BuildRecord,
    stage: StageRecord,
    digest: str,
    version: str | None = None,
    now: datetime | None = None,
) -> None:
    TypeAdapter(Digest).validate_python(digest)
    current = now or datetime.now(UTC)
    if (
        run.get("repository", {}).get("full_name") != REPOSITORY
        or run.get("head_repository", {}).get("full_name") != REPOSITORY
        or run.get("path") != ".github/workflows/ci.yml"
        or run.get("head_branch") != "main"
        or run.get("event") not in {"push", "workflow_dispatch"}
        or run.get("status") != "completed"
        or run.get("conclusion") != "success"
    ):
        raise ValueError("Candidate is not a successful trusted main CI run.")
    if (
        run["id"] != build.run_id
        or run["run_attempt"] != build.run_attempt
        or run["head_sha"] != build.revision
        or digest != build.digest
    ):
        raise ValueError("Requested digest/source/run does not match the build evidence.")
    if version is not None and version != f"v{build.version}":
        raise ValueError(
            "Release identifier must be vMAJOR.MINOR.PATCH and match the application version."
        )
    verify_stage(build, stage)
    for timestamp in (build.built_at, stage.verified_at):
        age = current - timestamp
        if age > timedelta(days=7) or age < -timedelta(minutes=5):
            raise ValueError("Candidate evidence is stale or has an invalid future timestamp.")


def artifact_json(
    client: httpx.Client,
    run: dict[str, Any],
    artifacts: list[dict[str, Any]],
    name: str,
) -> str:
    matches = [artifact for artifact in artifacts if artifact["name"] == name]
    if len(matches) != 1 or matches[0]["expired"]:
        raise ValueError(f"Exactly one unexpired {name} artifact is required.")
    artifact = matches[0]
    if artifact.get("workflow_run", {}).get("head_sha") != run["head_sha"]:
        raise ValueError("Artifact source revision does not match the selected CI run.")
    response = client.get(
        f"/repos/{REPOSITORY}/actions/artifacts/{int(artifact['id'])}/zip", follow_redirects=True
    )
    response.raise_for_status()
    archive = response.content
    if len(archive) > 1_000_000:
        raise ValueError("Evidence artifact exceeds its size limit.")
    if artifact.get("digest") != "sha256:" + hashlib.sha256(archive).hexdigest():
        raise ValueError("GitHub artifact archive checksum verification failed.")
    with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
        filename = name + ".json"
        if zipped.namelist() != [filename] or zipped.getinfo(filename).file_size > 100_000:
            raise ValueError("Unexpected contents in the evidence artifact.")
        return zipped.read(filename).decode("utf-8")


def fetch(run_id: int, digest: str, output: Path, version: str | None = None) -> BuildRecord:
    TypeAdapter(Digest).validate_python(digest)
    if run_id <= 0:
        raise ValueError("CI run ID must be positive.")
    token = os.environ.get("GH_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN with repository Actions read permission is required.")
    with httpx.Client(
        base_url="https://api.github.com",
        timeout=30,
        trust_env=False,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    ) as client:
        response = client.get(f"/repos/{REPOSITORY}/actions/runs/{run_id}")
        response.raise_for_status()
        run = response.json()
        if run.get("status") != "completed" or run.get("conclusion") != "success":
            raise ValueError("A completed successful CI run is required before promotion.")
        response = client.get(
            f"/repos/{REPOSITORY}/actions/runs/{run_id}/artifacts", params={"per_page": 100}
        )
        response.raise_for_status()
        listing = response.json()
        if listing["total_count"] > 100:
            raise ValueError("Unexpected number of CI artifacts; refusing ambiguous evidence.")
        artifacts = listing["artifacts"]
        build = BuildRecord.model_validate_json(
            artifact_json(client, run, artifacts, "build-record")
        )
        stage = StageRecord.model_validate_json(
            artifact_json(client, run, artifacts, "staging-record")
        )
    verify_run(run, build, stage, digest, version)
    output.mkdir(parents=True, exist_ok=True)
    (output / "build-record.json").write_text(
        build.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (output / "staging-record.json").write_text(
        stage.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    (output / "source-run.json").write_text(
        json.dumps(
            {
                "id": run["id"],
                "run_attempt": run["run_attempt"],
                "head_sha": run["head_sha"],
                "conclusion": run["conclusion"],
                "html_url": run["html_url"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Verified trusted CI and staging evidence for {build.reference}.")
    return build


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--version")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/candidate"))
    args = parser.parse_args()
    fetch(args.run_id, args.digest, args.output_dir, args.version)


if __name__ == "__main__":
    main()
