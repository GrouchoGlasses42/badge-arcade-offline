"""Build the EUR Badge Arcade offline patch for Luma3DS."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
import subprocess
import tempfile

from patch_format import ROOT, arm_branch, encode_ips, read_arm_object, write_zip
from badge_versions import BASE, REVISIONS, UPDATE, Revision

TITLE_ID = "0004000000153600"
CODE_SIZE = 0x356000
CODE_SHA256 = "4278e14228eff0672b017d5a532210497ec824d7354fbb0c18ddae97f88323af"
LOAD_ADDRESS = 0x100000
PAYLOAD_ADDRESS = 0x34C7A4
RELEASE_VERSION = (ROOT / "VERSION").read_text().strip()
PAYLOAD_LIMIT = 0x34D0E0  # Keep the following NEX request wrapper intact.

# Replace the unused NEX upload worker with the local completion routines.
HOOKS = {
    0x18F7B4: "badge_return_zero",  # BOSS StartTaskImmediate
    0x18F8B4: "badge_return_zero",  # BOSS StartBgImmediate
    0x18F9C4: "badge_return_zero",  # BOSS StartTask: never schedule network work
    # The single HTTP client and SOC SDK copies in this executable. Keep local
    # service initialization, but reject request creation, DNS and socket I/O.
    0x190360: "badge_http_unavailable",  # HTTP BeginRequest
    0x19063C: "badge_return_zero",  # Second BOSS interface: StartTaskImmediate
    0x1906C8: "badge_return_zero",  # Second BOSS interface: StartBgImmediate
    0x19075C: "badge_return_zero",  # Second BOSS interface: StartTask
    0x190D5C: "badge_http_unavailable",  # HTTP CreateContext
    0x190EDC: "badge_http_unavailable",  # HTTP BeginRequestAsync
    0x1A5754: "badge_soc_unavailable",   # SOC GetHostByName
    0x1A58F0: "badge_soc_unavailable",   # SOC SendToMultiple
    0x1A5AE4: "badge_soc_unavailable",   # SOC SendToOther
    0x1A5B68: "badge_soc_unavailable",   # SOC Socket
    0x22DA20: "badge_return_zero",  # Download-storage quota setup is unused offline
    0x2408B8: "badge_home_complete",
    0x2409A8: "badge_home_complete",
    0x244EE4: "badge_home_result",
    0x244F44: "badge_home_query",
    0x245248: "badge_home_result",
    0x245734: "badge_return",
    0x24575C: "badge_download_unavailable",
    # Synchronous SpotPass task lookup/registration runs before the title.
    # Failure enters the generic SD error path on an uninitialized console.
    # Offline play does not need these background tasks in either HOME variant.
    0x245808: "badge_return_zero",
    0x24598C: "badge_download_unavailable",
    0x246D18: "badge_request_complete",
    0x246D28: "badge_return_true",
    0x246DC0: "badge_identity_complete",
    0x246E10: "badge_return_true",
    0x249C48: "badge_upload_owned",
    0x24B33C: "badge_upload_profile",
    0x24E870: "badge_home_has_collection",
    0x258B80: "badge_schedule_lookup",
    0x259680: "badge_story_flag",
    0x263E80: "badge_home_unavailable",
    0x28FBAC: "badge_persistent_id",
    0x2BBE04: "badge_home_unavailable",
    0x2BCBD0: "badge_return_zero",
    0x2E8C44: "badge_home_result",
    0x2EFDD8: "badge_return",
    0x2F1B34: "badge_home_categories",
    0x2F1CDC: "badge_return_zero",
    0x30A604: "badge_free_purchase",
    0x321078: "badge_boot_prepare_extdata",
    0x322608: "badge_home_boot_check",
    0x33F30C: "badge_title_resources_done",
    0x342FBC: "badge_title_start",
    0x348794: "badge_return_true",
    0x34B8B8: "badge_boss_register_complete",
    0x350718: "badge_request_complete",
}


# Keep the network and local-save hooks in both builds. In the HOME build these
# functions remain Nintendo's original code, including the archive safeguards,
# asynchronous export worker and its error reporting.
HOME_HOOKS = frozenset({
    0x2408B8, 0x2409A8, 0x244EE4, 0x244F44, 0x245248, 0x245734,
    0x24E870, 0x259680, 0x263E80, 0x2BBE04, 0x2BCBD0, 0x2E8C44,
    0x2F1B34, 0x2F1CDC, 0x322608,
})
EXPORT_SCENES = (0x3034DC, 0x333830, 0x335FDC)


def selected_hooks(home_menu: bool = False) -> dict[int, str]:
    return {a: name for a, name in HOOKS.items() if not home_menu or a not in HOME_HOOKS}


def detect_revision(code: bytes) -> Revision:
    digest = hashlib.sha256(code).hexdigest()
    for revision in REVISIONS:
        if len(code) == revision.size and digest == revision.sha256:
            return revision
    raise ValueError("Unsupported executable; expected a supplied EUR 1.3.0 or 1.3.1 decompressed .code")


def build_records(revision: Revision = BASE, *, home_menu: bool = False) -> tuple[list[tuple[int, bytes]], dict[str, int]]:
    with tempfile.TemporaryDirectory(prefix="badge-patch-") as temp:
        obj = Path(temp) / "badge.o"
        source = (ROOT / "patches/badge_offline.s").read_text()
        filenames = re.findall(r'\.L(?:owned|profile)_[ab]:\s*\.asciz "([^"]+)"', source)
        if len(filenames) != 4 or any(len(name.encode("ascii")) > 16 for name in filenames):
            raise ValueError("Extdata backup filenames must fit the console's 16-byte name field")
        source = re.sub(r"0x[0-9a-fA-F]+", lambda m: hex(revision.address(int(m[0], 16))), source)
        assembly = Path(temp) / "badge.s"
        assembly.write_text(source)
        subprocess.run([
            "clang", "-target", "arm-none-eabi", "-march=armv6k", "-c",
            str(assembly), "-o", str(obj),
        ], check=True)
        payload_address = revision.address(PAYLOAD_ADDRESS)
        payload, symbols = read_arm_object(obj.read_bytes(), payload_address)
    if len(payload) > revision.address(PAYLOAD_LIMIT) - payload_address:
        raise ValueError("Badge payload exceeds the unused NEX worker")
    records = [(payload_address - LOAD_ADDRESS, payload)]
    records.extend((revision.address(a) - LOAD_ADDRESS, arm_branch(revision.address(a), symbols[n]))
                   for a, n in selected_hooks(home_menu).items())
    # The default catcher vector is independently capped at 30. Reserve enough
    # pointer slots for the merged catalog's original and bonus catchers.
    records.append((revision.address(0x247E24) - LOAD_ADDRESS, bytes.fromhex("021ca0e3")))
    # Schedule entries own strings in a dedicated heap. The update has an
    # additional small-heap branch; both must accommodate the expanded list.
    records.append((revision.address(0x24D438) - LOAD_ADDRESS, bytes.fromhex("0137a0e3")))
    if revision.version == "1.3.1":
        records.append((0x24DE08 - LOAD_ADDRESS, bytes.fromhex("0137a0e3")))
    # The former export buttons open the in-game collection viewer instead.
    if not home_menu:
        for address in EXPORT_SCENES:
            records.append((revision.address(address) - LOAD_ADDRESS, b"Book" + bytes(6)))
    return sorted(records), symbols


def apply_records(code: bytes, records: list[tuple[int, bytes]], revision: Revision = BASE) -> bytes:
    if detect_revision(code) != revision:
        raise ValueError("Unsupported executable for these patch records; select its matching revision")
    result = bytearray(code)
    for offset, payload in records:
        if not 0 <= offset < offset + len(payload) <= len(result):
            raise ValueError("Patch record outside executable")
        result[offset:offset + len(payload)] = payload
    return bytes(result)


def write_package(path: Path, ips: bytes, manifest: dict) -> None:
    """Package only the Luma patch, without game data or documentation."""
    write_zip(path, {
        f"luma/titles/{TITLE_ID}/code.ips": ips,
    })


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--code", type=Path, help="Optionally verify an extracted decompressed .code")
    parser.add_argument("--game-version", choices=[r.version for r in REVISIONS],
                        help="Default without --code: 1.3.1; otherwise detected from executable")
    parser.add_argument("--output", type=Path, default=ROOT / "build/code")
    parser.add_argument("--package", type=Path, help="Also write a Luma ZIP without game data")
    parser.add_argument("--home-menu", action="store_true",
                        help="Enable original HOME badge access; can replace custom GYTB badges")
    args = parser.parse_args()
    if args.code:
        from private_assets import require_external
        try:
            require_external(args.code)
            require_external(args.output)
        except ValueError as exc:
            parser.error(str(exc))
    code = args.code.read_bytes() if args.code else None
    revision = detect_revision(code) if code is not None else next(
        (r for r in REVISIONS if r.version == args.game_version), UPDATE,
    )
    if args.game_version and revision.version != args.game_version:
        parser.error("--game-version does not match the supplied executable")
    records, symbols = build_records(revision, home_menu=args.home_menu)
    patched = apply_records(code, records, revision) if code is not None else None
    ips = encode_ips(records, revision.size)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "code.ips").write_bytes(ips)
    if patched is not None:
        (args.output / "patched.code.bin").write_bytes(patched)
    manifest = {
        "status": "Works with Luma3DS",
        "title_id": TITLE_ID,
        "game_version": revision.version,
        "release_version": RELEASE_VERSION,
        "variant": "home-menu" if args.home_menu else "game-only",
        "home_menu_badges": ("enabled; native HOME export and archive access" if args.home_menu
                             else "disabled; collection stays inside the game"),
        "region": "EUR",
        "requires_installed_update": revision.version == "1.3.1",
        "source_code_sha256": revision.sha256,
        "ips_sha256": hashlib.sha256(ips).hexdigest(),
        "patched_code_sha256": hashlib.sha256(patched).hexdigest() if patched is not None else None,
        "symbols": {name: f"{addr:08x}" for name, addr in sorted(symbols.items())},
    }
    (args.output / "build.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    if args.package:
        write_package(args.package, ips, manifest)
        print(f"Luma package written to {args.package}.")
    print(f"Luma patch written to {args.output}.")


if __name__ == "__main__":
    main()
