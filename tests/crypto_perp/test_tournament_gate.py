from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.tournament import TournamentEventResult, build_tournament_report
from sis.crypto_perp.tournament_gate import TournamentGatePolicy, build_tournament_gate


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _rows(*, no_trade_wins: bool = False, large_loss: bool = False) -> list[TournamentEventResult]:
    continuation_first_cash = Decimal("-30") if large_loss else Decimal("6")
    continuation_second_cash = Decimal("50") if large_loss else Decimal("4")
    no_trade_cash = Decimal("12") if no_trade_wins else Decimal("0")
    return [
        TournamentEventResult(
            event_id="event-1",
            action="REVERSAL_SHORT",
            actual_cash_result_usd=Decimal("-3"),
            market_adjusted_return=Decimal("-0.03"),
            operator_time_minutes=Decimal("2"),
        ),
        TournamentEventResult(
            event_id="event-2",
            action="REVERSAL_SHORT",
            actual_cash_result_usd=Decimal("1"),
            market_adjusted_return=Decimal("0.01"),
            operator_time_minutes=Decimal("1"),
        ),
        TournamentEventResult(
            event_id="event-1",
            action="CONTINUATION_LONG",
            actual_cash_result_usd=continuation_first_cash,
            market_adjusted_return=Decimal("0.02"),
            operator_time_minutes=Decimal("2"),
        ),
        TournamentEventResult(
            event_id="event-2",
            action="CONTINUATION_LONG",
            actual_cash_result_usd=continuation_second_cash,
            market_adjusted_return=Decimal("0.02"),
            operator_time_minutes=Decimal("1"),
        ),
        TournamentEventResult(
            event_id="event-1",
            action="NO_TRADE",
            actual_cash_result_usd=no_trade_cash,
            market_adjusted_return=Decimal("0"),
            operator_time_minutes=Decimal("0"),
        ),
        TournamentEventResult(
            event_id="event-2",
            action="NO_TRADE",
            actual_cash_result_usd=Decimal("0"),
            market_adjusted_return=Decimal("0"),
            operator_time_minutes=Decimal("0"),
        ),
    ]


def _report_path(tmp_path: Path, *, known_gaps: list[str] | None = None) -> Path:
    report = build_tournament_report(
        report_id="tournament-1",
        generated_at="2026-06-21T07:00:00Z",
        rows=_rows(),
        min_events=2,
        known_gaps=known_gaps or [],
    )
    path = tmp_path / "tournament_report.json"
    path.write_text(json.dumps(report.model_dump(mode="json")), encoding="utf-8")
    return path


def test_tournament_gate_allows_human_review_for_actual_cash_report() -> None:
    report = build_tournament_report(
        report_id="tournament-1",
        generated_at="2026-06-21T07:00:00Z",
        rows=_rows(),
        min_events=2,
    )

    gate = build_tournament_gate(report=report, created_at="2026-06-21T08:00:00Z")

    assert gate.gate_status == "READY_FOR_HUMAN_TINY_LIVE_REVIEW"
    assert gate.recommended_action == "PREPARE_TINY_LIVE_APPROVAL_PACKET"
    assert not gate.failed_conditions
    assert gate.boundary.permits_live_order is False


def test_tournament_gate_blocks_proxy_rows_until_actual_cash() -> None:
    report = build_tournament_report(
        report_id="tournament-1",
        generated_at="2026-06-21T07:00:00Z",
        rows=_rows(),
        min_events=2,
        known_gaps=["OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH"],
    )

    gate = build_tournament_gate(report=report, created_at="2026-06-21T08:00:00Z")

    assert gate.gate_status == "NEEDS_ACTUAL_CASH"
    assert gate.recommended_action == "REBUILD_WITH_ACTUAL_CASH"
    assert "no_proxy_known_gap" in {condition.condition_id for condition in gate.failed_conditions}


def test_tournament_gate_blocks_non_actual_cash_basis_without_proxy_gap() -> None:
    report = build_tournament_report(
        report_id="tournament-1",
        generated_at="2026-06-21T07:00:00Z",
        rows=[row.model_copy(update={"cash_metric_basis": "before_cost_proxy"}) for row in _rows()],
        min_events=2,
    )

    gate = build_tournament_gate(report=report, created_at="2026-06-21T08:00:00Z")

    assert gate.gate_status == "NEEDS_ACTUAL_CASH"
    assert gate.recommended_action == "REBUILD_WITH_ACTUAL_CASH"
    assert "actual_cash_basis" in {condition.condition_id for condition in gate.failed_conditions}


def test_tournament_gate_revises_when_loss_threshold_fails() -> None:
    report = build_tournament_report(
        report_id="tournament-1",
        generated_at="2026-06-21T07:00:00Z",
        rows=_rows(large_loss=True),
        min_events=2,
    )

    gate = build_tournament_gate(
        report=report,
        created_at="2026-06-21T08:00:00Z",
        policy=TournamentGatePolicy(max_largest_loss_usd=Decimal("1")),
    )

    assert gate.gate_status == "REVISE_OR_RETIRE"
    assert "largest_loss_within_limit" in {
        condition.condition_id for condition in gate.failed_conditions
    }


def test_tournament_gate_blocks_when_no_trade_leads() -> None:
    report = build_tournament_report(
        report_id="tournament-1",
        generated_at="2026-06-21T07:00:00Z",
        rows=_rows(no_trade_wins=True),
        min_events=2,
    )

    gate = build_tournament_gate(report=report, created_at="2026-06-21T08:00:00Z")

    assert gate.gate_status == "HOLD_NO_TRADE_LEADS"
    assert gate.recommended_action == "KEEP_CAPTURING_NO_TRADE"


def test_tournament_gate_schema_and_cli(tmp_path: Path) -> None:
    report_path = _report_path(tmp_path)

    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-gate",
            "--report",
            str(report_path),
            "--out",
            str(tmp_path / "gate"),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "status=needs_human_approval" in result.stdout
    assert "gate_status=READY_FOR_HUMAN_TINY_LIVE_REVIEW" in result.stdout
    assert "requires_explicit_approval=true" in result.stdout
    assert "permits_live_order=false" in result.stdout
    assert "status=pass" not in result.stdout
    payload = json.loads((tmp_path / "gate/tournament_gate.json").read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_tournament_gate.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["source_refs"][0]["schema_version"] == "crypto_perp_tournament_report.v1"


def test_tournament_gate_cli_blocks_proxy_gap(tmp_path: Path) -> None:
    report_path = _report_path(tmp_path, known_gaps=["OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH"])

    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-gate",
            "--report",
            str(report_path),
            "--out",
            str(tmp_path / "gate"),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=blocked" in result.stdout
    assert "gate_status=NEEDS_ACTUAL_CASH" in result.stdout
    markdown = (tmp_path / "gate/tournament_gate.md").read_text(encoding="utf-8")
    assert "OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH" in markdown
