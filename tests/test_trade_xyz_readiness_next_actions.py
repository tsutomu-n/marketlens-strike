from __future__ import annotations

from typing import Any

from sis.venues.trade_xyz import readiness_next_actions as actions


def _requirement(
    key: str,
    status: str,
    *,
    reason: str | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "status": status,
        "reason": reason,
        "details": details or {},
    }


def test_build_next_actions_records_quote_coverage_collection_details() -> None:
    requirements = [
        _requirement(
            "quote_coverage",
            "fail",
            details={
                "traceable_only": True,
                "excluded_missing_raw_payload_ref_count": 7,
                "excluded_missing_raw_payload_ref_by_symbol": {"QQQ": 7},
                "per_symbol": {
                    "SPY": {"coverage_status": "pass"},
                    "QQQ": {
                        "coverage_status": "insufficient",
                        "span_days": 2.2,
                        "min_days_required": 5.0,
                        "insufficient_reasons": ["span_days_below_min"],
                        "missing_rates": {"raw_payload_ref": 0.25},
                    },
                },
            },
        ),
    ]

    action = actions.build_next_actions(requirements)[0]

    assert action["key"] == "collect_quote_coverage"
    assert action["command"].endswith("--symbols QQQ")
    assert action["symbols"] == ["QQQ"]
    assert action["estimated_collection_days_required_by_symbol"] == {"QQQ": 3}
    assert action["estimated_max_collection_days_required"] == 3
    assert action["additional_days_required_by_symbol"] == {"QQQ": 2.8}
    assert action["insufficient_reasons_by_symbol"] == {"QQQ": ["span_days_below_min"]}
    assert action["missing_rates_by_symbol"] == {"QQQ": {"raw_payload_ref": 0.25}}
    assert action["traceable_only"] is True
    assert action["excluded_missing_raw_payload_ref_count"] == 7
    assert action["excluded_missing_raw_payload_ref_by_symbol"] == {"QQQ": 7}


def test_build_next_actions_uses_signal_candle_failed_subset(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(actions, "DEFAULT_COLLECTION_CONFIG_PATH", tmp_path / "missing.toml")
    requirements = [
        _requirement(
            "signal_candles",
            "fail",
            reason="signal candle request errors",
            details={
                "request_errors": [
                    {"canonical_symbol": "QQQ", "interval": "4h"},
                    {"canonical_symbol": "qqq", "interval": "30m"},
                ],
            },
        ),
    ]

    action = actions.build_next_actions(requirements)[0]

    assert action["key"] == "collect_signal_candles"
    assert action["reason"] == "signal candle request errors"
    assert "--symbols QQQ" in action["command"]
    assert "--intervals 30m,4h" in action["command"]
    assert "--period-days 365" in action["command"]
    assert "--request-delay-seconds 3" in action["command"]
    assert action["follow_up_command"] == "uv run sis build-trade-xyz-data-readiness"


def test_build_next_actions_preserves_order_and_filters_passing_requirements() -> None:
    requirements = [
        _requirement("reference_datasets", "pass"),
        _requirement("funding_events", "known_gap", reason="partial funding join"),
        _requirement("account_specific_fee", "known_gap", reason="account fee not collected"),
        _requirement("oracle_timestamp_provenance", "pass"),
    ]

    result = actions.build_next_actions(requirements)

    assert [item["key"] for item in result] == [
        "collect_funding_history",
        "collect_account_fee",
    ]
    assert result[0]["command"] == "uv run sis build-trade-xyz-data-bundle --auto-funding-window"
    assert result[1]["command"] == "uv run sis collect-trade-xyz-account-fee --user-address 0x..."
    assert result[1]["follow_up_command"] == "uv run sis build-trade-xyz-data-readiness"
    assert "read-only Hyperliquid /info userFees request" in result[1]["notes"][0]
