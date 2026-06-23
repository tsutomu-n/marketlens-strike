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


def _refresh(
    repo: Path,
    handoff: Path,
    verification_note: str | None = None,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(SCRIPT),
        "--repo-root",
        str(repo),
        "--handoff",
        str(handoff),
        "--refresh-contract",
    ]
    if verification_note is not None:
        command.extend(["--verification-note", verification_note])
    return _run(
        command,
        repo,
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


def test_refresh_contract_updates_stale_handoff_body_restart_lines(tmp_path: Path) -> None:
    repo = _init_repo(tmp_path)
    (repo / "tracked.txt").write_text("changed\n", encoding="utf-8")
    (repo / "untracked.txt").write_text("local\n", encoding="utf-8")
    stale_contract = {
        "branch_line": "## stale",
        "head_short": "stale",
        "schema_version": 1,
        "tracked_dirty_files": [],
        "untracked_files": [],
    }
    handoff = _write_handoff(repo, stale_contract)
    handoff.write_text(
        handoff.read_text(encoding="utf-8")
        + "\n".join(
            [
                "# 1. Restart Contract",
                "",
                "Restart-ready when: A2 shows `stale-head`.",
                "",
                "# 2. Action Queue",
                "",
                "## A2",
                "Kind: inspect",
                "Expect: `stale-head`",
                "",
                "# 3. Verified Facts",
                "",
                "[FACT git-status] status => stale-status",
                "[FACT git-diff] worktree_diff_stat => empty",
                "[FACT git-log] head => stale-head",
                "[FACT verification] latest_known_full_check => stale-check",
                "",
            ]
        ),
        encoding="utf-8",
    )

    _refresh(repo, handoff, verification_note="./scripts/check passed; pytest 999 passed")

    text = handoff.read_text(encoding="utf-8")
    head = _git(repo, "log", "-1", "--oneline", "--decorate")
    assert f"A2 shows `{head}`" in text
    assert f"Expect: `{head}`" in text
    assert f"[FACT git-log] head => {head}" in text
    assert (
        "[FACT verification] latest_known_full_check => ./scripts/check passed; pytest 999 passed"
    ) in text
    assert "stale-head" not in text
    assert "stale-check" not in text
    assert "tracked.txt" in text
    assert "untracked.txt" in text
