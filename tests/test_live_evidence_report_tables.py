from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from sis.reports.live_evidence_report_tables import detail_markdown_lines
from sis.reports.quote_diagnostics import QuoteDiagnostic
from sis.validation.artifacts import ValidationIssue, ValidationSummary


def _base_data(*, blockers: list[str], next_actions: list[str]) -> SimpleNamespace:
    return SimpleNamespace(
        row_counts={
            "sidecar_metadata": 2,
            "sidecar_pricing": 3,
            "raw_quotes": 4,
        },
        artifacts=SimpleNamespace(
            normalized_quotes=Path("data/normalized/quotes.parquet"),
            cost_matrix=Path("data/research/venue_cost_matrix.csv"),
            backtest_metrics=Path("data/research/backtest_metrics.json"),
            go_no_go_report=Path("data/research/go_no_go_report.md"),
            evidence_card=Path("data/evidence/evidence_card_20260522.json"),
        ),
        venue_decisions=[
            {"venue": "gtrade", "decision": "GO", "main_blocker": None},
            {"venue": "ostium", "decision": "NO_GO", "main_blocker": "missing_registry"},
            "ignored",
        ],
        quote_diagnostics=[
            QuoteDiagnostic(
                venue="gtrade",
                symbol="SPY",
                stale_threshold_ms=3000,
                rows=10,
                market_open_rows=9,
                tradable_rate=0.9,
                stale_rate=0.1,
                missing_mark_price_rate=0.2,
                missing_index_price_rate=0.3,
                missing_oracle_price_rate=0.0,
                missing_funding_rate=0.0,
                missing_open_interest_rate=0.0,
                missing_spread_rate=0.0,
                l2_only_rate=0.0,
                fee_mode_unknown_rate=0.0,
                block_reason_distribution={},
                stale_missing_oracle_ts_rate=0.0,
                stale_old_oracle_ts_rate=0.0,
                market_status_unknown_rate=0.0,
                market_closed_rate=0.0,
                oracle_age_p50_ms=120,
                oracle_age_p90_ms=250,
                spread_p50_bps=1.2,
                spread_p90_bps=3.4,
            )
        ],
        cost_rows=[
            {
                "venue": "gtrade",
                "symbol": "SPY",
                "stale_rate": "0.1",
                "tradable_rate": "0.9",
                "spread_p90_bps": "3.4",
                "holding_cost_4h_bps": "0.0",
                "notes": "ok",
            }
        ],
        backtest_metrics=[
            {
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "trade_count": 2,
                "avg_trade_return": "0.01",
                "cost_drag_bps": "1.5",
                "stale_rejected_count": 1,
                "halt_rejected_count": 0,
            }
        ],
        validation=ValidationSummary(
            checked_files=2,
            issues=[ValidationIssue(path="data/evidence/bad.json", message="missing run_id")],
        ),
        blockers=blockers,
        next_actions=next_actions,
        log_tail=["line one", "line two"],
    )


def test_detail_markdown_lines_render_artifacts_tables_and_footer() -> None:
    lines = detail_markdown_lines(
        _base_data(blockers=["missing_sidecar"], next_actions=["rerun collection"])
    )

    assert lines[:13] == [
        "## Artifact Summary",
        "",
        "- sidecar_metadata_rows: `2`",
        "- sidecar_pricing_rows: `3`",
        "- raw_quote_rows: `4`",
        "- normalized_quotes: `data/normalized/quotes.parquet`",
        "- cost_matrix: `data/research/venue_cost_matrix.csv`",
        "- backtest_metrics: `data/research/backtest_metrics.json`",
        "- go_no_go_report: `data/research/go_no_go_report.md`",
        "- evidence_card: `data/evidence/evidence_card_20260522.json`",
        "",
        "## Venue Decisions",
        "",
    ]
    assert "| gtrade | GO |  |" in lines
    assert "| ostium | NO_GO | missing_registry |" in lines
    assert "| SPY | 10 | 9 | 0.9000 | 0.1000 | 0.2000 | 0.3000 | 250 | 3.4 |" in lines
    assert "| gtrade | SPY | 0.1 | 0.9 | 3.4 | 0.0 | ok |" in lines
    assert "| gtrade | SPY | 2 | 0.01 | 1.5 | 1 | 0 |" in lines
    assert "- data/evidence/bad.json: missing run_id" in lines
    assert "- missing_sidecar" in lines
    assert "- rerun collection" in lines
    assert lines[-7:] == [
        "## Log Tail",
        "",
        "```text",
        "line one",
        "line two",
        "```",
        "",
    ]


def test_detail_markdown_lines_render_none_for_empty_blockers_and_next_actions() -> None:
    lines = detail_markdown_lines(_base_data(blockers=[], next_actions=[]))

    blockers_index = lines.index("## Blockers")
    next_actions_index = lines.index("## Next Actions")

    assert lines[blockers_index : blockers_index + 4] == [
        "## Blockers",
        "",
        "- none",
        "",
    ]
    assert lines[next_actions_index : next_actions_index + 4] == [
        "## Next Actions",
        "",
        "- none",
        "",
    ]
