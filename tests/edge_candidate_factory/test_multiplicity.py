from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from sis.edge_candidate_factory.generator import (
    EdgeCandidateFactoryConfig,
    build_edge_candidate_factory_run,
)
from sis.edge_candidate_factory.multiplicity import (
    MultiplicityAccountError,
    build_trial_multiplicity_account,
)


REPO_ROOT = Path(__file__).resolve().parents[2]


def _schema(name: str) -> dict:
    return json.loads((REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def _run():
    return build_edge_candidate_factory_run(
        EdgeCandidateFactoryConfig(
            run_id="edge-multiplicity-001",
            generated_at=datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc),
            source_root="data/prep/watchdeck",
            symbols=["BTCUSDT"],
            product_type="USDT-FUTURES",
            timeframe="5m",
            families=[
                "liquidation_exhaustion_reversal",
                "spread_widening_no_trade",
                "spread_widening_no_trade",
                "funding_pressure_reversion",
            ],
            candidate_cap=2,
            venue_id="bitget",
        )
    )


def test_build_trial_multiplicity_account_counts_all_search_rows() -> None:
    run = _run()

    account = build_trial_multiplicity_account(
        account_id="multiplicity-focused-001",
        created_at=datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc),
        source_refs=run.report.source_refs,
        candidate_run_id=run.config.run_id,
        search_ledger_rows=run.search_ledger_rows,
        expected_trial_count=4,
        validation_peek_count=2,
        rerank_count=1,
    )

    assert account.candidate_count_total == 4
    assert account.candidate_count_shortlisted == 2
    assert account.candidate_count_rejected == 2
    assert account.family_count == 3
    assert account.family_trial_counts["spread_widening_no_trade"] == 2
    assert account.validation_peek_count == 2
    assert account.rerank_count == 1
    assert account.effective_trial_count_status == "NOT_ESTIMABLE"
    assert account.effective_trial_count is None
    assert account.sealed_test_used_for_selection is False
    assert account.success_only_reporting is False
    assert any("not estimated" in gap for gap in account.known_gaps)
    Draft202012Validator(_schema("trial_multiplicity_account.v1.schema.json")).validate(
        account.model_dump(mode="json", exclude_none=True)
    )


def test_build_trial_multiplicity_account_rejects_selected_only_omitted_trials() -> None:
    run = _run()

    with pytest.raises(MultiplicityAccountError, match="selected-only"):
        build_trial_multiplicity_account(
            account_id="multiplicity-focused-002",
            created_at=datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc),
            source_refs=run.report.source_refs,
            candidate_run_id=run.config.run_id,
            search_ledger_rows=run.search_ledger_rows[:2],
            expected_trial_count=4,
        )


def test_build_trial_multiplicity_account_rejects_sealed_test_selection() -> None:
    run = _run()

    with pytest.raises(MultiplicityAccountError, match="sealed_test_used_for_selection"):
        build_trial_multiplicity_account(
            account_id="multiplicity-focused-003",
            created_at=datetime(2026, 7, 2, 11, 0, tzinfo=timezone.utc),
            source_refs=run.report.source_refs,
            candidate_run_id=run.config.run_id,
            search_ledger_rows=run.search_ledger_rows,
            expected_trial_count=4,
            sealed_test_used_for_selection=True,
        )
