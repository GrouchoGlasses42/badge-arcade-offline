"""Verify the public release against source and its documented checksums."""
from pathlib import Path
import hashlib
import json
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from badge_patch import build_records  # noqa: E402
from badge_versions import UPDATE  # noqa: E402
from patch_format import encode_ips  # noqa: E402

ALLOWED = {'INSTALL.md', 'LICENSE', 'README.md', 'RELEASE_NOTES.md', 'build.json', 'docs/BUILD.md', 'docs/RESEARCH.md', 'luma/titles/0004000000153600/code.ips', 'src/badge_catalog.py', 'src/patch_format.py', 'tools/build_complete.py'}
SOURCE_FILES = {'INSTALL.md': 'docs/INSTALL.md', 'LICENSE': 'LICENSE', 'README.md': 'README.md', 'RELEASE_NOTES.md': 'releases/v0.4.0/RELEASE_NOTES.md', 'docs/BUILD.md': 'docs/BUILD.md', 'docs/RESEARCH.md': 'docs/RESEARCH.md', 'src/badge_catalog.py': 'src/badge_catalog.py', 'src/patch_format.py': 'src/patch_format.py', 'tools/build_complete.py': 'tools/build_complete.py'}


def verify() -> dict:
    folder = ROOT / "releases/v0.4.0"
    package = folder / "nba-offline-v0.4.0.zip"
    expected = encode_ips(build_records(UPDATE)[0], UPDATE.size)
    with zipfile.ZipFile(package) as archive:
        if len(archive.namelist()) != len(ALLOWED) or set(archive.namelist()) != ALLOWED:
            raise ValueError("Unexpected public ZIP member; refusing unreviewed release content")
        if archive.testzip() is not None:
            raise ValueError("Corrupt ZIP")
        ips = archive.read("luma/titles/0004000000153600/code.ips")
        manifest = json.loads(archive.read("build.json"))
        if ips != expected or hashlib.sha256(ips).hexdigest() != manifest["ips_sha256"]:
            raise ValueError("Release IPS does not match the source or manifest")
        for member, source in SOURCE_FILES.items():
            if archive.read(member) != (ROOT / source).read_bytes():
                raise ValueError(f"Outdated bundled file: {member}")
    if json.loads((folder / "build.json").read_text()) != manifest:
        raise ValueError("Loose manifest differs from packaged manifest")
    digest, filename = (folder / "SHA256SUMS").read_text().split()
    if filename != package.name or hashlib.sha256(package.read_bytes()).hexdigest() != digest:
        raise ValueError("Release ZIP checksum mismatch")
    return dict(package=str(package), ips_sha256=manifest["ips_sha256"], zip_sha256=digest)


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
