from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from sis.cli import app
from sis.crypto_perp.cash_ledger import CashLedgerEntry, CashLedgerEntryType, build_cash_ledger
from sis.edge_candidates.tiny_actual_cash_measurement import (
    ProfitCoreTinyActualCashMeasurementStatus,
    build_and_write_tiny_actual_cash_measurement,
    build_tiny_actual_cash_measurement,
)
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact


REPO_ROOT = Path(__file__).resolve().parents[2]
runner = CliRunner()


def _write_all_inputs(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "readiness_packet": _write_readiness_packet(tmp_path),
        "external_venue_adapter": _write_external_venue_adapter(tmp_path),
        "human_approval": _write_human_approval(tmp_path),
        "order_intent": _write_order_intent(tmp_path),
        "submitted_order": _write_submitted_order(tmp_path),
        "fills": _write_fills(tmp_path),
        "fee_funding": _write_fee_funding(tmp_path),
        "cash_ledger": _write_cash_ledger(tmp_path),
        "actual_cash_rows": _write_actual_cash_rows(tmp_path),
        "flat_reconciliation": _write_flat_reconciliation(tmp_path),
        "stop_condition": _write_stop_condition(tmp_path),
    }
    return paths


def _write_readiness_packet(tmp_path: Path, *, status: str | None = None) -> Path:
    path = tmp_path / "profit_core_actual_cash_readiness_packet.json"
    write_json_artifact(
        path,
        {
            "schema_version": "profit_core_actual_cash_readiness_packet.v1",
            "candidate_id": "idea-cand-001",
            "measurement_id": "tiny-actual-cash-idea-cand-001",
            "readiness_status": status or "PACKET_COMPLETE_REQUIRES_HUMAN_APPROVAL",
        },
    )
    return path


def _write_external_venue_adapter(
    tmp_path: Path,
    *,
    status: str | None = None,
    candidate_id: str = "idea-cand-001",
) -> Path:
    path = tmp_path / "profit_core_external_venue_adapter_run.json"
    write_json_artifact(
        path,
        {
            "schema_version": "profit_core_external_venue_adapter_run.v1",
            "candidate_id": candidate_id,
            "venue": "bitget",
            "adapter_mode": "public_read_only",
            "adapter_status": status or "RECORDED_EXTERNAL_READ_ONLY_REQUIRES_HUMAN_REVIEW",
        },
    )
    return path


def _write_human_approval(tmp_path: Path, *, approved: bool = True) -> Path:
    path = tmp_path / "human_approval.json"
    write_json_artifact(
        path,
        {
            "approval_id": "approval-001",
            "candidate_id": "idea-cand-001",
            "approval_scope": "tiny_actual_cash_measurement",
            "approved": approved,
            "approved_at": "2026-07-01T08:00:00Z",
        },
    )
    return path


def _write_order_intent(
    tmp_path: Path,
    *,
    event_id: str = "event-1",
    action: str = "CONTINUATION_LONG",
    actual_cash: bool = True,
) -> Path:
    path = tmp_path / "order_intent.json"
    write_json_artifact(
        path,
        {
            "order_intent_id": "intent-001",
            "candidate_id": "idea-cand-001",
            "event_id": event_id,
            "action": action,
            "notional_usd": "10",
            "actual_cash": actual_cash,
        },
    )
    return path


def _write_submitted_order(
    tmp_path: Path,
    *,
    demo: bool = False,
    order_intent_id: str = "intent-001",
    event_id: str = "event-1",
    venue: str = "bitget",
) -> Path:
    path = tmp_path / "submitted_order.json"
    write_json_artifact(
        path,
        {
            "order_id": "order-001",
            "order_intent_id": order_intent_id,
            "candidate_id": "idea-cand-001",
            "event_id": event_id,
            "venue": venue,
            "source_kind": "actual_exchange_order",
            "actual_cash": not demo,
            "paper": False,
            "demo": demo,
            "testnet": False,
            "submitted_at": "2026-07-01T08:01:00Z",
        },
    )
    return path


def _write_fills(
    tmp_path: Path,
    *,
    event_id: str = "event-1",
    order_id: str = "order-001",
) -> Path:
    path = tmp_path / "fills.json"
    write_json_artifact(
        path,
        {
            "candidate_id": "idea-cand-001",
            "event_id": event_id,
            "order_id": order_id,
            "actual_cash": True,
            "fills": [
                {
                    "fill_id": "fill-001",
                    "quantity": "0.001",
                    "price": "10000",
                    "filled_at": "2026-07-01T08:02:00Z",
                }
            ],
        },
    )
    return path


