import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from scripts.security_gate import enforce, findings, load_exceptions

pytestmark = pytest.mark.unit


def trivy_report(severity: str = "HIGH", fixed: str = "2.0") -> dict[str, Any]:
    return {
        "SchemaVersion": 2,
        "Results": [
            {
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "DEMO-ADVISORY-001",
                        "PkgName": "synthetic-package",
                        "Severity": severity,
                        "FixedVersion": fixed,
                    }
                ]
            }
        ],
    }


def test_serious_fixable_vulnerabilities_block_and_full_report_is_preserved(tmp_path: Path) -> None:
    report = tmp_path / "trivy.json"
    exceptions = tmp_path / "exceptions.json"
    report.write_text(json.dumps(trivy_report()), encoding="utf-8")
    exceptions.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="blocked promotion"):
        enforce("trivy", report, exceptions)
    assert findings("trivy", trivy_report("LOW")) == []
    assert findings("trivy", trivy_report(fixed="")) == []
    assert "DEMO-ADVISORY-001" in report.read_text(encoding="utf-8")


def test_python_advisory_policy_blocks_all_severities() -> None:
    assert findings(
        "pip-audit",
        {
            "dependencies": [
                {
                    "name": "synthetic-package",
                    "vulns": [{"id": "DEMO-ADVISORY-001"}],
                }
            ]
        },
    ) == [("DEMO-ADVISORY-001", "synthetic-package")]


@pytest.mark.parametrize(
    "report", [{}, {"dependencies": []}, {"dependencies": [{"skip_reason": "offline"}]}]
)
def test_incomplete_dependency_audits_fail_closed(report: dict[str, Any]) -> None:
    with pytest.raises(ValueError):
        findings("pip-audit", report)


def test_exceptions_are_exact_and_expire(tmp_path: Path) -> None:
    path = tmp_path / "exceptions.json"
    exception = {
        "scanner": "trivy",
        "id": "DEMO-ADVISORY-001",
        "package": "synthetic-package",
        "reason": "Synthetic test only",
        "owner": "test",
        "expires": "2030-01-01",
    }
    path.write_text(json.dumps([exception]), encoding="utf-8")
    assert load_exceptions(path, today=date(2029, 1, 1)) == {
        ("trivy", "DEMO-ADVISORY-001", "synthetic-package")
    }
    with pytest.raises(ValueError, match="Expired"):
        load_exceptions(path, today=date(2030, 1, 1))
    path.write_text(json.dumps([exception | {"package": "*"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="exact"):
        load_exceptions(path, today=date(2029, 1, 1))


def test_malformed_image_scan_is_not_a_pass() -> None:
    with pytest.raises(ValueError, match="supported image scan"):
        findings("trivy", {})
