#!/usr/bin/env python3
from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[1]

CURRENT_DOC_FILES = (
    "AGENTS.md",
    "README.md",
    "docs/CURRENT_STATE.md",
    "docs/APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md",
    "docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md",
    "docs/AGENT_ASSESSMENT_INDIVIDUAL_TRADER_2026-06-20.md",
    "docs/AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md",
    "docs/AI_AGENT_STRATEGY_BACKTEST_GUIDE.md",
    "docs/STRATEGY_AND_BACKTEST_USER_GUIDE.md",
    "docs/CODE_STATUS.md",
    "docs/IMPLEMENTED_SURFACES.md",
    "docs/MIGRATION_HISTORY.md",
    "docs/NEXT_DIRECTION_CURRENT.md",
    "docs/TARGET_STRATEGY_OPERATIONS_WORKBENCH_2026-06-18.md",
    "docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md",
    "docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md",
    "docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md",
    "docs/FEATURE_CAPABILITY_SUMMARY_2026-06-27.md",
    "docs/REALISTIC_ROADMAP_CURRENT_2026-06-28.md",
    "docs/final-summary.md",
    "docs/STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md",
    "docs/STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md",
    "docs/STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md",
    "docs/STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md",
    "docs/CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md",
    "docs/DOCUMENT_AUDIT_2026-07-05_CODE_TRUTH_DOC_TRIAGE.md",
    "docs/DOCS_LINT_POLICY_2026-05-30.md",
    "docs/OPERATIONS_RUNBOOK.md",
    "docs/LONG_RUNNING_SCRIPT_OPERATION_RUNBOOK_2026-06-05.md",
    "docs/ARCHITECTURE_AND_PHASES.md",
    "docs/XNYS_MARKET_CALENDAR.md",
    "docs/algo/README.md",
    "docs/algo/ALGO_STRATEGY_SYSTEM_GUIDE.md",
    "docs/algo/STRATEGY_PARTS_CATALOG.md",
    "docs/algo/STRATEGY_BLUEPRINTS.md",
    "docs/algo/STRATEGY_PREP_WORKFLOW.md",
    "docs/algo/EXPERIMENT_SCORECARD.md",
    "docs/algo/RESEARCH_VALIDATION_PLAYBOOK.md",
    "docs/algo/SOURCE_NOTES_INDEX.md",
    "docs/live_evidence_reports/README.md",
    "docs/archive/README.md",
    "docs/trade_xyz_bot_beginner_guide.md",
    "docs/trade_xyz_bot_beginner_guide.html",
    "plan/README.md",
)

CURRENT_DOC_DIRS = (
    "docs/backtest",
    "docs/research/ndx",
    "docs/strategy_lifecycle",
    "docs/strategy_inputs",
    "docs/strategy_paper_smoke",
    "docs/strategy_stage",
    "docs/strategy_review",
    "docs/strategy_runtime_observation",
    "docs/strategy_drift_review",
    "docs/strategy_learning",
    "docs/strategy_case_lite",
    "docs/strategy_input_feedback",
    "docs/strategy_case_index",
    "docs/strategy_daily_brief",
    "docs/strategy_ai_review",
    "docs/strategy_model_loop",
    "docs/strategy_micro_live_plan",
    "docs/strategy_next_scale_plan",
    "docs/strategy_live_observation",
    "docs/strategy_scale_decision",
    "docs/strategy_workbench_viewer",
    "docs/strategy_research_lab",
    "docs/strategy_idea_candidates",
    "docs/runbooks",
    "docs/crypto_perp",
    "docs/venues",
    "docs/references/crypto_perp",
    "docs/algo/strategy_factory",
    "plan/2026-06-22-strategy-feedback-case-index",
)

PLAN_ROUTING_ALLOWED_FILES = ("plan/README.md",)

PLAN_ROUTING_ALLOWED_PREFIXES = (
    "plan/2026-06-22-strategy-feedback-case-index/",
    "plan/archive/",
)

EXCLUDED_DOC_PREFIXES = (
    "docs/archive/",
    "docs/algo/obsidian_note_copies/",
    "docs/algo/obsidian_note_rewrites_2026-05-28/",
    "plan/archive/",
)

