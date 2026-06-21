from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.outcomes import OutcomePriceWindow, build_outcome
from sis.crypto_perp.tournament import TournamentEventResult, build_tournament_report
from sis.crypto_perp.tournament_rows import build_tournament_rows_preview


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
    assert preview.rows[0].actual_cash_result_usd == Decimal("-1.25")
    assert preview.rows[1].actual_cash_result_usd == Decimal("1.25")
    assert preview.rows[2].actual_cash_result_usd == Decimal("0")
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
    report = build_tournament_report(
        report_id="preview-report",
        generated_at="2026-06-21T07:00:00Z",
        rows=[TournamentEventResult.model_validate(row) for row in payload["rows"]],
        min_events=1,
        known_gaps=payload["known_gaps"],
    )
    assert report.tournament_status == "COMPLETE"
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
