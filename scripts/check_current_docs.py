#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[1]

CURRENT_DOC_FILES = (
    "AGENTS.md",
    "README.md",
    "docs/CURRENT_STATE.md",
    "docs/CODE_STATUS.md",
    "docs/IMPLEMENTED_SURFACES.md",
    "docs/MIGRATION_HISTORY.md",
    "docs/NEXT_DIRECTION_CURRENT.md",
    "docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md",
    "docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md",
    "docs/DOCUMENT_AUDIT_2026-05-31.md",
    "docs/DOCUMENT_AUDIT_2026-06-15_CODE_TRUTH_CHECKLIST.md",
    "docs/DOCUMENT_AUDIT_2026-06-17_CODE_TRUTH_CHECKLIST.md",
    "docs/DOCS_LINT_POLICY_2026-05-30.md",
    "docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md",
    "docs/OPERATIONS_RUNBOOK.md",
    "docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md",
    "docs/TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md",
    "docs/TRADE_XYZ_DATA_CYCLE_NATURAL_EXIT_CONDITIONS_2026-06-05.md",
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
    "docs/trade_xyz_bot_beginner_guide.html",
    "plan/README.md",
)

CURRENT_DOC_DIRS = (
    "docs/backtest",
    "docs/research/ndx",
    "docs/strategy_lifecycle",
    "docs/strategy_review",
    "docs/strategy_research_lab",
    "docs/runbooks",
    "docs/venues",
    "docs/algo/strategy_factory",
    "docs/algo/obsidian_note_rewrites_2026-05-29",
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
    "docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md",
    "docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-27.md",
    "docs/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md",
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

ALLOW_LEGACY_ROOT_PATH_TEXT = {
    "docs/DOCUMENT_AUDIT_2026-05-31.md",
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


def _iter_current_docs() -> list[Path]:
    paths = {REPO_ROOT / file_path for file_path in CURRENT_DOC_FILES}
    for directory in CURRENT_DOC_DIRS:
        root = REPO_ROOT / directory
        if root.exists():
            paths.update(path for path in root.rglob("*") if path.suffix in {".md", ".html"})
    return sorted(paths)


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

    if rel not in ALLOW_LEGACY_ROOT_PATH_TEXT:
        for legacy_path in LEGACY_ROOT_PATHS:
            if legacy_path in text:
                errors.append(f"{rel}: references legacy root path {legacy_path}")

    if rel.startswith(LAYER22_DOC_PREFIX):
        for marker, reason in LAYER22_SEMANTIC_DRIFT_MARKERS:
            if marker in text:
                errors.append(f"{rel}: Layer 2.2 semantic drift marker {marker!r}: {reason}")

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
    return errors


def main() -> int:
    errors = check_current_docs()
    if errors:
        print("\n".join(errors))
        return 1
    checked_count = len(_iter_current_docs())
    print(f"checked {checked_count} current docs: metadata, links, EOF, and legacy roots ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
