from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec


def _parse_event_ts(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str) and value.strip():
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise StrategyAuthoringValidationError(
                f"Invalid event window timestamp value: {value!r}"
            ) from exc
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)
    return None


def _event_window_block_reason(row: dict[str, Any], spec: StrategyAuthoringSpec) -> str | None:
    if not spec.rules.event_windows:
        return None
    ts_value = row.get("ts")
    if not isinstance(ts_value, datetime):
        raise StrategyAuthoringValidationError(f"Unsupported event window ts value: {ts_value!r}")
    ts_signal = ts_value if ts_value.tzinfo is not None else ts_value.replace(tzinfo=timezone.utc)
    for event_window in spec.rules.event_windows:
        event_ts = _parse_event_ts(row.get(event_window.event_ts_column))
        reason = event_window.block_reason or f"event_window_{event_window.name}"
        if event_ts is None:
            if event_window.mode == "allow":
                return f"{reason}_missing"
            continue
        start = event_ts - timedelta(minutes=event_window.before_minutes)
        end = event_ts + timedelta(minutes=event_window.after_minutes)
        in_window = start <= ts_signal <= end
        if event_window.mode == "allow" and not in_window:
            return f"{reason}_outside"
        if event_window.mode == "block" and in_window:
            return reason
    return None


def _feature_timestamp(row: dict[str, Any]) -> datetime:
    ts = _parse_event_ts(row.get("ts"))
    if ts is None:
        raise StrategyAuthoringValidationError(f"Unsupported feature ts value: {row.get('ts')!r}")
    return ts
