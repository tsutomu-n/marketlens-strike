from __future__ import annotations

from sis.backtest.engine.parameter_sweep import default_breakout_parameter_grid


def test_default_breakout_parameter_grid_matches_rev3() -> None:
    grid = default_breakout_parameter_grid()

    assert len(grid) == 9
    assert {"entry_lookback": 20, "exit_lookback": 10} in grid
    assert {"entry_lookback": 40, "exit_lookback": 20} in grid
