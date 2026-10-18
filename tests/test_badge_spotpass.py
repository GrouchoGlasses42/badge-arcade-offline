"""Synthetic desktop BOSS import fixtures, with no game assets."""
from datetime import date, timedelta
import hashlib
import struct
import xml.etree.ElementTree as ET

import pytest

from badge_catalog import REGISTRIES, encode_yaz0_literals, write_sarc
from badge_spotpass import EUR_TITLE_ID, open_spotpass


def sarc(files):
    template = (struct.pack("<4sHHIIHH", b"SARC", 20, 0xFEFF, 128, 128, 0x100, 0)
                + struct.pack("<4sHHI", b"SFAT", 12, 0, 101)
                + struct.pack("<4sHH", b"SFNT", 8, 0) + bytes(88))
    return write_sarc(files, template)


def synthetic_assets():
    files = {}
    registry = ET.Element("PrizeCollection")
    for block, (tag, prefix, suffix, _) in REGISTRIES.items():
        name = tag + "Test"
        raw = bytearray(0x2000)
        if block == "Categories":
            struct.pack_into("<I", raw, 0x24, 1)
        elif block == "Prizes":
            struct.pack_into("<I", raw, 0x3C, 1)
            raw[0x74:0xA4] = b"CategoryTest".ljust(48, b"\0")
        elif block == "CraneInstances":
            for offset, value in ((0x60, b"CraneTest"), (0x90, b"CraneIconTest"),
                                  (0x1100, b"PrizeTest")):
                raw[offset:offset + 48] = value.ljust(48, b"\0")
            struct.pack_into("<I", raw, 0xE0, 1)
        files[prefix + name + suffix] = encode_yaz0_literals(raw)
        node = ET.SubElement(registry, block, count="1")
        ET.SubElement(node, tag, name=name)
    files["pc/PrizeCollection.xml"] = ET.tostring(registry)
    return files


def synthetic_week(start=date(2022, 5, 27), *, region="EUR"):
    root = ET.Element("FileItems")
    items = ET.SubElement(root, "Items")
    for key, name, first, last, kind in [
        ("sharc/pc00.sarc", "sharc/test.sarc", 0, 7, "PrizeCollection"),
        *[("DefaultStageName000", "CraneInstanceTest", day, day + 1, "DefaultStage") for day in range(7)],
        *[("BonusStageName", "CraneInstanceTest", day, day + 1, "BonusStage") for day in range(7)],
    ]:
        node = ET.SubElement(items, "FileItem")
        for tag, value in (("Key", key), ("Value", name), ("RegexSetName", kind),
                           ("DateStartText", (start + timedelta(days=first)).strftime("%Y%m%d")),
                           ("DateExpireText", (start + timedelta(days=last)).strftime("%Y%m%d"))):
            ET.SubElement(node, tag).text = value
    ET.SubElement(root, "ItemsCount").text = str(len(items))
    return sarc({"Schedule.xml": ET.tostring(root), "sharc/test.sarc": sarc(synthetic_assets()),
                 f"message/boss_{region}/test": b"synthetic"})


def plain_container(payload, *, program=EUR_TITLE_ID):
    content = bytearray(0x132)
    struct.pack_into(">H", content, 0x10, 1)
    content[0x12:0x32] = hashlib.sha256(content[:0x12] + bytes(2)).digest()
    header = bytearray(0x13C)
    struct.pack_into(">QIII", header, 0, program, 0, 0, len(payload))
    header[0x1C:0x3C] = hashlib.sha256(header[:0x1C] + bytes(2) + payload).digest()
    body = content + header + payload
    boss = bytearray(0x28)
    boss[:4] = b"boss"
    struct.pack_into(">II", boss, 4, 0x10001, len(boss) + len(body))
    return bytes(boss) + body


def encrypted_container(payload, *, program=EUR_TITLE_ID):
    AES = pytest.importorskip("Crypto.Cipher.AES")
    plain = plain_container(payload, program=program)
    body = AES.new(bytes(16), AES.MODE_CTR, nonce=bytes(12), initial_value=1).encrypt(plain[0x28:])
    return plain[:0x28] + body


def test_encrypted_import_checks_integrity_region_and_dump_without_exporting_keys():
    payload = synthetic_week()
    encrypted = encrypted_container(payload)
    assert open_spotpass(encrypted, bytes(0x8000)) == payload
    assert open_spotpass(encrypted, bytes(0x10000)) == payload
    assert open_spotpass(payload) == payload
    with pytest.raises(ValueError, match="require --boot9"):
        open_spotpass(encrypted)
    with pytest.raises(ValueError, match="dump"):
        open_spotpass(encrypted, bytes(100))
    damaged = encrypted[:-1] + bytes([encrypted[-1] ^ 1])
    with pytest.raises(ValueError, match="payload hash"):
        open_spotpass(damaged, bytes(0x8000))
    with pytest.raises(ValueError, match="not for EUR"):
        open_spotpass(encrypted_container(payload, program=0x1234), bytes(0x8000))
    with pytest.raises(ValueError, match="container length"):
        open_spotpass(encrypted[:-1], bytes(0x8000))
