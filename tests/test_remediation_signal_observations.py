from __future__ import annotations

from sis.reports.remediation_signal_observations import (
    coerce_value,
    diagnostics_row_presence,
    observed_counts,
    observed_fields,
)


def test_coerce_value_handles_booleans_none_ints_backticks_and_strings() -> None:
    assert coerce_value("True") is True
    assert coerce_value("False") is False
    assert coerce_value("None") is None
    assert coerce_value("-42") == -42
    assert coerce_value("`READ_ONLY_GO`") == "READ_ONLY_GO"
    assert coerce_value("NO_GO") == "NO_GO"


def test_observed_counts_reads_stdout_and_stderr_key_value_ints() -> None:
    counts = observed_counts(
        "checked_files=3 issues=0 status=NO_GO",
        "issues=2 blocker_count=4",
    )

    assert counts == {
        "checked_files": 3,
        "issues": 2,
        "blocker_count": 4,
    }


def test_observed_fields_coerces_stdout_and_stderr_key_value_pairs() -> None:
    fields = observed_fields(
        "phase_gate_decision=NO_GO phase2_entry_allowed=False checked_files=3",
        "readiness_execution_ready=True live_evidence_run_id=run-001",
    )

    assert fields == {
        "phase_gate_decision": "NO_GO",
        "phase2_entry_allowed": False,
        "checked_files": 3,
        "readiness_execution_ready": True,
        "live_evidence_run_id": "run-001",
    }


def test_diagnostics_row_presence_reports_exact_presence_keys() -> None:
    presence = diagnostics_row_presence(
        "venue=trade_xyz symbol=BTCUSD rows=12 tradable_rate=1.0",
        "stale_rate=0.0",
    )

    assert presence == {
        "venue_present": True,
        "symbol_present": True,
        "rows_present": True,
        "tradable_rate_present": True,
        "stale_rate_present": True,
    }
