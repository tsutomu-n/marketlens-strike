from __future__ import annotations

from pathlib import Path
from typing import Any, cast

from sis.models import Decision, GoNoGoCriterion, GoNoGoReport, VenueDecision
from sis.reports import go_no_go_costs
from sis.reports.go_no_go_markdown import write_go_no_go_markdown
from sis.reports.loaders import safe_read_json_dict_list
from sis.storage.jsonl_store import read_json

MAX_STALE_RATE = 0.05
MIN_TRADABLE_RATE = 0.95
MAX_SPREAD_P90_BPS = 25.0
__all__ = ["build_go_no_go_report", "write_go_no_go_markdown"]

_cost_matrix_rows = go_no_go_costs.cost_matrix_rows
_threshold_result = go_no_go_costs.threshold_result
_holding_cost_result = go_no_go_costs.holding_cost_result
_venue_cost_rows = go_no_go_costs.venue_cost_rows


def latest_positions_sidecar(root: Path) -> Path | None:
    return None


def positions_have_liquidation_reference(path: Path | None) -> bool:
    return False


def _ostium_registry_resolved(path: Path) -> bool:
    if not path.exists():
        return False
    data = read_json(path)
    if not isinstance(data, list):
        return False
    return all(
        isinstance(item, dict)
        and cast(dict[str, Any], item).get("active") is True
        and cast(dict[str, Any], item).get("venue_symbol") != "requires_probe"
        for item in data
    )


def _ostium_fees_oi_complete(path: Path) -> bool:
    if not path.exists():
        return False
    data = read_json(path)
    if not isinstance(data, list):
        return False
    target_rows = [
        cast(dict[str, Any], item)
        for item in data
        if isinstance(item, dict) and cast(dict[str, Any], item).get("venue") == "ostium"
    ]
    return bool(target_rows) and all(
        item.get("opening_fee_bps") is not None
        and item.get("max_open_interest") is not None
        and item.get("rollover_fee_per_block") is not None
        and item.get("max_leverage") is not None
        for item in target_rows
    )


def _load_backtest_metrics(path: Path) -> list[dict]:
    return safe_read_json_dict_list(path)


def _backtest_expected_value_result(path: Path) -> str:
    metrics = _load_backtest_metrics(path)
    if not metrics:
        return "MISSING"
    traded = [item for item in metrics if int(item.get("trade_count") or 0) > 0]
    if not traded:
        return "NO_GO"
    if any(float(item.get("avg_trade_return") or 0.0) > 0.0 for item in traded):
        return "PASS"
    return "NO_GO"


def _first_blocker(checks: list[GoNoGoCriterion]) -> str | None:
    for item in checks:
        if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE", "NO_GO", "PARTIAL"}:
            return item.criterion
    return None


def _has_trade_xyz_artifacts(data_dir: Path) -> bool:
    return (
        (data_dir / "registry/trade_xyz_instrument_registry.json").exists()
        or any((data_dir / "raw/quotes/trade_xyz").glob("*.jsonl"))
        or (data_dir / "ops/trade_xyz_quote_collection_summary.json").exists()
    )


def _latest_trade_xyz_quote(data_dir: Path) -> Path | None:
    paths = sorted((data_dir / "raw/quotes/trade_xyz").glob("*.jsonl"))
    return paths[-1] if paths else None


def _trade_xyz_summary_row_count(path: Path) -> int:
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


def _build_trade_xyz_go_no_go_report(data_dir: Path) -> GoNoGoReport:
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    quote_path = _latest_trade_xyz_quote(data_dir)
    summary_path = data_dir / "ops/trade_xyz_quote_collection_summary.json"
    normalized_quotes = data_dir / "normalized/quotes.parquet"
    phase_gate_summary = data_dir / "ops/phase_gate_review_summary.json"
    row_count = _trade_xyz_summary_row_count(summary_path)
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


def _venue_decision_from_checks(venue: str, checks: list[GoNoGoCriterion]) -> VenueDecision:
    blocker = _first_blocker(checks)
    if blocker is None:
        return VenueDecision(venue=venue, decision=Decision.GO, main_blocker=None)
    blocking_names = {
        item.criterion
        for item in checks
        if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE", "NO_GO", "PARTIAL"}
    }
    data_readiness_blockers = {
        "Ostium symbol resolved",
        "Ostium fees/OI/rollover metadata complete",
        "Liquidation reference complete",
        "Venue cost matrix",
        "Holding/rollover cost reproduced for target horizons",
    }
    if venue == "ostium" and blocking_names and blocking_names.issubset(data_readiness_blockers):
        return VenueDecision(
            venue=venue, decision=Decision.CONDITIONAL_GO_DATA_READY, main_blocker=blocker
        )
    if blocker in {"stale_rate at or below threshold", "tradable_rate at or above threshold"}:
        return VenueDecision(
            venue=venue, decision=Decision.CONDITIONAL_GO_NEEDS_LIVE_WINDOW, main_blocker=blocker
        )
    if blocker == "spread_p90 at or below threshold":
        return VenueDecision(venue=venue, decision=Decision.NO_GO_COST, main_blocker=blocker)
    return VenueDecision(venue=venue, decision=Decision.NO_GO, main_blocker=blocker)


