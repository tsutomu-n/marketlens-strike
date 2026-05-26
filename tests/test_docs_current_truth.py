from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_operations_runbook_does_not_claim_trade_xyz_log_quotes_cli() -> None:
    text = _read("docs/OPERATIONS_RUNBOOK.md")

    assert "uv run sis probe trade-xyz" in text
    assert "uv run sis log-quotes --venue trade_xyz --replace" not in text
    assert "uv run sis log-quotes --venue gtrade --replace" in text
    assert "public CLI command" in text


def test_live_evidence_reports_are_archived_and_ignored() -> None:
    readme = _read("docs/live_evidence_reports/README.md")
    archive_readme = _read("docs/archive/README.md")
    gitignore = _read(".gitignore")

    assert "README.md" in readme
    assert "docs/archive/2026-05-26-live-evidence-history/" in readme
    assert "Archived on 2026-05-26" in archive_readme
    assert "docs/live_evidence_reports/live_evidence_report_*.md" in gitignore
    assert "docs/live_evidence_reports/live_evidence_report_*.html" in gitignore
    assert "docs/live_evidence_reports/live_evidence_followup_*.md" in gitignore
    assert "!docs/live_evidence_reports/README.md" in gitignore


def test_live_evidence_reports_directory_keeps_only_readme_tracked_docs() -> None:
    report_dir = Path("docs/live_evidence_reports")
    files = sorted(path.name for path in report_dir.iterdir() if path.is_file())

    assert files == ["README.md"]
