"""Native ARM checks with isolated OS boundaries."""

from __future__ import annotations

import os
import json
from pathlib import Path
import struct
import sys
import zipfile

import pytest
from unicorn import Uc, UcError, UC_ARCH_ARM, UC_HOOK_CODE, UC_HOOK_INTR, UC_MODE_ARM
from unicorn.arm_const import (
    UC_ARM_REG_C1_C0_2, UC_ARM_REG_FPEXC,
    UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1,
    UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_R5,
    UC_ARM_REG_R6, UC_ARM_REG_R7, UC_ARM_REG_R8, UC_ARM_REG_R9,
    UC_ARM_REG_R10, UC_ARM_REG_R11, UC_ARM_REG_SP,
)

import badge_patch as badge
from badge_versions import BASE, REVISIONS
from patch_format import ROOT, encode_ips

SAVE = 0x500000
STORAGE = 0x540000
WORLD = 0x580000
TASK = 0x680000
CONTEXT = 0x690000
STATUS = 0x69F000
STOP = 0x6FF000
STACK = 0x8FF000
ARGS = [UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3]
PRESERVED = [UC_ARM_REG_R4, UC_ARM_REG_R5, UC_ARM_REG_R6, UC_ARM_REG_R7,
             UC_ARM_REG_R8, UC_ARM_REG_R9, UC_ARM_REG_R10, UC_ARM_REG_R11]


@pytest.fixture(scope="module", params=REVISIONS, ids=lambda r: r.version)
def badge_revision(request):
    return request.param


@pytest.fixture(scope="module", params=[False, True], ids=["game-only", "home-menu"])
def home_menu(request):
    return request.param


@pytest.fixture(autouse=True)
def home_variant_requirement(request):
    marker = request.node.get_closest_marker("home_variant")
    if marker is not None and request.getfixturevalue("home_menu") != marker.args[0]:
        pytest.skip("Test applies to the other HOME variant")


@pytest.fixture(scope="module")
def badge_records(badge_revision, home_menu):
    return badge.build_records(badge_revision, home_menu=home_menu)


class RevisionCode(bytes):
    def __new__(cls, code, revision):
        obj = super().__new__(cls, code)
        obj.revision = revision
        return obj


@pytest.fixture(scope="module")
def badge_code(badge_records, badge_revision):
    path = Path(os.environ.get("BADGE_CODE", Path(os.environ.get("BADGE_INPUT_DIR", ROOT.parent / "nba-private/inputs")) / badge_revision.input_name))
    if not path.is_file():
        pytest.skip("Native Badge Arcade tests require BADGE_CODE (decompressed EUR executable)")
    code = path.read_bytes()
    if badge.detect_revision(code) != badge_revision:
        pytest.skip("BADGE_CODE selects a different supported revision")
    return RevisionCode(badge.apply_records(code, badge_records[0], badge_revision), badge_revision)


class BadgeMachine:
    def __init__(self, code):
        self.revision = getattr(code, "revision", BASE)
        self.canonical = {value: key for key, value in self.revision.addresses.items()}
        self.uc = Uc(UC_ARCH_ARM, UC_MODE_ARM)
        self.uc.reg_write(UC_ARM_REG_C1_C0_2, 0xF << 20)
        self.uc.reg_write(UC_ARM_REG_FPEXC, 0x40000000)
        self.uc.mem_map(0x100000, 0x800000)
        self.uc.mem_write(0x100000, code)
        self.put(0x42B140, SAVE)
        self.put(0x42AE3C, STORAGE)
        self.put(0x42AE68, WORLD)
        self.put(0x42AD9C, 0x6A1000)
        self.put(0x6A1064, 0x6A2000)
        self.put(WORLD + 0x70E54, 0x6A3000)
        self.calls = []
        self.boundaries = {}
        self.uc.hook_add(UC_HOOK_CODE, self.on_code)
        self.uc.hook_add(UC_HOOK_INTR, self.on_svc)

    def init_owned_pool(self, capacity=8):
        """Supply the four native fixed-capacity node pools used by OwnedBadge."""
        model = self.word(WORLD + 0x70E54)
        for index, offset in enumerate((0xC, 0x20, 0x34, 0x48)):
            self.put(model + offset, 0)
            self.put(model + offset + 4, capacity)
            self.put(model + offset + 8, 0x750000 + index * 0x1000)
            self.put(model + offset + 12, 0x760000 + index * 0x1000)
            for item in range(capacity):
                node = 0x760000 + index * 0x1000 + item * 16
                self.put(node, node + 16 if item < capacity - 1 else 0)
        # Acquisition history has separate locking and is outside this test.
        self.boundaries[0x2CD5DC] = lambda: None

    def mock_storage(self, files=None):
        """Isolate the native FileDevice boundary, retaining real ARM framing."""
        self.files = {} if files is None else dict(files)
        self.open_files = {}
        self.fail_write = None
        self.fail_create = False
        self.boundaries.update({
            0x25ACD4: lambda: self.result(0x6B0000),
            0x2704B8: self.open_file,
            0x25A684: self.create_file,
            0x2703BC: self.write_file,
            0x271DE4: self.read_file,
            0x271EFC: lambda: self.result(1),
        })

    def cstring(self, address):
        return bytes(self.uc.mem_read(address, 128)).split(b"\0")[0].decode()

    def open_file(self):
        name = self.cstring(self.word(self.reg(2) + 4))
        # The console's extdata table has a 16-byte ASCII name field. Azahar's
        # host filesystem accepts longer names, so it cannot catch this alone.
        if len(name.encode("ascii")) > 16 or name not in self.files:
            self.result(0)
            return
        self.open_files[self.reg(1)] = [name, 0]
        self.result(0x6B0000)

    def create_file(self):
        if self.fail_create:
            self.result(0)
            return
        name = self.cstring(self.reg(1))
        if len(name.encode("ascii")) > 16:
            self.result(0)
            return
        self.files[name] = bytes(self.reg(2))
        self.result(1)

    def write_file(self):
        name, position = self.open_files[self.reg(2)]
        if self.fail_write == name:
            self.result(0)
            return
        count = self.word(self.uc.reg_read(UC_ARM_REG_SP))
        blob = bytearray(self.files[name])
        blob[position:position + count] = self.uc.mem_read(self.reg(3), count)
        self.files[name] = bytes(blob)
        self.open_files[self.reg(2)][1] += count
        self.put(self.reg(1), count)
        self.result(1)

    def read_file(self):
        name, position = self.open_files[self.reg(2)]
        count = self.word(self.uc.reg_read(UC_ARM_REG_SP))
        blob = self.files[name][position:position + count]
        self.uc.mem_write(self.reg(3), blob)
        self.open_files[self.reg(2)][1] += len(blob)
        self.put(self.reg(1), len(blob))
        self.result(1)

    def reg(self, i=0):
        return self.uc.reg_read(ARGS[i])

    def native(self, address):
        """Translate canonical fixture addresses to the executable under test."""
        if WORLD + 0x70DF4 <= address <= WORLD + 0x70E54:
            shift = self.revision.world_shift
            # The update moves the later pending-play/ownership fields four
            # bytes less than its earlier profile and schedule fields.
            if shift and address >= WORLD + 0x70E38:
                shift -= 4
            return address + shift
        return self.revision.address(address)

    def put(self, address, value):
        self.uc.mem_write(self.native(address), struct.pack("<I", value))

    def word(self, address):
        return struct.unpack("<I", self.uc.mem_read(self.native(address), 4))[0]

    def byte(self, address):
        return self.uc.mem_read(self.native(address), 1)[0]

    def result(self, value):
        self.uc.reg_write(UC_ARM_REG_R0, value)

    def on_svc(self, uc, number, data):
        raise AssertionError(f"Unexpected SVC {number} at {uc.reg_read(UC_ARM_REG_PC):08x}")

    def on_code(self, uc, address, size, data):
        address = self.canonical.get(address, address)
        if address == STOP:
            uc.emu_stop()
        elif address in self.boundaries:
            self.calls.append(address)
            self.boundaries[address]()
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    def run(self, address, *args):
        self.uc.reg_write(UC_ARM_REG_SP, STACK)
        self.uc.reg_write(UC_ARM_REG_LR, STOP)
        for register, value in zip(ARGS, args):
            self.uc.reg_write(register, value)
        for i, register in enumerate(PRESERVED):
            self.uc.reg_write(register, 0xABC000 + i)
        try:
            self.uc.emu_start(self.native(address), STOP + 4, count=200000)
        except UcError as exc:
            raise AssertionError(f"ARM failed at {self.uc.reg_read(UC_ARM_REG_PC):08x}") from exc
        assert self.uc.reg_read(UC_ARM_REG_PC) == STOP, "Routine failed to return"
        assert self.uc.reg_read(UC_ARM_REG_SP) == STACK
        for i, register in enumerate(PRESERVED):
            assert self.uc.reg_read(register) == 0xABC000 + i
        return self.reg()


