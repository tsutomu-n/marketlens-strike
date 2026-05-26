from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

MIN_SOURCE_CONFIDENCE = 0.70
MIN_VENUE_QUALITY_SCORE = 0.70


@dataclass(frozen=True)
class MicroLivePolicy:
    enabled: bool
    venue: str
    max_notional_usd: float
    max_daily_loss_usd: float
    max_open_positions: int
    max_leverage: float
    allowed_symbols: tuple[str, ...]
    prohibited_order_types: tuple[str, ...]
    schedule_cancel_deadline_seconds_after_now: int
    close_require_reduce_only: bool
    min_source_confidence: float = MIN_SOURCE_CONFIDENCE
    min_venue_quality_score: float = MIN_VENUE_QUALITY_SCORE


@dataclass(frozen=True)
class MicroLiveGateInput:
    enable_live_flag: bool
    kill_switch_clear: bool
    schedule_cancel_success: bool
    daily_loss_remaining_usd: float
    requested_notional_usd: float
    requested_leverage: float
    order_type: str
    canonical_symbol: str
    underlying_session_regular: bool
    tracking_trade_allowed: bool
    source_confidence: float
    venue_quality_score: float
    open_positions_count: int = 0
    event_window_blocked: bool = False


def load_micro_live_policy(
    path: Path = Path("configs/micro_live_policy.yaml"),
) -> MicroLivePolicy:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    root = payload.get("micro_live_policy", payload) if isinstance(payload, dict) else {}
    schedule_cancel = root.get("schedule_cancel", {}) if isinstance(root, dict) else {}
    close = root.get("close", {}) if isinstance(root, dict) else {}
    allowed_symbols = root.get("allowed_symbols", [])
    prohibited_order_types = root.get("prohibited_order_types", [])
    return MicroLivePolicy(
        enabled=bool(root.get("enabled", False)),
        venue=str(root.get("venue", "trade_xyz")),
        max_notional_usd=float(root.get("max_notional_usd", 50.0)),
        max_daily_loss_usd=float(root.get("max_daily_loss_usd", 10.0)),
        max_open_positions=int(root.get("max_open_positions", 1)),
        max_leverage=float(root.get("max_leverage", 2.0)),
        allowed_symbols=tuple(str(symbol).upper() for symbol in allowed_symbols if str(symbol).strip()),
        prohibited_order_types=tuple(
            str(order_type).lower() for order_type in prohibited_order_types if str(order_type).strip()
        ),
        schedule_cancel_deadline_seconds_after_now=int(
            schedule_cancel.get("deadline_seconds_after_now", 300)
        ),
        close_require_reduce_only=bool(close.get("require_reduce_only", True)),
    )


def evaluate_micro_live_gates(
    policy: MicroLivePolicy,
    gate_input: MicroLiveGateInput,
) -> list[str]:
    reasons: list[str] = []
    if not policy.enabled:
        reasons.append("BLOCK_MICRO_LIVE_DISABLED")
    if not gate_input.enable_live_flag:
        reasons.append("BLOCK_CONFIRM_FLAG_REQUIRED")
    if not gate_input.kill_switch_clear:
        reasons.append("BLOCK_KILL_SWITCH_ACTIVE")
    if not gate_input.schedule_cancel_success:
        reasons.append("BLOCK_SCHEDULE_CANCEL_REQUIRED")
    if gate_input.order_type.lower() in policy.prohibited_order_types:
        reasons.append("BLOCK_ORDER_TYPE_PROHIBITED")
    if gate_input.requested_notional_usd > policy.max_notional_usd:
        reasons.append("BLOCK_NOTIONAL_TOO_HIGH")
    if gate_input.requested_leverage > policy.max_leverage:
        reasons.append("BLOCK_LEVERAGE_TOO_HIGH")
    if gate_input.open_positions_count >= policy.max_open_positions:
        reasons.append("BLOCK_MAX_OPEN_POSITIONS")
    if gate_input.daily_loss_remaining_usd < gate_input.requested_notional_usd:
        reasons.append("BLOCK_DAILY_LOSS_LIMIT")
    if policy.allowed_symbols and gate_input.canonical_symbol.upper() not in policy.allowed_symbols:
        reasons.append("BLOCK_SYMBOL_NOT_ALLOWED")
    if not gate_input.underlying_session_regular:
        reasons.append("BLOCK_UNDERLYING_NOT_REGULAR_SESSION")
    if not gate_input.tracking_trade_allowed:
        reasons.append("BLOCK_TRACKING_DISALLOWS_TRADE")
    if gate_input.source_confidence < policy.min_source_confidence:
        reasons.append("BLOCK_LOW_SOURCE_CONFIDENCE")
    if gate_input.venue_quality_score < policy.min_venue_quality_score:
        reasons.append("BLOCK_LOW_VENUE_QUALITY")
    if gate_input.event_window_blocked:
        reasons.append("BLOCK_EVENT_WINDOW")
    return list(dict.fromkeys(reasons))
