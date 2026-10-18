"""Build both public Luma-only releases, without game data."""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    version = (ROOT / "VERSION").read_text().strip()
    release = ROOT / "releases" / ("v" + version)
    release.mkdir(parents=True, exist_ok=True)
    checksums = []
    for variant in ("game-only", "home-menu"):
        output = ROOT / "build/release" / variant
        package = release / f"nba-offline-v{version}-{variant}.zip"
        subprocess.run([
            sys.executable, str(ROOT / "src/badge_patch.py"), "--game-version", "1.3.1",
            "--output", str(output), "--package", str(package),
            *(["--home-menu"] if variant == "home-menu" else []),
        ], check=True)
        (release / f"{variant}.json").write_bytes((output / "build.json").read_bytes())
        checksums.append(f"{hashlib.sha256(package.read_bytes()).hexdigest()}  {package.name}\n")
        print(f"Release: {package}")
    (release / "SHA256SUMS").write_text("".join(checksums))


if __name__ == "__main__":
    main()
