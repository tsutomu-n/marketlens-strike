from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from ..pack_reader import load_candidate_pack
from ..run_matrix import run_scenario_matrix

from .fixtures import write_pack


def test_scenario_matrix_contains_exactly_64_cases(tmp_path: Path) -> None:
    pack = load_candidate_pack(write_pack(tmp_path))

    rows, results = run_scenario_matrix(pack, initial_cash_usd=Decimal("3000"))

    assert len(rows) == 64
    assert len(results) == 64
    assert {row["action_policy"] for row in rows} == {
        "CURRENT_SELECTOR",
        "ALWAYS_CONTINUATION",
        "ALWAYS_REVERSAL",
        "NO_TRADE",
    }
    assert {row["max_open_positions"] for row in rows} == {1, 2, 3, None}
    assert {row["metric_scenario"] for row in rows} == {"BASE", "STRESS"}
    assert {row["same_timestamp_cash_policy"] for row in rows} == {
        "NO_SAME_TIMESTAMP_REUSE",
        "EXIT_THEN_ENTRY",
    }
