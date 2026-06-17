from pathlib import Path
import runpy
import subprocess
import sys
from typing import Any


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def _checker_globals() -> dict[str, Any]:
    return runpy.run_path("scripts/check_current_docs.py", run_name="check_current_docs_under_test")


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
    assert '"docs/trade_xyz_bot_beginner_guide.md"' in script
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
    assert "missing same-name Markdown source" in script
    assert "LAYER22_SEMANTIC_DRIFT_MARKERS" in script
    assert "research-dag-" in script
    assert "CURRENT_STATUS_DOC_FILES" in script
    assert "CURRENT_STATUS_SEMANTIC_DRIFT_MARKERS" in script
    assert "CURRENT_STATUS_SEMANTIC_DRIFT_PATTERNS" in script
    assert "PLAN_ROUTING_ALLOWED_FILES" in script
    assert "PLAN_ROUTING_ALLOWED_PREFIXES" in script
    assert "check_plan_routing" in script
    assert "plan/0609ここからの計画/03_venue_read_only_capability_probe/" in script
    assert "REVISE_2_3" in script
    assert "162 commands" in script
    assert "checked 125 current docs" in script
    assert "latest local `refresh-operations-artifacts`" in script
    assert "evidence_card_20260617_111729.json" in script
    assert "old copied operations artifact timestamp" in script
    assert "通常ペーパー観察の session 数:" in script
    assert "local-paper-20260617-200702" in script
    assert "old copied paper-observation session count" in script
    assert "fills=20/20" in script
    assert "trading_days=1/10" in script
    assert "phase_gate_decision=READ_ONLY_GO" in script
    assert "final_decision=READ_ONLY_GO" in script
    assert "310 rows, 3673.995702 observed seconds" in script
    assert "row_count=605" in script
    assert "PID 2484910" in script
    assert "2026-06-04_16:39 JST" in script
    assert "generated artifact gate は `READ_ONLY_GO` まで確認済み" in script
    assert "2026-06-15_19:13 JST 時点では、代表的な状態は次の通りです。" in script

    checker_globals = _checker_globals()
    current_doc_files = set(checker_globals["CURRENT_DOC_FILES"])
    legacy_root_paths = set(checker_globals["LEGACY_ROOT_PATHS"])
    assert "docs/DOCUMENT_AUDIT_2026-05-31.md" not in current_doc_files
    assert "docs/DOCUMENT_AUDIT_2026-05-31.md" in legacy_root_paths
    assert "docs/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md" not in current_doc_files
    assert "docs/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md" in legacy_root_paths
    assert "docs/backtest/BACKTEST_DOCS_CODE_TRUTH_AUDIT_2026-06-15.md" not in current_doc_files
    assert "docs/backtest/BACKTEST_DOCS_CODE_TRUTH_AUDIT_2026-06-15.md" in legacy_root_paths
    assert (
        "docs/backtest/BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md"
        not in current_doc_files
    )
    assert (
        "docs/backtest/BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md"
        in legacy_root_paths
    )
    assert (
        "docs/backtest/OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md"
        not in current_doc_files
    )
    assert (
        "docs/backtest/OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md"
        in legacy_root_paths
    )
    assert (
        "docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md"
        not in current_doc_files
    )
    assert (
        "docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md"
        in legacy_root_paths
    )
    assert (
        "docs/strategy_research_lab/12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md"
        not in current_doc_files
    )
    assert (
        "docs/strategy_research_lab/12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md"
        in legacy_root_paths
    )
    assert "docs/strategy_research_lab/14_COMPLETION_EVIDENCE_LEDGER.md" not in current_doc_files
    assert "docs/strategy_research_lab/14_COMPLETION_EVIDENCE_LEDGER.md" in legacy_root_paths
    assert "docs/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md" not in current_doc_files
    assert "docs/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md" in legacy_root_paths
    assert "docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md" not in current_doc_files
    assert "docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md" in legacy_root_paths
    assert (
        "docs/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md" not in current_doc_files
    )
    assert "docs/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md" in legacy_root_paths
    assert (
        "docs/TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md" not in current_doc_files
    )
    assert "docs/TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md" in legacy_root_paths

    current_status_docs = set(checker_globals["CURRENT_STATUS_DOC_FILES"])
    assert "README.md" in current_status_docs
    assert "docs/CURRENT_STATE.md" in current_status_docs
    assert "docs/CODE_STATUS.md" in current_status_docs
    assert "docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md" in current_status_docs
    assert "docs/research/ndx/README.md" in current_status_docs
    assert "docs/runbooks/NDX_RESEARCH_RUNBOOK.md" in current_status_docs
    assert "docs/DOCUMENT_AUDIT_2026-06-17_CODE_TRUTH_CHECKLIST.md" not in current_status_docs
    assert (
        "docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md" not in current_status_docs
    )


