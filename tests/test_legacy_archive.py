from pathlib import Path


def test_legacy_sidecars_are_archived_not_active() -> None:
    assert sorted(Path("archive").glob("gtrade_ostium_legacy_archive_*.zip"))
    legacy_root = Path("sidecars")
    assert not (legacy_root / "gtrade").exists()
    assert not (legacy_root / "ostium").exists()
