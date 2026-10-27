"""Check dependency export freshness and mechanical workflow security invariants."""

import re
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def check_workflows() -> None:
    for path in (ROOT / ".github/workflows").glob("*.yml"):
        text = path.read_text(encoding="utf-8")
        workflow = yaml.safe_load(text)
        if workflow.get("permissions") != {"contents": "read"}:
            raise ValueError(f"{path.name}: workflow token default must be contents: read")
        if "pull_request_target" in text or "continue-on-error: true" in text:
            raise ValueError(f"{path.name}: unsafe trigger or bypassed quality gate")
        for reference in re.findall(r"uses:\s*([^\s#]+)", text):
            if not reference.startswith("./") and not re.fullmatch(
                r"[\w./-]+@[0-9a-f]{40}", reference
            ):
                raise ValueError(f"{path.name}: action reference is not immutable: {reference}")
        for job in workflow["jobs"].values():
            if "uses" not in job and "timeout-minutes" not in job:
                raise ValueError(f"{path.name}: every runner job needs a bounded timeout")
            for step in job.get("steps", []):
                if (
                    step.get("uses", "").startswith("actions/checkout@")
                    and step.get("with", {}).get("persist-credentials") is not False
                ):
                    raise ValueError(f"{path.name}: checkout must not persist credentials")


def main() -> None:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("Install uv 0.13.6 and place it on PATH.")
    exported = subprocess.check_output(  # noqa: S603 - fixed executable and arguments
        [uv, "export", "--frozen", "--no-dev", "--no-emit-project", "--no-header"],
        cwd=ROOT,
        text=True,
    )
    if exported.strip() != (ROOT / "requirements.txt").read_text(encoding="utf-8").strip():
        raise ValueError("requirements.txt is stale; regenerate the production dependency export.")
    check_workflows()
    print("Dependency export and workflow security invariants passed.")


if __name__ == "__main__":
    main()