def _write_fee_funding(
    tmp_path: Path,
    *,
    event_id: str = "event-1",
    total_fees_usd: str = "-1",
    total_funding_usd: str = "-0.5",
) -> Path:
    path = tmp_path / "fee_funding.json"
    write_json_artifact(
        path,
        {
            "candidate_id": "idea-cand-001",
            "event_id": event_id,
            "actual_cash": True,
            "total_fees_usd": total_fees_usd,
            "total_funding_usd": total_funding_usd,
        },
    )
    return path


def _write_cash_ledger(
    tmp_path: Path,
    *,
    event_id: str = "event-1",
    include_unassigned_zero_entry: bool = False,
) -> Path:
    path = tmp_path / "cash_ledger.json"
    entries = [
        CashLedgerEntry(
            entry_id="pnl-001",
            pod_id="pod-candidate",
            event_id=event_id,
            entry_type="REALIZED_PNL",
            amount_usd=Decimal("8"),
            occurred_at="2026-07-01T08:05:00Z",
        ),
        CashLedgerEntry(
            entry_id="fee-001",
            pod_id="pod-candidate",
            event_id=event_id,
            entry_type="FEE",
            amount_usd=Decimal("-1"),
            occurred_at="2026-07-01T08:05:00Z",
        ),
        CashLedgerEntry(
            entry_id="funding-001",
            pod_id="pod-candidate",
            event_id=event_id,
            entry_type="FUNDING",
            amount_usd=Decimal("-0.5"),
            occurred_at="2026-07-01T08:05:00Z",
        ),
    ]
    if include_unassigned_zero_entry:
        entries.append(
            CashLedgerEntry(
                entry_id="unassigned-001",
                pod_id="pod-unassigned",
                event_id=None,
                entry_type=CashLedgerEntryType.INFRA_COST,
                amount_usd=Decimal("0"),
                occurred_at="2026-07-01T08:05:00Z",
            )
        )
    ledger = build_cash_ledger(
        ledger_id="ledger-001",
        observed_at="2026-07-01T08:10:00Z",
        entries=entries,
    )
    write_json_artifact(path, ledger.model_dump(mode="json"))
    return path


def _write_actual_cash_rows(
    tmp_path: Path,
    *,
    basis: str = "actual_cash",
    include_no_trade: bool = True,
    include_extra_trade: bool = False,
) -> Path:
    path = tmp_path / "actual_cash_rows.jsonl"
    rows = [
        {
            "event_id": "event-1",
            "action": "CONTINUATION_LONG",
            "cash_metric_value_usd": "6.5",
            "actual_cash_result_usd": "6.5" if basis == "actual_cash" else None,
            "cash_metric_basis": basis,
            "market_adjusted_return": "0",
            "operator_time_minutes": "1",
            "near_miss": False,
        }
    ]
    if include_extra_trade:
        rows.append(
            {
                "event_id": "event-1",
                "action": "REVERSAL_SHORT",
                "cash_metric_value_usd": "0",
                "actual_cash_result_usd": "0" if basis == "actual_cash" else None,
                "cash_metric_basis": basis,
                "market_adjusted_return": "0",
                "operator_time_minutes": "0",
                "near_miss": False,
            }
        )
    if include_no_trade:
        rows.append(
            {
                "event_id": "event-1",
                "action": "NO_TRADE",
                "cash_metric_value_usd": "0",
                "actual_cash_result_usd": "0" if basis == "actual_cash" else None,
                "cash_metric_basis": basis,
                "market_adjusted_return": "0",
                "operator_time_minutes": "0",
                "near_miss": False,
            }
        )
    write_text_artifact(
        path,
        "\n".join(json.dumps(row, sort_keys=True) for row in rows) + "\n",
    )
    return path


def _write_flat_reconciliation(tmp_path: Path, *, reconciled: bool = True) -> Path:
    path = tmp_path / "flat_reconciliation.json"
    write_json_artifact(
        path,
        {
            "candidate_id": "idea-cand-001",
            "event_id": "event-1",
            "reconciled_flat": reconciled,
            "open_position_count": 0 if reconciled else 1,
            "cash_ledger_reconciled": reconciled,
            "reconciled_at": "2026-07-01T08:15:00Z",
        },
    )
    return path


def _write_stop_condition(tmp_path: Path, *, complete: bool = True) -> Path:
    path = tmp_path / "stop_condition.json"
    write_json_artifact(
        path,
        {
            "candidate_id": "idea-cand-001",
            "event_id": "event-1",
            "loss_stop_defined": complete,
            "venue_stop_defined": complete,
            "credential_stop_defined": complete,
            "legal_stop_defined": complete,
            "stop_conditions_respected": complete,
        },
    )
    return path


