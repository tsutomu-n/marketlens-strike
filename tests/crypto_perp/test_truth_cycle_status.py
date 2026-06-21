from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.tournament import TournamentEventResult, build_tournament_report
from sis.crypto_perp.tournament_gate import build_tournament_gate
from sis.crypto_perp.truth_cycle_status import build_truth_cycle_status


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _write_json(path: Path, payload: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _ready_probe_audit(path: Path) -> Path:
    return _write_json(
        path,
        {
            "schema_version": "crypto_perp_probe_audit.v1",
            "audit_status": "READY_FOR_EVENT_REFRESH",
            "known_gaps": [],
            "summary": {
                "network_attempted": True,
                "credentials_used": False,
            },
        },
    )


def _rows() -> list[TournamentEventResult]:
    return [
        TournamentEventResult(
            event_id="event-1",
            action="REVERSAL_SHORT",
            actual_cash_result_usd=Decimal("-1"),
            market_adjusted_return=Decimal("-0.01"),
            operator_time_minutes=Decimal("1"),
        ),
        TournamentEventResult(
            event_id="event-1",
            action="CONTINUATION_LONG",
            actual_cash_result_usd=Decimal("2"),
            market_adjusted_return=Decimal("0.02"),
            operator_time_minutes=Decimal("1"),
        ),
        TournamentEventResult(
            event_id="event-1",
            action="NO_TRADE",
            actual_cash_result_usd=Decimal("0"),
            market_adjusted_return=Decimal("0"),
            operator_time_minutes=Decimal("0"),
        ),
    ]


def test_truth_cycle_status_starts_with_probe_audit() -> None:
    status = build_truth_cycle_status()

    assert status.cycle_status == "MISSING_PROBE_AUDIT"
    assert "crypto-perp-probe-audit" in status.recommended_next_command
    assert "PROBE_AUDIT_REQUIRED_BEFORE_EVENT_REFRESH" in status.stop_reasons
    assert status.next_steps[0].step_id == "resolve_stop_reasons"
    assert status.next_steps[0].live_order_allowed is False
    assert status.stage_checklist[0].stage_id == "probe_audit"
    assert status.stage_checklist[0].blocks_progress is True
    assert status.stage_checklist[0].expected_cli_option == "--probe-audit"
    assert status.boundary.exchange_write_used is False


def test_truth_cycle_status_moves_from_ready_audit_to_raw_refresh(tmp_path: Path) -> None:
    probe_audit = _ready_probe_audit(tmp_path / "probe_audit.json")

    status = build_truth_cycle_status(probe_audit_path=probe_audit)

    assert status.cycle_status == "READY_FOR_RAW_REFRESH"
    assert "crypto-perp-raw-refresh" in status.recommended_next_command
    assert status.summary["present_stage_count"] == 1
    assert status.summary["next_step_count"] == 1
    assert status.summary["stage_checklist_blocker_count"] == 1
    assert status.next_steps[0].step_id == "recommended_local_next_command"
    raw_refresh_item = next(
        item for item in status.stage_checklist if item.stage_id == "raw_refresh"
    )
    assert raw_refresh_item.blocks_progress is True
    assert raw_refresh_item.expected_cli_option == "--raw-refresh"


def test_truth_cycle_status_carries_gate_need_for_actual_cash(tmp_path: Path) -> None:
    report = build_tournament_report(
        report_id="report-1",
        generated_at="2026-06-21T09:00:00Z",
        rows=_rows(),
        min_events=1,
        known_gaps=["OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH"],
    )
    gate = build_tournament_gate(report=report, created_at="2026-06-21T09:01:00Z")
    gate_path = _write_json(tmp_path / "gate.json", gate.model_dump(mode="json"))

    status = build_truth_cycle_status(tournament_gate_path=gate_path)

    assert status.cycle_status == "NEEDS_ACTUAL_CASH"
    assert status.recommended_next_command == "REBUILD_WITH_ACTUAL_CASH"
    assert status.summary["human_summary"] == (
        "before-cost proxyやcash attribution不足があるため、actual cash basisへ作り直す。"
    )
    assert "GATE_STATUS_NEEDS_ACTUAL_CASH" in status.stop_reasons
    assert "GATE_FAILED_CONDITION_no_proxy_known_gap" in status.stop_reasons
    assert "OUTCOME_BEFORE_COST_PROXY_NOT_ACTUAL_CASH" in status.known_gaps
    assert [step.step_id for step in status.next_steps] == [
        "resolve_stop_reasons",
        "rebuild_actual_cash_basis",
    ]


def test_truth_cycle_status_marks_explicit_missing_artifact_path(tmp_path: Path) -> None:
    missing_probe_audit = tmp_path / "missing_probe_audit.json"

    status = build_truth_cycle_status(probe_audit_path=missing_probe_audit)

    assert status.cycle_status == "MISSING_PROBE_AUDIT"
    assert "PROBE_AUDIT_ARTIFACT_PATH_NOT_FOUND" in status.stop_reasons
    probe_stage = next(stage for stage in status.stages if stage.stage_id == "probe_audit")
    assert probe_stage.status == "path_not_found"
    assert probe_stage.details == {"path_exists": False}
    assert status.summary["missing_artifact_path_count"] == 1
    assert status.next_steps[0].step_id == "verify_artifact_path"
    assert status.stage_checklist[0].status == "path_not_found"
    assert status.stage_checklist[0].blocks_progress is True


def test_truth_cycle_status_schema_and_cli(tmp_path: Path) -> None:
    probe_audit = _ready_probe_audit(tmp_path / "probe_audit.json")

    result = runner.invoke(
        app,
        [
            "crypto-perp-truth-cycle-status",
            "--probe-audit",
            str(probe_audit),
            "--out",
            str(tmp_path / "status"),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "cycle_status=READY_FOR_RAW_REFRESH" in result.stdout
    assert "human_summary=probe audit は通過しているため" in result.stdout
    assert "next_step_count=1" in result.stdout
    assert "first_next_step=recommended_local_next_command" in result.stdout
    assert "stage_checklist_blocker_count=1" in result.stdout
    payload = json.loads((tmp_path / "status/truth_cycle_status.json").read_text(encoding="utf-8"))
    schema = json.loads(
        (REPO_ROOT / "schemas/crypto_perp_truth_cycle_status.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(payload)
    assert payload["next_steps"][0]["exchange_write_allowed"] is False
    assert payload["next_steps"][0]["live_order_allowed"] is False
    assert payload["stage_checklist"][0]["expected_cli_option"] == "--probe-audit"
    report = (tmp_path / "status/truth_cycle_status.md").read_text(encoding="utf-8")
    assert "human_summary:" in report
    assert "probe audit は通過しているため" in report
    assert "## Next Steps" in report
    assert "## Stage Checklist" in report
    assert "--raw-refresh" in report


def test_truth_cycle_dogfood_pack_cli_builds_status_brief_and_viewer(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "crypto-perp-truth-cycle-dogfood-pack",
            "--out",
            str(tmp_path / "data/crypto_perp/truth_cycle_dogfood"),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "cycle_status=MISSING_PROBE_AUDIT" in result.stdout
    assert "first_next_step=verify_artifact_path" in result.stdout
    assert "stage_checklist_blocker_count=1" in result.stdout
    assert "viewer_artifact_count=4" in result.stdout
    root = tmp_path / "data/crypto_perp/truth_cycle_dogfood"
    assert (root / "truth_cycle_status/truth_cycle_status.json").exists()
    pack_report = root / "dogfood_pack.md"
    daily_report = root / "reports/strategy_daily_brief/strategy_daily_brief.md"
    viewer_html = root / "reports/strategy_workbench_viewer/strategy_workbench_viewer.html"
    assert pack_report.exists()
    assert daily_report.exists()
    assert viewer_html.exists()
    pack_text = pack_report.read_text(encoding="utf-8")
    assert "## Review Order" in pack_text
    assert "## Stop Decision" in pack_text
    assert "## Next Steps" in pack_text
    assert "## Stage Checklist" in pack_text
    assert "verify_artifact_path" in pack_text
    assert "--probe-audit" in pack_text
    assert "crypto_perp_probe_audit.v1" in pack_text
    assert "live_order_allowed=`false`" in pack_text
    assert "MISSING_PROBE_AUDIT" in pack_text
    assert "stop and verify the provider probe / probe audit artifact path first" in pack_text
    daily_text = daily_report.read_text(encoding="utf-8")
    viewer_text = viewer_html.read_text(encoding="utf-8")
    assert "crypto_perp_truth_cycle_follow_up" in daily_text
    assert "verify_artifact_path" in daily_text
    assert "first stage blocker: probe_audit via --probe-audit" in daily_text
    assert "path または生成済みrun directory" in viewer_text
    assert "first_next_step" in viewer_text
    assert "first_stage_blocker" in viewer_text
    assert "first_next_step_live_order_allowed" in viewer_text
