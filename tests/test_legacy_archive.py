import subprocess
from pathlib import Path


def _git_ls_files(pathspec: str) -> list[str]:
    if not Path(".git").exists():
        return []
    result = subprocess.run(
        ["git", "ls-files", pathspec],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def _git_check_ignore(pathspec: str) -> bool:
    if not Path(".git").exists():
        return True
    result = subprocess.run(
        ["git", "check-ignore", pathspec],
        check=False,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def test_legacy_sidecars_are_archived_not_active() -> None:
    legacy_root = Path("sidecars")
    assert not (legacy_root / "gtrade").exists()
    assert not (legacy_root / "ostium").exists()


def test_legacy_archive_is_local_ignored_not_tracked() -> None:
    assert _git_ls_files("archive/gtrade_ostium_legacy_archive_*.zip") == []
    assert _git_check_ignore("archive/gtrade_ostium_legacy_archive_20260527_013818.zip")
