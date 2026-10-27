"""Intentionally fail a selected gate using synthetic, isolated fixtures."""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from scripts.security_gate import enforce


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenario", choices=["quality", "security"])
    scenario = parser.parse_args().scenario
    if scenario == "security":
        reports = Path("reports")
        reports.mkdir(exist_ok=True)
        fixture = {
            "SchemaVersion": 2,
            "Results": [
                {
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "DEMO-ADVISORY-001",
                            "PkgName": "synthetic-package",
                            "Severity": "CRITICAL",
                            "FixedVersion": "2.0",
                        }
                    ]
                }
            ],
        }
        path = reports / "synthetic-trivy.json"
        path.write_text(json.dumps(fixture, indent=2) + "\n", encoding="utf-8")
        # Empty fixture exceptions prevent real policy edits from bypassing this demonstration.
        exceptions = reports / "synthetic-exceptions.json"
        exceptions.write_text("[]\n", encoding="utf-8")
        enforce("trivy", path, exceptions)
        raise RuntimeError("The security fixture unexpectedly passed.")
    with tempfile.TemporaryDirectory(prefix="pipeline-failure-") as temporary:
        test = Path(temporary) / "test_controlled_failure.py"
        test.write_text(
            "def test_controlled_quality_failure():\n"
            "    expected_quantity = 3\n"
            "    observed_quantity = 2\n"
            "    assert observed_quantity == expected_quantity\n",
            encoding="utf-8",
        )
        result = subprocess.run(  # noqa: S603 - fixed pytest invocation and owned temporary file
            [
                sys.executable,
                "-m",
                "pytest",
                str(test),
                "-c",
                "pyproject.toml",
                "-p",
                "no:cacheprovider",
            ],
            check=False,
            timeout=30,
        )
        if result.returncode != 1:
            raise RuntimeError("The synthetic test did not produce the expected assertion failure.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
