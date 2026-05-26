from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from sis.execution.base import AdapterActionResult, AdapterOrderStatus
from sis.execution.live_order_policy import MicroLiveGateInput, MicroLivePolicy, evaluate_micro_live_gates
from sis.execution.trade_xyz_adapter import TradeXyzOrderIntent, TradeXyzSafetyAdapter
from sis.storage.jsonl_store import write_json


@dataclass(frozen=True)
class MicroLiveCanaryRequest:
    canonical_symbol: str
    side: str
    quantity: float
    limit_price: float
    cloid: str
    notional_usd: float
    leverage: float
    master_address: str
    subaccount_address: str | None = None


@dataclass(frozen=True)
class MicroLiveCanaryResult:
    status: str
    blocked_reasons: list[str]
    schedule_cancel: AdapterActionResult | None
    order_submit: AdapterActionResult | None
    order_status: AdapterOrderStatus | None
    cancel_result: AdapterActionResult | None
    close_result: AdapterActionResult | None
    report_path: Path | None


def _build_report_text(
    *,
    policy: MicroLivePolicy,
    request: MicroLiveCanaryRequest,
    account_state: dict,
    gate_input: MicroLiveGateInput,
    result: MicroLiveCanaryResult,
) -> str:
    lines = [
        "# Micro Live Safety Report",
        "",
        "## Policy References",
        "",
        f"- venue: {policy.venue}",
        f"- enabled: {policy.enabled}",
        f"- max_notional_usd: {policy.max_notional_usd}",
        f"- max_leverage: {policy.max_leverage}",
        f"- min_source_confidence: {policy.min_source_confidence}",
        f"- min_venue_quality_score: {policy.min_venue_quality_score}",
        f"- schedule_cancel_deadline_seconds_after_now: {policy.schedule_cancel_deadline_seconds_after_now}",
        f"- close_require_reduce_only: {policy.close_require_reduce_only}",
        "",
        "## Account References",
        "",
        f"- master_address: {request.master_address}",
        f"- subaccount_address: {request.subaccount_address or ''}",
        f"- account_equity: {account_state.get('equity')}",
        f"- account_available_cash: {account_state.get('available_cash')}",
        "",
        "## Action References",
        "",
        f"- status: {result.status}",
        f"- canonical_symbol: {request.canonical_symbol}",
        f"- cloid: {request.cloid}",
        f"- notional_usd: {request.notional_usd}",
        f"- leverage: {request.leverage}",
        f"- source_confidence: {gate_input.source_confidence}",
        f"- venue_quality_score: {gate_input.venue_quality_score}",
        f"- tracking_trade_allowed: {gate_input.tracking_trade_allowed}",
        f"- underlying_session_regular: {gate_input.underlying_session_regular}",
        f"- blocked_reasons: {', '.join(result.blocked_reasons)}",
    ]
    if result.schedule_cancel is not None:
        lines.append(f"- schedule_cancel_status: {result.schedule_cancel.status}")
    if result.order_submit is not None:
        lines.append(f"- order_submit_status: {result.order_submit.status}")
    if result.order_status is not None:
        lines.append(f"- order_status: {result.order_status.status}")
    if result.cancel_result is not None:
        lines.append(f"- cancel_status: {result.cancel_result.status}")
    if result.close_result is not None:
        lines.append(f"- close_status: {result.close_result.status}")
    return "\n".join(lines) + "\n"