def test_badge_rejects_other_revisions(badge_records):
    with pytest.raises(ValueError, match="Unsupported executable"):
        badge.apply_records(bytes(badge.CODE_SIZE), badge_records[0])


@pytest.mark.parametrize("full_catalog", [False, True])
def test_full_catalog_reserves_metadata_heap_without_growing_temporary_heaps(badge_code, full_catalog):
    from badge_versions import CATALOG_RECORDS, UPDATE
    if badge_code.revision != UPDATE:
        pytest.skip("Full catalog targets EUR update 1.3.1")
    m = BadgeMachine(badge_code)
    m.put(0x450798, 0x6B0000)  # Native heap-manager singleton.
    if full_catalog:
        for offset, data in CATALOG_RECORDS:
            m.uc.mem_write(badge.LOAD_ADDRESS + offset, data)
    sizes = []

    def create_heap(uc, address, size, data):
        if address != 0x264F4C:
            return
        sizes.append(m.reg(3))
        # Supply only the OS heap factory boundary; execute the real manager
        # initializer so an incorrect instruction address fails this check.
        m.uc.mem_write(m.reg(), struct.pack("<II", 0x700000, 0x700000))
        if len(sizes) == 3:
            uc.emu_stop()
        else:
            uc.reg_write(UC_ARM_REG_PC, uc.reg_read(UC_ARM_REG_LR))

    m.uc.hook_add(UC_HOOK_CODE, create_heap)
    m.uc.reg_write(UC_ARM_REG_SP, STACK)
    for register, value in zip(ARGS, (0x6A1000, 0x700100, 0)):
        m.uc.reg_write(register, value)
    m.uc.emu_start(0x248038, STOP, count=1000)
    assert sizes == [0x800000 if full_catalog else 0x380000, 0x380000, 0x100000]


@pytest.mark.parametrize("filename", ["offline-owned-a.dat", "offline-profile-a.dat"])
def test_builder_rejects_backup_names_that_cannot_exist_in_console_extdata(tmp_path, monkeypatch, filename):
    source = (ROOT / "patches/badge_offline.s").read_text().replace("ba_owned_a.dat", filename)
    (tmp_path / "patches").mkdir()
    (tmp_path / "patches/badge_offline.s").write_text(source)
    monkeypatch.setattr(badge, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="16-byte"):
        badge.build_records()


def test_badge_ips_records_are_bounded_and_nonoverlapping(badge_records, badge_revision, home_menu):
    records, symbols = badge_records
    ips = encode_ips(records, badge.CODE_SIZE)
    assert ips.startswith(b"PATCH") and ips.endswith(b"EOF")
    assert len(records) == len(badge.selected_hooks(home_menu)) + 3 + (0 if home_menu else 3) + (badge_revision.version == "1.3.1")
    assert symbols["badge_title_start"] == badge_revision.address(badge.PAYLOAD_ADDRESS)
    assert max(a + len(b) for a, b in records) <= badge.CODE_SIZE
    payload = next(b for a, b in records
                   if a == badge_revision.address(badge.PAYLOAD_ADDRESS) - badge.LOAD_ADDRESS)
    assert badge_revision.address(badge.PAYLOAD_ADDRESS) + len(payload) <= badge_revision.address(badge.PAYLOAD_LIMIT)


def test_luma_package_contains_only_the_patch(tmp_path, badge_records):
    ips = encode_ips(badge_records[0], badge.CODE_SIZE)
    path = tmp_path / "output/badge.zip"
    badge.write_package(path, ips, {})
    with zipfile.ZipFile(path) as archive:
        target = "luma/titles/0004000000153600/code.ips"
        assert set(archive.namelist()) == {target}
        assert archive.read(target) == ips


def test_cli_selects_the_executable_revision_before_packaging(
    badge_code, badge_revision, tmp_path, monkeypatch, home_menu,
):
    source = Path(os.environ.get("BADGE_CODE", Path(os.environ.get("BADGE_INPUT_DIR", ROOT.parent / "nba-private/inputs")) / badge_revision.input_name))
    package = tmp_path / "patch.zip"
    output = tmp_path / "build"
    monkeypatch.setattr(sys, "argv", ["badge_patch", "--code", str(source),
                                    "--output", str(output), "--package", str(package),
                                    *(["--home-menu"] if home_menu else [])])
    badge.main()
    with zipfile.ZipFile(package) as archive:
        assert set(archive.namelist()) == {"luma/titles/0004000000153600/code.ips"}
    manifest = json.loads((output / "build.json").read_text())
    assert manifest["game_version"] == badge_revision.version
    assert manifest["release_version"] == badge.RELEASE_VERSION
    assert manifest["variant"] == ("home-menu" if home_menu else "game-only")
    assert manifest["source_code_sha256"] == badge_revision.sha256
    assert manifest["requires_installed_update"] == (badge_revision.version == "1.3.1")
    other = next(r for r in REVISIONS if r != badge_revision)
    with pytest.raises(ValueError, match="Unsupported executable"):
        badge.apply_records(source.read_bytes(), badge.build_records(other)[0], other)


def test_title_uses_local_resources_before_native_commit(badge_code):
    m = BadgeMachine(badge_code)
    m.mock_storage()
    m.uc.mem_write(TASK, b"\xA5" * 0x418)

    def now():
        assert m.reg() == TASK + 0x410
        m.uc.mem_write(m.reg(), struct.pack("<Q", 123456789))

    m.boundaries[0x25BA24] = now
    m.run(0x342FBC, TASK)
    assert m.word(TASK + 0x1BC) == 0x26
    assert [m.word(TASK + a) for a in (0x3FC, 0x400, 0x404, 0x408, 0x40C)] == [2, 0, 0, 0, 2]
    assert m.byte(TASK + 0x1C0) == m.byte(TASK + 0x1C2) == 0
    assert m.word(TASK + 0x410) == 123456789
    assert m.calls == [0x25BA24]
    m.boundaries[0x21C1E0] = lambda: m.result(0)
    m.run(0x33F30C, TASK)
    assert m.word(TASK + 0x1BC) == 0x36


