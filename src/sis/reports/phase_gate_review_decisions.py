from __future__ import annotations

from pathlib import Path

from sis.reports import phase_gate_review_paths

PHASE2_ALLOWED_DECISIONS = {
    "GO",
    "CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST",
    "READ_ONLY_GO",
    "PAPER_GO",
    "CONDITIONAL_INDEX_ONLY",
}


def trade_xyz_artifacts_present(data_dir: Path) -> bool:
    return (
        (data_dir / "registry/trade_xyz_instrument_registry.json").exists()
        or (data_dir / "ops/trade_xyz_quote_collection_summary.json").exists()
        or phase_gate_review_paths.latest_path(data_dir / "raw/quotes/trade_xyz", "*.jsonl")
        is not None
    )


def phase2_entry_allowed(
    *,
    strict_validation_passed: bool,
    diagnostics_all_available: bool,
    collector_gate: dict[str, object],
    decision: object,
) -> bool:
    return bool(
        strict_validation_passed
        and diagnostics_all_available
        and collector_gate["read_only_collector_gate_passed"] is True
        and isinstance(decision, str)
        and decision in PHASE2_ALLOWED_DECISIONS
    )