def run_micro_live_canary(
    *,
    policy: MicroLivePolicy,
    adapter: TradeXyzSafetyAdapter,
    request: MicroLiveCanaryRequest,
    gate_input: MicroLiveGateInput,
    report_path: Path | None = None,
    summary_path: Path | None = None,
    now: datetime | None = None,
) -> MicroLiveCanaryResult:
    account_state = adapter.read_account_state(
        master_address=request.master_address,
        subaccount_address=request.subaccount_address,
    )
    pre_schedule_input = replace(gate_input, schedule_cancel_success=True)
    pre_schedule_reasons = evaluate_micro_live_gates(policy, pre_schedule_input)
    if pre_schedule_reasons:
        result = MicroLiveCanaryResult(
            status="blocked_preflight",
            blocked_reasons=pre_schedule_reasons,
            schedule_cancel=None,
            order_submit=None,
            order_status=None,
            cancel_result=None,
            close_result=None,
            report_path=report_path,
        )
        text = _build_report_text(
            policy=policy,
            request=request,
            account_state=account_state,
            gate_input=gate_input,
            result=result,
        )
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(text, encoding="utf-8")
        if summary_path is not None:
            write_json(
                summary_path,
                {
                    "status": result.status,
                    "blocked_reasons": result.blocked_reasons,
                    "report_path": str(report_path) if report_path is not None else None,
                },
            )
        return result

    ts_now = now or datetime.now(timezone.utc)
    deadline_ts_ms = int(
        (ts_now.timestamp() + policy.schedule_cancel_deadline_seconds_after_now) * 1000
    )
    schedule_cancel = adapter.schedule_cancel(deadline_ts_ms=deadline_ts_ms)
    schedule_gate_input = replace(
        gate_input,
        schedule_cancel_success=schedule_cancel.success,
    )
    blocked_reasons = evaluate_micro_live_gates(policy, schedule_gate_input)
    if blocked_reasons:
        result = MicroLiveCanaryResult(
            status="blocked_policy",
            blocked_reasons=blocked_reasons,
            schedule_cancel=schedule_cancel,
            order_submit=None,
            order_status=None,
            cancel_result=None,
            close_result=None,
            report_path=report_path,
        )
        text = _build_report_text(
            policy=policy,
            request=request,
            account_state=account_state,
            gate_input=schedule_gate_input,
            result=result,
        )
        if report_path is not None:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(text, encoding="utf-8")
        if summary_path is not None:
            write_json(
                summary_path,
                {
                    "status": result.status,
                    "blocked_reasons": result.blocked_reasons,
                    "report_path": str(report_path) if report_path is not None else None,
                },
            )
        return result

    order_submit = adapter.place_limit_order(
        TradeXyzOrderIntent(
            canonical_symbol=request.canonical_symbol,
            side=request.side,
            quantity=request.quantity,
            limit_price=request.limit_price,
            cloid=request.cloid,
            notional_usd=request.notional_usd,
            leverage=request.leverage,
            post_only=True,
            reduce_only=False,
            tif="Alo",
        )
    )
    if not order_submit.success:
        result = MicroLiveCanaryResult(
            status="order_rejected",
            blocked_reasons=["BLOCK_ORDER_REJECTED"],
            schedule_cancel=schedule_cancel,
            order_submit=order_submit,
            order_status=None,
            cancel_result=None,
            close_result=None,
            report_path=report_path,
        )
    else:
        order_status = adapter.order_status_by_cloid(request.cloid)
        cancel_result: AdapterActionResult | None = None
        close_result: AdapterActionResult | None = None
        status = "completed_open"
        if order_status.status.lower() in {"open", "working", "resting"}:
            cancel_result = adapter.cancel_by_cloid(request.cloid)
            status = "completed_canceled_open_order" if cancel_result.success else "cancel_failed"
        elif order_status.status.lower() == "filled":
            close_result = adapter.close_position_reduce_only(
                canonical_symbol=request.canonical_symbol,
                side=("short" if request.side.lower() == "long" else "long"),
                quantity=request.quantity,
                limit_price=request.limit_price,
                cloid=f"{request.cloid}-close",
                reduce_only=policy.close_require_reduce_only,
            )
            status = "completed_filled_close_submitted" if close_result.success else "close_failed"
        result = MicroLiveCanaryResult(
            status=status,
            blocked_reasons=[],
            schedule_cancel=schedule_cancel,
            order_submit=order_submit,
            order_status=order_status,
            cancel_result=cancel_result,
            close_result=close_result,
            report_path=report_path,
        )

    text = _build_report_text(
        policy=policy,
        request=request,
        account_state=account_state,
        gate_input=schedule_gate_input,
        result=result,
    )
    if report_path is not None:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(text, encoding="utf-8")
    if summary_path is not None:
        write_json(
            summary_path,
            {
                "status": result.status,
                "blocked_reasons": result.blocked_reasons,
                "schedule_cancel_status": (
                    result.schedule_cancel.status if result.schedule_cancel is not None else None
                ),
                "order_submit_status": result.order_submit.status if result.order_submit is not None else None,
                "order_status": result.order_status.status if result.order_status is not None else None,
                "cancel_status": result.cancel_result.status if result.cancel_result is not None else None,
                "close_status": result.close_result.status if result.close_result is not None else None,
                "report_path": str(report_path) if report_path is not None else None,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
        )
    return result
