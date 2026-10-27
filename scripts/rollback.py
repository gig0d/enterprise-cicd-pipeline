"""Reject a non-ready candidate and recover a different previously validated image."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from scripts.container_smoke import docker, exercise
from scripts.scan_image import scan
from scripts.verify_candidate import fetch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-run", type=int, required=True)
    parser.add_argument("--candidate-digest", required=True)
    parser.add_argument("--previous-run", type=int, required=True)
    parser.add_argument("--previous-digest", required=True)
    args = parser.parse_args()
    candidate = fetch(args.candidate_run, args.candidate_digest, Path("reports/candidate"))
    previous = fetch(args.previous_run, args.previous_digest, Path("reports/previous"))
    if candidate.digest == previous.digest or candidate.built_at <= previous.built_at:
        raise ValueError("Rollback requires a different previously validated, older image.")
    for build in (candidate, previous):
        docker("pull", build.reference, timeout=180)
    scan(previous.reference, Path("reports/previous-trivy.json"))
    try:
        exercise(
            candidate.reference,
            candidate.revision,
            "production",
            Path("reports/rejected-candidate.json"),
            timeout=3,
            readiness_failure=True,
        )
    except TimeoutError:
        pass
    else:
        raise ValueError("The controlled readiness failure unexpectedly succeeded.")
    restored = exercise(
        previous.reference, previous.revision, "production", Path("reports/restored-image.json")
    )
    record = {
        "schema_version": 1,
        "simulation": True,
        "status": "passed",
        "recovered_at": datetime.now(UTC).isoformat(),
        "candidate_rejected": True,
        "rejected": candidate.model_dump(mode="json"),
        "restored": previous.model_dump(mode="json"),
        "restored_smoke": restored,
    }
    Path("reports/rollback-record.json").write_text(
        json.dumps(record, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Ephemeral rollback simulation recovered {previous.reference}.")


if __name__ == "__main__":
    main()
