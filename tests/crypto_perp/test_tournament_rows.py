from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.cost_model import (
    CRYPTO_PERP_PROJECT_COST_MODEL_ID,
    CRYPTO_PERP_PROJECT_FUNDING_RATE_TEXT,
    CRYPTO_PERP_PROJECT_SLIPPAGE_BPS_TEXT,
    CRYPTO_PERP_PROJECT_TAKER_FEE_RATE_TEXT,
    CRYPTO_PERP_STRESS_SLIPPAGE_MULTIPLIER,
)
from sis.crypto_perp.outcomes import CryptoPerpOutcome, OutcomePriceWindow, build_outcome
from sis.crypto_perp.tournament import TournamentEventResult, build_tournament_report
from sis.crypto_perp.tournament_rows import (
    build_cost_aware_tournament_rows,
    build_tournament_rows_preview,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _outcome_path(tmp_path: Path) -> Path:
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
                market_return=Decimal("0.01"),
            )
        ],
        known_gaps=["books15_missing"],
    )
    path = tmp_path / "outcome.json"
    path.write_text(json.dumps(outcome.model_dump(mode="json")), encoding="utf-8")
    return path


def test_tournament_rows_preview_builds_three_action_rows() -> None:
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
    )

    preview = build_tournament_rows_preview(outcome=outcome, notional_usd=Decimal("25"))

    assert [row.action for row in preview.rows] == [
        "REVERSAL_SHORT",
        "CONTINUATION_LONG",
        "NO_TRADE",
    ]
    assert preview.rows[0].actual_cash_result_usd is None
    assert preview.rows[0].cash_metric_value_usd == Decimal("-1.25")
    assert preview.rows[1].actual_cash_result_usd is None
    assert preview.rows[1].cash_metric_value_usd == Decimal("1.25")
    assert preview.rows[2].actual_cash_result_usd is None
    assert preview.rows[2].cash_metric_value_usd == Decimal("0")
    assert {row.cash_metric_basis for row in preview.rows} == {"before_cost_proxy"}
    assert "OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH" in preview.known_gaps
    assert "AMBIGUOUS_HIGH_LOW_ORDERING" in preview.known_gaps


def test_crypto_perp_tournament_rows_preview_cli_writes_jsonl_and_preview(
    tmp_path: Path,
) -> None:
    outcome = _outcome_path(tmp_path)

    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-rows-preview",
            "--outcome",
            str(outcome),
            "--out",
            str(tmp_path / "rows"),
            "--notional-usd",
            "25",
            "--operator-time-minutes",
            "2",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "known_gap_count=4" in result.stdout

    preview_path = tmp_path / "rows/tournament_rows_preview.json"
    rows_path = tmp_path / "rows/tournament_rows.jsonl"
    payload = json.loads(preview_path.read_text(encoding="utf-8"))
    markdown = (tmp_path / "rows/tournament_rows_preview.md").read_text(encoding="utf-8")
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_tournament_rows_preview.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    rows = [json.loads(line) for line in rows_path.read_text(encoding="utf-8").splitlines()]
    assert {row["action"] for row in rows} == {
        "REVERSAL_SHORT",
        "CONTINUATION_LONG",
        "NO_TRADE",
    }
    assert {row["cash_metric_basis"] for row in rows} == {"before_cost_proxy"}
    assert {row["actual_cash_result_usd"] for row in rows} == {None}
    assert rows[0]["cash_metric_value_usd"] == "-1.25"
    assert "outcome_before_cost_proxy_usd" in markdown
    assert "cash_metric_basis: `before_cost_proxy`" in markdown
    assert "actual_cash" not in markdown
    assert "| action | actual_cash_result_usd |" not in markdown
    report = build_tournament_report(
        report_id="preview-report",
        generated_at="2026-06-21T07:00:00Z",
        rows=[TournamentEventResult.model_validate(row) for row in payload["rows"]],
        min_events=1,
        known_gaps=payload["known_gaps"],
    )
    assert report.tournament_status == "COMPLETE"
    assert report.actual_cash is False
    assert "OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH" in report.known_gaps


def test_tournament_rows_preview_schema_requires_all_three_actions(
    tmp_path: Path,
) -> None:
    outcome = _outcome_path(tmp_path)
    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-rows-preview",
            "--outcome",
            str(outcome),
            "--out",
            str(tmp_path / "rows"),
            "--notional-usd",
            "25",
        ],
    )
    assert result.exit_code == 0, result.stdout
    payload = json.loads((tmp_path / "rows/tournament_rows_preview.json").read_text())
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_tournament_rows_preview.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    payload["rows"][2] = dict(payload["rows"][0])

    with pytest.raises(ValidationError):
        Draft202012Validator(schema).validate(payload)


