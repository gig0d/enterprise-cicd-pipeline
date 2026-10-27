"""Start an isolated loopback-only container, verify it, and remove all owned resources."""

import argparse
import json
import shutil
import subprocess
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from scripts.smoke import verify


def docker(*args: str, timeout: int = 120, include_stderr: bool = False) -> str:
    executable = shutil.which("docker")
    if executable is None:
        raise RuntimeError("Docker is required; install Docker Desktop with Linux containers.")
    result = subprocess.run(  # noqa: S603,S607 - fixed docker CLI; arguments never use a shell
        [executable, *args], capture_output=True, text=True, check=True, timeout=timeout
    )
    return (result.stdout + (result.stderr if include_stderr else "")).strip()


def exercise(
    image: str,
    revision: str,
    environment: str,
    report: Path,
    timeout: float = 45,
    readiness_failure: bool = False,
) -> dict[str, Any]:
    name = "pipeline-" + uuid.uuid4().hex[:12]
    report.parent.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "schema_version": 1,
        "image": image,
        "revision": revision,
        "environment": environment,
        "verified_at": datetime.now(UTC).isoformat(),
        "status": "failed",
        "simulation": True,
    }
    network_created = False
    started = False
    try:
        docker("network", "create", name)
        network_created = True
        command = [
            "run",
            "--detach",
            "--name",
            name,
            "--network",
            name,
            "--publish",
            "127.0.0.1::8000",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--pids-limit=128",
            "--memory=256m",
            "--cpus=1",
            "--tmpfs=/tmp:rw,noexec,nosuid,size=16m",
            "--stop-timeout=10",
            "--env",
            f"APP_ENVIRONMENT={environment}",
            image,
        ]
        if readiness_failure:
            # Purpose-built non-HTTP process; no vulnerable dependencies or exposed service.
            command.extend(["python", "-c", "import time; time.sleep(300)"])
        started = True
        docker(*command)
        inspected = json.loads(docker("inspect", name))[0]
        config = inspected["Config"]
        if config["User"] != "10001:10001":
            raise ValueError("Container is not configured with the expected non-root user.")
        if config["Labels"].get("org.opencontainers.image.revision") != revision:
            raise ValueError("Image revision label does not match the expected source revision.")
        mappings = inspected["NetworkSettings"]["Ports"].get("8000/tcp")
        if not mappings:
            raise ValueError("Docker did not publish the expected loopback HTTP port.")
        address = mappings[0]
        if address["HostIp"] != "127.0.0.1":
            raise ValueError("Container port must be published only on loopback.")
        metadata = verify(f"http://127.0.0.1:{address['HostPort']}", revision, environment, timeout)
        docker("stop", "--time", "10", name, timeout=20)
        state = json.loads(docker("inspect", name))[0]["State"]
        if state["ExitCode"] != 0 or state["OOMKilled"]:
            raise ValueError("Container failed to stop cleanly.")
        result.update(status="passed", metadata=metadata, exit_code=state["ExitCode"])
        return result
    finally:
        cleanup_errors: list[str] = []
        if started:
            try:
                logs = docker("logs", "--tail", "100", name, include_stderr=True)
                report.with_suffix(".log").write_text(logs + "\n", encoding="utf-8")
            except (subprocess.SubprocessError, OSError) as error:
                cleanup_errors.append(type(error).__name__ + ": logs")
            try:
                docker("rm", "--force", name)
            except (subprocess.SubprocessError, OSError) as error:
                cleanup_errors.append(type(error).__name__ + ": container")
        if network_created:
            try:
                docker("network", "rm", name)
            except (subprocess.SubprocessError, OSError) as error:
                cleanup_errors.append(type(error).__name__ + ": network")
        if cleanup_errors:
            result.update(status="failed", cleanup_errors=cleanup_errors)
        report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        if cleanup_errors:
            raise RuntimeError("Resource cleanup or diagnostic collection failed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument(
        "--environment", choices=["test", "staging", "production"], default="staging"
    )
    parser.add_argument("--report", type=Path, default=Path("reports/container-smoke.json"))
    parser.add_argument("--timeout", type=float, default=45)
    args = parser.parse_args()
    print(
        json.dumps(exercise(args.image, args.revision, args.environment, args.report, args.timeout))
    )


if __name__ == "__main__":
    main()
