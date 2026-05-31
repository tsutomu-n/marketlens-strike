from __future__ import annotations


def default_breakout_parameter_grid() -> list[dict[str, int]]:
    return [
        {"entry_lookback": entry, "exit_lookback": exit_}
        for entry in (10, 20, 40)
        for exit_ in (5, 10, 20)
    ]
