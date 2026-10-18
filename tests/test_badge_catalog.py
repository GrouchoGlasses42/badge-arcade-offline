"""Native archive audits require the user's extracted data, never bundled art."""
from pathlib import Path
import hashlib
import os
import json
import struct
import xml.etree.ElementTree as ET
import zipfile

import pytest

from badge_catalog import ROMFS_FILES, decompress_yaz0, expand_catalog, read_sarc, replace_sarc_files, write_personal_package
from patch_format import ROOT, decode_ips, encode_ips


def test_yaz0_rejects_invalid_back_reference_and_oversized_resource():
    header = b"Yaz0" + struct.pack(">I", 3) + bytes(8)
    with pytest.raises(ValueError, match="back-reference"):
        decompress_yaz0(header + bytes(3))
    with pytest.raises(ValueError, match="size"):
        decompress_yaz0(b"Yaz0" + struct.pack(">I", 9 * 1024 * 1024) + bytes(8))


def test_expanded_catalog_registers_all_bundled_machines_and_preserves_assets():
    archive = Path(os.environ.get("BADGE_ARCHIVE", ROOT.parent / "nba-private/inputs/pc.sarc"))
    schedule = Path(os.environ.get("BADGE_SCHEDULE", ROOT.parent / "nba-private/inputs/Schedule.xml"))
    if not archive.is_file() or not schedule.is_file():
        pytest.skip("Requires the user's extracted EUR update prize archive")
    original = archive.read_bytes()
    files = read_sarc(original)
    expanded, timetable, counts = expand_catalog(original, schedule.read_bytes())
    result = read_sarc(expanded)
    assert result.keys() == files.keys()
    assert all(result[name] == value for name, value in files.items() if name != "pc/PrizeCollection.xml")
    registry = ET.fromstring(result["pc/PrizeCollection.xml"])
    machines = {p.attrib["name"] for p in registry.find("CraneInstances")}
    expected = {Path(name).name.removesuffix(".cib.szs") for name in files if name.endswith(".cib.szs")}
    assert machines == expected
    assert len(machines) == counts["CraneInstances"] == 385
    items = ET.fromstring(timetable).find("Items")
    stages = [item for item in items if (item.findtext("Key") or "").startswith("DefaultStageName")]
    assert len(stages) == counts["SelectableMachines"] == 384
    assert {item.findtext("Value") for item in stages} == expected - {"MroSMB_018"}
    assert [item.findtext("Key") for item in stages] == [f"DefaultStageName{i:03d}" for i in range(384)]
    for section in registry:
        assert int(section.attrib["count"]) == len(section)
    assert replace_sarc_files(original, {}) == original


@pytest.mark.parametrize("version,release,valid_hash", [("1.3.0", "0.5.0", True), ("1.3.1", "0.3.0", True),
                                                      ("1.3.1", "0.5.0", False), ("1.3.1", "0.5.0", True)])
def test_personal_zip_requires_matching_patch_and_contains_only_intended_overrides(
    tmp_path, version, release, valid_hash,
):
    patch_name = "luma/titles/0004000000153600/code.ips"
    patch = tmp_path / "patch.zip"
    manifest = dict(title_id="0004000000153600", game_version=version, release_version=release,
                    ips_sha256=hashlib.sha256(b"PATCH" if valid_hash else b"wrong").hexdigest())
    with zipfile.ZipFile(patch, "w") as source:
        source.writestr(patch_name, b"PATCH")
        source.writestr("build.json", json.dumps(manifest))
        source.writestr("INSTALL.md", "Instructions")
    for name in ROMFS_FILES:
        target = tmp_path / "catalog" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"user supplied " + name.encode())
    (tmp_path / "catalog/catalog.json").write_text('{"SelectableMachines":384}')
    output = tmp_path / "personal.zip"
    if version != "1.3.1" or release != "0.5.0" or not valid_hash:
        with pytest.raises(ValueError):
            write_personal_package(patch, tmp_path / "catalog", output)
        assert not output.exists()
        return
    write_personal_package(patch, tmp_path / "catalog", output)
    with zipfile.ZipFile(output) as result:
        assert set(result.namelist()) == {patch_name, "build.json", "INSTALL.md"} | {
            "luma/titles/0004000000153600/romfs/" + n for n in ROMFS_FILES
        }
        built = json.loads(result.read("build.json"))
        assert built["personal_package_contains_game_assets"] is True
        assert built["catalog"]["SelectableMachines"] == 384
        for name in ROMFS_FILES:
            blob = result.read("luma/titles/0004000000153600/romfs/" + name)
            assert hashlib.sha256(blob).hexdigest() == built["romfs_sha256"][name]


def test_sarc_writer_hashes_and_aligns_new_members():
    from badge_catalog import write_sarc
    template = (struct.pack("<4sHHIIHH", b"SARC", 20, 0xFEFF, 128, 128, 0x100, 0)
                + struct.pack("<4sHHI", b"SFAT", 12, 0, 101)
                + struct.pack("<4sHH", b"SFNT", 8, 0) + bytes(88))
    files = {"pc/new.z": b"last", "pc/new.a": bytes(131), "pc/other": b"other"}
    blob = write_sarc(files, template)
    assert read_sarc(blob) == files
    nodes = [struct.unpack_from("<4I", blob, 32 + 16 * i) for i in range(3)]
    assert [n[0] for n in nodes] == sorted(n[0] for n in nodes)
    assert all(n[2] % 128 == 0 for n in nodes)
    assert struct.unpack_from("<I", blob, 8)[0] == len(blob)
    assert write_sarc(files, template) == blob


