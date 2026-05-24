from __future__ import annotations

from datetime import datetime, timezone

from sis.execution.base import AdapterPositionSnapshot
from sis.ops.daily_loss_limit import evaluate_daily_loss_limit, evaluate_max_exposure
from sis.ops.healthcheck import build_healthcheck
from sis.ops.kill_switch import KillSwitch
from sis.paper.portfolio import PaperPosition
from sis.state.reconciliation import reconcile_positions
from sis.state.store import StateStore


def test_state_store_roundtrips_json_and_reconciliation_payload(tmp_path) -> None:
    store = StateStore(tmp_path / "state.sqlite")
    store.set_json("paper:last_run", {"status": "ok"})
    store.record_reconciliation("run-1", "2026-05-24T00:00:00+00:00", {"matched": 1})

    assert store.get_json("paper:last_run") == {"status": "ok"}


def test_reconcile_positions_detects_missing_entries() -> None:
    internal = [
        PaperPosition(
            venue="gtrade",
            canonical_symbol="QQQ",
            side="long",
            quantity=1.0,
            avg_entry_price=100.0,
            opened_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
            updated_at=datetime(2026, 5, 24, tzinfo=timezone.utc),
        )
    ]
    adapter = [
        AdapterPositionSnapshot(
            venue="ostium",
            canonical_symbol="SPY",
            side="long",
            quantity=2.0,
        )
    ]
    result = reconcile_positions(internal, adapter)

    assert result.matched == 0
    assert result.missing_in_adapter
    assert result.missing_in_internal


def test_kill_switch_and_healthcheck_work(tmp_path) -> None:
    kill_switch = KillSwitch(tmp_path / "kill_switch.flag")
    assert kill_switch.is_enabled() is False
    kill_switch.enable("test")
    status = build_healthcheck(
        kill_switch=kill_switch,
        decision_summary_path=tmp_path / "decision_summary.json",
        reconciliation_store_present=True,
    )

    assert kill_switch.is_enabled() is True
    assert status["kill_switch_enabled"] is True
    assert status["status"] == "degraded"


def test_daily_loss_limit_and_exposure_limit_block() -> None:
    loss = evaluate_daily_loss_limit(-150.0, 100.0)
    exposure = evaluate_max_exposure(3.0, 2.0)

    assert loss.allowed is False
    assert loss.reason == "BLOCK_DAILY_LOSS_LIMIT"
    assert exposure.allowed is False
    assert exposure.reason == "BLOCK_MAX_EXPOSURE"
