from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.tournament import TournamentEventResult, build_tournament_report


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _rows() -> list[TournamentEventResult]:
    return [
        TournamentEventResult(
            event_id="event-1",
            action="REVERSAL_SHORT",
            actual_cash_result_usd=Decimal("-10"),
            market_adjusted_return=Decimal("-0.03"),
            operator_time_minutes=Decimal("2"),
            near_miss=True,
        ),
        TournamentEventResult(
            event_id="event-2",
            action="REVERSAL_SHORT",
            actual_cash_result_usd=Decimal("5"),
            market_adjusted_return=Decimal("0.01"),
            operator_time_minutes=Decimal("1"),
        ),
        TournamentEventResult(
            event_id="event-1",
            action="CONTINUATION_LONG",
            actual_cash_result_usd=Decimal("2"),
            market_adjusted_return=Decimal("0.01"),
            operator_time_minutes=Decimal("2"),
            near_miss=True,
        ),
        TournamentEventResult(
            event_id="event-2",
            action="CONTINUATION_LONG",
            actual_cash_result_usd=Decimal("3"),
            market_adjusted_return=Decimal("0.02"),
            operator_time_minutes=Decimal("1"),
        ),
        TournamentEventResult(
            event_id="event-1",
            action="NO_TRADE",
            actual_cash_result_usd=Decimal("0"),
            market_adjusted_return=Decimal("0"),
            operator_time_minutes=Decimal("0"),
            near_miss=True,
        ),
        TournamentEventResult(
            event_id="event-2",
            action="NO_TRADE",
            actual_cash_result_usd=Decimal("0"),
            market_adjusted_return=Decimal("0"),
            operator_time_minutes=Decimal("0"),
        ),
    ]


def test_tournament_compares_actions_on_same_event_set_with_actual_cash_primary() -> None:
    report = build_tournament_report(
        report_id="tournament-1",
        generated_at="2026-06-21T07:00:00Z",
        rows=_rows(),
        min_events=2,
    )

    assert report.tournament_status == "COMPLETE"
    assert report.primary_metric == "actual_cash_result_usd"
    assert report.cash_metric_basis == "actual_cash"
    assert report.primary_metric_display_name == "actual_cash_result_usd"
    assert report.actual_cash is True
    assert report.event_set == ["event-1", "event-2"]
    assert report.leader_action == "CONTINUATION_LONG"
    assert report.summary["leader_action"] == "CONTINUATION_LONG"
    assert report.summary["cash_metric_basis"] == "actual_cash"
    assert report.summary["actual_cash"] is True
    assert report.summary["leader_cash_metric_value_usd"] == Decimal("5")
    assert report.summary["leader_actual_cash_result_usd"] == Decimal("5")

    reversal = next(score for score in report.scores if score.action == "REVERSAL_SHORT")
    continuation = next(score for score in report.scores if score.action == "CONTINUATION_LONG")
    assert reversal.actual_cash_result_usd == Decimal("-5")
    assert reversal.largest_loss_usd == Decimal("-10")
    assert reversal.near_miss_count == 1
    assert continuation.profit_concentration == Decimal("0.6")


def test_tournament_insufficient_evidence_is_inconclusive() -> None:
    report = build_tournament_report(
        report_id="tournament-1",
        generated_at="2026-06-21T07:00:00Z",
        rows=[row for row in _rows() if row.event_id == "event-1"],
        min_events=2,
    )

    assert report.tournament_status == "INCONCLUSIVE_DATA"
    assert report.leader_action is None
    assert "INCONCLUSIVE_DATA" in report.known_gaps
    assert "INSUFFICIENT_EVENT_COUNT" in report.inconclusive_reasons


def test_tournament_proxy_basis_report_is_not_actual_cash() -> None:
    rows = [row.model_copy(update={"cash_metric_basis": "before_cost_proxy"}) for row in _rows()]

    report = build_tournament_report(
        report_id="proxy-report",
        generated_at="2026-06-21T07:00:00Z",
        rows=rows,
        min_events=2,
    )

    assert report.tournament_status == "COMPLETE"
    assert report.leader_action == "CONTINUATION_LONG"
    assert report.cash_metric_basis == "before_cost_proxy"
    assert report.primary_metric_display_name == "before_cost_proxy_usd"
    assert report.actual_cash is False
    assert report.leader_cash_metric_value_usd == Decimal("5")
    assert report.leader_actual_cash_result_usd is None
    assert report.summary["actual_cash"] is False
    assert report.summary["leader_actual_cash_result_usd"] is None


def test_tournament_known_proxy_gap_overrides_row_basis_to_non_actual() -> None:
    report = build_tournament_report(
        report_id="proxy-gap-report",
        generated_at="2026-06-21T07:00:00Z",
        rows=_rows(),
        min_events=2,
        known_gaps=["OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH"],
    )

    assert report.cash_metric_basis == "before_cost_proxy"
    assert report.actual_cash is False
    assert report.leader_actual_cash_result_usd is None


