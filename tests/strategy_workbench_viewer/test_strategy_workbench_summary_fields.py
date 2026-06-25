from __future__ import annotations

from sis.strategy_workbench_viewer.summary_fields import (
    _set_compact_summary_value,
    artifact_status,
)


def test_artifact_status_prefers_direct_status_fields() -> None:
    assert artifact_status({"decision": "HOLD"}, {}) == "HOLD"


def test_artifact_status_uses_latest_status_for_case_schemas_only() -> None:
    assert (
        artifact_status(
            {"schema_version": "strategy_case_lite.v1"},
            {"latest_status": "READY_FOR_HUMAN_REVIEW"},
        )
        == "READY_FOR_HUMAN_REVIEW"
    )
    assert (
        artifact_status(
            {"schema_version": "strategy_backtest_pack.v1"},
            {"latest_status": "READY_FOR_HUMAN_REVIEW"},
        )
        is None
    )


def test_set_compact_summary_value_filters_types_and_preserves_existing_values() -> None:
    summary = {"trade_count": 3}

    _set_compact_summary_value(summary, "trade_count", 10)
    _set_compact_summary_value(summary, "strategy_id", 123)
    _set_compact_summary_value(summary, "strategy_id", "ndx-breakout")
    _set_compact_summary_value(summary, "total_return", 0.12)
    _set_compact_summary_value(summary, "paper_only", True)
    _set_compact_summary_value(summary, "live_order_submitted", "false")

    assert summary == {
        "trade_count": 3,
        "strategy_id": "ndx-breakout",
        "total_return": 0.12,
        "paper_only": True,
    }


def test_set_compact_summary_value_keeps_only_false_for_permission_like_flags() -> None:
    summary: dict[str, object] = {}

    _set_compact_summary_value(summary, "first_next_step_network_allowed", True)
    _set_compact_summary_value(summary, "first_next_step_exchange_write_allowed", False)
    _set_compact_summary_value(summary, "first_next_step_live_order_allowed", False)

    assert "first_next_step_network_allowed" not in summary
    assert summary["first_next_step_exchange_write_allowed"] is False
    assert summary["first_next_step_live_order_allowed"] is False
