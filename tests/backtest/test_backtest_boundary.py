from __future__ import annotations

import pytest

from sis.backtest.boundary import (
    BACKTEST_NO_LIVE_CAPABILITY_BOUNDARY,
    BACKTEST_PAPER_ONLY_BOUNDARY,
    assert_backtest_paper_only_boundary,
    assert_no_live_capability_boundary,
    with_backtest_paper_only_boundary,
    with_no_live_capability_boundary,
)


def test_no_live_capability_boundary_contains_only_schema_safe_four_fields() -> None:
    assert BACKTEST_NO_LIVE_CAPABILITY_BOUNDARY == {
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
    assert "paper_only" not in BACKTEST_NO_LIVE_CAPABILITY_BOUNDARY
    assert "live_order_submitted" not in BACKTEST_NO_LIVE_CAPABILITY_BOUNDARY


def test_paper_only_boundary_extends_no_live_boundary() -> None:
    assert BACKTEST_PAPER_ONLY_BOUNDARY == {
        "paper_only": True,
        "live_order_submitted": False,
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }


def test_boundary_helpers_return_copies_and_preserve_payload_values() -> None:
    payload = {"schema_version": "example.v1", "status": "pass"}

    no_live = with_no_live_capability_boundary(payload)
    paper_only = with_backtest_paper_only_boundary(payload)

    assert no_live is not payload
    assert paper_only is not payload
    assert payload == {"schema_version": "example.v1", "status": "pass"}
    assert no_live["schema_version"] == "example.v1"
    assert "paper_only" not in no_live
    assert paper_only["paper_only"] is True
    assert paper_only["live_order_submitted"] is False


def test_boundary_assertions_reject_missing_or_wrong_values() -> None:
    assert_no_live_capability_boundary(with_no_live_capability_boundary({}))
    assert_backtest_paper_only_boundary(with_backtest_paper_only_boundary({}))

    with pytest.raises(ValueError, match="permits_live_order must be False"):
        assert_no_live_capability_boundary({"permits_live_order": True})

    with pytest.raises(ValueError, match="paper_only must be True"):
        assert_backtest_paper_only_boundary({"paper_only": False})