@pytest.mark.parametrize("mounted", [False, True])
def test_existing_extdata_is_used_without_creation(badge_code, badge_records, mounted):
    m = BadgeMachine(badge_code)
    m.put(0x42C94C, int(mounted))
    m.boundaries[0x21C1E0] = lambda: m.result(0)
    assert m.run(badge_records[1]["badge_prepare_extdata"], TASK) == 1
    assert m.calls == ([] if mounted else [0x21C1E0])


def mock_extdata_creation(m, mount_results):
    m.put(TASK + 0xBC, 0x710000)
    mounts = iter(mount_results)
    m.boundaries[0x21C1E0] = lambda: m.result(next(mounts))

    def allocate_icon():
        assert [m.reg(i) for i in range(3)] == [0x36C0, 0x710000, 0x20]
        m.result(0x750000)

    def free_icon():
        assert m.reg() == 0x750000

    def create_archive():
        assert [m.reg(i) for i in range(4)] == [0x1536, 0, 0x750000, 0x36C0]
        icon = bytes(m.uc.mem_read(m.reg(2), 0x36C0))
        assert icon[:8] == b"SMDH" + bytes(4)
        for language in range(16):
            title = icon[8 + language * 0x200:8 + language * 0x200 + 128]
            assert title.decode("utf-16le").rstrip("\0") == "Badge Arcade Offline"
        assert icon[0x2018:0x201C] == bytes.fromhex("ffffff7f")
        assert icon[0x2040:] == bytes.fromhex("ff07") * (24 * 24 + 48 * 48)
        stack = m.uc.reg_read(UC_ARM_REG_SP)
        assert m.word(stack) == m.word(stack + 4) == 16
        m.result(0)

    m.boundaries.update({
        0x2B9D68: allocate_icon,
        0x2AE42C: create_archive,
        0x2BA5F4: free_icon,
    })


ICON_CALLS = [0x2B9D68, 0x2AE42C, 0x21C1E0, 0x2BA5F4]


def test_missing_extdata_is_created_with_local_icon_and_remounted(badge_code, badge_records):
    m = BadgeMachine(badge_code)
    mock_extdata_creation(m, [0xC8804464, 0])
    assert m.run(badge_records[1]["badge_prepare_extdata"], TASK) == 1
    assert m.calls == [0x21C1E0] + ICON_CALLS


@pytest.mark.parametrize("missing", [False, True])
def test_bootstrap_loads_local_saves_from_fresh_or_existing_storage(badge_code, missing):
    m = BadgeMachine(badge_code)
    # A second mount of the same SDK archive name would fail on the console.
    mock_extdata_creation(m, [0xC8804478, 0] if missing else [0])
    manager, successor = 0x6A4000, 0x6A5000
    m.put(CONTEXT + 4, TASK)
    m.put(CONTEXT + 8, manager)
    m.put(manager, 0x710000)
    m.put(manager + 4, TASK)

    allocate_icon = m.boundaries[0x2B9D68]

    def allocate_state():
        if m.reg() == 0x36C0:
            allocate_icon()
            return
        assert [m.reg(i) for i in range(3)] == [12, 0x710000, 4]
        m.result(successor)

    m.boundaries[0x2B9D68] = allocate_state
    assert m.run(0x321078, CONTEXT) == successor
    # The native mounted-archive successor loads local saves. The other native
    # branch (0x418c10 in 1.3.0) enters the original first-time setup instead.
    assert m.word(successor) == (0x418A20 if m.revision == BASE else 0x419F80)
    assert m.word(successor + 4) == TASK
    assert m.word(successor + 8) == manager
    expected = [0x21C1E0] + (ICON_CALLS if missing else [])
    assert m.calls == expected + [0x2B9D68]


@pytest.mark.parametrize("failure", ["allocate", "create", "remount"])
def test_fresh_extdata_failures_release_icon_and_do_not_report_success(badge_code, badge_records, failure):
    m = BadgeMachine(badge_code)
    mock_extdata_creation(m, [0xC8804478, 0xC86044C8])
    boundary = {
        "allocate": 0x2B9D68, "create": 0x2AE42C,
    }.get(failure)
    if boundary is not None:
        m.boundaries[boundary] = lambda: m.result(0 if failure == "allocate" else 0xC86044C8)
    assert m.run(badge_records[1]["badge_prepare_extdata"], TASK) == 0
    assert m.calls.count(0x2BA5F4) == (0 if failure == "allocate" else 1)
    if failure not in {"create", "remount"}:
        assert 0x2AE42C not in m.calls


def test_bootstrap_retains_native_storage_error_dispatch(badge_code):
    m = BadgeMachine(badge_code)
    m.put(CONTEXT + 4, TASK)
    m.put(CONTEXT + 8, 0x6A4000)
    m.boundaries[0x21C1E0] = lambda: m.result(0xC8804554)
    states = iter([0x6A5000, 0x6A5100])

    def allocate_state():
        assert m.reg() == 12  # No icon allocation or archive creation on corruption.
        m.result(next(states))

    m.boundaries[0x2B9D68] = allocate_state
    m.run(0x321078, CONTEXT)
    assert m.word(TASK + 0x2A8) == 1
    assert m.calls == [0x21C1E0, 0x21C1E0, 0x2B9D68, 0x2B9D68]


@pytest.mark.parametrize("legacy_registration", [False, True], ids=["offline", "legacy"])
@pytest.mark.parametrize("failure", ["task-list", "registration"])
def test_bootstrap_spotpass_failure_does_not_become_sd_error(badge_code, legacy_registration, failure):
    m = BadgeMachine(badge_code)
    if legacy_registration:
        # Restore the native synchronous SpotPass helper to reproduce 0.5.1.
        m.uc.mem_write(m.native(0x245808), bytes.fromhex("08402de9"))
    controller, boss = 0x6A6000, 0x6A7000
    manager, successor = 0x6A4000, 0x6A5000
    m.put(0x42ACD0, controller)
    m.put(controller + 0x10, boss)
    m.put(boss + 0x44, 0x6A8000)
    m.put(CONTEXT + 4, TASK)
    m.put(CONTEXT + 8, manager)
    m.put(manager, 0x710000)
    m.put(manager + 4, TASK)
    states = iter([successor, successor + 0x100])
    m.boundaries[0x2B9D68] = lambda: m.result(next(states))
    # A real console can initialize BOSS but reject task setup for an unlinked
    # account. Azahar's successful BOSS stubs do not exercise this combination.
    m.boundaries[0x239B14] = lambda: m.result(0)

    def task_list():
        m.uc.mem_write(m.reg() + 4, bytes(2))
        m.result(0x80000000 if failure == "task-list" else 0)

    m.boundaries[0x18DD5C] = task_list
    m.boundaries[0x349E6C] = lambda: m.result(0x80000000)
    # The independent new-arrival query can fail as well. Its native caller
    # initializes the output byte and already tolerates an unavailable service.
    m.boundaries[0x18DCF0] = lambda: m.result(0x80000000)
    result = m.run(0x3231FC, CONTEXT)
    if legacy_registration:
        assert result == successor + 0x100
        assert m.word(TASK + 0x2A8) == 9  # Native "Unable to read the SD card" path.
        assert 0x18DD5C in m.calls
        assert (0x349E6C in m.calls) == (failure == "registration")
    else:
        assert result == successor
        assert m.word(TASK + 0x2A8) == 0
        assert m.word(successor) == (0x418AE8 if m.revision == BASE else 0x41A048)
        assert m.word(successor + 4) == TASK
        assert m.word(successor + 8) == manager
        assert 0x18DD5C not in m.calls
        assert 0x349E6C not in m.calls


