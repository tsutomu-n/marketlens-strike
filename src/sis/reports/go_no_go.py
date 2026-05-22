from __future__ import annotations

import json
from pathlib import Path

from sis.models import Decision, GoNoGoCriterion, GoNoGoReport, VenueDecision
from sis.storage.jsonl_store import read_json
from sis.venues.ostium.positions import (
    latest_positions_sidecar,
    positions_have_liquidation_reference,
)

MAX_STALE_RATE = 0.05
MIN_TRADABLE_RATE = 0.95
MAX_SPREAD_P90_BPS = 25.0


def _ostium_registry_resolved(path: Path) -> bool:
    if not path.exists():
        return False
    data = read_json(path)
    if not isinstance(data, list):
        return False
    return all(
        isinstance(item, dict)
        and item.get("active") is True
        and item.get("venue_symbol") != "requires_probe"
        for item in data
    )


def _ostium_fees_oi_complete(path: Path) -> bool:
    if not path.exists():
        return False
    data = read_json(path)
    if not isinstance(data, list):
        return False
    target_rows = [
        item for item in data if isinstance(item, dict) and item.get("venue") == "ostium"
    ]
    return bool(target_rows) and all(
        item.get("opening_fee_bps") is not None
        and item.get("max_open_interest") is not None
        and item.get("rollover_fee_per_block") is not None
        and item.get("max_leverage") is not None
        for item in target_rows
    )


def _load_backtest_metrics(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


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


def _cost_matrix_rows(path: Path) -> list[dict[str, str | None]]:
    if not path.exists():
        return []
    import csv

    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def _threshold_result(
    rows: list[dict[str, str | None]],
    column: str,
    *,
    maximum: float | None = None,
    minimum: float | None = None,
) -> str:
    values: list[float] = []
    for row in rows:
        value = row.get(column)
        if value in {None, ""}:
            return "MISSING"
        values.append(float(value))
    if not values:
        return "MISSING"
    if maximum is not None and any(value > maximum for value in values):
        return "NO_GO"
    if minimum is not None and any(value < minimum for value in values):
        return "NO_GO"
    return "PASS"


def _holding_cost_result(rows: list[dict[str, str | None]]) -> str:
    if not rows:
        return "MISSING"
    required = ("holding_cost_4h_bps", "holding_cost_24h_bps", "holding_cost_72h_bps")
    completed = [
        all(row.get(column) not in {None, ""} for column in required)
        for row in rows
    ]
    if all(completed):
        return "PASS"
    if any(completed):
        return "PARTIAL"
    return "MISSING"


def _first_blocker(checks: list[GoNoGoCriterion]) -> str | None:
    for item in checks:
        if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE", "NO_GO", "PARTIAL"}:
            return item.criterion
    return None


def _venue_cost_rows(rows: list[dict[str, str | None]], venue: str) -> list[dict[str, str | None]]:
    return [row for row in rows if row.get("venue") == venue]


def _venue_decision_from_checks(venue: str, checks: list[GoNoGoCriterion]) -> VenueDecision:
    blocker = _first_blocker(checks)
    if blocker is None:
        return VenueDecision(venue=venue, decision=Decision.GO, main_blocker=None)
    blocker_names = {item.criterion for item in checks if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE", "PARTIAL"}}
    if venue == "ostium" and blocker_names.issubset(
        {
            "Ostium symbol resolved",
            "Ostium fees/OI/rollover metadata complete",
            "Liquidation reference complete",
            "Venue cost matrix",
            "Holding/rollover cost reproduced for target horizons",
        }
    ):
        return VenueDecision(venue=venue, decision=Decision.CONDITIONAL_GO_DATA_READY, main_blocker=blocker)
    if blocker in {"stale_rate at or below threshold", "tradable_rate at or above threshold"}:
        return VenueDecision(venue=venue, decision=Decision.CONDITIONAL_GO_NEEDS_LIVE_WINDOW, main_blocker=blocker)
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
        actions.append("Collect a sufficient gTrade/Ostium quote window during tradable sessions")
    if not signals_exists:
        actions.append("Provide data/research/signals.csv to run signal-driven backtests instead of quote-only fallback")
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
    if "4h-3d after-cost backtest" in blocker_set or "Holding/rollover cost reproduced for target horizons" in blocker_set:
        return Decision.NO_GO_COST
    if "stale_rate at or below threshold" in blocker_set:
        return Decision.NO_GO_STALE
    if "tradable_rate at or above threshold" in blocker_set:
        return Decision.NO_GO_SESSION
    return Decision.CONDITIONAL_GO_DATA_READY


def build_go_no_go_report(data_dir: Path) -> GoNoGoReport:
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
            result="PASS" if ostium_resolved else ("REQUIRES_PROBE" if ostium_registry.exists() else "MISSING"),
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
            evidence="docs/sis_venue_probe_handoff/docs/08_ostium_probe_spec.md",
        ),
        GoNoGoCriterion(
            criterion="Liquidation reference complete",
            result="PASS" if positions_have_liquidation_reference(ostium_positions) else "NOT_DONE",
            evidence=str(ostium_positions)
            if ostium_positions
            else "Ostium liquidationPx requires an open-position sidecar from SDK getOpenPositions",
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
    core_ready = quotes.exists() and cost_matrix.exists() and backtest_report.exists() and ostium_resolved
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
            result=_threshold_result(gtrade_cost_rows, "spread_p90_bps", maximum=MAX_SPREAD_P90_BPS),
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
            result=_threshold_result(ostium_cost_rows, "spread_p90_bps", maximum=MAX_SPREAD_P90_BPS),
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


def write_go_no_go_markdown(report: GoNoGoReport, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(
        f"| {item.criterion} | {item.result} | {item.evidence or ''} |"
        for item in report.criteria
    )
    blockers = "\n".join(f"- {item}" for item in report.blockers) or "- none"
    next_actions = "\n".join(f"- {item}" for item in report.next_actions) or "- none"
    venue_decision_rows = "\n".join(
        f"| {item.venue} | {item.decision.value} | {item.main_blocker or ''} |"
        for item in report.venue_decisions
    ) or "| none |  |  |"
    out_path.write_text(
        "\n".join(
            [
                "# Go/No-Go Report",
                "",
                "## Decision",
                "",
                f"`{report.decision.value}`",
                "",
                "## Summary",
                "",
                report.summary,
                "",
                "## Criteria",
                "",
                "| Criterion | Result | Evidence |",
                "|---|---|---|",
                rows,
                "",
                "## Venue Decisions",
                "",
                "| Venue | Decision | Main Blocker |",
                "|---|---|---|",
                venue_decision_rows,
                "",
                "## Blockers",
                "",
                blockers,
                "",
                "## Next Actions",
                "",
                next_actions,
                "",
            ]
        ),
        encoding="utf-8",
    )