LEGACY_ROOT_PATHS = (
    "docs/DOCUMENT_AUDIT_2026-05-26.md",
    "docs/DOCUMENT_AUDIT_2026-05-27.md",
    "docs/DOCUMENT_AUDIT_2026-05-28.md",
    "docs/DOCUMENT_AUDIT_2026-05-30.md",
    "docs/DOCUMENT_AUDIT_2026-05-31.md",
    "docs/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md",
    "docs/backtest/BACKTEST_DOCS_CODE_TRUTH_AUDIT_2026-06-15.md",
    "docs/backtest/BACKTEST_MAINTAINABILITY_RESPONSIBILITY_PLAN_2026-06-14.md",
    "docs/backtest/OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md",
    "docs/backtest/OSS_BACKTEST_CAPABILITY_EXPANSION_IMPLEMENTATION_PLAN_2026-06-15.md",
    "docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md",
    "docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md",
    "plan/0609ここからの計画/03_venue_read_only_capability_probe/",
    "docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md",
    "docs/research/ndx/2_2_IMPLEMENTATION_BOUNDARY.md",
    "docs/strategy_research_lab/12_STRATEGY_AUTHORING_PROGRESS_SUMMARY_2026-05-30.md",
    "docs/strategy_research_lab/14_COMPLETION_EVIDENCE_LEDGER.md",
    "docs/NEXT_IMPLEMENTATION_SEQUENCE_CURRENT.md",
    "docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md",
    "docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-27.md",
    "docs/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md",
    "docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md",
    "docs/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md",
    "docs/TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md",
    "plan/20260526_211746_trade_xyz_quote_collector_cli_plan.md",
)

LAYER22_DOC_PREFIX = "docs/research/ndx/"
LAYER22_SEMANTIC_DRIFT_MARKERS = (
    ("research-dag-", "old Layer 2.2 CLI prefix; use research-layer22-*"),
    ("checked 96 current docs", "old current-doc count snapshot"),
    ("875 passed", "old full-gate pass snapshot"),
    ("ff42f535", "old Layer 2.2 foundation-only HEAD"),
    ("t_after_open", "old temporal layer; use t_open_plus_buffer"),
    ("actual_open_gap", "old QQQ proxy label; use qqq_open_gap"),
    ("open_to_close_outcome", "old QQQ proxy label; use qqq_open_to_close_return"),
)

CURRENT_DOC_SEMANTIC_DRIFT_MARKERS = (
    (
        "PID 2484910",
        "old Trade[XYZ] quote coverage process id; current docs should link archive history instead",
    ),
    (
        "2026-06-04_16:39 JST",
        "old Trade[XYZ] quote coverage start timestamp; current docs should link archive history instead",
    ),
    (
        "Trade[XYZ] read-only PR12 の generated artifact gate は `READ_ONLY_GO` まで確認済み",
        "old copied PR12 generated artifact gate wording; rerun phase-gate-review and keep live-readiness boundary explicit",
    ),
    (
        "Trade[XYZ]用の読み取り専用ゲートは通りました",
        "old fixed Trade[XYZ] guide wording; describe rerunnable read-only state checks instead",
    ),
    (
        "PR12の読み取り専用ゲート結果を毎回確認する",
        "old fixed PR12 guide wording; avoid tying current steps to a stale run label",
    ),
    (
        "Trade[XYZ] Implementation Status Audit",
        "old Trade[XYZ] archive audit link label; route current readers to current guides/runbooks",
    ),
    (
        "2026-06-15_19:13 JST 時点では、代表的な状態は次の通りです。",
        "old copied backtest high-school guide runtime snapshot; rerun backtest artifact/status commands instead",
    ),
    (
        "2026-06-15_21:08 JST 時点で、現在の artifact summary",
        "old copied backtest user guide runtime snapshot; rerun backtest artifact/status commands instead",
    ),
    (
        "strategy total return: `0.0046531202609065075`",
        "old copied backtest benchmark runtime value; inspect strategy-backtest-artifact-summary instead",
    ),
    (
        "benchmark total return: `0.004920882894421784`",
        "old copied backtest benchmark runtime value; inspect strategy-backtest-artifact-summary instead",
    ),
    (
        "information ratio: `-0.08156554737966769`",
        "old copied backtest benchmark runtime value; inspect strategy-backtest-artifact-summary instead",
    ),
    (
        "worst stressed total return: `-0.012846879739093493`",
        "old copied backtest stress runtime value; inspect strategy-backtest-artifact-summary instead",
    ),
    (
        "future candidate count: `3`",
        "old copied backtest data-availability runtime value; inspect strategy-backtest-artifact-summary instead",
    ),
    (
        "unknown critical assumptions: `0`",
        "old copied backtest assumption-ledger runtime value; inspect strategy-backtest-artifact-summary instead",
    ),
    (
        "次に作る operator review artifact",
        "old Strategy Review wording; use strategy-review-record and operator_review.yaml",
    ),
    (
        "別の operator review artifact と既存 paper revalidation を通す",
        "old Strategy Review checklist wording; record operator_review.yaml before paper revalidation",
    ),
)

