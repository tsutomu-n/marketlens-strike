from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from sis.crypto_perp.events import CryptoPerpEvent


class EventCardLine(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    label: str
    value: str


class EventCard(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    title: str
    status: str
    lines: list[EventCardLine]
    warnings: list[str]


def build_event_card(event: CryptoPerpEvent) -> EventCard:
    features = event.features_at_detection
    lines = [
        EventCardLine(label="event_family", value=event.event_family),
        EventCardLine(label="return_15m", value=features.return_15m),
        EventCardLine(label="return_60m", value=features.return_60m),
        EventCardLine(label="return_74h", value=features.return_74h),
        EventCardLine(label="recent_turnover", value=features.recent_turnover),
        EventCardLine(label="previous_turnover", value=features.previous_turnover),
        EventCardLine(label="turnover_impulse", value=features.turnover_impulse),
        EventCardLine(label="spread_bps", value=features.spread_bps),
        EventCardLine(label="funding_rate", value=features.funding_rate),
        EventCardLine(label="open_interest_raw", value=features.open_interest_raw),
    ]
    warnings = event.data_quality.reason_codes
    return EventCard(
        event_id=event.event_id,
        title=f"{event.native_symbol} {event.event_family}",
        status=event.status,
        lines=lines,
        warnings=warnings,
    )
