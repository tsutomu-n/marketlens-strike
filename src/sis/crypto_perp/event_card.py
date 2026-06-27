from __future__ import annotations

from typing import Any

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


def _maybe_summary_value(payload: Any, key: str) -> str | None:
    summary = getattr(payload, "summary", None)
    if not isinstance(summary, dict):
        return None
    value = summary.get(key)
    if value is None:
        return None
    return str(value)


def _extend_profit_readiness_lines(
    lines: list[EventCardLine],
    *,
    source_availability: Any | None,
    edge_score: Any | None,
    tournament_rows_v2: Any | None,
    bias_guard: Any | None,
) -> None:
    if source_availability is not None:
        lines.extend(
            [
                EventCardLine(
                    label="can_compute_cost_adjusted_estimate",
                    value=str(
                        getattr(source_availability, "can_compute_cost_adjusted_estimate", False)
                    ).lower(),
                ),
                EventCardLine(
                    label="can_compute_actual_cash",
                    value=str(getattr(source_availability, "can_compute_actual_cash", False)).lower(),
                ),
            ]
        )
    if edge_score is not None:
        lines.append(
            EventCardLine(
                label="edge_selected_action",
                value=str(getattr(edge_score, "selected_action", "UNKNOWN")),
            )
        )
        why_no_trade = getattr(edge_score, "why_no_trade", [])
        if why_no_trade:
            lines.append(EventCardLine(label="why_no_trade", value=",".join(why_no_trade)))
    if tournament_rows_v2 is not None:
        leader = _maybe_summary_value(tournament_rows_v2, "leader_action")
        if leader is not None:
            lines.append(EventCardLine(label="leader_action_estimate", value=leader))
        leader_estimate = _maybe_summary_value(
            tournament_rows_v2, "leader_cost_adjusted_cash_estimate_usd"
        )
        if leader_estimate is not None:
            lines.append(
                EventCardLine(
                    label="leader_cost_adjusted_cash_estimate_usd",
                    value=leader_estimate,
                )
            )
    if bias_guard is not None:
        lines.extend(
            [
                EventCardLine(
                    label="bias_guard_status",
                    value=str(getattr(bias_guard, "guard_status", "UNKNOWN")),
                ),
                EventCardLine(
                    label="pbo_status",
                    value=str(getattr(bias_guard, "pbo_status", "UNKNOWN")),
                ),
            ]
        )


def _extend_profit_readiness_warnings(
    warnings: list[str],
    *payloads: Any | None,
) -> list[str]:
    extended = list(warnings)
    for payload in payloads:
        if payload is None:
            continue
        for gap in getattr(payload, "known_gaps", []) or []:
            extended.append(str(gap))
        for reason in getattr(payload, "stop_reasons", []) or []:
            extended.append(str(reason))
    return list(dict.fromkeys(extended))


def build_event_card(
    event: CryptoPerpEvent,
    *,
    source_availability: Any | None = None,
    edge_score: Any | None = None,
    tournament_rows_v2: Any | None = None,
    bias_guard: Any | None = None,
) -> EventCard:
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
    _extend_profit_readiness_lines(
        lines,
        source_availability=source_availability,
        edge_score=edge_score,
        tournament_rows_v2=tournament_rows_v2,
        bias_guard=bias_guard,
    )
    warnings = _extend_profit_readiness_warnings(
        event.data_quality.reason_codes,
        source_availability,
        edge_score,
        tournament_rows_v2,
        bias_guard,
    )
    return EventCard(
        event_id=event.event_id,
        title=f"{event.native_symbol} {event.event_family}",
        status=event.status,
        lines=lines,
        warnings=warnings,
    )
