"""Create a GitHub draft release only for an owner-tagged, validated simulation."""

import argparse
import json
import os
from pathlib import Path

import httpx
from pydantic import TypeAdapter

from scripts.evidence import REPOSITORY, BuildRecord, Revision
from scripts.verify_candidate import fetch


def verify_owner_tag(client: httpx.Client, version: str, revision: str) -> None:
    response = client.get(f"/repos/{REPOSITORY}/git/ref/tags/{version}")
    response.raise_for_status()
    reference = response.json()["object"]
    if reference["type"] != "tag":
        raise ValueError("An annotated owner-created release tag is required.")
    tag_sha = TypeAdapter(Revision).validate_python(reference["sha"])
    response = client.get(f"/repos/{REPOSITORY}/git/tags/{tag_sha}")
    response.raise_for_status()
    tag = response.json()
    if (
        tag["object"]["type"] != "commit"
        or tag["object"]["sha"] != revision
        or tag["tagger"]["name"] != "Giovanny Alvarado Barrantes"
        or tag["tagger"]["email"] != "gioab0411@gmail.com"
        or tag["tag"] != version
    ):
        raise ValueError("The release tag has the wrong source revision or tagger identity.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", type=int, required=True)
    parser.add_argument("--digest", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    build = fetch(args.run_id, args.digest, Path("reports/candidate"), args.version)
    record = json.loads(Path("reports/release-record.json").read_text(encoding="utf-8"))
    recorded = BuildRecord.model_validate(record["candidate"])
    if (
        recorded != build
        or record["status"] != "passed"
        or record["simulation"] is not True
        or record["version"] != args.version
        or record["release_run_id"] != os.environ["GITHUB_RUN_ID"]
    ):
        raise ValueError("A matching successful simulation from this release run is required.")
    with httpx.Client(
        base_url="https://api.github.com",
        timeout=30,
        trust_env=False,
        headers={
            "Authorization": f"Bearer {os.environ['GH_TOKEN']}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    ) as client:
        verify_owner_tag(client, args.version, build.revision)
        existing = client.get(f"/repos/{REPOSITORY}/releases/tags/{args.version}")
        if existing.status_code != 404:
            existing.raise_for_status()
            raise ValueError("A release already exists for this tag; it will not be overwritten.")
        response = client.post(
            f"/repos/{REPOSITORY}/releases",
            json={
                "tag_name": args.version,
                "target_commitish": build.revision,
                "name": args.version,
                "body": Path("reports/release-notes.md").read_text(encoding="utf-8"),
                "draft": True,
            },
        )
        response.raise_for_status()
        release = response.json()
        for filename in ("release-record.json", "release-notes.md"):
            response = client.post(
                f"https://uploads.github.com/repos/{REPOSITORY}/releases/{int(release['id'])}/assets",
                params={"name": filename},
                content=(Path("reports") / filename).read_bytes(),
                headers={"Content-Type": "application/octet-stream"},
            )
            response.raise_for_status()
        print(f"Draft release created for owner review: {release['html_url']}")


if __name__ == "__main__":
    main()
