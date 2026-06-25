from __future__ import annotations

from typing import Literal


def _resolve_leg_side(base_side: str, leg_side: str) -> Literal["long", "short"]:
    if leg_side == "long":
        return "long"
    if leg_side == "short":
        return "short"
    if leg_side == "same":
        return "short" if base_side == "short" else "long"
    return "long" if base_side == "short" else "short"
