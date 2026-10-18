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

ALLOWED = {'luma/titles/0004000000153600/code.ips'}


def verify() -> dict:
    version = (ROOT / "VERSION").read_text().strip()
    folder = ROOT / "releases" / ("v" + version)
    checksums = dict(line.split()[::-1] for line in (folder / "SHA256SUMS").read_text().splitlines())
    report = {}
    for variant in ("game-only", "home-menu"):
        package = folder / f"nba-offline-v{version}-{variant}.zip"
        expected = encode_ips(build_records(UPDATE, home_menu=variant == "home-menu")[0], UPDATE.size)
        with zipfile.ZipFile(package) as archive:
            if len(archive.namelist()) != len(ALLOWED) or set(archive.namelist()) != ALLOWED:
                raise ValueError("Unexpected public ZIP member; refusing unreviewed release content")
            if archive.testzip() is not None:
                raise ValueError("Corrupt ZIP")
            ips = archive.read("luma/titles/0004000000153600/code.ips")
            if ips != expected:
                raise ValueError("Release IPS does not match the source")
        digest = hashlib.sha256(package.read_bytes()).hexdigest()
        if checksums.get(package.name) != digest:
            raise ValueError("Release ZIP checksum mismatch")
        report[variant] = dict(package=str(package), ips_sha256=hashlib.sha256(ips).hexdigest(),
                               zip_sha256=digest)
    if report["game-only"]["ips_sha256"] == report["home-menu"]["ips_sha256"]:
        raise ValueError("HOME variants must have different patches")
    return report


if __name__ == "__main__":
    print(json.dumps(verify(), indent=2))
