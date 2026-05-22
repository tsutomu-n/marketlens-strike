from __future__ import annotations

from pathlib import Path

from sis.models import Decision, GoNoGoCriterion, GoNoGoReport


def build_go_no_go_report(data_dir: Path) -> GoNoGoReport:
    gtrade_registry = data_dir / "registry/gtrade_instrument_registry.json"
    ostium_registry = data_dir / "registry/ostium_instrument_registry.json"
    quotes = data_dir / "normalized/quotes.parquet"
    cost_matrix = data_dir / "research/venue_cost_matrix.csv"

    criteria = [
        GoNoGoCriterion(
            criterion="gTrade registry generated",
            result="PASS" if gtrade_registry.exists() else "MISSING",
            evidence=str(gtrade_registry),
        ),
        GoNoGoCriterion(
            criterion="Ostium symbol resolved",
            result="REQUIRES_PROBE" if ostium_registry.exists() else "MISSING",
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
    ]

    blockers = [
        item.criterion for item in criteria if item.result in {"MISSING", "REQUIRES_PROBE"}
    ]
    decision = Decision.CONDITIONAL_GO if gtrade_registry.exists() else Decision.NO_GO
    if quotes.exists() and cost_matrix.exists() and ostium_registry.exists() and not blockers:
        decision = Decision.GO

    return GoNoGoReport(
        decision=decision,
        summary="Research scaffold status. This report does not authorize live trading.",
        criteria=criteria,
        blockers=blockers,
        next_actions=[
            "Run gTrade sidecar and collect quote JSONL",
            "Run normalize-quotes after raw quote logs exist",
            "Implement read-only Ostium symbol and price probe",
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