def test_tournament_mixed_cash_metric_basis_is_inconclusive() -> None:
    rows = _rows()
    rows[0] = rows[0].model_copy(update={"cash_metric_basis": "before_cost_proxy"})

    report = build_tournament_report(
        report_id="mixed-report",
        generated_at="2026-06-21T07:00:00Z",
        rows=rows,
        min_events=2,
    )

    assert report.tournament_status == "INCONCLUSIVE_DATA"
    assert report.leader_action is None
    assert report.cash_metric_basis == "mixed"
    assert report.actual_cash is False
    assert "MIXED_CASH_METRIC_BASIS" in report.known_gaps
    assert "MIXED_CASH_METRIC_BASIS" in report.inconclusive_reasons


def test_tournament_rejects_mismatched_event_sets() -> None:
    rows = [row for row in _rows() if not (row.event_id == "event-2" and row.action == "NO_TRADE")]

    with pytest.raises(ValueError, match="same event set"):
        build_tournament_report(
            report_id="tournament-1",
            generated_at="2026-06-21T07:00:00Z",
            rows=rows,
            min_events=2,
        )


def test_tournament_rejects_non_positive_min_events() -> None:
    with pytest.raises(ValueError, match="min_events must be positive"):
        build_tournament_report(
            report_id="tournament-1",
            generated_at="2026-06-21T07:00:00Z",
            rows=_rows(),
            min_events=0,
        )


def test_tournament_dump_matches_schema() -> None:
    report = build_tournament_report(
        report_id="tournament-1",
        generated_at="2026-06-21T07:00:00Z",
        rows=_rows(),
        min_events=2,
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_tournament_report.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(report.model_dump(mode="json"))


def test_crypto_perp_tournament_report_cli_writes_json_and_markdown(tmp_path: Path) -> None:
    rows_path = tmp_path / "rows.jsonl"
    rows_path.write_text(
        "\n".join(json.dumps(row.model_dump(mode="json")) for row in _rows()) + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-report",
            "--rows",
            str(rows_path),
            "--out",
            str(tmp_path / "out"),
            "--report-id",
            "tournament-cli",
            "--min-events",
            "2",
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "tournament_status=COMPLETE" in result.stdout
    assert "leader_action=CONTINUATION_LONG" in result.stdout

    report_path = tmp_path / "out/tournament_report.json"
    markdown_path = tmp_path / "out/tournament_report.md"
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "crypto_perp_tournament_report.v1"
    assert payload["primary_metric"] == "actual_cash_result_usd"
    assert payload["cash_metric_basis"] == "actual_cash"
    assert payload["primary_metric_display_name"] == "actual_cash_result_usd"
    assert payload["actual_cash"] is True
    assert payload["leader_action"] == "CONTINUATION_LONG"
    assert payload["source_refs"][0]["path"] == rows_path.as_posix()
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "Crypto Perp Tournament Report" in markdown
    assert "cash_metric_basis: `actual_cash`" in markdown
    assert "actual_cash: `true`" in markdown
    assert "automatic_trading: `false`" in markdown


def test_crypto_perp_tournament_report_cli_rejects_preview_rows_json(
    tmp_path: Path,
) -> None:
    rows_path = tmp_path / "tournament_rows_preview.json"
    rows_path.write_text(
        json.dumps(
            {
                "schema_version": "crypto_perp_tournament_rows_preview.v1",
                "rows": [row.model_dump(mode="json") for row in _rows()],
                "known_gaps": [
                    "OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH",
                    "FEES_FUNDING_AND_FILL_SLIPPAGE_NOT_INCLUDED",
                ],
            }
        ),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-report",
            "--rows",
            str(rows_path),
            "--out",
            str(tmp_path / "out"),
            "--report-id",
            "preview-report",
            "--min-events",
            "2",
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "PREVIEW_ROWS_NOT_ACTUAL_CASH" in result.stdout
    assert "crypto-perp-tournament-rows-v2" in result.stdout
    assert not (tmp_path / "out/tournament_report.json").exists()


def test_crypto_perp_tournament_report_cli_rejects_non_actual_cash_jsonl(
    tmp_path: Path,
) -> None:
    rows_path = tmp_path / "rows.jsonl"
    rows = [row.model_copy(update={"cash_metric_basis": "before_cost_proxy"}) for row in _rows()]
    rows_path.write_text(
        "\n".join(json.dumps(row.model_dump(mode="json")) for row in rows) + "\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-report",
            "--rows",
            str(rows_path),
            "--out",
            str(tmp_path / "out"),
            "--report-id",
            "proxy-report",
            "--min-events",
            "2",
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "PREVIEW_ROWS_NOT_ACTUAL_CASH" in result.stdout
    assert not (tmp_path / "out/tournament_report.json").exists()


def test_crypto_perp_tournament_report_cli_rejects_mismatched_event_sets(
    tmp_path: Path,
) -> None:
    rows = [row for row in _rows() if not (row.event_id == "event-2" and row.action == "NO_TRADE")]
    rows_path = tmp_path / "rows.json"
    rows_path.write_text(
        json.dumps([row.model_dump(mode="json") for row in rows]),
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "crypto-perp-tournament-report",
            "--rows",
            str(rows_path),
            "--out",
            str(tmp_path / "out"),
            "--min-events",
            "2",
        ],
    )

    assert result.exit_code == 2
    assert "status=fail" in result.stdout
    assert "same event set" in result.stdout
