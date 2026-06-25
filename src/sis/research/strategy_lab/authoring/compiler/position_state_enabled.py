from __future__ import annotations

from typing import Any


def _position_state_limits_enabled(spec: Any) -> bool:
    position = spec.rules.position
    order = spec.rules.order
    return position.enabled or order.reduce_only or order.reduce_only_column is not None
