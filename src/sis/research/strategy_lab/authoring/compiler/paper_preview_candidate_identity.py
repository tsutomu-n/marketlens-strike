from __future__ import annotations

from typing import Any, Literal


def _candidate_id(*, trial_id: str, row: dict[str, Any]) -> str:
    return f"candidate-{trial_id}-{row['signal_id']}" if row else f"candidate-{trial_id}-no-signal"


def _base_status(
    *, selected: bool, row: dict[str, Any]
) -> Literal["candidate", "hold", "no_signal"]:
    return "candidate" if selected else ("no_signal" if not row else "hold")
