from __future__ import annotations

from decimal import Decimal
import json
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.cash_ledger import CashLedgerEntry, build_cash_ledger
from sis.crypto_perp.events import detect_event
from sis.crypto_perp.features import EventDetectorConfig
from sis.crypto_perp.outcomes import OutcomePriceWindow, build_outcome
from sis.crypto_perp.pre_actual_cash import (
    PRE_ACTUAL_CASH_SUMMARY_ARTIFACT_NAMES,
    build_pre_actual_cash_evidence_pack,
    write_pre_actual_cash_evidence_pack,
)
from sis.crypto_perp.profit_readiness import (
    build_profit_readiness_inventory,
    build_profit_readiness_plan,
    build_profit_readiness_run,
)
from sis.crypto_perp.quality import validate_candle_series
from .test_features import make_bars, ticker


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _event():
    bars = make_bars(["100"] * 591 + ["105"], ["1000"] * 296 + ["1200"] * 296)
    event = detect_event(
        provider_id="bitget",
        native_symbol="BTCUSDT",
        canonical_symbol="BTCUSDT",
        bars=bars,
        ticker=ticker(),
        quality_report=validate_candle_series(bars, interval="15m"),
        universe_snapshot_id="universe-1",
        market_snapshot_id="market-1",
        detector_config=EventDetectorConfig(),
    )
    assert event is not None
    return event


