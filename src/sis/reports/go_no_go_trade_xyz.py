from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.models import Decision, GoNoGoCriterion, GoNoGoReport, VenueDecision
from sis.storage.jsonl_store import read_json


def has_trade_xyz_artifacts(data_dir: Path) -> bool:
    return (
        (data_dir / "registry/trade_xyz_instrument_registry.json").exists()
        or any((data_dir / "raw/quotes/trade_xyz").glob("*.jsonl"))
        or (data_dir / "ops/trade_xyz_quote_collection_summary.json").exists()
    )


def latest_trade_xyz_quote(data_dir: Path) -> Path | None:
    paths = sorted((data_dir / "raw/quotes/trade_xyz").glob("*.jsonl"))
    return paths[-1] if paths else None


def trade_xyz_summary_row_count(path: Path) -> int:
    if not path.exists():
        return 0
    payload = read_json(path)
    if not isinstance(payload, dict):
        return 0
    payload = cast(dict[str, Any], payload)
    try:
        return int(payload.get("row_count") or 0)
    except (TypeError, ValueError):
        return 0


def build_trade_xyz_go_no_go_report(data_dir: Path) -> GoNoGoReport:
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    quote_path = latest_trade_xyz_quote(data_dir)
    summary_path = data_dir / "ops/trade_xyz_quote_collection_summary.json"
    normalized_quotes = data_dir / "normalized/quotes.parquet"
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    row_count = trade_xyz_summary_row_count(summary_path)
    criteria = [
        GoNoGoCriterion(
            criterion="Trade[XYZ] registry generated",
            result="PASS" if registry.exists() else "MISSING",
            evidence=str(registry),
        ),
        GoNoGoCriterion(
            criterion="Trade[XYZ] quote window collected",
            result="PASS" if quote_path is not None else "MISSING",
            evidence=str(quote_path) if quote_path else str(data_dir / "raw/quotes/trade_xyz"),
        ),
        GoNoGoCriterion(
            criterion="Trade[XYZ] quote collection summary",
            result="PASS"
            if row_count > 0
            else ("MISSING" if not summary_path.exists() else "NO_GO"),
            evidence=str(summary_path),
        ),
        GoNoGoCriterion(
            criterion="Normalized quote data",
            result="PASS" if normalized_quotes.exists() else "MISSING",
            evidence=str(normalized_quotes),
        ),
        GoNoGoCriterion(
            criterion="Phase gate review summary",
            result="PASS" if phase_gate_summary.exists() else "MISSING",
            evidence=str(phase_gate_summary),
        ),
    ]
    blockers = [
        item.criterion
        for item in criteria
        if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE", "NO_GO", "PARTIAL"}
    ]
    next_actions: list[str] = []
    if not registry.exists():
        next_actions.append("Run `uv run sis probe trade-xyz`.")
    if quote_path is None or row_count <= 0:
        next_actions.append(
            "Run `uv run sis collect-trade-xyz-quotes --write-summary --write-report`."
        )
    if not normalized_quotes.exists():
        next_actions.append("Collect Trade[XYZ] quotes with normalization enabled.")
    if not phase_gate_summary.exists():
        next_actions.append("Run `uv run sis phase-gate-review`.")
    decision = Decision.GO if not blockers else Decision.NO_GO
    return GoNoGoReport(
        decision=decision,
        summary=(
            "Trade[XYZ] supplemental Go/No-Go report. Bot readiness is gated by "
            "`phase-gate-review`; this report only summarizes local artifacts."
        ),
        criteria=criteria,
        venue_decisions=[
            VenueDecision(
                venue="trade_xyz",
                decision=decision,
                main_blocker=blockers[0] if blockers else None,
            )
        ],
        blockers=blockers,
        next_actions=next_actions,
    )
