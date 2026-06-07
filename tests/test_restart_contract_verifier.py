import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "verify_restart_contract.py"


def _run(command: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=check, capture_output=True, text=True)


def _git(repo: Path, *args: str) -> str:
    return _run(["git", *args], repo).stdout.strip()


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "Test User")
    (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
    _git(repo, "add", "tracked.txt")
    _git(repo, "commit", "-m", "initial")
    return repo


def _write_handoff(repo: Path, contract: dict[object, object]) -> Path:
    handoff = repo / "HANDOFF.md"
    frontmatter = json.dumps(contract, indent=2, sort_keys=True)
    handoff.write_text(
        f"---\nrestart_contract_json: |\n{_indent(frontmatter)}\n---\n", encoding="utf-8"
    )
    return handoff


def _indent(text: str) -> str:
    return "\n".join(f"  {line}" for line in text.splitlines())


def _current_contract(repo: Path) -> dict[object, object]:
    result = _run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo),
            "--print-current-contract",
        ],
        repo,
    )
    return json.loads(result.stdout)


def _verify(repo: Path, handoff: Path) -> subprocess.CompletedProcess[str]:
    return _run(
        [
            sys.executable,
            str(SCRIPT),
            "--repo-root",
            str(repo),
            "--handoff",
            str(handoff),
        ],
        repo,
        check=False,
    )


def test_restart_contract_verifier_accepts_matching_dirty_and_untracked_state(
    tmp_path: Path,
) -> None:
    repo = _init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("local\n", encoding="utf-8")

    handoff = _write_handoff(repo, _current_contract(repo))

    result = _verify(repo, handoff)

    assert result.returncode == 0
    assert "restart contract ok" in result.stdout


def test_restart_contract_verifier_reports_unexpected_dirty_file(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    handoff = _write_handoff(repo, _current_contract(repo))
    (repo / "tracked.txt").write_text("changed after handoff\n", encoding="utf-8")

    result = _verify(repo, handoff)

    assert result.returncode == 1
    assert "unexpected_dirty_present: tracked.txt" in result.stdout


def test_restart_contract_verifier_reports_expected_dirty_missing(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    contract = _current_contract(repo)
    (repo / "tracked.txt").write_text("initial\n", encoding="utf-8")
    handoff = _write_handoff(repo, contract)

    result = _verify(repo, handoff)

    assert result.returncode == 1
    assert "expected_dirty_missing: tracked.txt" in result.stdout


def test_restart_contract_verifier_reports_fingerprint_mismatch(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    contract = _current_contract(repo)
    assert isinstance(contract["tracked_dirty_files"], list)
    contract["tracked_dirty_files"][0]["diff_sha256"] = "0" * 64
    handoff = _write_handoff(repo, contract)

    result = _verify(repo, handoff)

    assert result.returncode == 1
    assert "fingerprint_mismatch: tracked.txt" in result.stdout
