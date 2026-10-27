"""Strict schemas for source, image, workflow, and staging identity."""

from datetime import datetime
from typing import Annotated, Final, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints

REPOSITORY: Final = "gig0d/enterprise-cicd-pipeline"
IMAGE: Final = "ghcr.io/gig0d/enterprise-cicd-pipeline"
Digest = Annotated[str, StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$")]
Revision = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{40}$")]
Version = Annotated[str, StringConstraints(pattern=r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")]


class BuildRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    repository: Literal["gig0d/enterprise-cicd-pipeline"] = REPOSITORY
    image: Literal["ghcr.io/gig0d/enterprise-cicd-pipeline"] = IMAGE
    digest: Digest
    revision: Revision
    version: Version
    run_id: int = Field(gt=0, strict=True)
    run_attempt: int = Field(gt=0, strict=True)
    built_at: AwareDatetime
    status: Literal["validated"] = "validated"

    @property
    def reference(self) -> str:
        return f"{self.image}@{self.digest}"


class StageRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal[1] = 1
    digest: Digest
    revision: Revision
    version: Version
    run_id: int = Field(gt=0, strict=True)
    run_attempt: int = Field(gt=0, strict=True)
    verified_at: AwareDatetime
    status: Literal["passed"] = "passed"
    environment: Literal["staging"] = "staging"
    simulation: Literal[True] = True


def verify_stage(build: BuildRecord, stage: StageRecord) -> None:
    for field in ("digest", "revision", "version", "run_id", "run_attempt"):
        if getattr(build, field) != getattr(stage, field):
            raise ValueError(f"Build/staging evidence mismatch: {field}")
    if stage.verified_at < build.built_at:
        raise ValueError("Staging evidence predates the image build.")


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
