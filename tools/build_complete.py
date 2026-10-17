"""Create the personal all-catchers install from your extracted base/update assets.

Works both from the source repository and an unpacked public release, using only
Python's standard library. No compiler, executable or console keys are needed.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from patch_format import write_zip  # noqa: E402

ARCHIVE_SHA256 = "0f379f61166ced829c0f757ade31c00c09ed8e849350edaa8fec2a30974dae48"
BASE_ARCHIVE_SHA256 = "2aca8529d7981a9ccad5a448ea06996fc861190b570ee4b25e4c651ce26347a5"
SCHEDULE_SHA256 = "af0f27304a495c3d8fd202631702016bffe0874471962f12cc45a297cb8887ab"


def verify_input(path: Path, expected: str) -> None:
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f"Unsupported input {path}; use the documented EUR base/update resource")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True, help="Extracted update pc.sarc")
    parser.add_argument("--base-archive", type=Path, required=True, help="Extracted base 1.3.0 pc.sarc")
    parser.add_argument("--schedule", type=Path, required=True, help="Extracted common Schedule.xml")
    parser.add_argument("--output", type=Path, default=ROOT / "build/nba-game-only-all-catchers-luma.zip")
    parser.add_argument("--patch-package", type=Path, help="Optional explicit release patch ZIP")
    args = parser.parse_args()
    verify_input(args.archive, ARCHIVE_SHA256)
    verify_input(args.base_archive, BASE_ARCHIVE_SHA256)
    verify_input(args.schedule, SCHEDULE_SHA256)
    with tempfile.TemporaryDirectory(prefix="nba-catalog-") as temp:
        scratch = Path(temp)
        package = args.patch_package
        if package is None and (ROOT / "build.json").is_file():
            # This is the unpacked portable public release.
            package = scratch / "patch.zip"
            names = ("build.json", "INSTALL.md", "luma/titles/0004000000153600/code.ips")
            write_zip(package, {name: (ROOT / name).read_bytes() for name in names})
        if package is None:
            package = ROOT / "releases/v0.4.0/nba-offline-v0.4.0.zip"
        if not package.is_file():
            parser.error("Patch package missing; run make release or supply --patch-package")
        subprocess.run([
            sys.executable, str(ROOT / "src/badge_catalog.py"),
            "--archive", str(args.archive.resolve()), "--schedule", str(args.schedule.resolve()),
            "--base-archive", str(args.base_archive.resolve()),
            "--output", str(scratch / "romfs"), "--patch-package", str(package.resolve()),
            "--package", str(args.output.resolve()),
        ], check=True)
    print(f"Complete personal install: {args.output}")
    print("Copy its luma folder to the SD root. This output contains your extracted game assets.")


if __name__ == "__main__":
    main()
