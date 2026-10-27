import pytest
from pydantic import ValidationError

from pipeline_demo_api.config import Settings

pytestmark = pytest.mark.unit


def test_configuration_reads_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENVIRONMENT", "staging")
    monkeypatch.setenv("APP_BUILD_ID", "b" * 40)
    monkeypatch.setenv("UNRELATED_SECRET", "synthetic-do-not-expose")
    settings = Settings()
    assert settings.environment == "staging"
    assert settings.build_id == "b" * 40
    assert "UNRELATED_SECRET" not in settings.model_dump()


@pytest.mark.parametrize(
    ("name", "value"),
    [("APP_ENVIRONMENT", "unknown"), ("APP_BUILD_ID", "unsafe\nvalue"), ("APP_VERSION", "bad")],
)
def test_invalid_configuration_fails_startup(
    monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError):
        Settings()
