from pathlib import Path


def test_legacy_sidecars_are_archived_not_active() -> None:
    assert Path("archive/legacy_sidecars/gtrade").exists()
    assert Path("archive/legacy_sidecars/ostium").exists()
    legacy_root = Path("sidecars")
    assert not (legacy_root / "gtrade").exists()
    assert not (legacy_root / "ostium").exists()