@pytest.mark.parametrize("error", [0xC8804554, 0xC86044C8, 0xD8A0A3F8])
def test_extdata_errors_do_not_reformat_or_overwrite_existing_archive(badge_code, error):
    m = BadgeMachine(badge_code)
    m.boundaries[0x21C1E0] = lambda: m.result(error)
    m.run(0x33F30C, TASK)
    assert m.word(TASK + 0x1BC) == 0x1D
    assert m.calls == [0x21C1E0]


@pytest.mark.parametrize("entry", [0x249C48, 0x24B33C])
def test_cloud_upload_completion_marks_local_save_dirty_and_preserves_handles(badge_code, entry):
    m = BadgeMachine(badge_code)
    m.mock_storage()
    before = b"\xA5" * 0x50
    m.uc.mem_write(CONTEXT, before)
    m.uc.mem_write(SAVE, b"\x5A" * 0x100)
    assert m.run(entry, 0, CONTEXT, 0x700000, 128) == 1
    expected = bytearray(before)
    expected[0x2C] = 2
    struct.pack_into("<I", expected, 0x30, 1)
    assert m.uc.mem_read(CONTEXT, 0x50) == expected
    assert m.byte(SAVE + 0x41) == 1
    assert m.run(0x2B8BFC, CONTEXT + 0x30) == 1
    assert m.word(CONTEXT + 0x34) == 0xA5A5A5A5
    prefix = "owned" if entry == 0x249C48 else "prof"
    assert set(m.files) == {f"ba_{prefix}_a.dat", f"ba_{prefix}_b.dat"}
    for data in m.files.values():
        assert data[:8] == struct.pack("<II", 0x464F4142, 128)


@pytest.mark.parametrize("entry", [0x24575C, 0x24598C])
def test_unexpected_download_fails_without_claiming_buffer_was_filled(badge_code, entry):
    m = BadgeMachine(badge_code)
    m.uc.mem_write(TASK, b"\xA5" * 0x100)
    assert m.run(entry, 0, CONTEXT, TASK, 0x100) == 1
    assert m.byte(CONTEXT + 0x2C) == 3
    assert m.run(0x2B8BFC, CONTEXT + 0x30) == 1
    assert m.uc.mem_read(TASK, 0x100) == b"\xA5" * 0x100


def test_native_promotional_consumption_persists_profile_locally(badge_code):
    m = BadgeMachine(badge_code)
    m.mock_storage()
    m.boundaries[0x24B644] = lambda: m.result(0)
    m.boundaries[0x24B3E4] = lambda: None
    assert m.run(0x2EA4A4, WORLD, CONTEXT, 4, 1) == 1
    assert m.byte(CONTEXT + 0x2C) == 2
    assert set(m.files) == {"ba_prof_a.dat", "ba_prof_b.dat"}


@pytest.mark.parametrize("kind", [3, 4])
def test_promotional_types_keep_native_lookup(badge_code, kind):
    m = BadgeMachine(badge_code)
    m.put(STATUS, 0xA5A5A5A5)
    m.put(STATUS + 4, 0xA5A5A5A5)
    assert m.run(0x240E40, WORLD, kind, STATUS, STATUS + 4) == 0
    assert m.word(STATUS) == m.word(STATUS + 4) == 0


@pytest.mark.parametrize("flags", [0x40, 0x41, 0x61, 0x43, 0x261])
@pytest.mark.home_variant(False)
def test_native_request_controller_completes_removed_home_phase_and_keeps_profile_save(badge_code, flags):
    m = BadgeMachine(badge_code)
    m.mock_storage()
    m.put(TASK + 0x40, CONTEXT)
    local_busy = 0x6A0000
    m.put(STORAGE + 0x3C, local_busy)

    def tick():
        m.uc.mem_write(m.reg(), bytes(8))

    m.boundaries.update({0x2AF858: tick,
                         0x283CE4: lambda: None, 0x309674: lambda: None,
                         0x24B644: lambda: m.result(0), 0x24B3E4: lambda: None})
    # Enter the original common request controller's local-write phase.
    m.uc.mem_write(TASK, b"\x16")
    m.uc.mem_write(TASK + 4, b"\xFF")
    assert m.run(0x252DA0, TASK, flags) == 1
    assert m.byte(local_busy + 0xC8) == 0
    # The removed HOME operation and native request controller each release
    # their own APT guard.
    assert m.calls.count(0x283CE4) == 2
    if flags == 0x261:
        # The tutorial's actual flags still update its game profile.
        assert m.word(WORLD + 0x70E00) == 1
        assert set(m.files) == {"ba_prof_a.dat", "ba_prof_b.dat"}


@pytest.mark.parametrize("option,quantity", [(0, 1), (1, 2), (2, 3), (3, 4)])
def test_free_purchase_completes_without_shop(badge_code, option, quantity):
    m = BadgeMachine(badge_code)
    m.mock_storage()
    m.init_owned_pool()
    m.put(TASK + 0x40, CONTEXT)
    m.put(SAVE + 0x82C, option)
    m.boundaries[0x24B3E4] = lambda: None
    m.boundaries[0x2AF858] = lambda: m.uc.mem_write(m.reg(), bytes(8))
    m.boundaries[0x252B94] = lambda: m.result(90)
    m.uc.mem_write(TASK, b"\x04")
    m.run(0x30A604, TASK, STATUS)
    assert m.word(TASK + 0x48) == m.word(TASK + 0x4C) == quantity
    assert m.byte(TASK + 0x51) == 1
    assert m.word(WORLD + 0x70E38) == 90
    assert m.word(WORLD + 0x70E3C) == 10
    assert m.byte(STATUS) == 1
    assert set(m.files) == {"ba_owned_a.dat", "ba_owned_b.dat"}


def test_native_login_advances_once_before_postplay_and_export(badge_code):
    m = BadgeMachine(badge_code)
    m.boundaries[0x2AF858] = lambda: m.uc.mem_write(m.reg(), bytes(8))
    m.boundaries[0x309674] = lambda: None
    # Native connection and login can complete together with local readiness.
    # Later request phases must remain under their own handlers' control.
    m.uc.mem_write(TASK, b"\x01")
    m.run(0x308A94, TASK, STATUS)
    assert m.byte(STATUS) == 1
    assert m.byte(TASK) == 2
    m.uc.mem_write(TASK, b"\x02")
    m.run(0x308A94, TASK, STATUS)
    assert m.byte(STATUS) == 1
    for phase in [0x12, 0x14, 0x15, 0x16, 0x17, 0x2A]:
        m.uc.mem_write(TASK, bytes([phase]))
        m.run(0x308A94, TASK, STATUS)
        assert m.byte(STATUS) == 0