def test_tiny_actual_cash_measurement_records_actual_cash_lineage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)

    result = build_and_write_tiny_actual_cash_measurement(
        readiness_packet_path=paths["readiness_packet"],
        external_venue_adapter_path=paths["external_venue_adapter"],
        human_approval_path=paths["human_approval"],
        order_intent_path=paths["order_intent"],
        submitted_order_path=paths["submitted_order"],
        fills_path=paths["fills"],
        fee_funding_path=paths["fee_funding"],
        cash_ledger_path=paths["cash_ledger"],
        actual_cash_rows_path=paths["actual_cash_rows"],
        flat_reconciliation_path=paths["flat_reconciliation"],
        stop_condition_path=paths["stop_condition"],
        out_dir=tmp_path / "measurement",
    )

    measurement = result.measurement

    assert measurement.schema_version == "profit_core_tiny_actual_cash_measurement.v1"
    assert measurement.candidate_id == "idea-cand-001"
    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.RECORDED_ACTUAL_CASH_REQUIRES_REPORT_GATE
    )
    assert measurement.actual_cash is True
    assert measurement.actual_cash_result_usd == "6.5"
    assert measurement.event_set == ["event-1"]
    assert measurement.no_trade_comparison_present is True
    assert measurement.flat_reconciled is True
    assert measurement.stop_conditions_respected is True
    assert measurement.order_submitted_by_this_command is False
    assert measurement.network_attempted is False
    assert measurement.exchange_write_used is False
    assert measurement.live_order_submitted is False
    assert result.measurement_path.exists()


