from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.portfolio_exposure_groups import (
    _portfolio_exposure_groups,
)


def test_portfolio_exposure_groups_split_passthrough_and_timestamp_groups() -> None:
    hold = {"execution_symbol": "HOLD100", "side": "none", "ts_signal": "2026-01-01"}
    first = {"execution_symbol": "AAA100", "side": "long", "ts_signal": "2026-01-01"}
    second = {"execution_symbol": "BBB100", "side": "short", "ts_signal": "2026-01-02"}
    first_late = {"execution_symbol": "CCC100", "side": "long", "ts_signal": "2026-01-01"}

    passthrough, grouped = _portfolio_exposure_groups([hold, first, second, first_late])

    assert passthrough == [hold]
    assert list(grouped) == ["2026-01-01", "2026-01-02"]
    assert grouped["2026-01-01"] == [first, first_late]
    assert grouped["2026-01-02"] == [second]
