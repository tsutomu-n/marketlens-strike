from __future__ import annotations

from types import MappingProxyType
from typing import Any, Mapping


BACKTEST_NO_LIVE_CAPABILITY_BOUNDARY: Mapping[str, bool] = MappingProxyType(
    {
        "permits_live_order": False,
        "live_conversion_allowed": False,
        "wallet_used": False,
        "exchange_write_used": False,
    }
)

BACKTEST_PAPER_ONLY_BOUNDARY: Mapping[str, bool] = MappingProxyType(
    {
        "paper_only": True,
        "live_order_submitted": False,
        **BACKTEST_NO_LIVE_CAPABILITY_BOUNDARY,
    }
)


def with_no_live_capability_boundary(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {**payload, **BACKTEST_NO_LIVE_CAPABILITY_BOUNDARY}


def with_backtest_paper_only_boundary(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {**payload, **BACKTEST_PAPER_ONLY_BOUNDARY}


def assert_no_live_capability_boundary(payload: Mapping[str, Any]) -> None:
    _assert_boundary(payload, BACKTEST_NO_LIVE_CAPABILITY_BOUNDARY)


def assert_backtest_paper_only_boundary(payload: Mapping[str, Any]) -> None:
    _assert_boundary(payload, BACKTEST_PAPER_ONLY_BOUNDARY)


def _assert_boundary(payload: Mapping[str, Any], expected_fields: Mapping[str, bool]) -> None:
    for field, expected in expected_fields.items():
        if payload.get(field) is not expected:
            raise ValueError(f"{field} must be {expected}")