def test_tiny_actual_cash_measurement_schema_validates_output(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    result = build_and_write_tiny_actual_cash_measurement(
        readiness_packet_path=paths["readiness_packet"],
        external_venue_adapter_path=paths["external_venue_adapter"],
        human_approval_path=paths["human_approval"],
        order_intent_path=paths["order_intent"],
        submitted_order_path=paths["submitted_order"],
        fills_path=paths["fills"],
        fee_funding_path=paths["fee_funding"],
        cash_ledger_path=paths["cash_ledger"],
        actual_cash_rows_path=paths["actual_cash_rows"],
        flat_reconciliation_path=paths["flat_reconciliation"],
        stop_condition_path=paths["stop_condition"],
        out_dir=tmp_path / "measurement",
    )
    schema = json.loads(
        (REPO_ROOT / "schemas/profit_core_tiny_actual_cash_measurement.v1.schema.json").read_text(
            encoding="utf-8"
        )
    )

    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(result.measurement.model_dump(mode="json"))


def test_tiny_actual_cash_measurement_blocks_missing_human_approval(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["human_approval"] = _write_human_approval(tmp_path, approved=False)

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_HUMAN_APPROVAL
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {
        "HUMAN_APPROVAL_NOT_PRESENT"
    }
    assert measurement.order_submitted_by_this_command is False


def test_tiny_actual_cash_measurement_blocks_non_actual_cash_rows(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["actual_cash_rows"] = _write_actual_cash_rows(tmp_path, basis="cost_adjusted_estimate")

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_NON_ACTUAL_CASH_BASIS
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {"NON_ACTUAL_CASH_BASIS"}
    assert measurement.actual_cash is False


def test_tiny_actual_cash_measurement_blocks_missing_no_trade_same_event_set(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["actual_cash_rows"] = _write_actual_cash_rows(tmp_path, include_no_trade=False)

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_MISSING_NO_TRADE_COMPARISON
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {
        "NO_TRADE_COMPARISON_MISSING"
    }


def test_tiny_actual_cash_measurement_blocks_upstream_candidate_lineage_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["external_venue_adapter"] = _write_external_venue_adapter(
        tmp_path,
        candidate_id="other-cand",
    )

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_CANDIDATE_LINEAGE
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {
        "CANDIDATE_LINEAGE_MISMATCH"
    }


def test_tiny_actual_cash_measurement_blocks_event_lineage_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["fills"] = _write_fills(tmp_path, event_id="event-2")

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_CANDIDATE_LINEAGE
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {"EVENT_LINEAGE_MISMATCH"}


def test_tiny_actual_cash_measurement_blocks_order_chain_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["submitted_order"] = _write_submitted_order(
        tmp_path,
        order_intent_id="other-intent",
    )

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_CANDIDATE_LINEAGE
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {"ORDER_CHAIN_MISMATCH"}


def test_tiny_actual_cash_measurement_blocks_order_intent_action_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["order_intent"] = _write_order_intent(tmp_path, action="REVERSAL_SHORT")

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_CANDIDATE_LINEAGE
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {
        "ORDER_INTENT_ACTION_MISMATCH"
    }


def test_tiny_actual_cash_measurement_blocks_venue_lineage_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["submitted_order"] = _write_submitted_order(tmp_path, venue="other-venue")

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_CANDIDATE_LINEAGE
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {"VENUE_LINEAGE_MISMATCH"}


def test_tiny_actual_cash_measurement_blocks_cash_ledger_event_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["cash_ledger"] = _write_cash_ledger(tmp_path, event_id="event-2")

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_CANDIDATE_LINEAGE
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {
        "CASH_LEDGER_EVENT_SET_MISMATCH"
    }


def test_tiny_actual_cash_measurement_blocks_unassigned_cash_ledger_entry(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["cash_ledger"] = _write_cash_ledger(
        tmp_path,
        include_unassigned_zero_entry=True,
    )

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_CANDIDATE_LINEAGE
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {
        "CASH_LEDGER_EVENT_SET_MISMATCH"
    }


def test_tiny_actual_cash_measurement_blocks_multiple_trade_actions_per_event(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["actual_cash_rows"] = _write_actual_cash_rows(tmp_path, include_extra_trade=True)

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_CANDIDATE_LINEAGE
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {
        "ACTUAL_CASH_ROWS_ACTION_SET_INVALID"
    }


def test_tiny_actual_cash_measurement_blocks_fee_funding_ledger_mismatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["fee_funding"] = _write_fee_funding(tmp_path, total_fees_usd="-2")

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_CANDIDATE_LINEAGE
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {
        "FEE_FUNDING_LEDGER_MISMATCH"
    }


def test_tiny_actual_cash_measurement_blocks_non_actual_cash_order_intent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["order_intent"] = _write_order_intent(tmp_path, actual_cash=False)

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_NON_ACTUAL_CASH_BASIS
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {"NON_ACTUAL_CASH_BASIS"}


def test_tiny_actual_cash_measurement_blocks_flat_reconciliation_gap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["flat_reconciliation"] = _write_flat_reconciliation(tmp_path, reconciled=False)

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_FLAT_RECONCILIATION
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {
        "FLAT_RECONCILIATION_MISSING"
    }
    assert measurement.flat_reconciled is False


def test_tiny_actual_cash_measurement_blocks_stop_condition_gap(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    paths["stop_condition"] = _write_stop_condition(tmp_path, complete=False)

    measurement = build_tiny_actual_cash_measurement(**_build_kwargs(paths))

    assert (
        measurement.measurement_status
        == ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_STOP_CONDITION
    )
    assert {blocker.blocker_code for blocker in measurement.blockers} == {
        "STOP_CONDITION_INCOMPLETE"
    }
    assert measurement.stop_conditions_respected is False


def test_tiny_actual_cash_measurement_cli_writes_measurement(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    paths = _write_all_inputs(tmp_path)
    out_dir = tmp_path / "measurement_cli"

    result = runner.invoke(
        app,
        [
            "edge-candidate-tiny-actual-cash-measurement-record",
            "--readiness-packet",
            str(paths["readiness_packet"]),
            "--external-venue-adapter",
            str(paths["external_venue_adapter"]),
            "--human-approval",
            str(paths["human_approval"]),
            "--order-intent",
            str(paths["order_intent"]),
            "--submitted-order",
            str(paths["submitted_order"]),
            "--fills",
            str(paths["fills"]),
            "--fee-funding",
            str(paths["fee_funding"]),
            "--cash-ledger",
            str(paths["cash_ledger"]),
            "--actual-cash-rows",
            str(paths["actual_cash_rows"]),
            "--flat-reconciliation",
            str(paths["flat_reconciliation"]),
            "--stop-condition",
            str(paths["stop_condition"]),
            "--out",
            str(out_dir),
        ],
    )

    assert result.exit_code == 0, result.stdout
    assert "network_attempted=false" in result.stdout
    assert "exchange_write_used=false" in result.stdout
    assert "live_order_submitted=false" in result.stdout
    assert "order_submitted_by_this_command=false" in result.stdout
    assert "status=pass" in result.stdout
    assert "measurement_status=RECORDED_ACTUAL_CASH_REQUIRES_REPORT_GATE" in result.stdout
    assert (out_dir / "profit_core_tiny_actual_cash_measurement.json").exists()


def _build_kwargs(paths: dict[str, Path]) -> dict:
    return {
        "readiness_packet_path": paths["readiness_packet"],
        "external_venue_adapter_path": paths["external_venue_adapter"],
        "human_approval_path": paths["human_approval"],
        "order_intent_path": paths["order_intent"],
        "submitted_order_path": paths["submitted_order"],
        "fills_path": paths["fills"],
        "fee_funding_path": paths["fee_funding"],
        "cash_ledger_path": paths["cash_ledger"],
        "actual_cash_rows_path": paths["actual_cash_rows"],
        "flat_reconciliation_path": paths["flat_reconciliation"],
        "stop_condition_path": paths["stop_condition"],
    }
