"""Public release checks require no private game files."""
import runpy
import zipfile

from patch_format import ROOT


def test_current_public_release_matches_source_and_allowlist():
    report = runpy.run_path(str(ROOT / "tools/verify_release.py"))["verify"]()
    assert set(report) == {"game-only", "home-menu"}
    for variant in report.values():
        assert len(variant["ips_sha256"]) == len(variant["zip_sha256"]) == 64


def test_game_only_patch_preserves_the_previous_release_bytes():
    patch = "luma/titles/0004000000153600/code.ips"
    with zipfile.ZipFile(ROOT / "releases/v0.4.0/nba-offline-v0.4.0.zip") as previous:
        with zipfile.ZipFile(ROOT / "releases/v0.5.0/nba-offline-v0.5.0-game-only.zip") as current:
            assert current.read(patch) == previous.read(patch)


def test_code_patch_builds_without_private_inputs_for_both_versions(tmp_path, monkeypatch):
    import json
    import sys
    import badge_patch
    from badge_versions import REVISIONS
    for revision in REVISIONS:
        output = tmp_path / revision.version
        monkeypatch.setattr(sys, "argv", ["badge_patch", "--game-version", revision.version,
                                         "--output", str(output)])
        badge_patch.main()
        manifest = json.loads((output / "build.json").read_text())
        assert manifest["source_code_sha256"] == revision.sha256
        assert manifest["game_version"] == revision.version
        assert manifest["patched_code_sha256"] is None
        assert not (output / "patched.code.bin").exists()


def test_complete_builder_rejects_incorrect_assets_before_creating_output(tmp_path):
    import pytest
    verify_input = runpy.run_path(str(ROOT / "tools/build_complete.py"))["verify_input"]
    wrong = tmp_path / "wrong.sarc"
    wrong.write_bytes(b"not the supported update")
    with pytest.raises(ValueError, match="Unsupported input"):
        verify_input(wrong, "0" * 64)
