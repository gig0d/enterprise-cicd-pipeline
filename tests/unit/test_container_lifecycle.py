import json
from pathlib import Path
from typing import Any

import pytest

from scripts import container_smoke

pytestmark = pytest.mark.unit


def test_failed_readiness_cleans_up_and_preserves_a_failure_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    commands: list[tuple[str, ...]] = []

    def fake_docker(*args: str, **kwargs: Any) -> str:
        commands.append(args)
        if args[0] == "inspect":
            return json.dumps(
                [
                    {
                        "Config": {
                            "User": "10001:10001",
                            "Labels": {"org.opencontainers.image.revision": "d" * 40},
                        },
                        "NetworkSettings": {
                            "Ports": {"8000/tcp": [{"HostIp": "127.0.0.1", "HostPort": "12345"}]}
                        },
                    }
                ]
            )
        return ""

    def unavailable(*args: Any, **kwargs: Any) -> dict[str, Any]:
        raise TimeoutError("Synthetic readiness failure")

    monkeypatch.setattr(container_smoke, "docker", fake_docker)
    monkeypatch.setattr(container_smoke, "verify", unavailable)
    report = tmp_path / "failed.json"
    with pytest.raises(TimeoutError, match="readiness failure"):
        container_smoke.exercise("test-image", "d" * 40, "staging", report)
    assert any(command[:2] == ("rm", "--force") for command in commands)
    assert any(command[:2] == ("network", "rm") for command in commands)
    assert json.loads(report.read_text(encoding="utf-8"))["status"] == "failed"
