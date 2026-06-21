from __future__ import annotations

from decimal import Decimal

from sis.crypto_perp.calibration import (
    ActualFill,
    SimulatedFill,
    build_calibration_report,
)


def test_calibration_reports_actual_vs_simulated_bias_and_low_confidence() -> None:
    report = build_calibration_report(
        report_id="calibration-1",
        generated_at="2026-06-21T07:00:00Z",
        actual_fills=[
            ActualFill(
                event_id="event-1",
                side="buy",
                actual_vwap=Decimal("101"),
                actual_fee_usd=Decimal("-0.2"),
            )
        ],
        simulated_fills=[
            SimulatedFill(
                event_id="event-1",
                side="buy",
                simulated_vwap=Decimal("100"),
                simulated_fee_usd=Decimal("-0.1"),
            )
        ],
        min_high_confidence_fills=30,
    )

    row = report.bias_rows[0]
    assert row.event_id == "event-1"
    assert row.vwap_bias_usd == Decimal("1")
    assert row.fee_bias_usd == Decimal("-0.1")
    assert report.fill_count == 1
    assert report.calibration_confidence == "LOW"


def test_calibration_keeps_unmatched_actual_fill_visible() -> None:
    report = build_calibration_report(
        report_id="calibration-1",
        generated_at="2026-06-21T07:00:00Z",
        actual_fills=[
            ActualFill(
                event_id="event-missing",
                side="sell",
                actual_vwap=Decimal("99"),
                actual_fee_usd=Decimal("-0.2"),
            )
        ],
        simulated_fills=[],
        min_high_confidence_fills=30,
    )

    assert report.bias_rows[0].status == "MISSING_SIMULATION"
    assert report.bias_rows[0].vwap_bias_usd is None
    assert "MISSING_SIMULATION" in report.known_gaps
