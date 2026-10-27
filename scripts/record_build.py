"""Write build metadata only after registry-digest smoke and vulnerability checks pass."""

import argparse
import json
import os
import tomllib
from datetime import UTC, datetime
from pathlib import Path

from scripts.evidence import IMAGE, BuildRecord, parse_time
from scripts.security_gate import enforce


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["metadata", "record"])
    parser.add_argument("--digest")
    args = parser.parse_args()
    version = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    if args.command == "metadata":
        with Path(os.environ["GITHUB_OUTPUT"]).open("a", encoding="utf-8") as output:
            output.write(f"version={version}\nbuilt_at={datetime.now(UTC).isoformat()}\n")
        return
    record = BuildRecord(
        digest=args.digest,
        revision=os.environ["GITHUB_SHA"],
        version=version,
        run_id=int(os.environ["GITHUB_RUN_ID"]),
        run_attempt=int(os.environ["GITHUB_RUN_ATTEMPT"]),
        built_at=parse_time(os.environ["BUILD_DATE"]),
    )
    smoke = json.loads(Path("reports/published-smoke.json").read_text(encoding="utf-8"))
    if (
        smoke["status"] != "passed"
        or smoke["image"] != record.reference
        or smoke["revision"] != record.revision
        or smoke["metadata"]["version"] != record.version
    ):
        raise ValueError("Published-image smoke evidence does not match this candidate.")
    enforce("trivy", Path("reports/published-trivy.json"))
    Path("build-record.json").write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(f"Recorded validated image: {IMAGE}@{record.digest}")


if __name__ == "__main__":
    main()
