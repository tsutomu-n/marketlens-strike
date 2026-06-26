from __future__ import annotations

from pathlib import Path

from sis.reports.phase_gate_review_decisions import (
    PHASE2_ALLOWED_DECISIONS,
    phase2_entry_allowed,
    trade_xyz_artifacts_present,
)


def test_phase2_allowed_decisions_are_explicit_and_stable() -> None:
    assert PHASE2_ALLOWED_DECISIONS == {
        "GO",
        "CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST",
        "READ_ONLY_GO",
        "PAPER_GO",
        "CONDITIONAL_INDEX_ONLY",
    }


def test_phase2_entry_allowed_requires_all_gate_conditions() -> None:
    collector_gate = {"read_only_collector_gate_passed": True}

    for decision in PHASE2_ALLOWED_DECISIONS:
        assert (
            phase2_entry_allowed(
                strict_validation_passed=True,
                diagnostics_all_available=True,
                collector_gate=collector_gate,
                decision=decision,
            )
            is True
        )

    assert (
        phase2_entry_allowed(
            strict_validation_passed=False,
            diagnostics_all_available=True,
            collector_gate=collector_gate,
            decision="READ_ONLY_GO",
        )
        is False
    )
    assert (
        phase2_entry_allowed(
            strict_validation_passed=True,
            diagnostics_all_available=False,
            collector_gate=collector_gate,
            decision="READ_ONLY_GO",
        )
        is False
    )
    assert (
        phase2_entry_allowed(
            strict_validation_passed=True,
            diagnostics_all_available=True,
            collector_gate={"read_only_collector_gate_passed": 1},
            decision="READ_ONLY_GO",
        )
        is False
    )
    assert (
        phase2_entry_allowed(
            strict_validation_passed=True,
            diagnostics_all_available=True,
            collector_gate=collector_gate,
            decision="NO_GO",
        )
        is False
    )
    assert (
        phase2_entry_allowed(
            strict_validation_passed=True,
            diagnostics_all_available=True,
            collector_gate=collector_gate,
            decision=None,
        )
        is False
    )


def test_trade_xyz_artifacts_present_accepts_any_current_trade_xyz_artifact(
    tmp_path: Path,
) -> None:
    assert trade_xyz_artifacts_present(tmp_path) is False

    registry_path = tmp_path / "registry/trade_xyz_instrument_registry.json"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text("[]", encoding="utf-8")
    assert trade_xyz_artifacts_present(tmp_path) is True

    registry_path.unlink()
    summary_path = tmp_path / "ops/trade_xyz_quote_collection_summary.json"
    summary_path.parent.mkdir(parents=True)
    summary_path.write_text("{}", encoding="utf-8")
    assert trade_xyz_artifacts_present(tmp_path) is True

    summary_path.unlink()
    quote_path = tmp_path / "raw/quotes/trade_xyz/2026-05-27.jsonl"
    quote_path.parent.mkdir(parents=True)
    quote_path.write_text("{}\n", encoding="utf-8")
    assert trade_xyz_artifacts_present(tmp_path) is True