def _next_actions(blockers: list[str], signals_exists: bool) -> list[str]:
    actions: list[str] = []
    if "stale_rate at or below threshold" in blockers:
        actions.append(
            "Collect quote rows with fresh venue timestamps so stale_rate is at or below threshold"
        )
    if "tradable_rate at or above threshold" in blockers:
        actions.append(
            "Collect a sufficient legacy gTrade/Ostium quote window only if the legacy archive is intentionally restored"
        )
    if not signals_exists:
        actions.append(
            "Provide data/research/signals.csv to run signal-driven backtests instead of quote-only fallback"
        )
    return actions


def _decision_for_state(
    *,
    core_ready: bool,
    blockers: list[str],
    signals_exists: bool,
) -> Decision:
    if not core_ready:
        return Decision.NO_GO
    if not blockers:
        if not signals_exists:
            return Decision.CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST
        return Decision.GO
    blocker_set = set(blockers)
    live_window_blockers = {
        "stale_rate at or below threshold",
        "tradable_rate at or above threshold",
    }
    if blocker_set.issubset(live_window_blockers):
        return Decision.CONDITIONAL_GO_NEEDS_LIVE_WINDOW
    if (
        "4h-3d after-cost backtest" in blocker_set
        or "Holding/rollover cost reproduced for target horizons" in blocker_set
    ):
        return Decision.NO_GO_COST
    if "stale_rate at or below threshold" in blocker_set:
        return Decision.NO_GO_STALE
    if "tradable_rate at or above threshold" in blocker_set:
        return Decision.NO_GO_SESSION
    return Decision.CONDITIONAL_GO_DATA_READY


