from __future__ import annotations

from datetime import datetime, timezone

from sis.execution.live_order_policy import MicroLiveGateInput, MicroLivePolicy
from sis.execution.micro_live_canary import (
    MicroLiveCanaryRequest,
    run_micro_live_canary,
)
from sis.execution.trade_xyz_adapter import TradeXyzSafetyAdapter
from sis.storage.jsonl_store import read_json


class _FakeExchange:
    def __init__(self, *, schedule_ok: bool = True, order_status: str = "open") -> None:
        self.schedule_ok = schedule_ok
        self.order_status = order_status
        self.calls: list[str] = []

    def read_account_state(
        self, master_address: str, subaccount_address: str | None = None
    ) -> dict:
        self.calls.append("read_account_state")
        return {
            "master_address": master_address,
            "subaccount_address": subaccount_address,
            "equity": 1000.0,
            "available_cash": 800.0,
        }

    def schedule_cancel(self, deadline_ts_ms: int) -> dict:
        self.calls.append("schedule_cancel")
        if self.schedule_ok:
            return {"status": "ok", "deadline_ts_ms": deadline_ts_ms}
        return {"status": "failed", "reason": "api_error"}

    def place_limit_order(self, payload: dict) -> dict:
        self.calls.append("place_limit_order")
        return {"status": "accepted", "cloid": payload["cloid"], "order_id": "ord-1"}

    def order_status_by_cloid(self, cloid: str) -> dict:
        self.calls.append("order_status_by_cloid")
        return {
            "status": self.order_status,
            "order_id": "ord-1",
            "symbol": "SP500",
            "side": "buy",
            "quantity": 1.0,
        }

    def cancel_by_cloid(self, cloid: str) -> dict:
        self.calls.append("cancel_by_cloid")
        return {"status": "canceled", "cloid": cloid}

    def close_position_reduce_only(self, payload: dict) -> dict:
        self.calls.append("close_position_reduce_only")
        return {"status": "accepted", "cloid": payload["cloid"]}


def _policy() -> MicroLivePolicy:
    return MicroLivePolicy(
        enabled=True,
        venue="trade_xyz",
        max_notional_usd=50.0,
        max_daily_loss_usd=10.0,
        max_open_positions=1,
        max_leverage=2.0,
        allowed_symbols=("SP500", "XYZ100", "NVDA", "AAPL", "MSFT"),
        prohibited_order_types=("market",),
        schedule_cancel_deadline_seconds_after_now=300,
        close_require_reduce_only=True,
    )


def _request() -> MicroLiveCanaryRequest:
    return MicroLiveCanaryRequest(
        canonical_symbol="SP500",
        side="long",
        quantity=1.0,
        limit_price=100.0,
        cloid="canary-cloid-1",
        notional_usd=25.0,
        leverage=1.5,
        master_address="0xmaster",
        subaccount_address="0xsub",
    )


def _gate_input(schedule_cancel_success: bool = False) -> MicroLiveGateInput:
    return MicroLiveGateInput(
        enable_live_flag=True,
        kill_switch_clear=True,
        schedule_cancel_success=schedule_cancel_success,
        daily_loss_remaining_usd=100.0,
        requested_notional_usd=25.0,
        requested_leverage=1.5,
        order_type="limit",
        canonical_symbol="SP500",
        underlying_session_regular=True,
        tracking_trade_allowed=True,
        source_confidence=0.80,
        venue_quality_score=0.85,
        event_window_blocked=False,
    )


def test_micro_live_canary_calls_schedule_cancel_before_order_and_cancels_open(tmp_path) -> None:
    exchange = _FakeExchange(schedule_ok=True, order_status="open")
    adapter = TradeXyzSafetyAdapter(exchange)
    report_path = tmp_path / "data/reports/micro_live_safety_report.md"
    summary_path = tmp_path / "data/ops/micro_live_canary_summary.json"
    audit_bundle_path = tmp_path / "data/ops/micro_live_audit_bundle.json"

    result = run_micro_live_canary(
        policy=_policy(),
        adapter=adapter,
        request=_request(),
        gate_input=_gate_input(),
        report_path=report_path,
        summary_path=summary_path,
        audit_bundle_path=audit_bundle_path,
        now=datetime(2026, 5, 26, 0, 0, tzinfo=timezone.utc),
    )

    assert result.status == "completed_canceled_open_order"
    assert exchange.calls == [
        "read_account_state",
        "schedule_cancel",
        "place_limit_order",
        "order_status_by_cloid",
        "cancel_by_cloid",
    ]
    report_text = report_path.read_text(encoding="utf-8")
    assert "Micro Live Safety Report" in report_text
    assert "Policy References" in report_text
    assert "Account References" in report_text
    assert "Action References" in report_text
    assert "schedule_cancel_status: scheduled" in report_text
    summary = read_json(summary_path)
    assert summary["status"] == "completed_canceled_open_order"
    assert summary["audit_bundle_path"] == str(audit_bundle_path)
    audit_bundle = read_json(audit_bundle_path)
    assert audit_bundle["operation"] == "micro_live_canary"
    assert audit_bundle["status"] == "completed_canceled_open_order"
    assert audit_bundle["policy"]["max_notional_usd"] == 50.0
    assert audit_bundle["request"]["cloid"] == "canary-cloid-1"


def test_micro_live_canary_closes_filled_position_with_reduce_only() -> None:
    exchange = _FakeExchange(schedule_ok=True, order_status="filled")
    adapter = TradeXyzSafetyAdapter(exchange)

    result = run_micro_live_canary(
        policy=_policy(),
        adapter=adapter,
        request=_request(),
        gate_input=_gate_input(),
    )

    assert result.status == "completed_filled_close_submitted"
    assert result.close_result is not None
    assert result.close_result.success is True
    assert "close_position_reduce_only" in exchange.calls


def test_micro_live_canary_blocks_when_schedule_cancel_fails() -> None:
    exchange = _FakeExchange(schedule_ok=False, order_status="open")
    adapter = TradeXyzSafetyAdapter(exchange)

    result = run_micro_live_canary(
        policy=_policy(),
        adapter=adapter,
        request=_request(),
        gate_input=_gate_input(),
    )

    assert result.status == "blocked_policy"
    assert "BLOCK_SCHEDULE_CANCEL_REQUIRED" in result.blocked_reasons
    assert exchange.calls == [
        "read_account_state",
        "schedule_cancel",
    ]


def test_micro_live_canary_uses_request_notional_for_policy_gate() -> None:
    exchange = _FakeExchange(schedule_ok=True, order_status="open")
    adapter = TradeXyzSafetyAdapter(exchange)
    request = MicroLiveCanaryRequest(
        canonical_symbol="SP500",
        side="long",
        quantity=1.0,
        limit_price=100.0,
        cloid="canary-cloid-2",
        notional_usd=75.0,
        leverage=1.5,
        master_address="0xmaster",
        subaccount_address="0xsub",
    )

    result = run_micro_live_canary(
        policy=_policy(),
        adapter=adapter,
        request=request,
        gate_input=_gate_input(),
    )

    assert result.status == "blocked_preflight"
    assert "BLOCK_NOTIONAL_TOO_HIGH" in result.blocked_reasons
    assert exchange.calls == ["read_account_state"]
