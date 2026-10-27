"""Fail closed on scanner errors; apply narrowly scoped, expiring advisory exceptions."""

import argparse
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_exceptions(path: Path, today: date | None = None) -> set[tuple[str, str, str]]:
    current = today or datetime.now(UTC).date()
    entries = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(entries, list):
        raise ValueError("Security exceptions must be a JSON list.")
    accepted: set[tuple[str, str, str]] = set()
    for entry in entries:
        required = {"scanner", "id", "package", "reason", "owner", "expires"}
        if not isinstance(entry, dict) or set(entry) != required:
            raise ValueError(
                "Every exception needs scanner, id, package, reason, owner, and expires."
            )
        if any(not isinstance(value, str) or not value.strip() for value in entry.values()):
            raise ValueError("Security exception fields must be nonempty strings.")
        if entry["scanner"] not in {"pip-audit", "trivy"} or "*" in entry["id"] + entry["package"]:
            raise ValueError(
                "Exceptions must name an exact supported scanner, advisory, and package."
            )
        if date.fromisoformat(entry["expires"]) <= current:
            raise ValueError(f"Expired security exception: {entry['id']}")
        key = (entry["scanner"], entry["id"], entry["package"])
        if key in accepted:
            raise ValueError(f"Duplicate security exception: {key}")
        accepted.add(key)
    return accepted


def findings(scanner: str, data: dict[str, Any]) -> list[tuple[str, str]]:
    blocked: list[tuple[str, str]] = []
    if scanner == "pip-audit":
        dependencies = data.get("dependencies")
        if not isinstance(dependencies, list) or not dependencies:
            raise ValueError("pip-audit produced no usable dependency results.")
        for dependency in dependencies:
            if "skip_reason" in dependency or not isinstance(dependency.get("vulns"), list):
                raise ValueError("pip-audit skipped a dependency; the audit is incomplete.")
            for vulnerability in dependency["vulns"]:
                blocked.append((vulnerability["id"], dependency["name"]))
    elif scanner == "trivy":
        if data.get("SchemaVersion") != 2 or not isinstance(data.get("Results"), list):
            raise ValueError("Trivy did not produce a supported image scan report.")
        for result in data["Results"]:
            for vulnerability in result.get("Vulnerabilities") or []:
                if vulnerability["Severity"] in {"HIGH", "CRITICAL"} and vulnerability.get(
                    "FixedVersion"
                ):
                    blocked.append((vulnerability["VulnerabilityID"], vulnerability["PkgName"]))
    else:
        raise ValueError(f"Unsupported scanner: {scanner}")
    return blocked


def enforce(
    scanner: str, report: Path, exceptions: Path = ROOT / "security/exceptions.json"
) -> None:
    accepted = load_exceptions(exceptions)
    data = json.loads(report.read_text(encoding="utf-8"))
    blocked = [
        (advisory, package)
        for advisory, package in findings(scanner, data)
        if (scanner, advisory, package) not in accepted
    ]
    if blocked:
        raise ValueError(f"{scanner} blocked promotion: {blocked}")
    print(f"{scanner}: blocking vulnerability policy passed; see the full report for all findings.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scanner", choices=["pip-audit", "trivy"])
    parser.add_argument("report", type=Path)
    parser.add_argument("--exceptions", type=Path, default=ROOT / "security/exceptions.json")
    args = parser.parse_args()
    enforce(args.scanner, args.report, args.exceptions)


if __name__ == "__main__":
    main()
