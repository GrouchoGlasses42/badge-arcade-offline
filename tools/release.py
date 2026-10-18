"""Build the public release with its portable catalog tool, without art."""
from pathlib import Path
import hashlib
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from patch_format import write_zip  # noqa: E402


def main() -> None:
    version = (ROOT / "VERSION").read_text().strip()
    if version != "0.4.0":
        raise ValueError("Update the release metadata and builder for a new version")
    output = ROOT / "build/release"
    inner = output / "code-only.zip"
    subprocess.run([
        sys.executable, str(ROOT / "src/badge_patch.py"), "--game-version", "1.3.1",
        "--output", str(output / "code"), "--package", str(inner),
    ], check=True)
    import zipfile
    with zipfile.ZipFile(inner) as source:
        files = {"luma/titles/0004000000153600/code.ips": source.read(
            "luma/titles/0004000000153600/code.ips",
        )}
    release = ROOT / "releases" / ("v" + version)
    package = release / f"nba-offline-v{version}.zip"
    write_zip(package, files)
    (release / "build.json").write_text((output / "code/build.json").read_text())
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (release / "SHA256SUMS").write_text(f"{digest}  {package.name}\n")
    print(f"Release: {package}")


if __name__ == "__main__":
    main()