def build_go_no_go_report(data_dir: Path) -> GoNoGoReport:
    if _has_trade_xyz_artifacts(data_dir):
        return _build_trade_xyz_go_no_go_report(data_dir)

    gtrade_registry = data_dir / "registry/gtrade_instrument_registry.json"
    ostium_registry = data_dir / "registry/ostium_instrument_registry.json"
    quotes = data_dir / "normalized/quotes.parquet"
    cost_matrix = data_dir / "research/venue_cost_matrix.csv"
    backtest_report = data_dir / "research/backtest_report.md"
    backtest_metrics = data_dir / "research/backtest_metrics.json"
    signals = data_dir / "research/signals.csv"
    ostium_positions = latest_positions_sidecar(data_dir / "raw/sidecar/ostium")
    ostium_resolved = _ostium_registry_resolved(ostium_registry)
    ostium_fees_oi_complete = _ostium_fees_oi_complete(ostium_registry)
    cost_rows = _cost_matrix_rows(cost_matrix)
    gtrade_cost_rows = _venue_cost_rows(cost_rows, "gtrade")
    ostium_cost_rows = _venue_cost_rows(cost_rows, "ostium")

    criteria = [
        GoNoGoCriterion(
            criterion="gTrade registry generated",
            result="PASS" if gtrade_registry.exists() else "MISSING",
            evidence=str(gtrade_registry),
        ),
        GoNoGoCriterion(
            criterion="Ostium symbol resolved",
            result="PASS"
            if ostium_resolved
            else ("REQUIRES_PROBE" if ostium_registry.exists() else "MISSING"),
            evidence=str(ostium_registry),
        ),
        GoNoGoCriterion(
            criterion="Normalized quote data",
            result="PASS" if quotes.exists() else "MISSING",
            evidence=str(quotes),
        ),
        GoNoGoCriterion(
            criterion="Venue cost matrix",
            result="PASS" if cost_matrix.exists() else "MISSING",
            evidence=str(cost_matrix),
        ),
        GoNoGoCriterion(
            criterion="Scalping not required",
            result="PASS",
            evidence="configs/scalping_policy.yaml",
        ),
        GoNoGoCriterion(
            criterion="Ostium fees/OI/rollover metadata complete",
            result="PASS" if ostium_fees_oi_complete else "MISSING",
            evidence=str(ostium_registry),
        ),
        GoNoGoCriterion(
            criterion="Liquidation reference complete",
            result="PASS" if positions_have_liquidation_reference(ostium_positions) else "NOT_DONE",
            evidence=str(ostium_positions)
            if ostium_positions
            else "Legacy Ostium liquidationPx requires restored open-position sidecar data",
        ),
        GoNoGoCriterion(
            criterion="4h-3d after-cost backtest",
            result=_backtest_expected_value_result(backtest_metrics),
            evidence=str(backtest_metrics),
        ),
        GoNoGoCriterion(
            criterion="stale_rate at or below threshold",
            result=_threshold_result(cost_rows, "stale_rate", maximum=MAX_STALE_RATE),
            evidence=f"{cost_matrix}; threshold<={MAX_STALE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="tradable_rate at or above threshold",
            result=_threshold_result(cost_rows, "tradable_rate", minimum=MIN_TRADABLE_RATE),
            evidence=f"{cost_matrix}; threshold>={MIN_TRADABLE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="spread_p90 at or below threshold",
            result=_threshold_result(cost_rows, "spread_p90_bps", maximum=MAX_SPREAD_P90_BPS),
            evidence=f"{cost_matrix}; threshold<={MAX_SPREAD_P90_BPS}bps",
        ),
        GoNoGoCriterion(
            criterion="Holding/rollover cost reproduced for target horizons",
            result=_holding_cost_result(cost_rows),
            evidence=str(cost_matrix),
        ),
        GoNoGoCriterion(
            criterion="Research signal CSV connected",
            result="PASS" if signals.exists() else "OPTIONAL_FALLBACK",
            evidence=str(signals),
        ),
    ]

    blockers = [
        item.criterion
        for item in criteria
        if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE", "NO_GO", "PARTIAL"}
    ]
    core_ready = (
        quotes.exists() and cost_matrix.exists() and backtest_report.exists() and ostium_resolved
    )
    decision = _decision_for_state(
        core_ready=core_ready,
        blockers=blockers,
        signals_exists=signals.exists(),
    )
    gtrade_checks = [
        criteria[0],
        criteria[2],
        criteria[3],
        criteria[7],
        GoNoGoCriterion(
            criterion="stale_rate at or below threshold",
            result=_threshold_result(gtrade_cost_rows, "stale_rate", maximum=MAX_STALE_RATE),
            evidence=f"{cost_matrix}; venue=gtrade; threshold<={MAX_STALE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="tradable_rate at or above threshold",
            result=_threshold_result(gtrade_cost_rows, "tradable_rate", minimum=MIN_TRADABLE_RATE),
            evidence=f"{cost_matrix}; venue=gtrade; threshold>={MIN_TRADABLE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="spread_p90 at or below threshold",
            result=_threshold_result(
                gtrade_cost_rows, "spread_p90_bps", maximum=MAX_SPREAD_P90_BPS
            ),
            evidence=f"{cost_matrix}; venue=gtrade; threshold<={MAX_SPREAD_P90_BPS}bps",
        ),
        GoNoGoCriterion(
            criterion="Holding/rollover cost reproduced for target horizons",
            result=_holding_cost_result(gtrade_cost_rows),
            evidence=str(cost_matrix),
        ),
    ]
    ostium_checks = [
        criteria[1],
        criteria[2],
        criteria[3],
        criteria[5],
        criteria[6],
        GoNoGoCriterion(
            criterion="stale_rate at or below threshold",
            result=_threshold_result(ostium_cost_rows, "stale_rate", maximum=MAX_STALE_RATE),
            evidence=f"{cost_matrix}; venue=ostium; threshold<={MAX_STALE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="tradable_rate at or above threshold",
            result=_threshold_result(ostium_cost_rows, "tradable_rate", minimum=MIN_TRADABLE_RATE),
            evidence=f"{cost_matrix}; venue=ostium; threshold>={MIN_TRADABLE_RATE}",
        ),
        GoNoGoCriterion(
            criterion="spread_p90 at or below threshold",
            result=_threshold_result(
                ostium_cost_rows, "spread_p90_bps", maximum=MAX_SPREAD_P90_BPS
            ),
            evidence=f"{cost_matrix}; venue=ostium; threshold<={MAX_SPREAD_P90_BPS}bps",
        ),
        GoNoGoCriterion(
            criterion="Holding/rollover cost reproduced for target horizons",
            result=_holding_cost_result(ostium_cost_rows),
            evidence=str(cost_matrix),
        ),
    ]

    return GoNoGoReport(
        decision=decision,
        summary="Implementation status report. This evaluates collected evidence and does not authorize live trading.",
        criteria=criteria,
        venue_decisions=[
            _venue_decision_from_checks("gtrade", gtrade_checks),
            _venue_decision_from_checks("ostium", ostium_checks),
        ],
        blockers=blockers,
        next_actions=_next_actions(blockers, signals.exists()),
    )
