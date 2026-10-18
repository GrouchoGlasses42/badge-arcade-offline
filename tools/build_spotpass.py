"""Build Custom Weekly: only one archived EUR week's unique playable machines.

Inputs: extracted base/update pc.sarc and update Schedule.xml, one weekly pack,
and full allbadge. Encrypted packs additionally require a local boot9 dump.
All inputs and the personal output must stay outside the source repository.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from badge_spotpass import open_spotpass  # noqa: E402
from badge_versions import UPDATE  # noqa: E402
from patch_format import encode_ips, write_zip  # noqa: E402
from private_assets import require_external  # noqa: E402
from weekly_builder import build_host, weekly_records  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-archive", "--archive", dest="archive", type=Path, required=True,
                        help="Extracted EUR update 1.3.1 pc.sarc (--archive is also accepted)")
    parser.add_argument("--base-archive", type=Path, required=True,
                        help="Extracted EUR base 1.3.0 pc.sarc for shared resources; no extra playable machines")
    parser.add_argument("--schedule", type=Path, required=True, help="Update common Schedule.xml")
    parser.add_argument("--week", type=Path, required=True, help="One archived EUR BOSS pack or decrypted SARC")
    parser.add_argument("--allbadge", type=Path, required=True, help="Full EUR allbadge_v131.dat.boss or decrypted SARC")
    parser.add_argument("--boot9", type=Path, help="Local boot9.bin dump; required if week or allbadge is encrypted")
    parser.add_argument("--home-menu", action="store_true", help="Enable native HOME export; default: game-only")
    parser.add_argument("--output", type=Path, default=ROOT.parent / "nba-private/nba-custom-weekly-luma.zip")
    args = parser.parse_args()
    try:
        for path in (args.archive, args.base_archive, args.schedule, args.week, args.allbadge, args.boot9, args.output):
            if path is not None:
                require_external(path)
        boot9 = args.boot9.read_bytes() if args.boot9 else None
        payload = open_spotpass(args.week.read_bytes(), boot9)
        allbadge = open_spotpass(args.allbadge.read_bytes(), boot9)
        with tempfile.TemporaryDirectory(prefix="nba-personal-week-") as temp:
            folder = Path(temp)
            host, week, output = folder / "nba-host", folder / "week.sarc", folder / "patch"
            build_host(host)
            week.write_bytes(payload)
            (folder / "allbadge.sarc").write_bytes(allbadge)
            subprocess.run([str(host), "build", str(args.base_archive), str(args.archive),
                            str(args.schedule), str(output), str(week), "--allbadge", str(folder / "allbadge.sarc")],
                           check=True, stdout=subprocess.PIPE, text=True)
            metadata = json.loads((output / "catalog.json").read_text(encoding="utf-8"))
            metadata["home_menu"] = args.home_menu
            (output / "catalog.json").write_text(json.dumps(metadata) + "\n", encoding="utf-8")
            (output / "code.ips").write_bytes(encode_ips(weekly_records(args.home_menu), UPDATE.size))
            prefix = "luma/titles/0004000000153600/"
            files = {prefix + path.relative_to(output).as_posix(): path.read_bytes()
                     for path in output.rglob("*") if path.is_file()}
            files["INSTALL.md"] = (ROOT / "README.md").read_bytes()
            write_zip(args.output, files)
    except (ValueError, OSError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
    print(f"Custom Weekly personal install: {args.output}")
    print(f"Week {metadata['week']}: {metadata['machines']} unique playable machines; "
          f"{metadata['badge_resources']} badge resources in the merged collection catalog.")
    print("Only the selected week's machines are playable; other allbadge layouts are display-only.")
    print("Contains game assets; keep private and outside the repository. No boot9 dump or keys are packaged.")


if __name__ == "__main__":
    main()
