from sis.reports.phase_gate_diagnostics import spread_threshold_for_symbol
from sis.reports.phase_gate_diagnostics import trade_xyz_diagnostic_blockers
from sis.reports.phase_gate_diagnostics import trade_xyz_diagnostic_healthy


def test_spread_threshold_for_symbol_uses_index_and_equity_defaults() -> None:
    thresholds = {"default_index": 10.0, "default_equity": 20.0, "NVDA": 15.0}

    assert spread_threshold_for_symbol("SP500", thresholds) == 10.0
    assert spread_threshold_for_symbol("XYZ100", thresholds) == 10.0
    assert spread_threshold_for_symbol("NVDA", thresholds) == 15.0
    assert spread_threshold_for_symbol("AAPL", thresholds) == 20.0
    assert spread_threshold_for_symbol("UNKNOWN", {}) == 25.0


def test_trade_xyz_diagnostic_healthy_requires_complete_zero_gap_diagnostics() -> None:
    healthy = {
        "missing_mark_price_rate": 0,
        "missing_oracle_price_rate": 0,
        "missing_funding_rate": 0,
        "missing_open_interest_rate": 0,
        "stale_rate": 0,
        "l2_only_rate": 0,
        "fee_mode_unknown_rate": 0,
        "spread_p90_bps": 9.5,
    }

    assert trade_xyz_diagnostic_healthy(healthy, "SP500", {"default_index": 10.0}) is True

    stale = {**healthy, "stale_rate": 0.1}
    assert trade_xyz_diagnostic_healthy(stale, "SP500", {"default_index": 10.0}) is False

    wide = {**healthy, "spread_p90_bps": 10.1}
    assert trade_xyz_diagnostic_healthy(wide, "SP500", {"default_index": 10.0}) is False


def test_trade_xyz_diagnostic_blockers_report_unavailable_malformed_and_rate_gaps() -> None:
    diagnostics = [
        {"symbol": "SP500", "available": False, "items": []},
        {"symbol": "XYZ100", "available": True, "items": ["bad"]},
        {
            "symbol": "NVDA",
            "available": True,
            "items": [
                {
                    "missing_mark_price_rate": 0.2,
                    "missing_oracle_price_rate": 0,
                    "missing_funding_rate": 0,
                    "missing_open_interest_rate": 0,
                    "stale_rate": 0,
                    "l2_only_rate": 0,
                    "fee_mode_unknown_rate": 0,
                    "spread_p90_bps": 16.0,
                }
            ],
        },
        {
            "symbol": "AAPL",
            "available": True,
            "items": [
                {
                    "missing_mark_price_rate": 0,
                    "missing_oracle_price_rate": 0,
                    "missing_funding_rate": 0,
                    "missing_open_interest_rate": 0,
                    "stale_rate": 0,
                    "l2_only_rate": 0,
                    "fee_mode_unknown_rate": 0,
                    "spread_p90_bps": None,
                }
            ],
        },
    ]

    assert trade_xyz_diagnostic_blockers(diagnostics, {"default_index": 10.0, "NVDA": 15.0}) == [
        "SP500:diagnostics_unavailable",
        "XYZ100:diagnostics_malformed",
        "NVDA:missing_mark_price_rate=0.2",
        "NVDA:spread_p90_bps=16.0>limit=15.0",
        "AAPL:spread_p90_bps_missing",
    ]
