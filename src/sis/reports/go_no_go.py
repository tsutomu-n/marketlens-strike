from __future__ import annotations

from pathlib import Path

from sis.models import Decision, GoNoGoCriterion, GoNoGoReport
from sis.storage.jsonl_store import read_json


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


def build_go_no_go_report(data_dir: Path) -> GoNoGoReport:
    gtrade_registry = data_dir / "registry/gtrade_instrument_registry.json"
    ostium_registry = data_dir / "registry/ostium_instrument_registry.json"
    quotes = data_dir / "normalized/quotes.parquet"
    cost_matrix = data_dir / "research/venue_cost_matrix.csv"
    backtest_report = data_dir / "research/backtest_report.md"
    ostium_resolved = _ostium_registry_resolved(ostium_registry)
    ostium_fees_oi_complete = _ostium_fees_oi_complete(ostium_registry)

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
            result="NOT_DONE",
            evidence="Ostium liquidationPx requires an open position from SDK getOpenPositions",
        ),
        GoNoGoCriterion(
            criterion="4h-3d after-cost backtest",
            result="PASS" if backtest_report.exists() else "MISSING",
            evidence=str(backtest_report),
        ),
    ]

    blockers = [
        item.criterion
        for item in criteria
        if item.result in {"MISSING", "REQUIRES_PROBE", "NOT_DONE"}
    ]
    decision = Decision.CONDITIONAL_GO if gtrade_registry.exists() else Decision.NO_GO
    if quotes.exists() and cost_matrix.exists() and ostium_resolved and not blockers:
        decision = Decision.GO

    return GoNoGoReport(
        decision=decision,
        summary="Implementation status report. The handoff zip is not fully implemented and this does not authorize live trading.",
        criteria=criteria,
        blockers=blockers,
        next_actions=[
            "Collect a sufficient gTrade/Ostium quote window",
            "Probe Ostium liquidation reference from read-only open position data",
            "Connect research signal generation to the backtest bridge",
        ],
    )


def write_go_no_go_markdown(report: GoNoGoReport, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rows = "\n".join(
        f"| {item.criterion} | {item.result} | {item.evidence or ''} |"
        for item in report.criteria
    )
    blockers = "\n".join(f"- {item}" for item in report.blockers) or "- none"
    next_actions = "\n".join(f"- {item}" for item in report.next_actions) or "- none"
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