CURRENT_STATUS_DOC_FILES = (
    "README.md",
    "docs/CURRENT_STATE.md",
    "docs/APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md",
    "docs/APP_CURRENT_STATE_DETAILED_2026-06-20.md",
    "docs/AI_AGENT_STRATEGY_BACKTEST_GUIDE.md",
    "docs/STRATEGY_AND_BACKTEST_USER_GUIDE.md",
    "docs/CODE_STATUS.md",
    "docs/IMPLEMENTED_SURFACES.md",
    "docs/NEXT_DIRECTION_CURRENT.md",
    "docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md",
    "docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md",
    "docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md",
    "docs/OPERATIONS_RUNBOOK.md",
    "docs/backtest/BACKTEST_USER_GUIDE_CURRENT_CAPABILITIES_2026-06-15.md",
    "docs/backtest/README.md",
    "docs/research/ndx/README.md",
    "docs/runbooks/README.md",
    "docs/runbooks/NDX_RESEARCH_RUNBOOK.md",
    "docs/runbooks/PAPER_EXECUTION_RUNBOOK.md",
    "docs/runbooks/STRATEGY_RESEARCH_RUNBOOK.md",
    "docs/runbooks/TRADE_XYZ_RUNBOOK.md",
    "docs/strategy_lifecycle/README.md",
    "docs/strategy_review/README.md",
    "docs/strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md",
    "docs/strategy_research_lab/README.md",
    "docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md",
    "docs/strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md",
    "docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.md",
    "docs/trade_xyz_bot_beginner_guide.md",
)

