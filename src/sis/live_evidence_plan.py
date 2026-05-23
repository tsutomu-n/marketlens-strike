from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sis.market_calendar import SessionWindow, market_session_window


@dataclass(frozen=True)
class LiveEvidencePlan:
    venue: str
    symbols: list[str]
    windows: list[SessionWindow]
    target_start_jst: datetime

    @property
    def target_spec_jst(self) -> str:
        return self.target_start_jst.strftime("%Y-%m-%dT%H:%M")


def build_live_evidence_plan(
    symbols: list[str],
    *,
    venue: str = "gtrade",
    now: datetime | None = None,
) -> LiveEvidencePlan:
    if not symbols:
        raise ValueError("At least one symbol is required")

    windows = [market_session_window(venue, symbol, now=now) for symbol in symbols]
    target_start_jst = max(window.recommended_start_jst for window in windows)

    missed = [
        window.symbol
        for window in windows
        if target_start_jst > window.recommended_end_jst
    ]
    if missed:
        raise ValueError(
            "No overlapping recommended live window for symbols: "
            + ", ".join(sorted(missed))
        )

    return LiveEvidencePlan(
        venue=venue,
        symbols=[window.symbol for window in windows],
        windows=windows,
        target_start_jst=target_start_jst,
    )
