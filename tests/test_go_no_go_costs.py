from __future__ import annotations

from pathlib import Path

from sis.reports.go_no_go_costs import (
    cost_matrix_rows,
    holding_cost_result,
    threshold_result,
    venue_cost_rows,
)


def test_cost_matrix_rows_returns_empty_list_for_missing_file(tmp_path: Path) -> None:
    assert cost_matrix_rows(tmp_path / "missing.csv") == []


def test_cost_matrix_rows_reads_csv_dict_rows(tmp_path: Path) -> None:
    path = tmp_path / "venue_cost_matrix.csv"
    path.write_text(
        "venue,symbol,stale_rate\ngtrade,SPY,0.0\nostium,XAU,0.1\n",
        encoding="utf-8",
    )

    assert cost_matrix_rows(path) == [
        {"venue": "gtrade", "symbol": "SPY", "stale_rate": "0.0"},
        {"venue": "ostium", "symbol": "XAU", "stale_rate": "0.1"},
    ]


def test_threshold_result_requires_values_for_every_row() -> None:
    rows = [
        {"venue": "gtrade", "symbol": "SPY", "stale_rate": ""},
        {"venue": "ostium", "symbol": "XAU", "stale_rate": "0.0"},
    ]

    assert threshold_result(rows, "stale_rate", maximum=0.05) == "MISSING"


def test_threshold_result_blocks_values_outside_maximum_or_minimum() -> None:
    assert (
        threshold_result(
            [{"venue": "gtrade", "spread_p90_bps": "26.0"}],
            "spread_p90_bps",
            maximum=25.0,
        )
        == "NO_GO"
    )
    assert (
        threshold_result(
            [{"venue": "ostium", "tradable_rate": "0.90"}],
            "tradable_rate",
            minimum=0.95,
        )
        == "NO_GO"
    )


def test_holding_cost_result_distinguishes_pass_partial_and_missing() -> None:
    complete = {
        "holding_cost_4h_bps": "1.0",
        "holding_cost_24h_bps": "2.0",
        "holding_cost_72h_bps": "3.0",
    }
    incomplete = {
        "holding_cost_4h_bps": "1.0",
        "holding_cost_24h_bps": "",
        "holding_cost_72h_bps": "3.0",
    }

    assert holding_cost_result([complete]) == "PASS"
    assert holding_cost_result([complete, incomplete]) == "PARTIAL"
    assert holding_cost_result([incomplete]) == "MISSING"
    assert holding_cost_result([]) == "MISSING"


def test_venue_cost_rows_filters_rows_by_venue() -> None:
    rows = [
        {"venue": "gtrade", "symbol": "SPY"},
        {"venue": "ostium", "symbol": "XAU"},
        {"venue": "gtrade", "symbol": "QQQ"},
    ]

    assert venue_cost_rows(rows, "gtrade") == [
        {"venue": "gtrade", "symbol": "SPY"},
        {"venue": "gtrade", "symbol": "QQQ"},
    ]
