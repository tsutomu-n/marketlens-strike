from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.outcomes import OutcomePriceWindow, build_outcome
from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_idea_candidates.perp_costs import (
    apply_perp_cost_estimates,
    build_perp_cost_estimate_report,
)
from sis.strategy_idea_candidates.selection_metrics import apply_selection_adjusted_metrics

from .fixtures import copy_payload, valid_candidate_set_payload
from .test_candidate_cli import _perp_input_files


runner = CliRunner()


def test_selection_adjusted_metrics_computes_bh_fdr_when_p_values_exist() -> None:
    payload = copy_payload(valid_candidate_set_payload())
    payload["candidate_inventory"][0]["raw_validation_metrics"] = {
        "validation_return": 0.03,
        "validation_p_value": 0.01,
    }
    payload["candidate_inventory"][1]["raw_validation_metrics"] = {
        "validation_return": -0.01,
        "validation_p_value": 0.20,
    }
    candidate_set = StrategyIdeaCandidateSet.model_validate(payload)

    updated, report = apply_selection_adjusted_metrics(
        candidate_set,
        generated_at="2026-06-18T12:45:00Z",
    )

    assert report.status_counts == {"AVAILABLE": 2}
    first = updated.candidate_inventory[0]
    assert first.selection_adjusted_metrics_status.value == "AVAILABLE"
    assert (
        first.raw_validation_metrics["selection_adjusted_metrics"]["benjamini_hochberg_q_value"]
        == 0.02
    )
    assert (
        "not_alpha_or_profit_proof"
        == first.raw_validation_metrics["selection_adjusted_metrics"]["proof_status"]
    )


def test_selection_adjusted_metrics_marks_missing_inputs_not_estimable() -> None:
    candidate_set = StrategyIdeaCandidateSet.model_validate(valid_candidate_set_payload())

    updated, report = apply_selection_adjusted_metrics(
        candidate_set,
        generated_at="2026-06-18T12:45:00Z",
    )

    assert report.status_counts == {"NOT_ESTIMABLE": 2}
    assert {
        candidate.selection_adjusted_metrics_status.value
        for candidate in updated.candidate_inventory
    } == {"NOT_ESTIMABLE"}
    assert "RAW_P_VALUE_MISSING_FOR_BH_FDR" in report.known_gaps


def test_perp_cost_evaluator_records_fee_funding_slippage_and_liquidation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    # Reuse the CLI fixture to keep the Perp contract shape identical to public build.
    contract_path, validation_path = _perp_input_files(tmp_path)
    result = runner.invoke(
        app,
        [
            "strategy-idea-candidates-build",
            "--contract",
            str(contract_path),
            "--validation",
            str(validation_path),
            "--profile",
            "crypto-perp-risk-taker",
            "--candidate-cap",
            "2",
            "--shortlist-count",
            "1",
            "--out",
            str(tmp_path / "data/strategy_idea_candidates/btc-perp-cost"),
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads(
        (
            tmp_path
            / "data/strategy_idea_candidates/btc-perp-cost/strategy_idea_candidate_set.json"
        ).read_text(encoding="utf-8")
    )
    candidate_set = StrategyIdeaCandidateSet.model_validate(payload)

    updated, report = apply_perp_cost_estimates(
        candidate_set,
        generated_at="2026-06-18T12:45:00Z",
    )

    assert report.estimates
    estimate = report.estimates[0]
    assert estimate.fee_rate == 0.0006
    assert estimate.round_trip_fee_usd > 0
    assert estimate.slippage_estimate_usd > 0
    assert estimate.liquidation_buffer_status == "RECORDED"
    assert estimate.actual_cash_result_usd is None
    assert (
        updated.candidate_inventory[0].raw_validation_metrics["perp_cost_estimate"][
            "actual_cash_result_usd"
        ]
        is None
    )


def test_perp_estimate_bridge_cli_writes_candidate_scoped_v2_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    contract_path, validation_path = _perp_input_files(tmp_path)
    build_result = runner.invoke(
        app,
        [
            "strategy-idea-candidates-build",
            "--contract",
            str(contract_path),
            "--validation",
            str(validation_path),
            "--profile",
            "crypto-perp-risk-taker",
            "--candidate-cap",
            "2",
            "--shortlist-count",
            "1",
            "--out",
            str(tmp_path / "data/strategy_idea_candidates/btc-perp"),
        ],
    )
    assert build_result.exit_code == 0, build_result.stdout
    outcome = build_outcome(
        event_id="event-1",
        settled_at="2026-06-21T06:00:00Z",
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=True,
                reference_price=Decimal("100"),
                close_price=Decimal("105"),
                high_price=Decimal("110"),
                low_price=Decimal("95"),
            )
        ],
        known_gaps=["fixture_outcome"],
    )
    outcome_path = tmp_path / "data/crypto_perp/outcomes/event-1.json"
    outcome_path.parent.mkdir(parents=True, exist_ok=True)
    outcome_path.write_text(json.dumps(outcome.model_dump(mode="json")), encoding="utf-8")

    bridge_result = runner.invoke(
        app,
        [
            "strategy-idea-candidates-perp-estimate",
            "--candidate-set",
            str(
                tmp_path / "data/strategy_idea_candidates/btc-perp/strategy_idea_candidate_set.json"
            ),
            "--outcome",
            str(outcome_path),
            "--out",
            str(tmp_path / "data/strategy_idea_candidates/btc-perp/perp_bridge"),
        ],
    )

    assert bridge_result.exit_code == 0, bridge_result.stdout
    assert "network_attempted=false" in bridge_result.stdout
    assert "exchange_write_used=false" in bridge_result.stdout
    manifest = json.loads(
        (
            tmp_path
            / "data/strategy_idea_candidates/btc-perp/perp_bridge/perp_estimate_bridge_manifest.json"
        ).read_text(encoding="utf-8")
    )
    assert manifest["summary"]["row_set_count"] == 1
    assert "DO_NOT_FEED_TO_CRYPTO_PERP_TOURNAMENT_REPORT_AS_ACTUAL_CASH" in manifest["known_gaps"]
    row_set_path = tmp_path / manifest["row_sets"][0]["row_set_path"]
    row_set = json.loads(row_set_path.read_text(encoding="utf-8"))
    assert {row["evidence_level"] for row in row_set["rows"]} == {"cost_adjusted_estimate"}
    assert {row["actual_cash_result_usd"] for row in row_set["rows"]} == {None}


def test_perp_cost_report_handles_no_perp_candidates() -> None:
    candidate_set = StrategyIdeaCandidateSet.model_validate(valid_candidate_set_payload())

    report = build_perp_cost_estimate_report(
        candidate_set,
        generated_at="2026-06-18T12:45:00Z",
    )

    assert report.estimates == []
    assert report.summary["estimate_count"] == 0
