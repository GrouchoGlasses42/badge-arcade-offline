"""Test the desktop weekly builder with synthetic and optional private inputs."""
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile

import pytest

from badge_patch import RELEASE_VERSION
from badge_catalog import decompress_yaz0, encode_yaz0_literals, read_sarc
from patch_format import ROOT, encode_ips
from private_assets import require_external
from weekly_builder import build_host, weekly_records
from test_badge_spotpass import sarc, synthetic_assets, synthetic_week


def tool(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "tools" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="session")
def host(tmp_path_factory):
    path = tmp_path_factory.mktemp("weekly") / "nba-host"
    build_host(path)
    return path


def invoke(host, *args, ok=True):
    result = subprocess.run([str(host), *map(str, args)], capture_output=True, text=True)
    assert (result.returncode == 0) == ok, result.stdout + result.stderr
    return result.stdout if ok else result.stderr


@pytest.mark.parametrize("length", [0, 1, 55, 56, 63, 64, 65, 65535, 65536, 65537, 200003])
def test_hash_matches_independent_sha256_across_block_boundaries(host, tmp_path, length):
    content = bytes(range(251)) * (length // 251) + bytes(range(length % 251))
    source = tmp_path / "input"
    source.write_bytes(content)
    assert invoke(host, "hash", source).strip() == hashlib.sha256(content).hexdigest()


def test_sarc_round_trip_and_invalid_bounds(host, tmp_path):
    files = {"pc/empty": b"", "folder/data": bytes(range(256)) * 1000, "x": b"synthetic"}
    source, output = tmp_path / "source", tmp_path / "output"
    source.write_bytes(sarc(files))
    invoke(host, "sarc", source, output)
    assert read_sarc(output.read_bytes()) == files
    damaged = bytearray(source.read_bytes())
    struct.pack_into("<I", damaged, 44, len(damaged) + 1)
    source.write_bytes(damaged)
    assert "member" in invoke(host, "sarc", source, output, ok=False)
    source.write_bytes(sarc({"../escape": b"no"}))
    assert "Unsafe" in invoke(host, "sarc", source, output, ok=False)


def test_yaz0_literals_and_backreferences_are_bounded(host, tmp_path):
    source, output = tmp_path / "source", tmp_path / "output"
    data = bytes(range(256)) * 40
    source.write_bytes(encode_yaz0_literals(data))
    invoke(host, "yaz0", source, output)
    assert output.read_bytes() == data
    source.write_bytes(b"Yaz0" + struct.pack(">I", 100) + bytes(8) + bytes(4))
    assert "back reference" in invoke(host, "yaz0", source, output, ok=False)
    source.write_bytes(encode_yaz0_literals(data)[:-1])
    assert "Truncated" in invoke(host, "yaz0", source, output, ok=False)


def weekly_inputs(tmp_path):
    assets = synthetic_assets()
    template = assets["pc/ci/CraneInstanceTest.cib.szs"]
    for number, name in enumerate(["Tuesday", "Wednesday", "UnrelatedBuiltin", "Practice", "BonusOnly"], 2):
        raw = bytearray(decompress_yaz0(template))
        struct.pack_into("<I", raw, 0x2C, number)
        struct.pack_into("<I", raw, 0xC0, 2 if name == "Practice" else 0)
        raw[0x30:0x60] = name.encode().ljust(48, b"\0")
        assets[f"pc/ci/{name}.cib.szs"] = encode_yaz0_literals(raw)
    retired = bytearray(decompress_yaz0(assets["pc/rt/Pr/PrizeTest.prb.szs"]))
    struct.pack_into("<I", retired, 0x3C, 2)
    assets["pc/rt/Pr/RetiredOwnedBadge.prb.szs"] = encode_yaz0_literals(retired)
    (tmp_path / "allbadge").write_bytes(sarc(synthetic_assets()))
    base = tmp_path / "base"
    base.write_bytes(sarc(assets))
    baseline = (b'<FileItems><Items><FileItem><Key>DefaultStageName000</Key>'
                b'<Value>UnrelatedBuiltin</Value></FileItem></Items><ItemsCount>1</ItemsCount></FileItems>')
    schedule = tmp_path / "Schedule.xml"
    schedule.write_bytes(baseline)
    top = read_sarc(synthetic_week())
    xml = ET.fromstring(top["Schedule.xml"])
    for item in xml.find("Items"):
        if item.findtext("Key") == "DefaultStageName000":
            item.find("Value").text = ["CraneInstanceTest", "Tuesday", "Wednesday"][int(item.findtext("DateStartText")[-2:]) % 3]
        elif item.findtext("Key") == "BonusStageName" and item.findtext("DateExpireText") == "20220603":
            item.find("Value").text = "BonusOnly"
    top["Schedule.xml"] = ET.tostring(xml)
    week = tmp_path / "week"
    week.write_bytes(sarc(top))
    return base, schedule, week, assets


def test_week_combines_all_seven_days_deduplicates_and_excludes_builtin_machines(host, tmp_path):
    base, schedule, week, original = weekly_inputs(tmp_path)
    output = tmp_path / "new"
    assert invoke(host, "build", base, base, schedule, output, week, "--allbadge", tmp_path / "allbadge", "--synthetic").startswith("4 2 2022-05-27")
    files = read_sarc((output / "romfs/region_EUR/common/sharc/pc.sarc").read_bytes())
    expected = {"CraneInstanceTest", "Tuesday", "Wednesday", "BonusOnly"}
    assert {name[6:-8] for name in files if name.endswith(".cib.szs")} == expected | {"Practice"}
    for name in expected | {"Practice"}:
        path = f"pc/ci/{name}.cib.szs"
        assert files[path] == original[path]
    assert files["pc/rt/Pr/RetiredOwnedBadge.prb.szs"] == original["pc/rt/Pr/RetiredOwnedBadge.prb.szs"]
    xml = ET.parse(output / "romfs/region_common/Schedule.xml")
    stages = [node for node in xml.find("Items") if node.findtext("Key", "").startswith("DefaultStageName")]
    assert {node.findtext("Value") for node in stages} == expected
    assert len(stages) == 4
    assert all(node.findtext("DateStartText") == "20000101" for node in stages)
    manifest = json.loads((output / "catalog.json").read_text())
    assert manifest["unique_weekly_machines"] is True
    assert manifest["machines"] == 4
    assert "day" not in manifest
    assert set(path.name for path in (output / "romfs/region_common").iterdir()) == {"Schedule.xml"}


def test_wrong_input_content_fails_before_output(host, tmp_path):
    base, schedule, week, _ = weekly_inputs(tmp_path)
    output = tmp_path / "new"
    assert "does not match" in invoke(host, "build", base, base, schedule, output, week, "--allbadge", tmp_path / "allbadge", ok=False)
    assert not output.exists()


def test_missing_weekly_resource_fails_before_writing_content(host, tmp_path):
    base, schedule, week, _ = weekly_inputs(tmp_path)
    files = read_sarc(base.read_bytes())
    del files["pc/ci/BonusOnly.cib.szs"]
    base.write_bytes(sarc(files))
    output = tmp_path / "new"
    assert "Missing machine resource" in invoke(host, "build", base, base, schedule,
                                               output, week, "--allbadge", tmp_path / "allbadge", "--synthetic", ok=False)
    assert not output.exists()


@pytest.mark.parametrize("problem", ["region", "dates", "overlap", "missing-day"])
def test_malformed_week_is_rejected(host, tmp_path, problem):
    top = read_sarc(synthetic_week(region="USA" if problem == "region" else "EUR"))
    xml = ET.fromstring(top["Schedule.xml"])
    items = xml.find("Items")
    first = items[1]
    if problem == "dates":
        first.find("DateStartText").text = "20220526"
    elif problem == "overlap":
        items.append(ET.fromstring(ET.tostring(first)))
    elif problem == "missing-day":
        items.remove(first)
    top["Schedule.xml"] = ET.tostring(xml)
    source = tmp_path / "bad-week"
    source.write_bytes(sarc(top))
    invoke(host, "week", source, ok=False)


def test_private_asset_paths_and_public_nested_archives_are_enforced(tmp_path):
    with pytest.raises(ValueError, match="outside"):
        require_external(ROOT / "build/personal.zip")
    link = tmp_path / "link"
    link.symlink_to(ROOT, target_is_directory=True)
    with pytest.raises(ValueError, match="outside"):
        require_external(link / "personal.zip")
    checker = tool("check_assets")
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        archive.writestr("nested/game.dat", b"SARC" + bytes(100))
    with pytest.raises(ValueError, match="signature"):
        checker.inspect("public.zip", stream.getvalue())
    ignored = tmp_path / "build"
    ignored.mkdir()
    (ignored / "private.enc").write_bytes(b"private")
    with pytest.raises(ValueError, match="forbidden"):
        checker.audit(ignored)


def test_weekly_patch_adds_romfs_schedule_and_full_catalog_memory():
    from badge_patch import build_records
    from badge_versions import UPDATE
    for home in (False, True):
        expected, _ = build_records(UPDATE, home_menu=home)
        records = weekly_records(home)
        additional = set(records) - set(expected)
        assert additional == {(0x140C6C, struct.pack("<I", 0xE3A01005)),
                              (0x1480B8, struct.pack("<I", 0xE3A03502)),
                              (0x148C1C, struct.pack("<I", 0xE3A02701))}
        encode_ips(records, UPDATE.size)  # Rejects overlaps and out-of-bounds writes.


def test_real_default_catalog_matches_python_and_preserves_weekly_layouts(host, tmp_path):
    base = Path(os.environ.get("BADGE_BASE_ARCHIVE", "missing"))
    update = Path(os.environ.get("BADGE_ARCHIVE", "missing"))
    schedule = Path(os.environ.get("BADGE_SCHEDULE", "missing"))
    if not all(path.is_file() for path in (base, update, schedule)):
        pytest.skip("Requires private matching game resources outside the repository")
    from badge_catalog import expand_catalog
    output = tmp_path / "default"
    assert invoke(host, "build", base, update, schedule, output).startswith("406 2078 default")
    actual = read_sarc((output / "romfs/region_EUR/common/sharc/pc.sarc").read_bytes())
    expected, _, counts = expand_catalog(update.read_bytes(), schedule.read_bytes(), base.read_bytes())
    expected = read_sarc(expected)
    assert counts["SelectableMachines"] == 406
    for path in actual:
        if path.endswith((".cib.szs", ".icb.szs")):
            assert actual[path] == expected[path], path
    week_path = os.environ.get("BADGE_WEEK_SARC")
    allbadge_path = os.environ.get("BADGE_ALLBADGE_SARC")
    if not week_path or not allbadge_path:
        return
    top = read_sarc(Path(week_path).read_bytes())
    xml = ET.fromstring(top["Schedule.xml"])
    chosen = {item.findtext("Value") for item in xml.find("Items")
              if item.findtext("Key", "").startswith("DefaultStageName") or item.findtext("Key") == "BonusStageName"}
    output = tmp_path / "week"
    line = invoke(host, "build", base, update, schedule, output, week_path, "--allbadge", allbadge_path)
    assert int(line.split()[0]) == len(chosen) == 210
    weekly = read_sarc((output / "romfs/region_EUR/common/sharc/pc.sarc").read_bytes())
    originals = read_sarc(base.read_bytes()) | read_sarc(update.read_bytes())
    archive_name = next(item.findtext("Value") for item in xml.find("Items") if item.findtext("RegexSetName") == "PrizeCollection")
    originals.update(read_sarc(Path(allbadge_path).read_bytes()))
    originals.update(read_sarc(top[archive_name]))
    for name in chosen:
        path = f"pc/ci/{name}.cib.szs"
        assert weekly[path] == originals[path]


def historical_catalog():
    catalog = synthetic_assets()
    prize = bytearray(decompress_yaz0(catalog["pc/rt/Pr/PrizeTest.prb.szs"]))
    struct.pack_into("<I", prize, 0x3C, 333)
    catalog["pc/rt/Pr/OnlyInAllbadge.prb.szs"] = encode_yaz0_literals(prize)
    raw = bytearray(decompress_yaz0(catalog["pc/ci/CraneInstanceTest.cib.szs"]))
    raw[0x30:0x60] = b"HistoricalMachine".ljust(48, b"\0")
    raw[0x1100:0x1130] = b"OnlyInAllbadge".ljust(48, b"\0")
    # The real allbadge archive omits obstacles used only during gameplay.
    struct.pack_into("<I", raw, 0xE8, 1)
    raw[0x1880:0x18B0] = b"UnneededPlayfieldObstacle".ljust(48, b"\0")
    catalog["pc/ci/HistoricalMachine.cib.szs"] = encode_yaz0_literals(raw)
    return catalog, raw


def test_full_allbadge_catalog_remains_browsable_without_extra_playable_machines(host, tmp_path):
    base, schedule, week, _ = weekly_inputs(tmp_path)
    catalog, raw = historical_catalog()
    allbadge = tmp_path / "allbadge"
    allbadge.write_bytes(sarc(catalog))
    output = tmp_path / "new"
    assert invoke(host, "build", base, base, schedule, output, week, "--allbadge", allbadge,
                  "--synthetic").startswith("4 3 2022-05-27")
    actual = read_sarc((output / "romfs/region_EUR/common/sharc/pc.sarc").read_bytes())
    assert actual["pc/rt/Pr/OnlyInAllbadge.prb.szs"] == catalog["pc/rt/Pr/OnlyInAllbadge.prb.szs"]
    historical = bytearray(decompress_yaz0(actual["pc/ci/HistoricalMachine.cib.szs"]))
    assert struct.unpack_from("<I", historical, 0xC0)[0] == 1
    struct.pack_into("<I", historical, 0xC0, 0)
    assert historical == raw
    schedule = ET.parse(output / "romfs/region_common/Schedule.xml")
    assert "HistoricalMachine" not in {node.findtext("Value") for node in schedule.find("Items")}
    assert json.loads((output / "catalog.json").read_text())["full_allbadge_catalog"] is True


@pytest.mark.parametrize("encrypted,home", [(False, False), (True, True)])
def test_weekly_to_expanded_preserves_historical_badges_and_only_expanded_machines(
        host, tmp_path, monkeypatch, encrypted, home):
    from badge_versions import CATALOG_RECORDS, UPDATE
    from patch_format import decode_ips
    from test_badge_spotpass import encrypted_container
    original = synthetic_assets()
    historical, _ = historical_catalog()
    base, schedule, week, allbadge = [tmp_path / name for name in ("base", "Schedule.xml", "week", "allbadge")]
    base.write_bytes(sarc(original))
    schedule.write_text('<FileItems><Items/><ItemsCount>0</ItemsCount></FileItems>')
    week.write_bytes(synthetic_week())
    allbadge.write_bytes(sarc(historical))
    weekly = tmp_path / "weekly"
    invoke(host, "build", base, base, schedule, weekly, week, "--allbadge", allbadge, "--synthetic")
    before = read_sarc((weekly / "romfs/region_EUR/common/sharc/pc.sarc").read_bytes())
    if encrypted:
        allbadge.write_bytes(encrypted_container(allbadge.read_bytes()))
    boot9 = tmp_path / "boot9"
    boot9.write_bytes(bytes(0x8000))
    inputs = {path: path.read_bytes() for path in (base, schedule, week, allbadge, boot9)}
    output = tmp_path / "expanded.zip"
    module = tool("build_complete")
    # Only the fixed game fingerprints need replacement for synthetic assets.
    monkeypatch.setattr(module, "verify_input", lambda path, expected: None)
    argv = ["build_complete", "--base-archive", str(base), "--update-archive", str(base),
            "--schedule", str(schedule), "--allbadge", str(allbadge), "--output", str(output)]
    if encrypted:
        argv += ["--boot9", str(boot9)]
    if home:
        argv += ["--home-menu"]
    monkeypatch.setattr(module.sys, "argv", argv)
    module.main()
    prefix = "luma/titles/0004000000153600/"
    variant = "home-menu" if home else "game-only"
    with zipfile.ZipFile(ROOT / f"releases/v{RELEASE_VERSION}/nba-offline-v{RELEASE_VERSION}-{variant}.zip") as release:
        source_ips = release.read(prefix + "code.ips")
    with zipfile.ZipFile(output) as package:
        after = read_sarc(package.read(prefix + "romfs/region_EUR/common/sharc/pc.sarc"))
        for name in before:
            if name.startswith("pc/rt/Pr/"):
                assert after[name] == before[name]
        assert after["pc/ci/CraneInstanceTest.cib.szs"] == original["pc/ci/CraneInstanceTest.cib.szs"]
        display = decompress_yaz0(after["pc/ci/HistoricalMachine.cib.szs"])
        assert struct.unpack_from("<I", display, 0xC0)[0] == 1
        timetable = ET.fromstring(package.read(prefix + "romfs/region_common/Schedule.xml"))
        assert [item.findtext("Value") for item in timetable.find("Items")] == ["CraneInstanceTest"]
        ips = package.read(prefix + "code.ips")
        assert decode_ips(ips, UPDATE.size) == sorted([*decode_ips(source_ips, UPDATE.size), *CATALOG_RECORDS])
        manifest = json.loads(package.read("build.json"))
        assert manifest["catalog"]["FullAllbadgeCatalog"] is True
        assert manifest["catalog"]["Prizes"] == 2
        assert manifest["catalog"]["PlayablePrizes"] == 1
        assert manifest["catalog"]["SelectableMachines"] == 1
        assert manifest["ips_sha256"] == hashlib.sha256(ips).hexdigest()
        assert manifest["source_ips_sha256"] == hashlib.sha256(source_ips).hexdigest()
        assert len(package.namelist()) == 6
        assert not any(name.endswith((".bin", ".boss", ".enc")) for name in package.namelist())
    for path, data in inputs.items():
        assert path.read_bytes() == data


def test_week_requires_allbadge_instead_of_silently_building_a_partial_browser(host, tmp_path):
    base, schedule, week, _ = weekly_inputs(tmp_path)
    output = tmp_path / "new"
    assert "require the full allbadge" in invoke(host, "build", base, base, schedule, output,
                                                week, "--synthetic", ok=False)
    assert not output.exists()


@pytest.mark.parametrize("encrypted,update_flag,home", [(False, "--update-archive", False),
                                                       (True, "--archive", True)])
def test_weekly_script_decrypts_locally_and_packages_only_the_personal_patch(
        tmp_path, monkeypatch, capsys, encrypted, update_flag, home):
    from test_badge_spotpass import encrypted_container
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    module = tool("build_spotpass")
    week, allbadge = synthetic_week(), sarc(synthetic_assets())
    inputs = {"base": b"synthetic base", "update": b"synthetic update", "schedule": b"synthetic schedule",
              "week": encrypted_container(week) if encrypted else week,
              "allbadge": encrypted_container(allbadge) if encrypted else allbadge}
    if encrypted:
        inputs["boot9"] = bytes(0x8000)
    for name, data in inputs.items():
        (tmp_path / name).write_bytes(data)
    records = [(0x100, b"HOME" if home else b"GAME")]
    monkeypatch.setattr(module, "weekly_records", lambda enabled: records if enabled == home else [])
    monkeypatch.setattr(module, "build_host", lambda path: None)

    def build_core(command, **kwargs):
        assert command[1] == "build"
        assert command[2:5] == [str(tmp_path / name) for name in ("base", "update", "schedule")]
        assert command[7] == "--allbadge"
        assert Path(command[6]).read_bytes() == week
        assert Path(command[8]).read_bytes() == allbadge
        assert not any("boot9" in argument for argument in command)
        assert kwargs["check"] is True
        output = Path(command[5])
        (output / "romfs").mkdir(parents=True)
        (output / "romfs/pc.sarc").write_bytes(b"synthetic merged catalog")
        (output / "catalog.json").write_text(json.dumps({
            "mode": "week", "week": "2022-05-27", "machines": 2, "badge_resources": 4,
            "unique_weekly_machines": True, "full_allbadge_catalog": True,
        }))

    monkeypatch.setattr(module.subprocess, "run", build_core)
    output = tmp_path / "custom-weekly.zip"
    argv = ["build_spotpass.py", "--base-archive", str(tmp_path / "base"),
            update_flag, str(tmp_path / "update"), "--schedule", str(tmp_path / "schedule"),
            "--week", str(tmp_path / "week"), "--allbadge", str(tmp_path / "allbadge"),
            "--output", str(output)]
    if encrypted:
        argv += ["--boot9", str(tmp_path / "boot9")]
    if home:
        argv += ["--home-menu"]
    monkeypatch.setattr(module.sys, "argv", argv)
    module.main()
    prefix = "luma/titles/0004000000153600/"
    with zipfile.ZipFile(output) as archive:
        assert set(archive.namelist()) == {"INSTALL.md", prefix + "code.ips",
                                         prefix + "catalog.json", prefix + "romfs/pc.sarc"}
        assert archive.read(prefix + "code.ips") == encode_ips(records, module.UPDATE.size)
        assert json.loads(archive.read(prefix + "catalog.json"))["home_menu"] is home
    for name, data in inputs.items():
        assert (tmp_path / name).read_bytes() == data
    assert "2 unique playable machines" in capsys.readouterr().out


@pytest.mark.parametrize("name", ["game.cia", "custom.cia", "public.zip:custom.cia"])
def test_asset_audit_rejects_all_cia_containers(name):
    with pytest.raises(ValueError, match="forbidden"):
        tool("check_assets").inspect(name, b"synthetic container")