@pytest.mark.parametrize("phase", [0, 1, 3, 0x12, 0x16, 0x17, 0x2A])
def test_free_purchase_does_not_complete_other_request_phases(badge_code, phase):
    m = BadgeMachine(badge_code)
    m.uc.mem_write(TASK, bytes([phase]))
    m.put(TASK + 0x788, 17)
    m.uc.mem_write(STATUS, b"\x01")
    m.run(0x30A604, TASK, STATUS)
    assert m.byte(STATUS) == 0
    assert m.word(TASK + 0x788) == 17


def test_first_time_identity_and_nex_login_complete_without_network(badge_code):
    m = BadgeMachine(badge_code)
    m.uc.mem_write(CONTEXT, b"\xA5" * 0x600)
    m.put(TASK + 0x10, CONTEXT)
    m.run(0x246DC0, TASK)
    m.run(0x246D98, STATUS, TASK)
    assert m.word(STATUS) == 2
    assert m.word(CONTEXT + 0x4D4) == 2
    m.run(0x246D18, TASK, CONTEXT)
    assert m.byte(CONTEXT + 0x2C) == 2
    assert m.run(0x2B8BFC, CONTEXT + 0x30) == 1
    assert m.run(0x246D28, TASK) == 1
    # The dialogue's original connection predicate now sees local readiness.
    assert m.run(0x30BEF8) == 1
    assert m.calls == []


def mock_local_account(m, persistent_id, account_result=0):
    m.boundaries[0x2B97BC] = lambda: None
    m.boundaries[0x2B9794] = lambda: None
    m.boundaries[0x2ABF30] = lambda: m.result(1)

    def account_data():
        assert m.reg() == 0xFE
        assert m.reg(2) == 4 and m.reg(3) == 12
        m.put(m.reg(1), persistent_id)
        m.result(account_result)

    m.boundaries[0x2ABEE0] = account_data


@pytest.mark.parametrize("persistent_id,account_result,expected", [
    (0, 0, 1), (123456, 0, 123456), (0, 0x80000000, 1),
])
def test_offline_identity_preserves_existing_account_and_enables_unlinked_save(
    badge_code, persistent_id, account_result, expected,
):
    m = BadgeMachine(badge_code)
    mock_local_account(m, persistent_id, account_result)
    assert m.run(0x28FBAC) == expected
    # Run the original save snapshot/queue routine. A zero account ID used to
    # leave it busy forever without queuing the file-writing worker.
    m.uc.mem_write(SAVE + 0x41, b"\x01\x01")
    m.put(SAVE + 0x18, TASK)
    m.put(SAVE + 0xB8, 37)
    queued = []
    m.boundaries[0x268EB8] = lambda: queued.append(m.reg(1))
    assert m.run(0x258768, SAVE) == 1
    assert queued == [SAVE + 0x1C]
    assert m.byte(SAVE + 0x40) == 1
    assert m.byte(SAVE + 0x41) == 0
    assert m.word(SAVE + 0xE55C) == expected
    assert m.word(SAVE + 0xE560) == (2 if m.revision == BASE else 3)
    assert m.word(SAVE + 0xE560 + 0x30) == 37
    # The original load-side account check accepts the same saved identity.
    assert m.run(0x2CD3A0, SAVE) == 1
    m.put(SAVE + 0xE55C, expected + 1)
    assert m.run(0x2CD3A0, SAVE) == 0


@pytest.mark.parametrize("stage,corrupt_primary", [(1, False), (2, False), (1, True)])
def test_native_setup_stage_upload_and_signed_restore_survive_restart(
    badge_code, badge_records, stage, corrupt_primary,
):
    m = BadgeMachine(badge_code)
    m.mock_storage()
    m.boundaries[0x24B644] = lambda: m.result(0)
    m.boundaries[0x24B3E4] = lambda: None
    # Preserve the original setter and serializer, including its rollback copy.
    m.run(0x246CC0, WORLD, CONTEXT, stage)
    assert m.word(WORLD + 0x70E00) == stage
    assert m.word(WORLD + 0x70E04) == 0
    assert m.byte(CONTEXT + 0x2C) == 2
    assert set(m.files) == {"ba_prof_a.dat", "ba_prof_b.dat"}
    if corrupt_primary:
        broken = bytearray(m.files["ba_prof_a.dat"])
        broken[8 + 12] ^= 1
        m.files["ba_prof_a.dat"] = bytes(broken)
    restarted = BadgeMachine(badge_code)
    restarted.mock_storage(m.files)
    restarted.put(TASK + 0x264, 0x700000)
    restarted.boundaries[0x2588FC] = lambda: restarted.uc.mem_write(restarted.reg(), bytes(8))
    restarted.boundaries[0x25BA24] = lambda: restarted.uc.mem_write(restarted.reg(), bytes(8))
    assert restarted.run(badge_records[1]["badge_restore_profile"], TASK) == 1
    assert restarted.word(WORLD + 0x70E00) == stage
    # The original first-time controller can now distinguish the intro from
    # post-tutorial setup (1) and normal play (2).
    assert restarted.byte(WORLD + 0x70E00) != 0


@pytest.mark.parametrize("completed,expected", [(False, 0), (True, 2)])
def test_missing_profile_respects_existing_native_first_time_completion(
    badge_code, badge_records, completed, expected,
):
    m = BadgeMachine(badge_code)
    m.mock_storage()
    m.put(TASK + 0x264, 0x700000)
    m.run(0x2595E4, SAVE, 5, int(completed))
    assert m.run(badge_records[1]["badge_restore_profile"], TASK) == 1
    assert m.word(WORLD + 0x70E00) == expected
    assert m.files == {}


@pytest.mark.parametrize("entry,module", [
    (0x190360, "http"), (0x190D5C, "http"), (0x190EDC, "http"),
    (0x1A5754, "soc"), (0x1A58F0, "soc"), (0x1A5AE4, "soc"), (0x1A5B68, "soc"),
])
def test_network_requests_fail_before_ipc_and_preserve_outputs(badge_code, entry, module):
    m = BadgeMachine(badge_code)
    m.uc.mem_write(CONTEXT, b"\xA5" * 0x100)
    m.uc.mem_write(STATUS, b"\x5A" * 0x100)
    assert m.run(entry, CONTEXT, STATUS, TASK, 64) == {
        "http": 0xD8A0A3F8, "soc": 0xD8A073F8,
    }[module]
    assert m.uc.mem_read(CONTEXT, 0x100) == b"\xA5" * 0x100
    assert m.uc.mem_read(STATUS, 0x100) == b"\x5A" * 0x100
    assert m.calls == []


@pytest.mark.parametrize("entry", [0x18F7B4, 0x18F8B4, 0x18F9C4,
                                  0x19063C, 0x1906C8, 0x19075C, 0x22DA20])
def test_boss_start_and_unused_download_storage_setup_complete_without_ipc(badge_code, entry):
    m = BadgeMachine(badge_code)
    m.uc.mem_write(CONTEXT, b"\xA5" * 0x100)
    assert m.run(entry, CONTEXT, STATUS, TASK, 64) == 0
    assert m.uc.mem_read(CONTEXT, 0x100) == b"\xA5" * 0x100
    assert m.calls == []
    headers = {0x18F7B4: 0x001D0042, 0x18F8B4: 0x00330042, 0x18F9C4: 0x001C0042,
               0x19063C: 0x001D0042, 0x1906C8: 0x00330042, 0x19075C: 0x001C0042}
    if entry in headers:
        assert m.word(entry + 0x3C) == headers[entry]


