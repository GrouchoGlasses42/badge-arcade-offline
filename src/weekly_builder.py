"""Compile the desktop catalog builder and assemble its weekly IPS variant."""
from __future__ import annotations

import os
from pathlib import Path
import struct
import subprocess

from badge_patch import build_records
from badge_versions import CATALOG_RECORDS, UPDATE

NATIVE = Path(__file__).resolve().parent / "weekly_native"


def weekly_records(home_menu: bool = False) -> list[tuple[int, bytes]]:
    """Read the primary schedule from RomFS and reserve full-catalog memory."""
    records, _ = build_records(UPDATE, home_menu=home_menu)
    records.extend([
        (0x240C6C - 0x100000, struct.pack("<I", 0xE3A01005)),  # GetFileDevice(5): RomFS.
        *CATALOG_RECORDS,
    ])
    return sorted(records)


def build_host(output: Path) -> None:
    """Compile the native helper with the local C++17 compiler."""
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        os.environ.get("CXX", "c++"), "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
        "-I" + str(NATIVE), "-I" + str(NATIVE / "vendor"),
        *[str(NATIVE / name) for name in ("files.cpp", "archive.cpp", "content.cpp", "host.cpp")],
        str(NATIVE / "vendor/tinyxml2.cpp"), "-o", str(output),
    ], check=True)
