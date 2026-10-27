"""Verify the exact published build on an ephemeral staging container."""

import argparse
import os
from datetime import UTC, datetime
from pathlib import Path

from scripts.container_smoke import docker, exercise
from scripts.evidence import BuildRecord, StageRecord


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--digest", required=True)
    args = parser.parse_args()
    build = BuildRecord.model_validate_json(Path("build-record.json").read_text(encoding="utf-8"))
    if (
        args.digest != build.digest
        or build.revision != os.environ["GITHUB_SHA"]
        or build.run_id != int(os.environ["GITHUB_RUN_ID"])
        or build.run_attempt != int(os.environ["GITHUB_RUN_ATTEMPT"])
    ):
        raise ValueError("Staging candidate does not match this trusted workflow run.")
    docker("pull", build.reference, timeout=180)
    smoke = exercise(build.reference, build.revision, "staging", Path("reports/staging-smoke.json"))
    if smoke["metadata"]["version"] != build.version:
        raise ValueError("Staging API version does not match the build record.")
    record = StageRecord(
        digest=build.digest,
        revision=build.revision,
        version=build.version,
        run_id=build.run_id,
        run_attempt=build.run_attempt,
        verified_at=datetime.now(UTC),
    )
    Path("staging-record.json").write_text(
        record.model_dump_json(indent=2) + "\n", encoding="utf-8"
    )
    print(f"Ephemeral staging passed for {build.reference}.")


if __name__ == "__main__":
    main()