@pytest.mark.parametrize("bundled,ignore_dates,expected", [
    (True, 0, 1), (False, 0, 0), (False, 1, 1),
])
def test_bundled_schedule_remains_available_after_2030(
    badge_code, bundled, ignore_dates, expected,
):
    m = BadgeMachine(badge_code)
    manager, vector, item, pointers = 0x720000, 0x721000, 0x722000, 0x723000
    m.put(WORLD + 0x70DF4, manager if bundled else manager + 0x100)
    m.put(manager + 8, vector)
    m.put(manager + 0x10, 0x100000)
    m.put(vector, 1)
    m.put(vector + 8, pointers)
    m.put(pointers, item)
    m.put(item + 0x14, 0x730000)
    m.put(item + 0x20, 0x730100)
    m.put(item + 0x30, 0x100)  # Entry expired long before manager's current date.
    m.uc.mem_write(0x730000, b"DefaultStageName000\0")
    m.uc.mem_write(0x730100, b"MroSMB_042\0")
    m.uc.mem_write(STATUS, struct.pack("<III", m.native(0x40E038), STATUS + 0x80, 64))
    m.uc.mem_write(TASK, struct.pack("<II", m.native(0x40E038), 0x730000))
    assert m.run(0x258B80, manager, STATUS, TASK, ignore_dates) == expected
    assert m.cstring(STATUS + 0x80) == ("MroSMB_042" if expected else "DefaultStageName000")


def test_play_log_completes_and_native_caller_clears_pending_log(badge_code):
    m = BadgeMachine(badge_code)
    m.put(TASK + 0x40, CONTEXT)
    m.put(TASK + 0x98, 0x700000)
    m.put(0x700004, 3)
    m.uc.mem_write(TASK, b"\x14")
    m.boundaries[0x24B3E4] = lambda: None
    m.boundaries[0x2AF858] = lambda: m.uc.mem_write(m.reg(), bytes(8))
    m.run(0x30A060, TASK, STATUS)
    assert m.byte(CONTEXT + 0x2C) == 2
    # Native next-frame processing clears all the completed play-log records.
    m.put(TASK + 8, 1)
    # Isolate subsequent ownership serialization; run the native transition.
    m.boundaries[0x2EC654] = lambda: m.result(1)
    m.run(0x30A060, TASK, STATUS)
    assert m.word(0x700004) == 0
    assert m.word(TASK + 0x228) == 0
    assert bytes(m.uc.mem_read(TASK + 0x9C, 99 * 4)) == b"\xFF" * 396


@pytest.mark.parametrize("fail_primary", [False, True])
def test_round_save_reports_success_only_after_native_ownership_is_written(badge_code, fail_primary):
    m = BadgeMachine(badge_code)
    m.init_owned_pool()
    previous = b"previous completed save".ljust(0x499F2, b"\0")
    m.mock_storage({"ba_owned_b.dat": previous})
    if fail_primary:
        m.fail_write = "ba_owned_a.dat"
    m.put(TASK + 0x40, CONTEXT)
    m.put(TASK + 0x44, 0x6B1000)
    m.uc.mem_write(TASK, b"\x15")
    m.boundaries[0x24B3E4] = lambda: None
    m.boundaries[0x24B644] = lambda: m.result(0)
    m.uc.mem_write(STATUS + 16, struct.pack("<II", 100, 200))
    m.run(0x258358, m.word(WORLD + 0x70E54), STATUS + 16, 3, 0)
    # Run both the real post-round handler and native signed serializer. The
    # storage boundary enforces the console's 16-byte filename constraint.
    m.run(0x30A060, TASK, STATUS)
    assert m.byte(STATUS) == (9 if fail_primary else 1)
    if fail_primary:
        assert m.files["ba_owned_b.dat"] == previous
        return
    raw = m.files["ba_owned_a.dat"]
    assert raw == m.files["ba_owned_b.dat"]
    _, length = struct.unpack_from("<II", raw)
    restarted = BadgeMachine(badge_code)
    restarted.init_owned_pool()
    restarted.uc.mem_write(0x700000, raw[8:8 + length])
    restarted.boundaries[0x25BA24] = lambda: restarted.uc.mem_write(restarted.reg(), bytes(8))
    assert restarted.run(0x23952C, WORLD, 0x700000, length) == 1
    restarted.uc.mem_write(STATUS + 16, struct.pack("<II", 100, 200))
    assert restarted.run(0x25460C, restarted.word(WORLD + 0x70E54), STATUS + 16) == 3


@pytest.mark.parametrize("length", [0, 32, 0x499EB, 0xFFFFFFFF])
def test_invalid_owned_write_does_not_change_either_copy(badge_code, length):
    m = BadgeMachine(badge_code)
    original = {"ba_owned_a.dat": b"primary", "ba_owned_b.dat": b"backup"}
    m.mock_storage(original)
    m.run(0x249C48, 0, CONTEXT, 0x700000, length)
    assert m.files == original
    assert m.calls == []
    assert m.byte(CONTEXT + 0x2C) == 3


def test_owned_save_preserves_backup_when_primary_write_fails(badge_code):
    m = BadgeMachine(badge_code)
    old_backup = b"previous completed ownership save"
    m.mock_storage({"ba_owned_b.dat": old_backup})
    m.fail_write = "ba_owned_a.dat"
    m.run(0x249C48, 0, CONTEXT, 0x700000, 128)
    assert m.byte(CONTEXT + 0x2C) == 3
    assert m.files["ba_owned_b.dat"] == old_backup


@pytest.mark.parametrize("length", [0, 32, 0x499EB, 0xFFFFFFFF])
def test_owned_restore_rejects_unbounded_lengths(badge_code, badge_records, length):
    m = BadgeMachine(badge_code)
    m.mock_storage({"ba_owned_a.dat": struct.pack("<II", 0x464F4142, length)})
    m.put(TASK + 0x264, 0x700000)
    m.uc.mem_write(0x700000, b"\xA5" * 64)
    m.run(badge_records[1]["badge_restore_owned"], TASK)
    assert m.uc.mem_read(0x700000, 64) == b"\xA5" * 64


def test_owned_restore_uses_backup_after_rejected_signature(badge_code, badge_records):
    m = BadgeMachine(badge_code)
    rejected = b"X" * 64
    accepted = b"Y" * 64
    m.mock_storage({
        "ba_owned_a.dat": struct.pack("<II", 0x464F4142, 64) + rejected,
        "ba_owned_b.dat": struct.pack("<II", 0x464F4142, 64) + accepted,
    })
    m.put(TASK + 0x264, 0x700000)
    seen = []

    def decode():
        assert m.reg() == WORLD
        blob = bytes(m.uc.mem_read(m.reg(1), m.reg(2)))
        seen.append(blob)
        m.result(int(blob == accepted))

    m.boundaries[0x23952C] = decode
    assert m.run(badge_records[1]["badge_restore_owned"], TASK) == 1
    assert seen == [rejected, accepted]