def test_plan_routing_keeps_historical_docs_archived() -> None:
    checker_globals = _checker_globals()
    assert checker_globals["check_plan_routing"]() == []

    result = subprocess.run(
        ["git", "ls-files", "-z", "--", "plan"],
        check=True,
        capture_output=True,
    )
    tracked_plan_files = {raw.decode("utf-8") for raw in result.stdout.split(b"\0") if raw}

    assert "plan/README.md" in tracked_plan_files
    assert (
        "plan/archive/2026-06-08-plan-routing/0607ここからの計画2/zip_intake_guide/README.md"
        in tracked_plan_files
    )
    assert all(not path.startswith("plan/0607ここからの計画2/") for path in tracked_plan_files)
    assert all(not path.startswith("plan/0608ここからの計画/") for path in tracked_plan_files)


def test_human_facing_html_guides_have_markdown_sources() -> None:
    readme = _read("README.md")
    algo_readme = _read("docs/algo/README.md")
    strategy_factory_readme = _read("docs/algo/strategy_factory/README.md")
    strategy_factory_html = _read("docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html")
    strategy_factory_markdown = _read(
        "docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md"
    )
    strategy_readme = _read("docs/strategy_research_lab/README.md")
    strategy_short = _read("docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md")
    strategy_html = _read("docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html")
    beginner = _read("docs/trade_xyz_bot_beginner_guide.md")

    assert "docs/trade_xyz_bot_beginner_guide.md" in readme
    assert "trade_xyz_bot_beginner_guide.html" in beginner
    assert "STRATEGY_FACTORY_OPERATOR_GUIDE.md" in readme
    assert "STRATEGY_FACTORY_OPERATOR_GUIDE.md" in algo_readme
    assert "STRATEGY_FACTORY_OPERATOR_GUIDE.md" in strategy_factory_readme
    assert "STRATEGY_FACTORY_OPERATOR_GUIDE.md" in strategy_factory_html
    assert "STRATEGY_FACTORY_OPERATOR_GUIDE.html" in strategy_factory_markdown
    assert "08_CURRENT_CAPABILITIES_EXPLAINED.md" in strategy_readme
    assert "08_CURRENT_CAPABILITIES_EXPLAINED.md" in strategy_short
    assert "08_CURRENT_CAPABILITIES_EXPLAINED.md" in strategy_html

    checker_globals = _checker_globals()
    html_without_markdown_source = [
        checker_globals["_repo_relative"](path)
        for path in checker_globals["_iter_current_docs"]()
        if path.suffix == ".html" and not path.with_suffix(".md").exists()
    ]
    assert html_without_markdown_source == []


def test_layer22_record_is_frozen_history_not_current_hash_source() -> None:
    readme = _read("README.md")
    ndx_readme = _read("docs/research/ndx/README.md")
    record = _read("docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md")

    assert "historical implementation record" in readme
    assert "Latest local Layer 2.2 exit decision artifact" not in readme
    assert "sha256:7fc0d644d4a8d7432df29a8dfd6c878fc97342b5745febc26e6cd6206a01dd6a" not in readme
    assert "現在の通過状態や pack hash は tracked docs へ写さず" in ndx_readme
    assert "現在値の証明として使わない" in record


def test_strategy_lifecycle_and_ndx_docs_cross_link_paper_only_handoff() -> None:
    strategy_lifecycle = _read("docs/strategy_lifecycle/README.md")
    ndx_readme = _read("docs/research/ndx/README.md")
    layer28 = _read("docs/research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md")
    paper_runbook = _read("docs/runbooks/PAPER_EXECUTION_RUNBOOK.md")

    canonical_review_path = "data/research/ndx/paper_observation_review_decision.json"
    assert canonical_review_path in strategy_lifecycle
    assert canonical_review_path in ndx_readme
    assert canonical_review_path in layer28
    assert canonical_review_path in paper_runbook
    assert (
        "--paper-review-path data/research/ndx/paper_observation_review_decision.json"
        in strategy_lifecycle
    )
    assert (
        "--canonical-review-path data/research/ndx/paper_observation_review_decision.json"
        in strategy_lifecycle
    )
    assert "strategy-paper-observation-status" in ndx_readme
    assert "[docs/strategy_lifecycle/README.md](../../strategy_lifecycle/README.md)" in ndx_readme
    assert "[docs/strategy_lifecycle/README.md](../../strategy_lifecycle/README.md)" in layer28
    assert "[docs/strategy_lifecycle/README.md](../strategy_lifecycle/README.md)" in paper_runbook
    assert "Layer 2.8 pass" in ndx_readme
    assert "live_conversion_allowed=false" in paper_runbook


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
