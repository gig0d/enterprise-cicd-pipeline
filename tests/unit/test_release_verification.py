import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
import pytest

from scripts.draft_release import verify_owner_tag
from scripts.evidence import REPOSITORY, BuildRecord, StageRecord
from scripts.promote import promote
from scripts.verify_candidate import artifact_json, verify_run

pytestmark = pytest.mark.unit


def evidence() -> tuple[dict[str, Any], BuildRecord, StageRecord]:
    built_at = datetime(2026, 10, 27, tzinfo=UTC)
    build = BuildRecord(
        digest="sha256:" + "a" * 64,
        revision="b" * 40,
        version="0.1.0",
        run_id=123,
        run_attempt=1,
        built_at=built_at,
    )
    stage = StageRecord(
        digest=build.digest,
        revision=build.revision,
        version=build.version,
        run_id=build.run_id,
        run_attempt=build.run_attempt,
        verified_at=built_at + timedelta(minutes=1),
    )
    run = {
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
        "path": ".github/workflows/ci.yml",
        "head_branch": "main",
        "event": "push",
        "status": "completed",
        "conclusion": "success",
        "id": 123,
        "run_attempt": 1,
        "head_sha": build.revision,
    }
    return run, build, stage


def test_validated_image_can_be_selected_without_rebuilding() -> None:
    run, build, stage = evidence()
    verify_run(run, build, stage, build.digest, "v0.1.0", now=stage.verified_at)


@pytest.mark.parametrize(
    "change",
    [
        {"event": "pull_request"},
        {"head_branch": "untrusted"},
        {"conclusion": "failure"},
        {"status": "in_progress"},
        {"path": ".github/workflows/other.yml"},
        {"head_repository": {"full_name": "other/project"}},
        {"run_attempt": 2},
        {"head_sha": "c" * 40},
    ],
)
def test_untrusted_or_mismatched_workflow_cannot_be_promoted(change: dict[str, Any]) -> None:
    run, build, stage = evidence()
    with pytest.raises(ValueError):
        verify_run(run | change, build, stage, build.digest, now=stage.verified_at)


def test_stale_evidence_wrong_digest_and_wrong_version_are_rejected() -> None:
    run, build, stage = evidence()
    with pytest.raises(ValueError, match="stale"):
        verify_run(run, build, stage, build.digest, now=build.built_at + timedelta(days=8))
    with pytest.raises(ValueError, match="digest/source/run"):
        verify_run(run, build, stage, "sha256:" + "c" * 64, now=stage.verified_at)
    with pytest.raises(ValueError, match="Release identifier"):
        verify_run(run, build, stage, build.digest, "v0.2.0", now=stage.verified_at)


def test_artifact_checksum_and_exact_archive_contents_are_verified() -> None:
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zipped:
        zipped.writestr("build-record.json", '{"synthetic":true}')
    content = archive.getvalue()
    run, _, _ = evidence()
    artifact = {
        "id": 456,
        "name": "build-record",
        "expired": False,
        "digest": "sha256:" + hashlib.sha256(content).hexdigest(),
        "workflow_run": {"head_sha": run["head_sha"]},
    }
    with httpx.Client(
        base_url="https://api.github.com",
        transport=httpx.MockTransport(lambda request: httpx.Response(200, content=content)),
    ) as client:
        assert json.loads(artifact_json(client, run, [artifact], "build-record"))["synthetic"]
        with pytest.raises(ValueError, match="checksum"):
            artifact_json(
                client, run, [artifact | {"digest": "sha256:" + "0" * 64}], "build-record"
            )
        with pytest.raises(ValueError, match="Exactly one"):
            artifact_json(client, run, [artifact, artifact], "build-record")


def test_semantic_tags_never_overwrite_a_different_image(monkeypatch: pytest.MonkeyPatch) -> None:
    from scripts import promote as module

    calls: list[tuple[str, ...]] = []

    def existing_other_digest(*args: str) -> str:
        calls.append(args)
        return "sha256:" + "c" * 64

    monkeypatch.setattr(module, "docker", existing_other_digest)
    _, build, _ = evidence()
    with pytest.raises(ValueError, match="will not be overwritten"):
        promote(build, "v0.1.0")
    assert all("create" not in call for call in calls)


def test_git_release_tag_requires_exact_owner_identity() -> None:
    _, build, _ = evidence()

    def handler(request: httpx.Request) -> httpx.Response:
        if "/git/ref/" in request.url.path:
            return httpx.Response(200, json={"object": {"type": "tag", "sha": "c" * 40}})
        return httpx.Response(
            200,
            json={
                "object": {"type": "commit", "sha": build.revision},
                "tag": "v0.1.0",
                "tagger": {"name": "Unexpected automation", "email": "synthetic@example.invalid"},
            },
        )

    with (
        httpx.Client(
            base_url="https://api.github.com", transport=httpx.MockTransport(handler)
        ) as client,
        pytest.raises(ValueError, match="tagger identity"),
    ):
        verify_owner_tag(client, "v0.1.0", build.revision)
