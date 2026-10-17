"""Build the public release with its portable catalog tool, without art."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import zipfile

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
    with zipfile.ZipFile(inner) as source:
        files = {name: source.read(name) for name in source.namelist()}
    for name in ("README.md", "LICENSE", "src/patch_format.py", "src/badge_catalog.py",
                 "tools/build_complete.py", "docs/BUILD.md", "docs/RESEARCH.md"):
        files[name] = (ROOT / name).read_bytes()
    files["RELEASE_NOTES.md"] = (ROOT / "releases/v0.4.0/RELEASE_NOTES.md").read_bytes()
    release = ROOT / "releases" / ("v" + version)
    package = release / f"nba-offline-v{version}.zip"
    write_zip(package, files)
    (release / "build.json").write_text(json.dumps(json.loads(files["build.json"]), indent=2) + "\n")
    digest = hashlib.sha256(package.read_bytes()).hexdigest()
    (release / "SHA256SUMS").write_text(f"{digest}  {package.name}\n")
    print(f"Release: {package}")


if __name__ == "__main__":
    main()
