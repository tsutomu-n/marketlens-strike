from pathlib import Path
import subprocess
import sys


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_operations_runbook_does_not_claim_trade_xyz_log_quotes_cli() -> None:
    root = _read("docs/OPERATIONS_RUNBOOK.md")
    trade_xyz = _read("docs/runbooks/TRADE_XYZ_RUNBOOK.md")
    paper_execution = _read("docs/runbooks/PAPER_EXECUTION_RUNBOOK.md")
    current_runbooks = trade_xyz + paper_execution

    assert "runbooks/TRADE_XYZ_RUNBOOK.md" in root
    assert "uv run sis probe trade-xyz" in trade_xyz
    assert "uv run sis log-quotes --venue trade_xyz --replace" not in current_runbooks
    assert "uv run sis collect-trade-xyz-quotes" in current_runbooks
    assert "uv run sis log-quotes --venue gtrade --replace" not in current_runbooks
    assert "public CLI command" in paper_execution


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

    assert "README.md" in files


def test_current_docs_checker_policy_is_current_scope_only() -> None:
    script = _read("scripts/check_current_docs.py")
    readme = _read("README.md")

    assert '"AGENTS.md"' in script
    assert '"docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md"' in script
    assert '"docs/DOCUMENT_AUDIT_2026-05-31.md"' in script
    assert '"docs/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md"' not in script
    assert '"docs/DOCUMENT_AUDIT_2026-05-31_BACKTEST_UPDATE.md"' not in script
    assert '"docs/LIVE_READINESS_BLOCKER_DECOMPOSITION_PLAN_2026-05-29.md"' not in script
    assert (
        "docs/archive/2026-06-17-doc-routing/DOCUMENT_AUDIT_2026-06-09_NDX_2_3_2_4_REFRESH.md"
        in readme
    )
    assert '"docs/DOCUMENT_AUDIT_2026-06-06_CODE_TRUTH_REFRESH.md"' not in script
    assert '"docs/algo/ALGO_STRATEGY_SYSTEM_GUIDE.md"' in script
    assert '"docs/algo/STRATEGY_PARTS_CATALOG.md"' in script
    assert '"docs/algo/STRATEGY_BLUEPRINTS.md"' in script
    assert '"docs/algo/STRATEGY_PREP_WORKFLOW.md"' in script
    assert '"docs/algo/EXPERIMENT_SCORECARD.md"' in script
    assert '"docs/algo/RESEARCH_VALIDATION_PLAYBOOK.md"' in script
    assert '"docs/algo/SOURCE_NOTES_INDEX.md"' in script
    assert '"docs/strategy_research_lab"' in script
    assert '"docs/runbooks"' in script
    assert '"docs/research/ndx"' in script
    assert '"docs/algo/strategy_factory"' in script
    assert '"docs/algo/obsidian_note_rewrites_2026-05-29"' in script
    assert '"docs/archive/"' in script
    assert '"docs/algo/obsidian_note_copies/"' in script
    assert '"docs/algo/obsidian_note_rewrites_2026-05-28/"' in script
    assert '"plan/archive/"' in script
    assert "MARKDOWN_METADATA_RE" in script
    assert "missing or invalid metadata header" in script
    assert "LAYER22_SEMANTIC_DRIFT_MARKERS" in script
    assert "research-dag-" in script


def test_cli_catalog_matches_registered_commands() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_cli_catalog.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "public CLI commands" in result.stdout


def test_current_docs_checker_passes() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/check_current_docs.py"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "current docs" in result.stdout