def _outcome(event_id: str):
    return build_outcome(
        event_id=event_id,
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


def _flat_outcome(event_id: str):
    return build_outcome(
        event_id=event_id,
        settled_at="2026-06-21T06:00:00Z",
        horizons=[
            OutcomePriceWindow(
                horizon_minutes=60,
                matured=True,
                reference_price=Decimal("100"),
                close_price=Decimal("100"),
                high_price=Decimal("100"),
                low_price=Decimal("100"),
            )
        ],
    )


def _write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if hasattr(payload, "model_dump"):
        payload = payload.model_dump(mode="json")
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _schema(name: str) -> dict[str, object]:
    return json.loads((REPO_ROOT / "schemas" / name).read_text(encoding="utf-8"))


def test_inventory_blocks_dogfood_only_and_records_bad_json(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "status.json",
        {"schema_version": "crypto_perp_truth_cycle_status.v1", "artifact_id": "status-1"},
    )
    (tmp_path / "broken.json").write_text("{", encoding="utf-8")

    inventory = build_profit_readiness_inventory(
        data_dir=tmp_path, created_at="2026-06-21T07:00:00Z"
    )

    assert inventory.inventory_status == "BLOCKED_MISSING_EVENT_OR_OUTCOME"
    assert inventory.summary["event_count"] == 0
    assert inventory.summary["outcome_count"] == 0
    assert inventory.summary["dogfood_status_viewer_count"] == 1
    assert inventory.summary["invalid_json_count"] == 1
    assert "BLOCKED_MISSING_EVENT_OR_OUTCOME" in inventory.known_gaps

    schema = _schema("crypto_perp_profit_readiness_inventory.v1.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(inventory.model_dump(mode="json"))


def test_inventory_and_plan_emit_single_candidate_command(tmp_path: Path) -> None:
    event = _event()
    outcome = _outcome(event.event_id)
    event_path = _write_json(tmp_path / "event.json", event)
    outcome_path = _write_json(tmp_path / "outcome.json", outcome)

    inventory = build_profit_readiness_inventory(
        data_dir=tmp_path, created_at="2026-06-21T07:00:00Z"
    )
    plan = build_profit_readiness_plan(
        inventory=inventory, created_at="2026-06-21T07:00:00Z", out_dir=tmp_path / "run"
    )

    assert inventory.inventory_status == "READY_FOR_LOCAL_PLAN"
    assert inventory.summary["has_real_event_and_outcome"] is True
    assert plan.plan_status == "READY_FOR_LOCAL_RUN"
    assert plan.event_path == event_path.as_posix()
    assert plan.outcome_path == outcome_path.as_posix()
    assert "crypto-perp-profit-readiness-run-local" in plan.runnable_commands[0]

    schema = _schema("crypto_perp_profit_readiness_plan.v1.schema.json")
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(plan.model_dump(mode="json"))


def test_inventory_classifies_profit_readiness_run_manifest(tmp_path: Path) -> None:
    event = _event()
    outcome = _outcome(event.event_id)
    event_path = _write_json(tmp_path / "event.json", event)
    outcome_path = _write_json(tmp_path / "outcome.json", outcome)
    manifest = build_profit_readiness_run(
        event=event,
        outcome=outcome,
        created_at="2026-06-21T07:00:00Z",
        out=tmp_path / "run",
        event_path=event_path,
        outcome_path=outcome_path,
        notional_usd=Decimal("100"),
    )
    _write_json(tmp_path / "run/manifest.json", manifest)

    inventory = build_profit_readiness_inventory(
        data_dir=tmp_path, created_at="2026-06-21T07:00:00Z"
    )

    assert inventory.inventory_status == "READY_FOR_LOCAL_PLAN"
    assert inventory.summary["profit_readiness_run_count"] == 1
    assert "UNKNOWN_SCHEMA_VERSION" not in inventory.known_gaps
    run_items = [item for item in inventory.items if item.category == "profit_readiness_run"]
    assert len(run_items) == 1
    assert run_items[0].artifact_id == manifest.run_id
    assert run_items[0].event_id == event.event_id


def test_inventory_classifies_known_profit_readiness_artifacts_without_unknown_gap(
    tmp_path: Path,
) -> None:
    event = _event()
    _write_json(tmp_path / "event.json", event)
    _write_json(tmp_path / "outcome.json", _outcome(event.event_id))
    known_artifacts = [
        ("inventory.json", "crypto_perp_profit_readiness_inventory.v1", "artifact_id"),
        ("plan.json", "crypto_perp_profit_readiness_plan.v1", "artifact_id"),
        ("replay_slice.json", "crypto_perp_replay_slice.v1", "slice_id"),
        ("feature_pack.json", "crypto_perp_feature_pack.v1", "feature_pack_id"),
        ("edge_score.json", "crypto_perp_edge_score.v1", "score_id"),
        ("bias_guard.json", "crypto_perp_bias_guard.v1", "guard_id"),
    ]
    for file_name, schema_version, id_key in known_artifacts:
        _write_json(
            tmp_path / "artifacts" / file_name,
            {
                "schema_version": schema_version,
                id_key: f"{file_name}-id",
                "event_id": event.event_id,
            },
        )

    inventory = build_profit_readiness_inventory(
        data_dir=tmp_path, created_at="2026-06-21T07:00:00Z"
    )

    assert "UNKNOWN_SCHEMA_VERSION" not in inventory.known_gaps
    assert inventory.summary["profit_readiness_inventory_count"] == 1
    assert inventory.summary["profit_readiness_plan_count"] == 1
    assert inventory.summary["replay_slice_count"] == 1
    assert inventory.summary["feature_pack_count"] == 1
    assert inventory.summary["edge_score_count"] == 1
    assert inventory.summary["bias_guard_count"] == 1


def test_plan_blocks_multiple_candidates(tmp_path: Path) -> None:
    event = _event()
    _write_json(tmp_path / "event-1.json", event)
    _write_json(tmp_path / "event-2.json", event.model_copy(update={"event_id": "event-2"}))
    _write_json(tmp_path / "outcome.json", _outcome(event.event_id))
    inventory = build_profit_readiness_inventory(
        data_dir=tmp_path, created_at="2026-06-21T07:00:00Z"
    )

    plan = build_profit_readiness_plan(inventory=inventory, created_at="2026-06-21T07:00:00Z")

    assert plan.plan_status == "BLOCKED_MULTIPLE_EVENT_OR_OUTCOME_CANDIDATES"
    assert "BLOCKED_MULTIPLE_EVENT_OR_OUTCOME_CANDIDATES" in plan.blockers
    assert plan.runnable_commands == []


def test_cash_ledger_cli_reads_json_and_actual_cash_rows_require_trade_entries(
    tmp_path: Path,
) -> None:
    entries = [
        CashLedgerEntry(
            entry_id="pnl-short",
            pod_id="pod-short",
            event_id="event-1",
            entry_type="REALIZED_PNL",
            amount_usd=Decimal("-4"),
            occurred_at="2026-06-21T06:10:00Z",
        ),
        CashLedgerEntry(
            entry_id="pnl-long",
            pod_id="pod-long",
            event_id="event-1",
            entry_type="REALIZED_PNL",
            amount_usd=Decimal("7"),
            occurred_at="2026-06-21T06:10:00Z",
        ),
    ]
    entries_path = _write_json(
        tmp_path / "entries.json", [entry.model_dump(mode="json") for entry in entries]
    )
    ledger_out = tmp_path / "ledger"

    result = runner.invoke(
        app,
        [
            "crypto-perp-cash-ledger",
            "--entries",
            str(entries_path),
            "--ledger-id",
            "ledger-1",
            "--observed-at",
            "2026-06-21T07:00:00Z",
            "--out",
            str(ledger_out),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    ledger_path = ledger_out / "cash_ledger.json"
    ledger_payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    Draft202012Validator(_schema("crypto_perp_cash_ledger.v1.schema.json")).validate(ledger_payload)

    assignment = [
        {"event_id": "event-1", "action": "REVERSAL_SHORT", "pod_id": "pod-short"},
        {"event_id": "event-1", "action": "CONTINUATION_LONG", "pod_id": "pod-long"},
        {"event_id": "event-1", "action": "NO_TRADE", "pod_id": None},
    ]
    assignment_path = _write_json(tmp_path / "assignment.json", assignment)
    rows_out = tmp_path / "rows"
    rows_result = runner.invoke(
        app,
        [
            "crypto-perp-actual-cash-rows-build",
            "--ledger",
            str(ledger_path),
            "--assignment",
            str(assignment_path),
            "--out",
            str(rows_out),
        ],
    )

    assert rows_result.exit_code == 0, rows_result.stdout
    rows = [
        json.loads(line)
        for line in (rows_out / "actual_cash_rows.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert {row["cash_metric_basis"] for row in rows} == {"actual_cash"}
    assert rows[0]["actual_cash_result_usd"] == rows[0]["cash_metric_value_usd"]
    summary = json.loads((rows_out / "actual_cash_rows_summary.json").read_text(encoding="utf-8"))
    Draft202012Validator(_schema("crypto_perp_actual_cash_rows_summary.v1.schema.json")).validate(
        summary
    )

    bad_assignment_path = _write_json(
        tmp_path / "bad_assignment.json",
        [
            {"event_id": "event-1", "action": "REVERSAL_SHORT", "pod_id": "missing"},
            {"event_id": "event-1", "action": "CONTINUATION_LONG", "pod_id": "pod-long"},
            {"event_id": "event-1", "action": "NO_TRADE", "pod_id": None},
        ],
    )
    bad = runner.invoke(
        app,
        [
            "crypto-perp-actual-cash-rows-build",
            "--ledger",
            str(ledger_path),
            "--assignment",
            str(bad_assignment_path),
            "--out",
            str(tmp_path / "bad_rows"),
        ],
    )
    assert bad.exit_code == 2
    assert "has no ledger entries" in bad.stdout


def test_report_gate_and_review_packet_keep_live_permissions_false(tmp_path: Path) -> None:
    ledger = build_cash_ledger(
        ledger_id="ledger-1",
        observed_at="2026-06-21T07:00:00Z",
        entries=[
            CashLedgerEntry(
                entry_id="short",
                pod_id="pod-short",
                event_id="event-1",
                entry_type="REALIZED_PNL",
                amount_usd=Decimal("-2"),
                occurred_at="2026-06-21T06:10:00Z",
            ),
            CashLedgerEntry(
                entry_id="long",
                pod_id="pod-long",
                event_id="event-1",
                entry_type="REALIZED_PNL",
                amount_usd=Decimal("4"),
                occurred_at="2026-06-21T06:10:00Z",
            ),
        ],
    )
    ledger_path = _write_json(tmp_path / "ledger.json", ledger)
    assignment_path = _write_json(
        tmp_path / "assignment.json",
        [
            {"event_id": "event-1", "action": "REVERSAL_SHORT", "pod_id": "pod-short"},
            {"event_id": "event-1", "action": "CONTINUATION_LONG", "pod_id": "pod-long"},
            {"event_id": "event-1", "action": "NO_TRADE", "pod_id": None},
        ],
    )
    rows_result = runner.invoke(
        app,
        [
            "crypto-perp-actual-cash-rows-build",
            "--ledger",
            str(ledger_path),
            "--assignment",
            str(assignment_path),
            "--out",
            str(tmp_path / "rows"),
        ],
    )
    assert rows_result.exit_code == 0, rows_result.stdout

    report_result = runner.invoke(
        app,
        [
            "crypto-perp-actual-cash-report-gate",
            "--rows",
            str(tmp_path / "rows/actual_cash_rows.jsonl"),
            "--report-id",
            "report-1",
            "--min-events",
            "2",
            "--out",
            str(tmp_path / "report_gate"),
        ],
    )
    assert report_result.exit_code == 0, report_result.stdout
    assert "status=blocked" in report_result.stdout
    manifest = json.loads((tmp_path / "report_gate/manifest.json").read_text(encoding="utf-8"))
    Draft202012Validator(
        _schema("crypto_perp_actual_cash_report_gate_run.v1.schema.json")
    ).validate(manifest)

    packet_result = runner.invoke(
        app,
        [
            "crypto-perp-tiny-live-review-packet",
            "--report",
            str(tmp_path / "report_gate/tournament_report.json"),
            "--gate",
            str(tmp_path / "report_gate/tournament_gate.json"),
            "--out",
            str(tmp_path / "packet"),
        ],
    )
    assert packet_result.exit_code == 0, packet_result.stdout
    packet = json.loads((tmp_path / "packet/review_packet.json").read_text(encoding="utf-8"))
    assert packet["packet_status"] == "BLOCKED_BY_TOURNAMENT_GATE"
    assert packet["requires_explicit_approval"] is True
    assert packet["live_order_allowed"] is False
    assert packet["exchange_write_allowed"] is False
    Draft202012Validator(_schema("crypto_perp_tiny_live_review_packet.v1.schema.json")).validate(
        packet
    )


def _write_event_outcome_pairs(root: Path, count: int) -> None:
    template_event = _event()
    for index in range(count):
        event_id = f"event-{index:02d}"
        event = template_event.model_copy(
            update={"event_id": event_id, "artifact_id": f"event-artifact-{index:02d}"}
        )
        _write_json(root / f"events/event-{index:02d}.json", event)
        _write_json(root / f"outcomes/outcome-{index:02d}.json", _outcome(event_id))


def test_pre_actual_cash_pack_is_not_public_cli() -> None:
    result = runner.invoke(app, ["crypto-perp-pre-actual-cash-evidence-pack", "--help"])

    assert result.exit_code != 0


def test_pre_actual_cash_pack_builder_returns_required_summaries_for_ten_pairs(
    tmp_path: Path,
) -> None:
    _write_event_outcome_pairs(tmp_path / "inputs", 10)
    summaries, decision, decision_md = build_pre_actual_cash_evidence_pack(
        data_dir=tmp_path / "inputs",
        created_at="2026-06-21T07:00:00Z",
        notional_usd=Decimal("100"),
        min_events=10,
    )

    assert set(summaries) == {
        "events_summary",
        "outcomes_summary",
        "source_availability_matrix",
        "known_gaps_by_source",
        "replay_slice_summary",
        "feature_pack_summary",
        "edge_score_summary",
        "tournament_rows_v2_summary",
        "bias_guard_summary",
    }
    decision_payload = decision.model_dump(mode="json")
    decision_schema = _schema("crypto_perp_pre_actual_cash_decision.v1.schema.json")
    validator = Draft202012Validator(decision_schema)
    validator.validate(decision_payload)
    overclaim_payload = json.loads(json.dumps(decision_payload))
    overclaim_payload["non_goal_flags"]["profit_proven"] = True
    assert list(validator.iter_errors(overclaim_payload))
    extra_flag_payload = json.loads(json.dumps(decision_payload))
    extra_flag_payload["non_goal_flags"]["unexpected_flag"] = False
    assert list(validator.iter_errors(extra_flag_payload))
    assert decision.event_count == 10
    assert decision.outcome_count == 10
    assert decision.decision in {
        "KILL",
        "REVISE_EVENT_DEFINITION",
        "COLLECT_MORE_SOURCES",
        "HOLD_FOR_FUTURE_ACTUAL_CASH",
    }
    assert decision.non_goal_flags["actual_cash_used"] is False
    assert decision.non_goal_flags["profit_proven"] is False
    assert decision.non_goal_flags["tiny_live_readiness_claimed"] is False
    assert decision.tournament_summary["actual_cash_result_null_count"] == 30
    assert decision.source_gap_summary["run_manifest"]["status"] == "missing"
    assert decision.source_gap_summary["run_manifest"]["known_gap_count"] > 0
    assert decision.non_goal_flags["cost_adjusted_estimate_is_actual_cash"] is False
    assert decision.non_goal_flags["bias_guard_sample_insufficient_is_robustness_pass"] is False
    assert decision.non_goal_flags["llm_trade_decision_used"] is False
    replay_summary = summaries["replay_slice_summary"]
    assert replay_summary["event_count"] == 10
    assert replay_summary["artifact_origin_counts"] == {"recomputed_minimal": 10}
    assert replay_summary["future_data_included"] is False
    assert summaries["source_availability_matrix"]["artifact_origin_counts"] == {
        "recomputed_minimal": 10
    }
    assert (
        summaries["source_availability_matrix"]["events"][0]["artifact_gap_origin"]
        == "minimal recomputed from event/outcome only"
    )
    assert (
        summaries["source_availability_matrix"]["events"][0]["outcome_id"]
        == summaries["outcomes_summary"]["outcomes"][0]["outcome_id"]
    )
    assert decision.source_gap_summary["artifact_usage"]["per_event_artifacts"][
        "source_availability"
    ] == {"recomputed_minimal": 10}
    assert (
        decision.source_gap_summary["artifact_usage"]["tournament_rows_v2"]["artifact_origin"]
        == "recomputed_minimal"
    )
    events_summary = summaries["events_summary"]
    assert events_summary["run_manifest"]["status"] == "missing"
    assert "event_count: `10`" in decision_md
    assert "outcome_count: `10`" in decision_md
    assert "main_source_gaps:" in decision_md
    assert "selected_action_counts:" in decision_md
    assert "leader_action:" in decision_md
    assert "bias_guard_status:" in decision_md
    assert "actual_cash_used: `false`" in decision_md
    assert "profit_proven: `false`" in decision_md


def test_pre_actual_cash_pack_writer_dogfoods_ten_pairs(
    tmp_path: Path,
) -> None:
    _write_event_outcome_pairs(tmp_path / "inputs", 10)

    paths = write_pre_actual_cash_evidence_pack(
        data_dir=tmp_path / "inputs",
        out_dir=tmp_path / "pack",
        created_at="2026-06-21T07:00:00Z",
        notional_usd=Decimal("100"),
        min_events=10,
    )

    expected_files = {f"{name}.json" for name in PRE_ACTUAL_CASH_SUMMARY_ARTIFACT_NAMES} | {
        "decision.json",
        "decision.md",
    }
    assert len(expected_files) == 11
    assert set(paths) == expected_files
    assert {path.name for path in paths.values()} == expected_files
    assert all(path.exists() for path in paths.values())

    decision_payload = json.loads((tmp_path / "pack/decision.json").read_text(encoding="utf-8"))
    Draft202012Validator(_schema("crypto_perp_pre_actual_cash_decision.v1.schema.json")).validate(
        decision_payload
    )
    decision_md = (tmp_path / "pack/decision.md").read_text(encoding="utf-8")

    assert decision_payload["event_count"] == 10
    assert decision_payload["outcome_count"] == 10
    assert decision_payload["decision"] in {
        "KILL",
        "REVISE_EVENT_DEFINITION",
        "COLLECT_MORE_SOURCES",
        "HOLD_FOR_FUTURE_ACTUAL_CASH",
    }
    assert all(value is False for value in decision_payload["non_goal_flags"].values())
    assert "event_count: `10`" in decision_md
    assert "outcome_count: `10`" in decision_md
    assert "main_source_gaps:" in decision_md
    assert "selected_action_counts:" in decision_md
    assert "leader_action:" in decision_md
    assert "bias_guard_status:" in decision_md
    assert "pbo_status:" in decision_md
    assert "actual_cash_used: `false`" in decision_md
    assert "profit_proven: `false`" in decision_md
    assert "actual_cash_readiness_claimed: `false`" in decision_md
    assert "tiny_live_readiness_claimed: `false`" in decision_md
    assert "live_trading_readiness_claimed: `false`" in decision_md
    assert (
        "This pack is a pre-actual-cash candidate handling gate only. "
        "It does not prove profit, actual cash readiness, tiny-live readiness, "
        "or live trading readiness."
    ) in decision_md


def test_pre_actual_cash_pack_writer_blocks_small_sample_without_profit_claim(
    tmp_path: Path,
) -> None:
    event = _event().model_copy(update={"event_id": "event-flat", "artifact_id": "event-flat"})
    _write_json(tmp_path / "inputs/events/event.json", event)
    _write_json(tmp_path / "inputs/outcomes/outcome.json", _flat_outcome(event.event_id))
    paths = write_pre_actual_cash_evidence_pack(
        data_dir=tmp_path / "inputs",
        out_dir=tmp_path / "pack",
        created_at="2026-06-21T07:00:00Z",
        notional_usd=Decimal("100"),
        min_events=10,
    )
    expected_files = {f"{name}.json" for name in PRE_ACTUAL_CASH_SUMMARY_ARTIFACT_NAMES} | {
        "decision.json",
        "decision.md",
    }
    assert set(paths) == expected_files
    assert {path.name for path in paths.values()} == expected_files
    assert all(path.exists() for path in paths.values())

    decision_payload = json.loads((tmp_path / "pack/decision.json").read_text(encoding="utf-8"))
    Draft202012Validator(_schema("crypto_perp_pre_actual_cash_decision.v1.schema.json")).validate(
        decision_payload
    )
    decision_md = (tmp_path / "pack/decision.md").read_text(encoding="utf-8")

    assert decision_payload["decision"] == "COLLECT_MORE_SOURCES"
    assert {
        "MIN_EVENT_OUTCOME_SAMPLE_NOT_MET",
        "COST_ADJUSTED_INPUTS_MISSING",
        "DEPTH_SOURCE_MISSING",
        "OPTIONAL_FEATURES_MISSING",
        "EDGE_SELECTED_ACTION_UNKNOWN",
        "TOURNAMENT_LEADER_NO_TRADE",
        "LEADER_DOES_NOT_BEAT_NO_TRADE",
        "BIAS_GUARD_SAMPLE_INSUFFICIENT_OR_NOT_ESTIMABLE",
        "BIAS_GUARD_NOT_PASSING",
    }.issubset(set(decision_payload["reason_codes"]))
    assert decision_payload["event_count"] == 1
    assert decision_payload["outcome_count"] == 1
    assert decision_payload["source_gap_summary"]["run_manifest"]["status"] == "missing"
    assert decision_payload["edge_summary"]["selected_action_counts"] == {"UNKNOWN": 1}
    assert decision_payload["tournament_summary"]["leader_action"] == "NO_TRADE"
    assert decision_payload["tournament_summary"]["leader_beats_no_trade"] is False
    assert decision_payload["tournament_summary"]["actual_cash_result_null_count"] == 3
    assert decision_payload["bias_guard_summary"]["guard_status"] == "BLOCKED"
    assert decision_payload["bias_guard_summary"]["pbo_status"] == "NOT_ESTIMABLE"
    assert decision_payload["non_goal_flags"]["actual_cash_used"] is False
    assert decision_payload["non_goal_flags"]["profit_proven"] is False
    assert decision_payload["non_goal_flags"]["actual_cash_readiness_claimed"] is False
    assert decision_payload["non_goal_flags"]["tiny_live_readiness_claimed"] is False
    assert decision_payload["non_goal_flags"]["live_trading_readiness_claimed"] is False
    assert decision_payload["non_goal_flags"]["exchange_write_used"] is False
    assert decision_payload["non_goal_flags"]["llm_trade_decision_used"] is False
    assert decision_payload["non_goal_flags"]["public_candle_outcome_is_profit_evidence"] is False
    assert "event_count: `1`" in decision_md
    assert "outcome_count: `1`" in decision_md
    assert "selected_action_counts: `{'UNKNOWN': 1}`" in decision_md
    assert "leader_action: `NO_TRADE`" in decision_md
    assert "leader_beats_no_trade: `False`" in decision_md
    assert "bias_guard_status: `BLOCKED`" in decision_md
    assert "pbo_status: `NOT_ESTIMABLE`" in decision_md
    assert "actual_cash_readiness_claimed: `false`" in decision_md
    assert "tiny_live_readiness_claimed: `false`" in decision_md
    assert "live_trading_readiness_claimed: `false`" in decision_md


def test_pre_actual_cash_pack_reads_existing_run_manifest(tmp_path: Path) -> None:
    event = _event().model_copy(
        update={"event_id": "event-with-run", "artifact_id": "event-artifact-with-run"}
    )
    outcome = _outcome(event.event_id)
    event_path = _write_json(tmp_path / "inputs/events/event.json", event)
    outcome_path = _write_json(tmp_path / "inputs/outcomes/outcome.json", outcome)
    run_dir = tmp_path / "inputs/run"
    run_result = runner.invoke(
        app,
        [
            "crypto-perp-profit-readiness-run-local",
            "--event",
            str(event_path),
            "--outcome",
            str(outcome_path),
            "--out",
            str(run_dir),
            "--notional-usd",
            "100",
        ],
    )
    assert run_result.exit_code == 0, run_result.stdout
    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))

    summaries, decision, _ = build_pre_actual_cash_evidence_pack(
        data_dir=tmp_path / "inputs",
        created_at="2026-06-21T07:00:00Z",
        notional_usd=Decimal("100"),
        min_events=1,
    )

    assert summaries["source_availability_matrix"]["artifact_origin_counts"] == {"existing": 1}
    assert summaries["replay_slice_summary"]["artifact_origin_counts"] == {"existing": 1}
    assert summaries["feature_pack_summary"]["artifact_origin_counts"] == {"existing": 1}
    assert summaries["edge_score_summary"]["artifact_origin_counts"] == {"existing": 1}
    source_event = summaries["source_availability_matrix"]["events"][0]
    assert source_event["artifact_origin"] == "existing"
    assert source_event["outcome_id"] == outcome.outcome_id
    assert source_event["artifact_path"].endswith("run/source_availability.json")
    assert source_event["artifact_gap_origin"] == "existing artifact payload"
    assert summaries["tournament_rows_v2_summary"]["artifact_origin"] == "existing"
    assert summaries["tournament_rows_v2_summary"]["outcome_ids"] == [outcome.outcome_id]
    assert summaries["tournament_rows_v2_summary"]["artifact_path"].endswith(
        "run/tournament_rows_v2.json"
    )
    assert summaries["bias_guard_summary"]["artifact_origin"] == "existing"
    assert summaries["bias_guard_summary"]["event_outcome_pairs"] == [
        {"event_id": event.event_id, "outcome_id": outcome.outcome_id}
    ]
    assert summaries["bias_guard_summary"]["artifact_path"].endswith("run/bias_guard.json")
    artifact_usage = decision.source_gap_summary["artifact_usage"]
    assert artifact_usage["event_outcome_pairs"] == [
        {"event_id": event.event_id, "outcome_id": outcome.outcome_id}
    ]
    assert artifact_usage["per_event_artifacts"]["source_availability"] == {"existing": 1}
    assert artifact_usage["per_event_artifacts"]["replay_slice"] == {"existing": 1}
    assert artifact_usage["per_event_artifacts"]["feature_pack"] == {"existing": 1}
    assert artifact_usage["per_event_artifacts"]["edge_score"] == {"existing": 1}
    assert artifact_usage["tournament_rows_v2"]["artifact_origin"] == "existing"
    assert artifact_usage["bias_guard"]["artifact_origin"] == "existing"
    run_manifest = decision.source_gap_summary["run_manifest"]
    assert run_manifest["status"] == "blocked"
    assert run_manifest["existing_manifest_count"] == 1
    assert run_manifest["matched_manifest_count"] == 1
    assert run_manifest["missing_pair_count"] == 0
    assert run_manifest["existing_manifest_known_gap_count"] == len(manifest["known_gaps"])
    assert run_manifest["manifests"][0]["known_gap_count"] == len(manifest["known_gaps"])
