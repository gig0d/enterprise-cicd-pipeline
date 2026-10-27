"""Exercise the same HTTP checks used by staging against a real local Uvicorn process."""

import os
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.smoke import verify

pytestmark = pytest.mark.integration


def test_real_service_startup_and_http_smoke(tmp_path: Path) -> None:
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    revision = "c" * 40
    environment = os.environ | {"APP_ENVIRONMENT": "test", "APP_BUILD_ID": revision}
    with (tmp_path / "server.log").open("w", encoding="utf-8") as logs:
        process = subprocess.Popen(  # noqa: S603 - fixed executable, arguments, loopback bind
            [
                sys.executable,
                "-m",
                "uvicorn",
                "pipeline_demo_api.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--no-access-log",
            ],
            env=environment,
            stdout=logs,
            stderr=logs,
        )
        try:
            metadata = verify(f"http://127.0.0.1:{port}", revision, "test", timeout=15)
            assert metadata["version"] == "0.1.0"
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
                pytest.fail("Uvicorn did not stop within the bounded timeout.")
