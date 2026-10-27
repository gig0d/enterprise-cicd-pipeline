"""Run pip-audit and distinguish advisory findings from execution or service failures."""

import argparse
import subprocess
import sys
from pathlib import Path

from scripts.security_gate import enforce, findings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=Path("requirements.txt"))
    parser.add_argument("--report", type=Path, default=Path("reports/pip-audit.json"))
    args = parser.parse_args()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.unlink(missing_ok=True)
    result = subprocess.run(  # noqa: S603 - fixed Python module and discrete arguments
        [
            sys.executable,
            "-m",
            "pip_audit",
            "--require-hashes",
            "--progress-spinner=off",
            "-r",
            str(args.requirements),
            "--format=json",
            "--output",
            str(args.report),
        ],
        check=False,
        timeout=600,
    )
    if result.returncode not in {0, 1} or not args.report.is_file():
        raise RuntimeError("Dependency scanner execution failed.")
    if result.returncode == 1:
        import json

        if not findings("pip-audit", json.loads(args.report.read_text(encoding="utf-8"))):
            raise RuntimeError("Dependency scanner returned an error without advisory findings.")
    enforce("pip-audit", args.report)


if __name__ == "__main__":
    main()
