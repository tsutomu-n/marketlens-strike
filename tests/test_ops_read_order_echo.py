from __future__ import annotations

from pathlib import Path

from sis.commands.ops_read_order_echo import (
    echo_recommended_read_order,
    recommended_read_order_lines,
)


def test_recommended_read_order_lines_uses_one_based_indices() -> None:
    calls: list[Path] = []

    def fake_read_order(data_dir: Path) -> list[str]:
        calls.append(data_dir)
        return ["docs/CURRENT_STATE.md", "data/reports/operations_dashboard.md"]

    data_dir = Path("data")

    assert recommended_read_order_lines(data_dir, fake_read_order) == [
        "recommended_read_order_1=docs/CURRENT_STATE.md",
        "recommended_read_order_2=data/reports/operations_dashboard.md",
    ]
    assert calls == [data_dir]


def test_echo_recommended_read_order_prints_exact_lines(capsys) -> None:
    def fake_read_order(_data_dir: Path) -> list[str]:
        return ["docs/CURRENT_STATE.md", "data/reports/phase_gate_review.md"]

    echo_recommended_read_order(Path("data"), fake_read_order)

    assert capsys.readouterr().out.splitlines() == [
        "recommended_read_order_1=docs/CURRENT_STATE.md",
        "recommended_read_order_2=data/reports/phase_gate_review.md",
    ]