def test_owned_restore_does_not_read_or_merge_home_badges(badge_code, badge_records):
    m = BadgeMachine(badge_code)
    m.init_owned_pool()
    m.mock_storage()
    m.put(TASK + 0x264, 0x700000)
    # A nonempty resource table previously triggered destructive HOME migration.
    m.put(0x6A2000, 1)
    assert m.run(badge_records[1]["badge_restore_owned"], TASK) == 1
    assert all(call not in m.calls for call in (0x245248, 0x24E870, 0x244F44, 0x244EE4))
    assert not m.files


@pytest.mark.parametrize("corrupt_primary", [False, True])
def test_native_signed_cache_restores_badge_counts_after_restart(
    badge_code, badge_records, corrupt_primary,
):
    m = BadgeMachine(badge_code)
    m.init_owned_pool()
    m.mock_storage()
    m.put(WORLD + 0x70E38, 123)
    m.put(WORLD + 0x70E3C, 2)
    uid_bytes = struct.pack("<4I", 100, 200, 101, 201)
    m.uc.mem_write(STATUS + 16, uid_bytes)
    model = m.word(WORLD + 0x70E54)
    m.run(0x258358, model, STATUS + 16, 3, 0)
    m.run(0x258358, model, STATUS + 24, 12, 0)
    # Run Nintendo's real serializer and HMAC implementation, not a fake blob.
    assert m.run(0x249CF0, WORLD, STATUS, STATUS + 4) == 1
    blob, length = m.word(STATUS), m.word(STATUS + 4)
    assert 32 < length <= 0x499EA
    assert m.run(0x249C48, WORLD, CONTEXT, blob, length) == 1
    if corrupt_primary:
        broken = bytearray(m.files["ba_owned_a.dat"])
        broken[8 + 12] ^= 1
        m.files["ba_owned_a.dat"] = bytes(broken)
    # Restart with fresh model memory and only the saved files carried over.
    restarted = BadgeMachine(badge_code)
    restarted.init_owned_pool()
    restarted.mock_storage(m.files)
    restarted.put(TASK + 0x264, 0x700000)
    restarted.boundaries[0x25BA24] = lambda: restarted.uc.mem_write(restarted.reg(), bytes(8))
    assert restarted.run(badge_records[1]["badge_restore_owned"], TASK) == 1
    assert restarted.word(WORLD + 0x70E38) == 123
    assert restarted.word(WORLD + 0x70E3C) == 2
    restarted.uc.mem_write(STATUS + 16, uid_bytes)
    assert restarted.run(0x25460C, model, STATUS + 16) == 3
    assert restarted.run(0x25460C, model, STATUS + 24) == 12


@pytest.mark.parametrize("entry", [0x2408B8, 0x2409A8])
@pytest.mark.home_variant(False)
def test_home_export_completes_without_filesystem_or_worker_calls(badge_code, entry):
    m = BadgeMachine(badge_code)
    m.put(STORAGE + 0x3C, STATUS)
    m.uc.mem_write(STATUS, bytes([0xA5]) * 0x100)
    m.uc.mem_write(STATUS + 0xCB, b"\x00")
    m.boundaries[0x283CE4] = lambda: None
    m.run(entry, STORAGE, 1)
    assert bytes(m.uc.mem_read(STATUS + 0xC8, 3)) == bytes(3)
    assert m.word(STATUS + 0xCC) == 0
    assert m.calls == [0x283CE4]


@pytest.mark.parametrize("entry", [0x263E80, 0x2BBE04])
@pytest.mark.home_variant(False)
def test_home_archive_cannot_be_mounted_created_or_reformatted(badge_code, entry):
    m = BadgeMachine(badge_code)
    assert m.run(entry, TASK) == 8
    assert not m.calls


@pytest.mark.parametrize("entry", [0x245248, 0x244EE4, 0x244F44, 0x24E870, 0x2E8C44])
@pytest.mark.home_variant(False)
def test_home_device_operations_do_not_access_sd(badge_code, entry):
    m = BadgeMachine(badge_code)
    m.put(STATUS, 0xA5A5A5A5)
    m.put(STATUS + 8, 0xA5A5A5A5)
    m.run(entry, STATUS, TASK, STATUS + 8, 100)
    assert m.word(STATUS) == 0
    if entry == 0x244F44:
        assert m.word(STATUS + 8) == 0
    if entry == 0x24E870:
        assert bytes(m.uc.mem_read(STATUS + 8, 4)) == b"\x00\xA5\xA5\xA5"
    assert not m.calls


@pytest.mark.home_variant(False)
def test_home_category_marks_are_empty_without_changing_owned_counts(badge_code):
    m = BadgeMachine(badge_code)
    m.uc.mem_write(STATUS, b"\xA5" * 8)
    m.run(0x2F1B34, STORAGE, STATUS + 1, TASK, 6)
    assert bytes(m.uc.mem_read(STATUS, 8)) == b"\xA5" + bytes(6) + b"\xA5"
    assert not m.calls


@pytest.mark.home_variant(False)
def test_only_the_removed_home_lesson_is_skipped(badge_code):
    m = BadgeMachine(badge_code)
    for value in (0, 0xA5A5A5A5):
        m.put(SAVE + 0x98, value)
        m.put(SAVE + 0x9C, value)
        for flag in range(64):
            assert m.run(0x259680, SAVE, flag) == (1 if flag == 4 else (value >> (flag % 32)) & 1)
        assert m.word(SAVE + 0x98) == m.word(SAVE + 0x9C) == value


def test_catcher_capacity_and_export_scene_redirects(badge_code, home_menu):
    m = BadgeMachine(badge_code)
    entry = m.native(0x247E24)
    m.uc.emu_start(entry, entry + 4)
    assert m.reg(1) == 512
    entry = m.native(0x24D438)
    m.uc.emu_start(entry, entry + 4)
    assert m.reg(3) == 0x40000
    if m.revision.version == "1.3.1":
        m.uc.emu_start(0x24DE08, 0x24DE0C)
        assert m.reg(3) == 0x40000
    for entry in (0x3034DC, 0x333830, 0x335FDC):
        assert m.cstring(m.native(entry)) == ("CExporter" if home_menu else "Book")


