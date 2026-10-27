from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from pydantic import ValidationError

from scripts.evidence import BuildRecord, StageRecord, verify_stage

pytestmark = pytest.mark.unit


def build_data() -> dict[str, Any]:
    return {
        "digest": "sha256:" + "a" * 64,
        "revision": "b" * 40,
        "version": "0.1.0",
        "run_id": 123,
        "run_attempt": 1,
        "built_at": datetime.now(UTC),
    }


@pytest.mark.parametrize(
    "digest", ["latest", "sha256:abc", "sha256:" + "A" * 64, "other@sha256:" + "a" * 64]
)
def test_invalid_digest_is_rejected_before_docker(digest: str) -> None:
    with pytest.raises(ValidationError):
        BuildRecord.model_validate(build_data() | {"digest": digest})


def test_matching_staging_identity_is_required() -> None:
    data = build_data()
    build = BuildRecord.model_validate(data)
    stage_data = {key: value for key, value in data.items() if key != "built_at"}
    stage = StageRecord.model_validate(
        stage_data | {"verified_at": data["built_at"] + timedelta(seconds=1)}
    )
    verify_stage(build, stage)
    with pytest.raises(ValueError, match="digest"):
        verify_stage(build, stage.model_copy(update={"digest": "sha256:" + "c" * 64}))
    with pytest.raises(ValueError, match="predates"):
        verify_stage(
            build, stage.model_copy(update={"verified_at": data["built_at"] - timedelta(seconds=1)})
        )


def test_image_repository_and_evidence_status_cannot_be_substituted() -> None:
    with pytest.raises(ValidationError):
        BuildRecord.model_validate(build_data() | {"image": "ghcr.io/other/project"})
    with pytest.raises(ValidationError):
        BuildRecord.model_validate(build_data() | {"status": "failed"})
