"""Reject private game content in the checkout, ZIPs, and tracked Git history."""
from __future__ import annotations

import argparse
import io
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
GAME_SUFFIXES = {".cia", ".ncch", ".cxi", ".3ds", ".bin", ".sarc", ".szs", ".enc", ".boss"}
MAGICS = (b"SARC", b"Yaz0", b"boss", b"IVFC")
SKIP = {".git", ".venv", "__pycache__", ".pytest_cache", ".ruff_cache"}


def inspect(name: str, data: bytes, *, depth: int = 0) -> None:
    path = Path(name)
    if path.suffix.lower() in GAME_SUFFIXES or path.name.lower().startswith(("boot9", "boot11")):
        raise ValueError(f"Private game material is forbidden in the repository: {name}")
    if data.startswith(MAGICS) or data[0x100:0x104] == b"NCCH":
        raise ValueError(f"Game-resource signature in {name}")
    if path.suffix.lower() == ".zip":
        if depth > 2:
            raise ValueError(f"Nested archive is not allowed: {name}")
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            for member in archive.infolist():
                if member.file_size > 4 * 1024 * 1024:
                    raise ValueError(f"Oversized public archive member: {name}:{member.filename}")
                inspect(f"{name}:{member.filename}", archive.read(member), depth=depth + 1)


def audit(root: Path = ROOT, *, history: bool = False) -> int:
    count = 0
    def walk(directory: Path) -> None:
        nonlocal count
        for path in directory.iterdir():
            if path.name in SKIP:
                continue
            if path.is_symlink():
                raise ValueError(f"Repository symlinks require explicit review: {path}")
            if path.is_dir():
                walk(path)
            else:
                # Large build artifacts may contain our compiler/debug symbols;
                # game containers are identified by name or their file header.
                with path.open("rb") as stream:
                    data = stream.read() if path.suffix.lower() in (".zip", ".cia") else stream.read(0x104)
                inspect(str(path.relative_to(root)), data)
                count += 1
    walk(root)
    if history:
        objects = subprocess.check_output(["git", "rev-list", "--objects", "--all"], cwd=root, text=True)
        seen = set()
        for line in objects.splitlines():
            digest, _, name = line.partition(" ")
            if not name or digest in seen:
                continue
            seen.add(digest)
            kind = subprocess.check_output(["git", "cat-file", "-t", digest], cwd=root, text=True).strip()
            if kind == "blob":
                inspect(f"history:{name}", subprocess.check_output(["git", "cat-file", "blob", digest], cwd=root))
    return count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", action="store_true")
    args = parser.parse_args()
    try:
        count = audit(history=args.history)
    except (ValueError, zipfile.BadZipFile) as exc:
        parser.error(str(exc))
    print(f"Asset audit passed: {count} checkout files. No private game resources or console keys.")


if __name__ == "__main__":
    main()
