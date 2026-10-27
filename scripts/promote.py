"""Attach a semantic registry tag to an existing index without rebuilding or overwriting tags."""

import argparse
import subprocess
from pathlib import Path

from scripts.container_smoke import docker
from scripts.evidence import BuildRecord


def promote(build: BuildRecord, version: str) -> None:
    if version != f"v{build.version}":
        raise ValueError("Semantic tag must match the validated application version.")
    target = f"{build.image}:{version}"
    try:
        existing = docker(
            "buildx", "imagetools", "inspect", target, "--format", "{{.Manifest.Digest}}"
        )
    except subprocess.CalledProcessError as error:
        message = (error.stderr or "").lower()
        if "not found" not in message and "manifest unknown" not in message:
            raise
    else:
        if existing != build.digest:
            raise ValueError(
                "This semantic tag already points to another digest; it will not be overwritten."
            )
        print(f"Semantic tag already matches the validated digest: {target}")
        return
    docker(
        "buildx", "imagetools", "create", "--prefer-index=false", "--tag", target, build.reference
    )
    actual = docker("buildx", "imagetools", "inspect", target, "--format", "{{.Manifest.Digest}}")
    if actual != build.digest:
        raise ValueError("Promoted tag digest differs from the validated candidate.")
    print(f"Promoted {target} to {build.digest}; no rebuild was performed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--record", type=Path, default=Path("reports/candidate/build-record.json"))
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    promote(BuildRecord.model_validate_json(args.record.read_text(encoding="utf-8")), args.version)


if __name__ == "__main__":
    main()