@pytest.mark.parametrize("fallback", [False, True], ids=["primary-schedule", "fallback-schedule"])
def test_vanilla_native_selector_includes_all_normal_layouts(badge_code, home_menu, fallback):
    from badge_versions import UPDATE
    if badge_code.revision != UPDATE:
        pytest.skip("The public Vanilla catalog targets EUR update 1.3.1")
    m = BadgeMachine(badge_code)
    for offset, data in badge.build_vanilla_records(UPDATE, home_menu=home_menu)[0]:
        m.uc.mem_write(badge.LOAD_ADDRESS + offset, data)
    manager, layouts, selection = 0x6A4000, 0x6A5000, 0x6A6000
    table, selected, objects = 0x770000, 0x771000, 0x730000
    # Include collection-only and practice layouts among the 384 normal ones.
    types = [0] * 150 + [1, 2] + [0] * 234
    m.put(manager + 0x50, layouts)
    m.put(manager + 0x54, selection)
    for address, values in ((layouts, (len(types), len(types), table)),
                            (selection, (0, 512, selected))):
        m.uc.mem_write(address, struct.pack("<III", *values))
    for index, kind in enumerate(types):
        item = objects + index * 0x100
        m.put(table + index * 4, item)
        m.put(item, 0x6B1000)
        m.put(item + 0xC, kind)
    m.put(0x6B1000, 0x600000)
    heap, vtable = 0x6B2000, 0x6B3000
    m.put(0x8F0000 + 0x410, heap)
    m.put(heap, vtable)
    m.put(vtable + 0x2C, 0x600004)
    # The game constructs its static format-string object before this loop.
    m.put(m.word(0x24952C), 0x6B5000)
    m.put(0x6B5008, 0x600008)
    m.put(0x42AE68, WORLD)
    m.uc.reg_write(UC_ARM_REG_SP, 0x8F0000)
    m.uc.reg_write(UC_ARM_REG_R4, manager)
    m.uc.reg_write(UC_ARM_REG_R5, 0x40F598)
    m.uc.reg_write(UC_ARM_REG_R6, m.native(0x42AE68))
    m.uc.reg_write(UC_ARM_REG_R9, 0x40F598)
    loads = []

    def format_stage():
        assert m.reg(2) == 0  # Reuse native availability fields for every layout.

    def load_layout():
        item = m.reg()
        loads.append(item)
        m.put(item + 8, 3)  # Native loader completed the machine's dependencies.

    def schedule_lookup():
        if fallback:
            assert m.reg(3) == 1  # The bundled fallback must work after 2030.
        m.result(1)

    m.boundaries.update({0x274D60: format_stage, 0x258B80: schedule_lookup,
                         0x23E4E4: lambda: m.result(0x6B4000), 0x23E5EC: load_layout,
                         0x600000: lambda: None, 0x600004: lambda: None,
                         0x600008: lambda: None})
    try:
        m.uc.emu_start(0x249138 if fallback else 0x248F50,
                       0x24930C if fallback else 0x24912C, count=100000)
    except UcError as exc:
        raise AssertionError(f"Selection failed at {m.uc.reg_read(UC_ARM_REG_PC):08x}") from exc
    assert m.uc.reg_read(UC_ARM_REG_PC) == (0x24930C if fallback else 0x24912C)
    expected = [objects + index * 0x100 for index, kind in enumerate(types) if kind == 0]
    assert loads == expected
    assert m.word(selection) == 384
    assert bytes(m.uc.mem_read(selected, 384 * 4)) == struct.pack("<384I", *expected)
    if not fallback:
        assert m.word(0x8F0000 + 0x33C) == 1  # Do not enter the native fallback schedule.


@pytest.mark.parametrize("filename,home", [
    ("BADGE:/BadgeMngFile.dat", True), ("BADGE:/BadgeData.dat", True),
    ("CENTER:/savedata", False), ("BADGEX:/savedata", False),
])
@pytest.mark.home_variant(False)
def test_boot_checker_skips_home_files_and_keeps_game_save_checks(badge_code, filename, home):
    m = BadgeMachine(badge_code)
    vtable, getter, success = 0x710000, 0x711000, 0x712000
    m.put(TASK, vtable)
    m.put(vtable + 0x28, getter)
    m.put(vtable + 0x2C, success)
    m.uc.mem_write(STATUS, filename.encode() + b"\0")
    m.boundaries[getter] = lambda: m.result(STATUS)
    m.boundaries[success] = lambda: m.result(17)

    def original_checker():
        assert m.reg() == TASK
        # The wrapper replayed the original push before this resume point.
        m.uc.reg_write(UC_ARM_REG_SP, STACK)
        m.result(23)

    m.boundaries[0x32260C] = original_checker
    assert m.run(0x322608, TASK) == (17 if home else 23)
    assert m.calls == [getter, success if home else 0x32260C]


@pytest.mark.home_variant(True)
def test_home_build_preserves_native_archive_export_and_tutorial_code(badge_code, badge_revision):
    path = Path(os.environ.get("BADGE_CODE", Path(os.environ.get("BADGE_INPUT_DIR", ROOT.parent / "nba-private/inputs")) / badge_revision.input_name))
    original = path.read_bytes()
    for address in badge.HOME_HOOKS:
        offset = badge_revision.address(address) - badge.LOAD_ADDRESS
        assert badge_code[offset:offset + 4] == original[offset:offset + 4]
    m = BadgeMachine(badge_code)
    for value in (0, 0xA5A5A5A5):
        m.put(SAVE + 0x98, value)
        for flag in range(32):
            assert m.run(0x259680, SAVE, flag) == (value >> flag) & 1


def native_calls(m, address, length):
    """Find ARM BL boundaries without requiring a disassembler dependency."""
    entry = m.native(address)
    calls = []
    for offset in range(0, length, 4):
        instruction = struct.unpack("<I", m.uc.mem_read(entry + offset, 4))[0]
        if instruction >> 24 == 0xEB:
            displacement = instruction & 0xFFFFFF
            if displacement & 0x800000:
                displacement -= 0x1000000
            target = entry + offset + 8 + displacement * 4
            calls.append(m.canonical.get(target, target))
    return calls


@pytest.mark.home_variant(True)
@pytest.mark.parametrize("entry", [0x2408B8, 0x2409A8])
@pytest.mark.parametrize("mount_fails", [False, True])
def test_home_export_queues_native_worker_and_preserves_mount_errors(badge_code, entry, mount_fails):
    m = BadgeMachine(badge_code)
    m.put(STORAGE + 0x3C, STATUS)
    m.put(STORAGE + 0x1C, CONTEXT)
    # Both entry points share a manager pointer in their PC-relative literals.
    start = m.native(entry)
    literal_instruction = struct.unpack("<I", m.uc.mem_read(start + (0x1C if entry == 0x2408B8 else 0x20), 4))[0]
    literal = start + (0x1C if entry == 0x2408B8 else 0x20) + 8 + (literal_instruction & 0xFFF)
    manager_global = struct.unpack("<I", m.uc.mem_read(literal, 4))[0]
    m.put(manager_global, TASK)
    worker = 0x6C0000
    calls = native_calls(m, entry, 0xE8)
    # Lock/overlay/worker allocation and scheduler boundaries are isolated, but
    # the restored export entry executes its real control flow and result check.
    for target in calls:
        m.boundaries[target] = lambda: None
    def mount():
        assert m.reg(1) == CONTEXT
        m.put(m.reg(), 8 if mount_fails else 0)
    m.boundaries[0x245248] = mount
    def accept_result():
        result = m.word(m.reg(1))
        m.uc.mem_write(STATUS + 0xCA, bytes([bool(result)]))
    m.boundaries[0x245130] = accept_result
    # Last four calls are allocation, construction, scheduling and unlock.
    allocate, construct, schedule = calls[-4:-1]
    m.boundaries[allocate] = lambda: m.result(worker)
    def create_worker():
        assert m.reg(3) == STORAGE
        m.result(worker)
    def enqueue():
        assert m.reg() == TASK
        assert m.reg(1) == worker
        assert m.reg(2) == 1
    m.boundaries[construct] = create_worker
    m.boundaries[schedule] = enqueue
    m.run(entry, STORAGE, 1)
    assert (construct in m.calls) == (not mount_fails)
    assert (schedule in m.calls) == (not mount_fails)
    if not mount_fails:
        assert m.word(worker + 0x24) == 0xFFFFFFFF