def test_ips_decode_handles_sorted_unordered_and_run_length_records():
    records = [(10, b"test"), (32, b"AAA")]
    assert decode_ips(encode_ips(records, 100), 100) == records
    run = (32).to_bytes(3, "big") + b"\0\0\0\x03A"
    literal = (10).to_bytes(3, "big") + b"\0\x04test"
    assert decode_ips(b"PATCH" + run + literal + b"EOF", 100) == records


@pytest.mark.parametrize("data", [b"", b"PATCH", b"PATCH\0\0\x01\0\x08xEOF",
                                 b"PATCH\0\0\x01\0\0", b"PATCHEOFextra",
                                 encode_ips([(10, b"x")], 100)[:-3] * 2 + b"EOF"])
def test_ips_decode_rejects_malformed_inputs(data):
    with pytest.raises(ValueError):
        decode_ips(data, 100)


def test_expanded_cli_requires_the_full_badge_catalog(tmp_path):
    import subprocess
    import sys
    result = subprocess.run([sys.executable, str(ROOT / "tools/build_complete.py"),
                             "--base-archive", "unused", "--archive", "unused",
                             "--schedule", "unused", "--output", str(tmp_path / "expanded.zip")],
                            capture_output=True, text=True)
    assert result.returncode == 2
    assert "--allbadge" in result.stderr
    assert not (tmp_path / "expanded.zip").exists()


def test_expanded_rejects_an_input_without_full_catalog_resources():
    from test_badge_spotpass import sarc, synthetic_assets
    with pytest.raises(ValueError, match="full allbadge"):
        expand_catalog(sarc(synthetic_assets()), b'<FileItems><Items/></FileItems>',
                       allbadge=sarc({"Schedule.xml": b"not a badge catalog"}))


def test_merged_catalog_preserves_originals_and_makes_every_badge_obtainable():
    base_path = Path(os.environ.get("BADGE_BASE_ARCHIVE", ROOT.parent / "nba-private/inputs/base-pc.sarc"))
    update_path = Path(os.environ.get("BADGE_ARCHIVE", ROOT.parent / "nba-private/inputs/pc.sarc"))
    schedule_path = Path(os.environ.get("BADGE_SCHEDULE", ROOT.parent / "nba-private/inputs/Schedule.xml"))
    if not all(p.is_file() for p in (base_path, update_path, schedule_path)):
        pytest.skip("Requires both private prize archives and the update schedule")
    from badge_catalog import resource_name
    base, update = read_sarc(base_path.read_bytes()), read_sarc(update_path.read_bytes())
    merged, timetable, counts = expand_catalog(update_path.read_bytes(), schedule_path.read_bytes(),
                                               base_path.read_bytes())
    result = read_sarc(merged)
    for name, data in update.items():
        if name != "pc/PrizeCollection.xml":
            assert result[name] == data
    restored = {n: b for n, b in base.items() if n not in update and n.startswith(("pc/rt/", "pc/ci/"))}
    assert all(result[n] == b for n, b in restored.items())
    assert counts["Prizes"] == 2078
    assert counts["OriginalSelectableMachines"] == 398
    assert counts["BonusCatchers"] == 8
    assert counts["SelectableMachines"] == 406
    assert counts["CraneInstances"] == 407
    assert counts["RestoredPrizes"] == 113
    assert counts["RestoredCatchers"] == 14
    stages = [n.findtext("Value") for n in ET.fromstring(timetable).find("Items")
              if (n.findtext("Key") or "").startswith("DefaultStageName")]
    assert len(stages) == len(set(stages)) == 406
    assert all(f"Emblem_{i:03d}" in stages for i in range(8))
    assert all(f"Rhythm_{i:03d}" in stages for i in range(15, 21))
    covered, identities, bonus = set(), set(), set()
    template = decompress_yaz0(update["pc/ci/Kirby_001.cib.szs"])
    for name in stages:
        raw = decompress_yaz0(result[f"pc/ci/{name}.cib.szs"])
        identity = struct.unpack_from("<I", raw, 0x2C)[0]
        assert identity not in identities
        identities.add(identity)
        assert resource_name(raw, 0x30) == name
        prizes = [resource_name(raw, 0x1100 + 48 * i) for i in range(struct.unpack_from("<I", raw, 0xE0)[0])]
        covered.update(prizes)
        if name in {f"BTCenter_{i:03d}" for i in range(4, 12)}:
            bonus.update(prizes)
            assert struct.unpack_from("<I", raw, 0xE8)[0] == 1
            assert resource_name(raw, 0x1880) == "FxOb_Nomal_StepsFour01"
            assert raw[0x1C40:0x4088] == template[0x1C40:0x4088]
            for prize in prizes:
                badge = decompress_yaz0(result[f"pc/rt/Pr/{prize}.prb.szs"])
                texture, polygons = struct.unpack_from("<II", badge, 0x2C)
                assert polygons > texture and struct.unpack_from("<I", badge, polygons)[0] > 0
    assert len(covered) == 2078
    assert len(bonus) == 32
    assert all(f"pc/rt/Pr/{name}.prb.szs" in restored for name in bonus)
