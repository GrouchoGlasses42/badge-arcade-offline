"""Build a personal LayeredFS catalog from a user's extracted prize archive.

The output SARC contains the user's game assets. Keep it out of public patch
packages; the generated XML registries and schedules contain only asset names.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET
import zipfile

from patch_format import ROOT, write_zip


REGISTRIES = {
    "Categories": ("Category", "pc/rt/Ca/", ".cab.szs", 200),
    "Cranes": ("Crane", "pc/rt/Cr/", ".crb.szs", 1500),
    "CraneIcons": ("CraneIcon", "pc/rt/CI/", ".icb.szs", 2000),
    "Prizes": ("Prize", "pc/rt/Pr/", ".prb.szs", 10000),
    "Attachments": ("Attachment", "pc/rt/At/", ".atb.szs", 200),
    "FixedObjects": ("FixedObject", "pc/rt/FO/", ".fob.szs", 500),
    "CraneInstances": ("CraneInstance", "pc/ci/", ".cib.szs", 2000),
}
ROMFS_FILES = (
    "region_common/Schedule.xml", "region_EUR/common/Schedule.xml",
    "region_EUR/common/sharc/pc.sarc",
)


def read_sarc(blob: bytes) -> dict[str, bytes]:
    """Read the little-endian SARC variant used by the supplied game."""
    if blob[:4] != b"SARC" or blob[6:8] != b"\xff\xfe":
        raise ValueError("Expected a little-endian SARC")
    data_offset = struct.unpack_from("<I", blob, 12)[0]
    count = struct.unpack_from("<H", blob, 26)[0]
    names_offset = 40 + 16 * count
    files = {}
    for index in range(count):
        _, attr, start, end = struct.unpack_from("<4I", blob, 32 + 16 * index)
        pos = names_offset + (attr & 0xFFFFFF) * 4
        if not names_offset <= pos < data_offset or not 0 <= start <= end <= len(blob) - data_offset:
            raise ValueError("Invalid SARC node")
        name = blob[pos:blob.index(b"\0", pos, data_offset)].decode("ascii")
        if name in files:
            raise ValueError("Duplicate SARC name")
        files[name] = blob[data_offset + start:data_offset + end]
    return files


def replace_sarc_files(original: bytes, replacements: dict[str, bytes]) -> bytes:
    """Retain the original name/hash table and rebuild aligned file offsets."""
    files = read_sarc(original)
    if replacements.keys() - files.keys():
        raise ValueError("Replacement is not an existing archive member")
    data_offset = struct.unpack_from("<I", original, 12)[0]
    out = bytearray(original[:data_offset])
    for index, (name, content) in enumerate(files.items()):
        out += bytes(-len(out) % 128)
        start = len(out) - data_offset
        out += replacements.get(name, content)
        struct.pack_into("<II", out, 40 + 16 * index, start, len(out) - data_offset)
    struct.pack_into("<I", out, 8, len(out))
    return bytes(out)


def write_sarc(files: dict[str, bytes], template: bytes) -> bytes:
    """Build a hash-sorted SARC, including new members and aligned names/data."""
    read_sarc(template)
    multiplier = struct.unpack_from("<I", template, 28)[0]

    def name_hash(name: str) -> int:
        value = 0
        for byte in name.encode("ascii"):
            value = (value * multiplier + byte) & 0xFFFFFFFF
        return value

    ordered = sorted(files, key=lambda name: (name_hash(name), name))
    if len(ordered) > 0xFFFF:
        raise ValueError("Too many SARC members")
    names = bytearray()
    offsets = {}
    for name in ordered:
        offsets[name] = len(names) // 4
        names += name.encode("ascii") + b"\0"
        names += bytes(-len(names) % 4)
    data_offset = (40 + 16 * len(ordered) + len(names) + 127) & ~127
    header = bytearray(template[:20])
    header += struct.pack("<4sHHI", b"SFAT", 12, len(ordered), multiplier)
    header += bytes(16 * len(ordered))
    header += struct.pack("<4sHH", b"SFNT", 8, 0) + names
    header += bytes(data_offset - len(header))
    for index, name in enumerate(ordered):
        header += bytes(-len(header) % 128)
        start = len(header) - data_offset
        header += files[name]
        struct.pack_into("<4I", header, 32 + 16 * index,
                         name_hash(name), 0x01000000 | offsets[name], start, len(header) - data_offset)
    struct.pack_into("<II", header, 8, len(header), data_offset)
    return bytes(header)


def encode_yaz0_literals(data: bytes) -> bytes:
    """Encode generated small resources without changing any original assets."""
    return b"Yaz0" + struct.pack(">I", len(data)) + bytes(8) + b"".join(
        b"\xff" + data[pos:pos + 8] for pos in range(0, len(data), 8)
    )


def decompress_yaz0(blob: bytes, limit: int | None = None) -> bytes:
    """Decode bounded Yaz0 data; optionally stop after the resource header."""
    if blob[:4] != b"Yaz0":
        raise ValueError("Expected Yaz0 resource")
    size = struct.unpack_from(">I", blob, 4)[0]
    if size > 8 * 1024 * 1024:
        raise ValueError("Unexpected resource size")
    size = min(size, limit) if limit is not None else size
    out = bytearray()
    pos = 16
    while len(out) < size:
        flags = blob[pos]
        pos += 1
        for bit in range(7, -1, -1):
            if flags & (1 << bit):
                out.append(blob[pos])
                pos += 1
            else:
                first, second = blob[pos:pos + 2]
                pos += 2
                distance = ((first & 15) << 8) + second + 1
                if distance > len(out):
                    raise ValueError("Invalid Yaz0 back-reference")
                length = first >> 4
                if length == 0:
                    length = blob[pos] + 18
                    pos += 1
                else:
                    length += 2
                for _ in range(length):
                    out.append(out[-distance])
                    if len(out) >= size:
                        break
            if len(out) >= size:
                break
    return bytes(out)


def resource_name(blob: bytes, offset: int) -> str:
    return blob[offset:offset + 48].split(b"\0", 1)[0].decode("ascii")


def add_bonus_catchers(files: dict[str, bytes], prizes: list[str]) -> int:
    """Place unassigned base Bunny badges in copies of the native four-badge layout."""
    # A platform is essential: the Bunny display layouts have no floor and
    # repeatedly award every badge as soon as the machine loads.
    template = decompress_yaz0(files["pc/ci/Kirby_001.cib.szs"])
    if struct.unpack_from("<8I", template, 0xE0) != (4, 0, 1, 4, 4, 0, 1, 0):
        raise ValueError("Unexpected bonus catcher template")
    icon_template = decompress_yaz0(files[f"pc/rt/CI/{resource_name(template, 0x90)}.icb.szs"])
    used_ids = {struct.unpack_from("<I", decompress_yaz0(blob, 0x30), 0x2C)[0]
                for name, blob in files.items() if name.endswith(".cib.szs")}
    if len(prizes) % 4:
        raise ValueError("Bonus badges must fill native four-badge layouts")
    for group in range(len(prizes) // 4):
        name = f"BTCenter_{group + 4:03d}"
        icon_name = f"CraneIcon_{name}"
        if f"pc/ci/{name}.cib.szs" in files or 4600 + group in used_ids:
            raise ValueError("Bonus catcher name or identity collision")
        raw = bytearray(template)
        struct.pack_into("<I", raw, 0x2C, 4600 + group)
        raw[0x30:0x60] = name.encode().ljust(48, b"\0")
        raw[0x90:0xC0] = icon_name.encode().ljust(48, b"\0")
        title = f"Arcade Bunny Bonus {group + 1}".encode("utf-16-le").ljust(256, b"\0")
        raw[0x100:0x1100] = title * 16
        for index, prize in enumerate(prizes[group * 4:group * 4 + 4]):
            badge = decompress_yaz0(files[f"pc/rt/Pr/{prize}.prb.szs"])
            if resource_name(badge, 0x74) != "BTCenter":
                raise ValueError("Unexpected unassigned badge category")
            # Both the machine and collection display use this same name table.
            raw[0x1100 + 48 * index:0x1130 + 48 * index] = prize.encode().ljust(48, b"\0")
        icon = bytearray(icon_template)
        icon[0x1C:0x4C] = icon_name.encode().ljust(48, b"\0")
        first = decompress_yaz0(files[f"pc/rt/Pr/{prizes[group * 4]}.prb.szs"])
        icon[0x100:0x2100] = first[0x1100:0x3100]
        files[f"pc/ci/{name}.cib.szs"] = encode_yaz0_literals(raw)
        files[f"pc/rt/CI/{icon_name}.icb.szs"] = encode_yaz0_literals(icon)
    return len(prizes) // 4


def expand_catalog(archive: bytes, schedule: bytes, base_archive: bytes | None = None) -> tuple[bytes, bytes, dict]:
    """Register all bundled assets, after checking every machine dependency."""
    files = read_sarc(archive)
    restored = {}
    if base_archive is not None:
        for name, data in read_sarc(base_archive).items():
            if name.startswith(("pc/rt/", "pc/ci/")) and name not in files:
                files[name] = data
                restored[name] = data
    referenced = set()
    for name, data in files.items():
        if name.endswith(".cib.szs"):
            raw = decompress_yaz0(data)
            if struct.unpack_from("<I", raw, 0xC0)[0] == 0:
                referenced.update(resource_name(raw, 0x1100 + 48 * i)
                                  for i in range(struct.unpack_from("<I", raw, 0xE0)[0]))
    unassigned = sorted(Path(name).name.removesuffix(".prb.szs") for name in files
                        if name.endswith(".prb.szs") and Path(name).name.removesuffix(".prb.szs") not in referenced)
    bonus_count = add_bonus_catchers(files, unassigned) if base_archive is not None and unassigned else 0
    catalog = ET.fromstring(files["pc/PrizeCollection.xml"])
    counts = {}
    names_by_kind = {}
    for block, (tag, prefix, suffix, capacity) in REGISTRIES.items():
        names = sorted(name[len(prefix):-len(suffix)] for name in files
                       if name.startswith(prefix) and name.endswith(suffix))
        if not names or len(names) > capacity:
            raise ValueError(f"{block} exceeds verified native capacity")
        names_by_kind[block] = names
        node = catalog.find(block)
        if node is None:
            raise ValueError(f"Missing registry {block}")
        node.clear()
        node.set("count", str(len(names)))
        for name in names:
            ET.SubElement(node, tag, name=name)
        counts[block] = len(names)

    category_ids = {}
    for name in names_by_kind["Categories"]:
        raw = decompress_yaz0(files[f"pc/rt/Ca/{name}.cab.szs"], 0x68)
        category_ids[name] = struct.unpack_from("<I", raw, 0x24)[0]
    if len(set(category_ids.values())) != len(category_ids):
        raise ValueError("Duplicate category identity")
    identities = set()
    for name in names_by_kind["Prizes"]:
        raw = decompress_yaz0(files[f"pc/rt/Pr/{name}.prb.szs"], 0xA4)
        category = resource_name(raw, 0x74)
        uid = (category_ids[category], struct.unpack_from("<I", raw, 0x3C)[0])
        if uid in identities:
            raise ValueError("Duplicate prize identity")
        identities.add(uid)

    selectable = []
    selectable_prizes = set()
    for name in names_by_kind["CraneInstances"]:
        raw = decompress_yaz0(files[f"pc/ci/{name}.cib.szs"])
        # Type 2 is the dedicated practice machine; the normal selector uses type 0.
        if struct.unpack_from("<I", raw, 0xC0)[0] == 0:
            selectable.append(name)
            selectable_prizes.update(resource_name(raw, 0x1100 + 48 * i)
                                     for i in range(struct.unpack_from("<I", raw, 0xE0)[0]))
        deps = [f"pc/rt/Cr/{resource_name(raw, 0x60)}.crb.szs",
                f"pc/rt/CI/{resource_name(raw, 0x90)}.icb.szs"]
        for index, block in enumerate(("Prizes", "Attachments", "FixedObjects")):
            _, prefix, suffix, _ = REGISTRIES[block]
            count = struct.unpack_from("<I", raw, 0xE0 + 4 * index)[0]
            if count > 20:
                raise ValueError("Machine dependency table is oversized")
            base = (0x1100, 0x14C0, 0x1880)[index]
            deps += [prefix + resource_name(raw, base + 48 * i) + suffix for i in range(count)]
        if any(dep not in files for dep in deps):
            raise ValueError(f"Incomplete machine {name}")
    if selectable_prizes != set(names_by_kind["Prizes"]):
        raise ValueError("Normal catcher lineup does not cover every bundled prize")
    counts["SelectableMachines"] = len(selectable)
    counts["OriginalSelectableMachines"] = len(selectable) - bonus_count
    counts["BonusCatchers"] = bonus_count
    counts["RestoredPrizes"] = sum(name.endswith(".prb.szs") for name in restored)
    counts["RestoredCatchers"] = sum(name.endswith(".cib.szs") for name in restored)

    root = ET.fromstring(schedule)
    items = root.find("Items")
    if items is None:
        raise ValueError("Missing schedule Items")
    for item in list(items):
        if (item.findtext("Key") or "").startswith("DefaultStageName"):
            items.remove(item)
    for index, name in enumerate(selectable):
        item = ET.SubElement(items, "FileItem")
        for tag, value in (("Priority", str(index + 100)), ("DateStartText", "20000101"),
                           ("DateExpireText", "20991231"), ("RegexSetName", "DefaultStage"),
                           ("Key", f"DefaultStageName{index:03d}"), ("Value", name)):
            ET.SubElement(item, tag).text = value
    root.find("ItemsCount").text = str(len(items))
    xml = ET.tostring(catalog, encoding="utf-8", xml_declaration=True)
    files["pc/PrizeCollection.xml"] = xml
    replacement = write_sarc(files, archive) if base_archive is not None else replace_sarc_files(
        archive, {"pc/PrizeCollection.xml": xml},
    )
    return replacement, ET.tostring(root, encoding="utf-8", xml_declaration=True), counts


def write_personal_package(patch: Path, catalog: Path, destination: Path) -> None:
    """Combine the release patch with user-owned assets for personal use."""
    with zipfile.ZipFile(patch) as source:
        manifest = json.loads(source.read("build.json"))
        if (manifest.get("title_id"), manifest.get("game_version"), manifest.get("release_version")) != (
            "0004000000153600", "1.3.1", (ROOT / "VERSION").read_text().strip(),
        ):
            raise ValueError("Expanded update catalog requires the current EUR 1.3.1 release package")
        patch_name = "luma/titles/0004000000153600/code.ips"
        ips = source.read(patch_name)
        if hashlib.sha256(ips).hexdigest() != manifest["ips_sha256"]:
            raise ValueError("Patch fingerprint mismatch")
        instructions = source.read("INSTALL.md")
    assets = {name: (catalog / name).read_bytes() for name in ROMFS_FILES}
    manifest["catalog"] = json.loads((catalog / "catalog.json").read_text())
    manifest["personal_package_contains_game_assets"] = True
    manifest["romfs_sha256"] = {name: hashlib.sha256(data).hexdigest() for name, data in assets.items()}
    files = {
        patch_name: ips,
        "build.json": (json.dumps(manifest, indent=2) + "\n").encode(),
        "INSTALL.md": instructions,
    }
    files.update({"luma/titles/0004000000153600/romfs/" + name: data for name, data in assets.items()})
    write_zip(destination, files)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--base-archive", type=Path, help="Base 1.3.0 pc.sarc to merge with the update")
    parser.add_argument("--schedule", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--patch-package", type=Path, help="Current code-only update ZIP")
    parser.add_argument("--package", type=Path, help="Personal ZIP including your extracted game assets")
    args = parser.parse_args()
    if bool(args.patch_package) != bool(args.package):
        parser.error("--patch-package and --package must be supplied together")
    archive, schedule, counts = expand_catalog(args.archive.read_bytes(), args.schedule.read_bytes(),
                                               args.base_archive.read_bytes() if args.base_archive else None)
    for region in ("region_common", "region_EUR/common"):
        dest = args.output / region
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "Schedule.xml").write_bytes(schedule)
    target = args.output / "region_EUR/common/sharc/pc.sarc"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(archive)
    (args.output / "catalog.json").write_text(json.dumps(counts, indent=2) + "\n")
    if args.package:
        write_personal_package(args.patch_package, args.output, args.package)
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