CURRENT_STATUS_SEMANTIC_DRIFT_MARKERS = (
    (
        "REVISE_2_3",
        "old NDX revision decision; current status docs must point to current artifacts",
    ),
    (
        "162 commands",
        "old public CLI count; rerun scripts/check_cli_catalog.py",
    ),
    (
        "Latest local Layer 2.2 exit decision artifact",
        "old copied Layer 2.2 status wording; rerun Layer 2.2 commands instead",
    ),
    (
        "pack hash sha256:",
        "old copied runtime hash wording; inspect runtime artifacts instead",
    ),
    (
        "latest local `refresh-operations-artifacts`",
        "old copied operations snapshot wording; rerun operations commands instead",
    ),
    (
        "2026-06-17_19:24 JST のローカル再計算",
        "old copied operations artifact timestamp; rerun operations commands instead",
    ),
    (
        "2026-06-17_20:17 JST の補助確認",
        "old copied auxiliary evidence timestamp; rerun evidence commands instead",
    ),
    (
        "2026-06-17_20:44 JST に execution",
        "old copied execution artifact timestamp; rerun execution commands instead",
    ),
    (
        "evidence_card_20260617_111729.json",
        "old copied evidence-card artifact path; rebuild or inspect runtime artifacts instead",
    ),
    (
        "通常ペーパー観察の session 数:",
        "old copied paper-observation session count; rerun strategy-paper-observation-status instead",
    ),
    (
        "最新通常 session の fills:",
        "old copied paper-observation fill gap; inspect latest_normal_requirement_gaps instead",
    ),
    (
        "最新通常 session の trading days:",
        "old copied paper-observation trading-day gap; inspect latest_normal_requirement_gaps instead",
    ),
    (
        "local-paper-20260617-200702",
        "old copied paper-observation session id; inspect runtime artifacts instead",
    ),
    (
        "fills=20/20",
        "old copied paper-observation fill snapshot; inspect latest_normal_requirement_gaps instead",
    ),
    (
        "trading_days=1/10",
        "old copied paper-observation trading-day snapshot; inspect latest_normal_requirement_gaps instead",
    ),
    (
        "phase_gate_decision=READ_ONLY_GO",
        "old copied phase-gate decision snapshot; rerun phase-gate-review instead",
    ),
    (
        'execution_drift_classification_counts={"P2_BLOCKER":0,"LIVE_READINESS_BLOCKER":5}',
        "old copied execution drift count snapshot; rerun phase-gate-review instead",
    ),
    (
        "final_decision=READ_ONLY_GO",
        "old copied PR12 smoke decision snapshot; rerun the smoke path instead",
    ),
    (
        "310 rows, 3673.995702 observed seconds",
        "old copied PR12 quote collection snapshot; rerun collectors instead",
    ),
    (
        "5 symbols x 62 rows",
        "old copied PR12 smoke report snapshot; rerun the smoke path instead",
    ),
    (
        "row_count=605",
        "old copied funding manifest row-count snapshot; inspect runtime artifacts instead",
    ),
    (
        "skipped.missing_oracle_quote_within_lag=671",
        "old copied funding manifest skip-count snapshot; inspect runtime artifacts instead",
    ),
)

CURRENT_STATUS_SEMANTIC_DRIFT_PATTERNS = (
    (
        re.compile(r"\bchecked \d+ current docs\b"),
        "fixed current-doc count snapshot such as checked 125 current docs; rerun scripts/check_current_docs.py",
    ),
    (
        re.compile(r"\b\d{3,4} passed\b"),
        "fixed local pass-count snapshot; rerun ./scripts/check",
    ),
)

ALLOW_LEGACY_ROOT_PATH_TEXT = {
    "docs/DOCS_LINT_POLICY_2026-05-30.md",
    "docs/archive/README.md",
}

MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]\n]+\]\(([^)\n]+)\)")
HTML_HREF_RE = re.compile(r"""href=["']([^"']+)["']""")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
MARKDOWN_METADATA_RE = re.compile(
    r"^<!--\n"
    r"作成日: \d{4}-\d{2}-\d{2}_\d{2}:\d{2} JST\n"
    r"更新日: \d{4}-\d{2}-\d{2}_\d{2}:\d{2} JST\n"
    r"-->\n"
)


