"""Run the pinned local Trivy executable and enforce the repository vulnerability policy."""

import argparse
import platform
import subprocess
from pathlib import Path

from scripts.security_gate import enforce


def scan(image: str, report: Path) -> None:
    suffix = ".exe" if platform.system() == "Windows" else ""
    executable = Path(__file__).resolve().parents[1] / ".tools/trivy" / f"trivy{suffix}"
    if not executable.is_file():
        raise RuntimeError("Install the pinned scanner with python -m scripts.install_tool trivy.")
    report.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(  # noqa: S603 - pinned executable and discrete arguments; no shell
        [
            str(executable),
            "image",
            "--scanners",
            "vuln",
            "--format",
            "json",
            "--output",
            str(report),
            "--timeout",
            "5m",
            image,
        ],
        check=True,
        timeout=360,
    )
    enforce("trivy", report)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image")
    parser.add_argument("--report", type=Path, default=Path("reports/trivy.json"))
    args = parser.parse_args()
    scan(args.image, args.report)


if __name__ == "__main__":
    main()
