"""Simulate a production release of a previously verified immutable candidate."""

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path

from scripts.container_smoke import docker, exercise
from scripts.evidence import BuildRecord, StageRecord, verify_stage
from scripts.security_gate import enforce


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=Path("reports/candidate"))
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    build = BuildRecord.model_validate_json(
        (args.candidate / "build-record.json").read_text(encoding="utf-8")
    )
    stage = StageRecord.model_validate_json(
        (args.candidate / "staging-record.json").read_text(encoding="utf-8")
    )
    verify_stage(build, stage)
    if args.version != f"v{build.version}":
        raise ValueError("Release version must match the validated application version.")
    docker("pull", build.reference, timeout=180)
    enforce("trivy", Path("reports/release-trivy.json"))
    smoke = exercise(
        build.reference, build.revision, "production", Path("reports/release-smoke.json")
    )
    if smoke["metadata"]["version"] != build.version:
        raise ValueError("Production simulation returned the wrong application version.")
    record = {
        "schema_version": 1,
        "version": args.version,
        "candidate": build.model_dump(mode="json"),
        "released_at": datetime.now(UTC).isoformat(),
        "status": "passed",
        "simulation": True,
        "release_run_id": os.environ.get("GITHUB_RUN_ID"),
        "authorization": (
            "owner-only workflow_dispatch; environment review applies only if configured"
        ),
    }
    Path("reports/release-record.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    Path("reports/release-notes.md").write_text(
        f"# {args.version}\n\nEphemeral production release simulation passed.\n\n"
        f"- Source: `{build.revision}`\n- Image: `{build.reference}`\n"
        f"- Validated CI: https://github.com/{build.repository}/actions/runs/{build.run_id}\n"
        "- Scope: isolated runner container; no persistent or public deployment.\n",
        encoding="utf-8",
    )
    print(f"Release simulation passed for {build.reference}.")


if __name__ == "__main__":
    main()