def _repo_relative(path: Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def _is_excluded(path: Path) -> bool:
    rel = _repo_relative(path)
    if rel in CURRENT_DOC_FILES:
        return False
    return any(rel.startswith(prefix) for prefix in EXCLUDED_DOC_PREFIXES)


def _is_current_status_doc(rel: str) -> bool:
    return rel in CURRENT_STATUS_DOC_FILES


def _iter_current_docs() -> list[Path]:
    paths = {REPO_ROOT / file_path for file_path in CURRENT_DOC_FILES}
    for directory in CURRENT_DOC_DIRS:
        root = REPO_ROOT / directory
        if root.exists():
            paths.update(path for path in root.rglob("*") if path.suffix in {".md", ".html"})
    return sorted(paths)


def _iter_tracked_files(pathspec: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z", "--", pathspec],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )
    return [raw.decode("utf-8") for raw in result.stdout.split(b"\0") if raw]


def _strip_fragment(target: str) -> str:
    return target.split("#", 1)[0]


def _normalize_link_target(raw_target: str) -> str:
    target = raw_target.strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    return unquote(_strip_fragment(target))


def _is_external_or_anchor(target: str) -> bool:
    return not target or target.startswith("#") or bool(SCHEME_RE.match(target))


def _link_path(source_path: Path, target: str) -> Path:
    target_path = Path(target)
    if target_path.is_absolute():
        return target_path
    return (source_path.parent / target_path).resolve()


def _local_link_targets(path: Path, text: str) -> list[tuple[str, str]]:
    targets: list[tuple[str, str]] = []
    if path.suffix == ".md":
        targets.extend(("markdown", match) for match in MARKDOWN_LINK_RE.findall(text))
    if path.suffix == ".html":
        targets.extend(("html", match) for match in HTML_HREF_RE.findall(text))
    return targets


def _check_path(path: Path) -> list[str]:
    errors: list[str] = []
    rel = _repo_relative(path)

    if _is_excluded(path):
        errors.append(f"{rel}: current-doc allowlist includes excluded path")
        return errors

    if not path.exists():
        return [f"{rel}: missing current doc"]

    data = path.read_bytes()
    if not data.endswith(b"\n"):
        errors.append(f"{rel}: missing final newline")
    if data.endswith(b"\n\n"):
        errors.append(f"{rel}: extra blank line at EOF")

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        return [f"{rel}: not valid UTF-8: {exc}"]

    if path.suffix == ".md" and not MARKDOWN_METADATA_RE.match(text):
        errors.append(f"{rel}: missing or invalid metadata header")

    if path.suffix == ".html":
        markdown_source = path.with_suffix(".md")
        if not markdown_source.exists():
            source_rel = _repo_relative(markdown_source)
            errors.append(f"{rel}: missing same-name Markdown source {source_rel}")

    if rel not in ALLOW_LEGACY_ROOT_PATH_TEXT:
        for legacy_path in LEGACY_ROOT_PATHS:
            if legacy_path in text:
                errors.append(f"{rel}: references legacy root path {legacy_path}")

    if rel.startswith(LAYER22_DOC_PREFIX):
        for marker, reason in LAYER22_SEMANTIC_DRIFT_MARKERS:
            if marker in text:
                errors.append(f"{rel}: Layer 2.2 semantic drift marker {marker!r}: {reason}")

    for marker, reason in CURRENT_DOC_SEMANTIC_DRIFT_MARKERS:
        if marker in text:
            errors.append(f"{rel}: current-doc semantic drift marker {marker!r}: {reason}")

    if _is_current_status_doc(rel):
        for marker, reason in CURRENT_STATUS_SEMANTIC_DRIFT_MARKERS:
            if marker in text:
                errors.append(f"{rel}: current-status semantic drift marker {marker!r}: {reason}")
        for pattern, reason in CURRENT_STATUS_SEMANTIC_DRIFT_PATTERNS:
            if pattern.search(text):
                errors.append(
                    f"{rel}: current-status semantic drift pattern {pattern.pattern!r}: {reason}"
                )

    for kind, raw_target in _local_link_targets(path, text):
        target = _normalize_link_target(raw_target)
        if _is_external_or_anchor(target):
            continue
        if any(legacy_path in target for legacy_path in LEGACY_ROOT_PATHS):
            errors.append(f"{rel}: {kind} link points at legacy root path {raw_target}")
            continue
        candidate = _link_path(path, target)
        if not candidate.exists():
            errors.append(f"{rel}: broken {kind} link {raw_target}")

    return errors


def check_current_docs() -> list[str]:
    errors: list[str] = []
    for path in _iter_current_docs():
        errors.extend(_check_path(path))
    errors.extend(check_plan_routing())
    return errors


def check_plan_routing() -> list[str]:
    errors: list[str] = []
    for rel in _iter_tracked_files("plan"):
        if not (REPO_ROOT / rel).exists():
            continue
        if rel in PLAN_ROUTING_ALLOWED_FILES:
            continue
        if any(rel.startswith(prefix) for prefix in PLAN_ROUTING_ALLOWED_PREFIXES):
            continue
        errors.append(f"{rel}: tracked plan file is outside current root plan or archive routing")
    return errors


def main() -> int:
    errors = check_current_docs()
    if errors:
        print("\n".join(errors))
        return 1
    checked_count = len(_iter_current_docs())
    print(
        f"checked {checked_count} current docs: "
        "metadata, links, EOF, legacy roots, HTML sources, semantic drift, and plan routing ok"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
