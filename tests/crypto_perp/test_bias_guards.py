from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator

from sis.crypto_perp.bias_guards import build_bias_guard
from sis.crypto_perp.outcomes import OutcomePriceWindow, build_outcome
from sis.crypto_perp.tournament_rows import build_cost_aware_tournament_rows


REPO_ROOT = Path(__file__).resolve().parents[2]


def _rows():
    outcome = build_outcome(
        event_id="event-1",
        settled_at="2026-06-27T10:00:00Z",
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=True,
                reference_price=Decimal("100"),
                close_price=Decimal("110"),
                high_price=Decimal("111"),
                low_price=Decimal("99"),
            )
        ],
    )
    return build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-27T10:01:00Z",
        notional_usd=Decimal("25"),
    )


def test_bias_guard_reports_pbo_not_estimable_without_faking_estimate() -> None:
    row_set = _rows()

    guard = build_bias_guard(
        rows=row_set.rows,
        created_at="2026-06-27T10:02:00Z",
        min_events_for_pbo=30,
        fold_count=0,
    )

    assert guard.pbo_status == "NOT_ESTIMABLE"
    assert guard.guard_status == "BLOCKED"
    assert "PBO_NOT_ESTIMABLE_SAMPLE_INSUFFICIENT" in guard.known_gaps
    assert "BIAS_GUARD_FAILED_sample_sufficient_for_pbo" in guard.stop_reasons


def test_pbo_input_threshold_is_not_reported_as_computed_estimate() -> None:
    guard = build_bias_guard(
        rows=_rows().rows,
        created_at="2026-06-27T10:02:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        max_profit_concentration=Decimal("1"),
    )

    assert guard.pbo_status == "INPUT_THRESHOLD_MET"
    assert guard.summary["pbo_computed"] is False
    assert "PBO_NOT_COMPUTED" in guard.known_gaps


def test_negative_counterfactual_stress_is_visible_warning_not_stop_reason() -> None:
    guard = build_bias_guard(
        rows=_rows().rows,
        created_at="2026-06-27T10:02:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        max_profit_concentration=Decimal("1"),
    )

    stress_check = next(
        check for check in guard.checks if check.check_id == "stress_cash_non_negative"
    )
    assert stress_check.passed is False
    assert stress_check.severity == "warning"
    assert guard.guard_status == "PASS"
    assert "BIAS_GUARD_FAILED_stress_cash_non_negative" not in guard.stop_reasons
    assert "BIAS_GUARD_WARNING_stress_cash_non_negative" in guard.known_gaps
    assert guard.summary["failed_check_count"] == 1
    assert guard.summary["failed_error_check_count"] == 0
    assert guard.summary["failed_warning_check_count"] == 1


def test_error_severity_failure_still_blocks_when_stress_warning_also_fails() -> None:
    guard = build_bias_guard(
        rows=_rows().rows,
        created_at="2026-06-27T10:02:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        lookahead_violation=True,
        max_profit_concentration=Decimal("1"),
    )

    assert guard.guard_status == "BLOCKED"
    assert "BIAS_GUARD_FAILED_lookahead_absent" in guard.stop_reasons
    assert "BIAS_GUARD_FAILED_stress_cash_non_negative" not in guard.stop_reasons
    assert "BIAS_GUARD_WARNING_stress_cash_non_negative" in guard.known_gaps
    assert guard.summary["failed_error_check_count"] == 1
    assert guard.summary["failed_warning_check_count"] == 1


def test_bias_guard_rejects_duplicate_action_even_when_row_count_is_three_per_event() -> None:
    rows = list(_rows().rows)
    continuation = next(row for row in rows if row.action == "CONTINUATION_LONG")
    malformed = [
        continuation.model_copy(update={"action": "REVERSAL_SHORT"})
        if row.action == "NO_TRADE"
        else row
        for row in rows
    ]

    guard = build_bias_guard(
        rows=malformed,
        created_at="2026-06-27T10:02:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        max_profit_concentration=Decimal("1"),
    )

    action_check = next(
        check for check in guard.checks if check.check_id == "same_event_set_has_three_actions"
    )
    assert action_check.passed is False
    assert guard.guard_status == "BLOCKED"
    assert "BIAS_GUARD_FAILED_same_event_set_has_three_actions" in guard.stop_reasons


def test_bias_guard_schema_accepts_artifact() -> None:
    row_set = _rows()
    guard = build_bias_guard(
        rows=row_set.rows,
        created_at="2026-06-27T10:02:00Z",
        min_events_for_pbo=1,
        fold_count=2,
        max_profit_concentration=Decimal("1"),
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_bias_guard.v1.schema.json").read_text(encoding="utf-8")
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(guard.model_dump(mode="json"))
