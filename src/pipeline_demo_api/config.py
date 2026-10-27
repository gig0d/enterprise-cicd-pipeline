"""Validated configuration, read only from explicitly prefixed environment variables."""

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from pipeline_demo_api import __version__


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="APP_", extra="ignore", frozen=True)

    name: Literal["pipeline-demo-api"] = "pipeline-demo-api"
    version: str = Field(default=__version__, pattern=r"^\d+\.\d+\.\d+(?:[-+][a-zA-Z0-9.-]+)?$")
    environment: Literal["development", "test", "staging", "production"] = "development"
    build_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9._-]{1,128}$")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
