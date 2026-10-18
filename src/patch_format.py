"""ARM ELF and IPS utilities; no game data or compiler dependencies at import."""
from pathlib import Path
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def arm_branch(source: int, target: int) -> bytes:
    """Encode an unconditional ARM branch, preserving the caller's LR."""
    displacement = target - source - 8
    if displacement % 4 or not -(1 << 25) <= displacement < (1 << 25):
        raise ValueError("ARM branch target is unaligned or out of range")
    return struct.pack("<I", 0xEA000000 | ((displacement >> 2) & 0xFFFFFF))


def read_arm_object(data: bytes, load_address: int) -> tuple[bytes, dict[str, int]]:
    """Read .text and symbols from clang's little-endian ARM ELF object."""
    if data[:6] != b"\x7fELF\x01\x01" or struct.unpack_from("<H", data, 18)[0] != 40:
        raise ValueError("Expected a 32-bit little-endian ARM ELF")
    shoff = struct.unpack_from("<I", data, 32)[0]
    shsize, shcount, shnames = struct.unpack_from("<HHH", data, 46)
    sections = [struct.unpack_from("<10I", data, shoff + i * shsize) for i in range(shcount)]

    def content(section: tuple[int, ...]) -> bytes:
        return data[section[4]:section[4] + section[5]]

    def name(table: bytes, offset: int) -> str:
        return table[offset:table.index(0, offset)].decode("ascii")

    names = content(sections[shnames])
    text_index = next(i for i, s in enumerate(sections) if name(names, s[0]) == ".text")
    symbols = {}
    for section in sections:
        if section[1] != 2:
            continue
        table = content(sections[section[6]])
        for offset in range(section[4], section[4] + section[5], section[9]):
            n, value, _, _, _, index = struct.unpack_from("<IIIBBH", data, offset)
            if index == text_index and n:
                symbols[name(table, n)] = load_address + value
    text = bytearray(content(sections[text_index]))
    for section in sections:
        if section[1] not in (4, 9) or section[7] != text_index or not section[5]:
            continue
        if section[1] != 9:
            raise ValueError("Unsupported ELF relocation section")
        symtab = sections[section[6]]
        for offset in range(section[4], section[4] + section[5], 8):
            position, info = struct.unpack_from("<II", data, offset)
            _, target, _, _, _, index = struct.unpack_from(
                "<IIIBBH", data, symtab[4] + (info >> 8) * symtab[9],
            )
            if info & 0xFF != 28 or index != text_index:
                raise ValueError("Only local R_ARM_CALL relocations are supported")
            if struct.unpack_from("<I", text, position)[0] != 0xEBFFFFFE:
                raise ValueError("Unexpected ARM call relocation addend")
            branch = arm_branch(position, target)
            struct.pack_into("<I", text, position, struct.unpack("<I", branch)[0] | 0x01000000)
    return bytes(text), symbols


def encode_ips(records: list[tuple[int, bytes]], code_size: int) -> bytes:
    """Encode standard IPS records against the decompressed ExeFS .code."""
    out = bytearray(b"PATCH")
    end = 0
    for offset, data in records:
        if offset < end or offset + len(data) > code_size or not 0 < len(data) <= 0xFFFF:
            raise ValueError("Invalid or overlapping patch record")
        out.extend(offset.to_bytes(3, "big"))
        out.extend(len(data).to_bytes(2, "big"))
        out.extend(data)
        end = offset + len(data)
    return bytes(out + b"EOF")


def decode_ips(data: bytes, code_size: int) -> list[tuple[int, bytes]]:
    """Read bounded IPS records, including run-length records."""
    if not data.startswith(b"PATCH"):
        raise ValueError("Invalid IPS header")
    records = []
    pos = 5
    while data[pos:pos + 3] != b"EOF":
        if pos + 5 > len(data):
            raise ValueError("Truncated IPS record")
        offset = int.from_bytes(data[pos:pos + 3], "big")
        length = int.from_bytes(data[pos + 3:pos + 5], "big")
        pos += 5
        if length:
            if pos + length > len(data):
                raise ValueError("Truncated IPS data")
            value = data[pos:pos + length]
            pos += length
        else:
            if pos + 3 > len(data):
                raise ValueError("Truncated IPS run")
            length = int.from_bytes(data[pos:pos + 2], "big")
            value = data[pos + 2:pos + 3] * length
            pos += 3
        records.append((offset, value))
    if pos + 3 != len(data):
        raise ValueError("Unexpected IPS trailing data")
    records.sort()
    encode_ips(records, code_size)  # Check bounds, empty records, and overlaps.
    return records


def write_zip(path: Path, files: dict[str, bytes]) -> None:
    """Write stable ZIP bytes, independent of host paths, mtimes and file modes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in sorted(files.items()):
            entry = zipfile.ZipInfo(name, date_time=(2026, 10, 17, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, data)
