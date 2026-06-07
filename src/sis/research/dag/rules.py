from __future__ import annotations


TEMPORAL_ORDER = {
    "t_prev_close": 0,
    "t_pre_open": 1,
    "t_open": 2,
    "t_after_open": 3,
    "t_after_close": 4,
}


def is_future_to_signal_edge(from_layer: str | None, to_layer: str | None) -> bool:
    if from_layer is None or to_layer is None:
        return False
    return TEMPORAL_ORDER[from_layer] > TEMPORAL_ORDER[to_layer]
