from __future__ import annotations

from sis.backtest.compare_completion_results import completion_artifact


def test_completion_artifact_returns_none_for_missing_payload() -> None:
    assert completion_artifact(None) is None


def test_completion_artifact_normalizes_summary_and_boundary_fields() -> None:
    assert completion_artifact(
        {
            "schema_version": "strategy_backtest_data_availability.v1",
            "status": "complete",
            "summary": "not-a-dict",
            "dependency_added": False,
            "paper_only": True,
            "permits_live_order": False,
            "live_conversion_allowed": False,
            "wallet_used": False,
            "exchange_write_used": False,
        }
    ) == {
        "schema_version": "strategy_backtest_data_availability.v1",
        "status": "complete",
        "summary": {},
        "dependency_added": False,
        "paper_only": True,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
