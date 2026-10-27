"""Download a pinned official tool asset and extract only its verified executable."""

import argparse
import hashlib
import io
import json
import platform
import tarfile
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def install(name: str) -> Path:
    system = platform.system().lower()
    if system not in {"linux", "windows"} or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise ValueError("Only Linux/Windows x86-64 tool downloads are configured.")
    lock = json.loads((ROOT / "tools.lock.json").read_text(encoding="utf-8"))[name]
    asset = lock[system]
    executable = name + (".exe" if system == "windows" else "")
    destination = ROOT / ".tools" / name / executable
    url = f"https://github.com/{lock['repository']}/releases/download/v{lock['version']}/{asset['asset']}"
    with urllib.request.urlopen(url, timeout=60) as response:  # noqa: S310 - fixed HTTPS origin
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != asset["sha256"]:
        raise ValueError(f"Checksum mismatch for {name}; refusing to execute the download.")
    if asset["asset"].endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(archive)) as zipped:
            binary = zipped.read(executable)
    else:
        with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tar:
            member = tar.extractfile(executable)
            if member is None:
                raise ValueError(f"Missing executable: {executable}")
            binary = member.read()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(binary)
    destination.chmod(0o755)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", choices=["gitleaks", "trivy", "actionlint"])
    print(install(parser.parse_args().name))


if __name__ == "__main__":
    main()