def test_crypto_perp_tournament_rows_preview_cli_rejects_unmatured_outcome(
    tmp_path: Path,
) -> None:
    outcome = build_outcome(
        event_id="event-1",
        settled_at="2026-06-21T06:00:00Z",
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=False,
                reference_price=Decimal("100"),
                close_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
            )
        ],
    )
    outcome_path = tmp_path / "outcome.json"
    outcome_path.write_text(json.dumps(outcome.model_dump(mode="json")), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-rows-preview",
            "--outcome",
            str(outcome_path),
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "matured horizon" in result.stdout


def test_cost_aware_tournament_rows_v2_separates_estimate_from_actual_cash() -> None:
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
    )

    row_set = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-27T10:00:00Z",
        notional_usd=Decimal("25"),
        fee_rate=Decimal("0.001"),
        slippage_bps=Decimal("2"),
        operator_time_minutes=Decimal("3"),
        operator_hourly_cost_usd=Decimal("60"),
    )

    assert [row.action for row in row_set.rows] == [
        "REVERSAL_SHORT",
        "CONTINUATION_LONG",
        "NO_TRADE",
    ]
    continuation = next(row for row in row_set.rows if row.action == "CONTINUATION_LONG")
    assert continuation.before_cost_proxy_usd == Decimal("1.25")
    assert continuation.actual_cash_result_usd is None
    assert continuation.cost_adjusted_cash_estimate_usd < continuation.before_cost_proxy_usd
    assert continuation.evidence_level == "cost_adjusted_estimate"
    assert "ESTIMATE_NOT_ACTUAL_CASH" in continuation.known_gaps


def test_cost_aware_tournament_rows_v2_defaults_to_project_cost_model() -> None:
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
    )

    row_set = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-27T10:00:00Z",
        notional_usd=Decimal("100"),
    )

    assumptions = row_set.summary["cost_assumptions"]
    assert assumptions == {
        "cost_model_id": CRYPTO_PERP_PROJECT_COST_MODEL_ID,
        "fee_rate": CRYPTO_PERP_PROJECT_TAKER_FEE_RATE_TEXT,
        "funding_rate": CRYPTO_PERP_PROJECT_FUNDING_RATE_TEXT,
        "slippage_bps": CRYPTO_PERP_PROJECT_SLIPPAGE_BPS_TEXT,
        "stress_slippage_multiplier": str(CRYPTO_PERP_STRESS_SLIPPAGE_MULTIPLIER),
        "actual_cash_used": False,
    }
    continuation = next(row for row in row_set.rows if row.action == "CONTINUATION_LONG")
    assert continuation.fee_estimate_usd == Decimal("0.0800")
    assert continuation.funding_estimate_usd == Decimal("0.0012500")
    assert continuation.slippage_estimate_usd == Decimal("0.02")
    assert continuation.cost_adjusted_cash_estimate_usd == Decimal("4.8987500")
    assert continuation.stress_cash_estimate_usd == Decimal("4.8787500")


def test_cost_aware_tournament_rows_v2_rejects_zero_cost_inputs() -> None:
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
    )

    with pytest.raises(ValueError, match="fee_rate must be positive"):
        build_cost_aware_tournament_rows(
            outcomes=[outcome],
            created_at="2026-06-27T10:00:00Z",
            notional_usd=Decimal("100"),
            fee_rate=Decimal("0"),
        )

    with pytest.raises(ValueError, match="slippage_bps must be positive"):
        build_cost_aware_tournament_rows(
            outcomes=[outcome],
            created_at="2026-06-27T10:00:00Z",
            notional_usd=Decimal("100"),
            slippage_bps=Decimal("0"),
        )


def test_crypto_perp_tournament_rows_v2_cli_uses_project_cost_defaults(tmp_path: Path) -> None:
    outcome = _outcome_path(tmp_path)

    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-rows-v2",
            "--outcome",
            str(outcome),
            "--out",
            str(tmp_path / "rows-v2"),
            "--notional-usd",
            "100",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads((tmp_path / "rows-v2/tournament_rows_v2.json").read_text())
    assert payload["summary"]["cost_assumptions"] == {
        "cost_model_id": CRYPTO_PERP_PROJECT_COST_MODEL_ID,
        "fee_rate": CRYPTO_PERP_PROJECT_TAKER_FEE_RATE_TEXT,
        "funding_rate": CRYPTO_PERP_PROJECT_FUNDING_RATE_TEXT,
        "slippage_bps": CRYPTO_PERP_PROJECT_SLIPPAGE_BPS_TEXT,
        "stress_slippage_multiplier": str(CRYPTO_PERP_STRESS_SLIPPAGE_MULTIPLIER),
        "actual_cash_used": False,
    }


def test_cost_aware_tournament_rows_v2_schema_accepts_artifact(tmp_path: Path) -> None:
    outcome_payload = json.loads(_outcome_path(tmp_path).read_text(encoding="utf-8"))
    outcome = CryptoPerpOutcome.model_validate(outcome_payload)
    row_set = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-27T10:00:00Z",
        notional_usd=Decimal("25"),
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_tournament_rows.v2.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(row_set.model_dump(mode="json"))


def test_tournament_report_cli_rejects_cost_aware_estimate_rows(
    tmp_path: Path,
) -> None:
    outcome_payload = json.loads(_outcome_path(tmp_path).read_text(encoding="utf-8"))
    outcome = CryptoPerpOutcome.model_validate(outcome_payload)
    row_set = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at="2026-06-27T10:00:00Z",
        notional_usd=Decimal("25"),
    )
    rows_path = tmp_path / "tournament_rows_v2.json"
    rows_path.write_text(json.dumps(row_set.model_dump(mode="json")), encoding="utf-8")

    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-report",
            "--rows",
            str(rows_path),
            "--out",
            str(tmp_path / "report"),
            "--min-events",
            "1",
        ],
    )

    assert result.exit_code == 2
    assert "PREVIEW_ROWS_NOT_ACTUAL_CASH" in result.stdout
