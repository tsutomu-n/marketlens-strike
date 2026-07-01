from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any, Literal

from sis.backtest.artifact_io import sha256_file
from sis.crypto_perp.clock import ensure_utc_aware
from sis.crypto_perp.models import decimal_to_json_string
from sis.crypto_perp.tournament import TournamentEventResult
from sis.edge_candidates.actual_cash_readiness import ProfitCoreActualCashReadinessPacket
from sis.edge_candidates.actual_cash_report_gate_models import (
    ActualCashReportGateArtifactRef,
    ActualCashReportGateBlocker,
    ActualCashReportGatePolicy,
    ActualCashReportGateWriteResult,
    ProfitCoreActualCashReportDecision,
    ProfitCoreActualCashReportGate,
    ProfitCoreActualCashReportStatus,
)
from sis.edge_candidates.evidence_packet import ProfitCoreArtifactRef, ProfitCoreEvidencePacket
from sis.edge_candidates.tiny_actual_cash_measurement import (
    ProfitCoreTinyActualCashMeasurement,
    ProfitCoreTinyActualCashMeasurementStatus,
)
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact
from sis.strategy_inputs.models import ProducerInfo


class ActualCashReportGateError(ValueError):
    pass


class ActualCashReportGateOutputExistsError(ActualCashReportGateError):
    pass


@dataclass(frozen=True)
class _RowsMetrics:
    sample_size: dict[str, Any]
    event_diversity: dict[str, Any]
    measured_action: str | None
    measured_total: Decimal | None
    no_trade_total: Decimal | None
    edge_over_no_trade: Decimal | None
    profit_concentration: Decimal | None
    largest_loss: Decimal | None
    operator_burden: Decimal | None
    blockers: list[ActualCashReportGateBlocker]


def build_actual_cash_report_gate(
    *,
    measurement_path: Path,
    min_events: int = 2,
    max_largest_loss_usd: Decimal | str = Decimal("25"),
    max_profit_concentration: Decimal | str = Decimal("0.60"),
    max_operator_burden_minutes: Decimal | str = Decimal("120"),
    recorded_at: datetime | str | None = None,
) -> ProfitCoreActualCashReportGate:
    policy = ActualCashReportGatePolicy(
        min_events=min_events,
        max_largest_loss_usd=_decimal_from_policy(max_largest_loss_usd),
        max_profit_concentration=_decimal_from_policy(max_profit_concentration),
        max_operator_burden_minutes=_decimal_from_policy(max_operator_burden_minutes),
    )
    measurement = ProfitCoreTinyActualCashMeasurement.model_validate(
        read_mapping_file(measurement_path)
    )
    measurement_ref = _artifact_ref(
        "tiny_actual_cash_measurement",
        measurement_path,
        measurement.schema_version,
    )
    blockers = _measurement_blockers(measurement)
    readiness_path = _resolve_ref_path(measurement.readiness_packet_ref.path, measurement_path)
    _validate_ref_hash(
        path=readiness_path,
        expected_sha256=measurement.readiness_packet_ref.sha256,
        role="readiness_packet",
    )
    readiness = ProfitCoreActualCashReadinessPacket.model_validate(
        read_mapping_file(readiness_path)
    )
    readiness_ref = _artifact_ref(
        "actual_cash_readiness_packet",
        readiness_path,
        readiness.schema_version,
    )
    evidence_path = _resolve_ref_path(readiness.evidence_packet_ref.path, readiness_path)
    _validate_ref_hash(
        path=evidence_path,
        expected_sha256=readiness.evidence_packet_ref.sha256,
        role="evidence_packet",
    )
    evidence = ProfitCoreEvidencePacket.model_validate(read_mapping_file(evidence_path))
    evidence_ref = _artifact_ref("evidence_packet", evidence_path, evidence.schema_version)
    rows_path = _resolve_ref_path(measurement.actual_cash_rows_ref.path, measurement_path)
    _validate_ref_hash(
        path=rows_path,
        expected_sha256=measurement.actual_cash_rows_ref.sha256,
        role="actual_cash_rows",
    )
    rows = _read_actual_cash_rows(rows_path)
    rows_ref = _artifact_ref("actual_cash_rows", rows_path, None)
    blockers.extend(_lineage_blockers(measurement, readiness, evidence))
    context_refs = _context_refs(evidence)
    blockers.extend(_missing_context_ref_blockers(context_refs))
    metrics = _rows_metrics(rows)
    blockers.extend(metrics.blockers)
    blockers.extend(_policy_blockers(metrics, measurement, policy))
    report_status = _report_status(blockers)
    decision = _decision(blockers)
    source_refs = _source_refs(
        measurement_ref=measurement_ref,
        readiness_ref=readiness_ref,
        evidence_ref=evidence_ref,
        rows_ref=rows_ref,
        context_refs=context_refs,
    )
    promotion_allowed = report_status is ProfitCoreActualCashReportStatus.COMPLETE and not blockers
    created = _coerce_datetime(recorded_at)
    return ProfitCoreActualCashReportGate(
        report_id=f"{measurement.measurement_id}-actual-cash-report-gate",
        recorded_at=created,
        producer=ProducerInfo(command="edge-candidate-actual-cash-report-gate"),
        candidate_id=measurement.candidate_id,
        measurement_id=measurement.measurement_id,
        report_status=report_status,
        decision=decision,
        promotion_allowed=promotion_allowed,
        blockers=blockers,
        source_refs=source_refs,
        measurement_ref=measurement_ref,
        readiness_packet_ref=readiness_ref,
        evidence_packet_ref=evidence_ref,
        actual_cash_rows_ref=rows_ref,
        protocol_ref=context_refs.get("protocol"),
        multiplicity_account_ref=context_refs.get("multiplicity_account"),
        backtest_kill_gate_ref=context_refs.get("backtest_kill_gate"),
        virtual_gate_ref=context_refs.get("virtual_gate"),
        policy=policy,
        sample_size=metrics.sample_size,
        event_diversity=metrics.event_diversity,
        measured_action=metrics.measured_action,
        actual_cash_result_usd=_decimal_string(metrics.measured_total),
        no_trade_result_usd=_decimal_string(metrics.no_trade_total),
        actual_cash_edge_over_NO_TRADE=_decimal_string(metrics.edge_over_no_trade),
        profit_concentration=_decimal_string(metrics.profit_concentration),
        largest_loss_usd=_decimal_string(metrics.largest_loss),
        operator_burden_minutes=_decimal_string(metrics.operator_burden),
        reconcile_mismatch=_reconcile_mismatch(measurement, metrics),
        evidence_basis=_evidence_basis(
            measurement=measurement,
            evidence=evidence,
            measured_total=metrics.measured_total,
            edge_over_no_trade=metrics.edge_over_no_trade,
        ),
        actual_cash=measurement.actual_cash
        and report_status is ProfitCoreActualCashReportStatus.COMPLETE,
        cash_metric_basis="actual_cash"
        if measurement.cash_metric_basis == "actual_cash"
        else "blocked",
    )


def build_and_write_actual_cash_report_gate(
    *,
    measurement_path: Path,
    out_dir: Path,
    min_events: int = 2,
    max_largest_loss_usd: Decimal | str = Decimal("25"),
    max_profit_concentration: Decimal | str = Decimal("0.60"),
    max_operator_burden_minutes: Decimal | str = Decimal("120"),
    recorded_at: datetime | str | None = None,
    replace_existing: bool = False,
) -> ActualCashReportGateWriteResult:
    gate_path = out_dir / "profit_core_actual_cash_report_gate.json"
    if gate_path.exists() and not replace_existing:
        raise ActualCashReportGateOutputExistsError(f"output already exists: {gate_path}")
    gate = build_actual_cash_report_gate(
        measurement_path=measurement_path,
        min_events=min_events,
        max_largest_loss_usd=max_largest_loss_usd,
        max_profit_concentration=max_profit_concentration,
        max_operator_burden_minutes=max_operator_burden_minutes,
        recorded_at=recorded_at,
    )
    write_json_artifact(gate_path, gate.model_dump(mode="json"))
    return ActualCashReportGateWriteResult(
        gate=gate,
        gate_path=gate_path,
        gate_sha256=sha256_file(gate_path),
    )


def _measurement_blockers(
    measurement: ProfitCoreTinyActualCashMeasurement,
) -> list[ActualCashReportGateBlocker]:
    blockers: list[ActualCashReportGateBlocker] = []
    if (
        measurement.measurement_status
        is not ProfitCoreTinyActualCashMeasurementStatus.RECORDED_ACTUAL_CASH_REQUIRES_REPORT_GATE
        or not measurement.actual_cash
        or measurement.cash_metric_basis != "actual_cash"
    ):
        blockers.append(
            _blocker(
                "P11_MEASUREMENT_NOT_COMPLETE",
                "P11 measurement must be recorded actual-cash evidence requiring a report gate.",
                "tiny_actual_cash_measurement",
                "block",
            )
        )
    if not measurement.no_trade_comparison_present:
        blockers.append(
            _blocker(
                "NO_TRADE_COMPARISON_MISSING",
                "P11 measurement must include NO_TRADE comparison.",
                "tiny_actual_cash_measurement",
                "block",
            )
        )
    if not measurement.flat_reconciled or not measurement.stop_conditions_respected:
        blockers.append(
            _blocker(
                "RECONCILIATION_OR_STOP_CONDITION_MISSING",
                "P11 measurement must have flat reconciliation and respected stop conditions.",
                "tiny_actual_cash_measurement",
                "block",
            )
        )
    return blockers


def _lineage_blockers(
    measurement: ProfitCoreTinyActualCashMeasurement,
    readiness: ProfitCoreActualCashReadinessPacket,
    evidence: ProfitCoreEvidencePacket,
) -> list[ActualCashReportGateBlocker]:
    blockers: list[ActualCashReportGateBlocker] = []
    if (
        readiness.candidate_id != measurement.candidate_id
        or evidence.candidate_id != measurement.candidate_id
    ):
        blockers.append(
            _blocker(
                "CANDIDATE_LINEAGE_MISMATCH",
                "Measurement, readiness packet, and evidence packet candidate ids must match.",
                "candidate_lineage",
                "block",
            )
        )
    if readiness.measurement_id != measurement.measurement_id:
        blockers.append(
            _blocker(
                "MEASUREMENT_LINEAGE_MISMATCH",
                "Readiness packet measurement_id must match P11 measurement.",
                "measurement_lineage",
                "block",
            )
        )
    return blockers


def _missing_context_ref_blockers(
    context_refs: dict[str, ActualCashReportGateArtifactRef],
) -> list[ActualCashReportGateBlocker]:
    blockers: list[ActualCashReportGateBlocker] = []
    for role in ("protocol", "multiplicity_account", "backtest_kill_gate", "virtual_gate"):
        if role not in context_refs:
            blockers.append(
                _blocker(
                    f"MISSING_{role.upper()}_REF",
                    f"Evidence packet source_refs must include {role}.",
                    "evidence_packet",
                    "wait",
                )
            )
    return blockers


def _rows_metrics(rows: list[TournamentEventResult]) -> _RowsMetrics:
    blockers: list[ActualCashReportGateBlocker] = []
    actual_cash_rows = [
        row
        for row in rows
        if row.cash_metric_basis == "actual_cash" and row.actual_cash_result_usd is not None
    ]
    if len(actual_cash_rows) != len(rows):
        blockers.append(
            _blocker(
                "NON_ACTUAL_CASH_ROWS",
                "P12 report gate only accepts actual-cash rows.",
                "actual_cash_rows",
                "block",
            )
        )
    measured_rows = [row for row in rows if row.action != "NO_TRADE"]
    no_trade_rows = [row for row in rows if row.action == "NO_TRADE"]
    event_set = sorted({row.event_id for row in rows})
    measured_event_set = sorted({row.event_id for row in measured_rows})
    no_trade_event_set = sorted({row.event_id for row in no_trade_rows})
    measured_actions = sorted({str(row.action) for row in measured_rows})
    if not event_set or measured_event_set != no_trade_event_set or event_set != measured_event_set:
        blockers.append(
            _blocker(
                "NO_TRADE_EVENT_SET_MISMATCH",
                "Measured action rows and NO_TRADE rows must use the same event set.",
                "actual_cash_rows",
                "block",
            )
        )
    if any(
        sum(1 for row in measured_rows if row.event_id == event_id) != 1 for event_id in event_set
    ):
        blockers.append(
            _blocker(
                "MEASURED_ACTION_EVENT_SET_INVALID",
                "Each event must have exactly one measured non-NO_TRADE action.",
                "actual_cash_rows",
                "block",
            )
        )
    measured_values = [row.actual_cash_result_usd or Decimal("0") for row in measured_rows]
    no_trade_values = [row.actual_cash_result_usd or Decimal("0") for row in no_trade_rows]
    measured_total = sum(measured_values, Decimal("0")) if measured_rows else None
    no_trade_total = sum(no_trade_values, Decimal("0")) if no_trade_rows else None
    edge = (
        measured_total - no_trade_total
        if measured_total is not None and no_trade_total is not None
        else None
    )
    positive_values = [value for value in measured_values if value > 0]
    positive_total = sum(positive_values, Decimal("0"))
    concentration = Decimal("0") if positive_total == 0 else max(positive_values) / positive_total
    largest_loss = min(measured_values) if measured_values else None
    operator_burden = (
        sum((row.operator_time_minutes for row in measured_rows), Decimal("0"))
        if measured_rows
        else None
    )
    return _RowsMetrics(
        sample_size={
            "event_count": len(event_set),
            "row_count": len(rows),
            "measured_row_count": len(measured_rows),
            "no_trade_row_count": len(no_trade_rows),
        },
        event_diversity={
            "event_set": event_set,
            "event_count": len(event_set),
            "measured_action_set": measured_actions,
            "no_trade_event_set": no_trade_event_set,
        },
        measured_action=measured_actions[0] if len(measured_actions) == 1 else None,
        measured_total=measured_total,
        no_trade_total=no_trade_total,
        edge_over_no_trade=edge,
        profit_concentration=concentration,
        largest_loss=largest_loss,
        operator_burden=operator_burden,
        blockers=blockers,
    )


def _policy_blockers(
    metrics: _RowsMetrics,
    measurement: ProfitCoreTinyActualCashMeasurement,
    policy: ActualCashReportGatePolicy,
) -> list[ActualCashReportGateBlocker]:
    blockers: list[ActualCashReportGateBlocker] = []
    if metrics.sample_size["event_count"] < policy.min_events:
        blockers.append(
            _blocker(
                "INSUFFICIENT_EVENT_COUNT",
                "Actual-cash sample size is below policy minimum.",
                "policy",
                "wait",
            )
        )
    if metrics.edge_over_no_trade is None:
        blockers.append(
            _blocker(
                "ACTUAL_CASH_EDGE_MISSING",
                "Actual-cash edge over NO_TRADE could not be computed.",
                "actual_cash_rows",
                "wait",
            )
        )
    elif metrics.edge_over_no_trade < 0:
        blockers.append(
            _blocker(
                "ACTUAL_CASH_EDGE_NEGATIVE",
                "Actual-cash edge over NO_TRADE is negative.",
                "actual_cash_rows",
                "kill",
            )
        )
    elif metrics.edge_over_no_trade == 0:
        blockers.append(
            _blocker(
                "ACTUAL_CASH_EDGE_NOT_POSITIVE",
                "Actual-cash edge over NO_TRADE must be positive before promotion.",
                "actual_cash_rows",
                "wait",
            )
        )
    if (
        metrics.largest_loss is not None
        and abs(min(metrics.largest_loss, Decimal("0"))) > policy.max_largest_loss_usd
    ):
        blockers.append(
            _blocker(
                "LARGEST_LOSS_LIMIT_BREACH",
                "Largest actual-cash loss breaches policy.",
                "policy",
                "kill",
            )
        )
    if (
        metrics.profit_concentration is not None
        and metrics.profit_concentration > policy.max_profit_concentration
    ):
        blockers.append(
            _blocker(
                "PROFIT_CONCENTRATION_TOO_HIGH",
                "Actual-cash profit is too concentrated for promotion.",
                "policy",
                "wait",
            )
        )
    if (
        metrics.operator_burden is not None
        and metrics.operator_burden > policy.max_operator_burden_minutes
    ):
        blockers.append(
            _blocker(
                "OPERATOR_BURDEN_TOO_HIGH",
                "Operator burden is too high for promotion.",
                "policy",
                "wait",
            )
        )
    if _reconcile_mismatch(measurement, metrics):
        blockers.append(
            _blocker(
                "RECONCILE_MISMATCH",
                "P11 measurement totals or flat reconciliation do not match P12 rows.",
                "reconciliation",
                "block",
            )
        )
    return blockers


def _reconcile_mismatch(
    measurement: ProfitCoreTinyActualCashMeasurement,
    metrics: _RowsMetrics,
) -> bool:
    row_total = None
    if metrics.measured_total is not None and metrics.no_trade_total is not None:
        row_total = metrics.measured_total + metrics.no_trade_total
    measurement_total = _decimal_or_none(measurement.actual_cash_result_usd)
    ledger_total = _decimal_or_none(measurement.cash_ledger_actual_cash_result_usd)
    return not (
        measurement.flat_reconciled
        and row_total is not None
        and measurement_total == row_total
        and ledger_total == row_total
    )


def _report_status(
    blockers: list[ActualCashReportGateBlocker],
) -> ProfitCoreActualCashReportStatus:
    if any(blocker.severity == "block" for blocker in blockers):
        return ProfitCoreActualCashReportStatus.BLOCKED
    return ProfitCoreActualCashReportStatus.COMPLETE


def _decision(
    blockers: list[ActualCashReportGateBlocker],
) -> ProfitCoreActualCashReportDecision:
    if any(blocker.severity == "kill" for blocker in blockers):
        return ProfitCoreActualCashReportDecision.KILL
    if blockers:
        return ProfitCoreActualCashReportDecision.WAIT
    return ProfitCoreActualCashReportDecision.PROMOTE


def _evidence_basis(
    *,
    measurement: ProfitCoreTinyActualCashMeasurement,
    evidence: ProfitCoreEvidencePacket,
    measured_total: Decimal | None,
    edge_over_no_trade: Decimal | None,
) -> dict[str, dict[str, Any]]:
    machine_summary = evidence.machine_summary
    return {
        "actual_cash": {
            "available": measurement.actual_cash,
            "cash_metric_basis": measurement.cash_metric_basis,
            "result_usd": _decimal_string(measured_total),
            "edge_over_NO_TRADE": _decimal_string(edge_over_no_trade),
            "promotion_metric_authority": True,
        },
        "virtual_exchange": {
            "available": machine_summary.get("cash_metric_basis") == "virtual_exchange",
            "cash_metric_basis": machine_summary.get("cash_metric_basis"),
            "actual_cash": False,
            "promotion_metric_authority": False,
        },
        "simulation": {
            "available": bool(machine_summary.get("backtest_gate_state")),
            "backtest_gate_state": machine_summary.get("backtest_gate_state"),
            "actual_cash": False,
            "promotion_metric_authority": False,
        },
        "estimate": {
            "available": False,
            "actual_cash": False,
            "promotion_metric_authority": False,
        },
    }


def _context_refs(
    evidence: ProfitCoreEvidencePacket,
) -> dict[str, ActualCashReportGateArtifactRef]:
    refs: dict[str, ActualCashReportGateArtifactRef] = {}
    for ref in evidence.source_refs:
        refs[ref.artifact_role] = _ref_from_profit_core_ref(ref)
    return refs


def _source_refs(
    *,
    measurement_ref: ActualCashReportGateArtifactRef,
    readiness_ref: ActualCashReportGateArtifactRef,
    evidence_ref: ActualCashReportGateArtifactRef,
    rows_ref: ActualCashReportGateArtifactRef,
    context_refs: dict[str, ActualCashReportGateArtifactRef],
) -> list[ActualCashReportGateArtifactRef]:
    refs = [measurement_ref, readiness_ref, evidence_ref, rows_ref]
    for role in ("protocol", "multiplicity_account", "backtest_kill_gate", "virtual_gate"):
        ref = context_refs.get(role)
        if ref is not None:
            refs.append(ref)
    return refs


def _read_actual_cash_rows(path: Path) -> list[TournamentEventResult]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ActualCashReportGateError("actual cash rows file is empty")
    try:
        if text.startswith("["):
            raw_rows = json.loads(text)
        else:
            raw_rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    except json.JSONDecodeError as exc:
        raise ActualCashReportGateError("actual cash rows must be JSONL or JSON array") from exc
    if not isinstance(raw_rows, list):
        raise ActualCashReportGateError("actual cash rows must be a list")
    return [TournamentEventResult.model_validate(row) for row in raw_rows]


def _validate_ref_hash(*, path: Path, expected_sha256: str, role: str) -> None:
    if not path.exists():
        raise ActualCashReportGateError(f"{role} missing: {path}")
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise ActualCashReportGateError(
            f"{role} hash mismatch: expected {expected_sha256}, got {actual_sha256}"
        )


def _resolve_ref_path(path_text: str, anchor_path: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    if path.exists():
        return path
    return anchor_path.parent / path


def _artifact_ref(
    role: str,
    path: Path,
    schema_version: str | None,
) -> ActualCashReportGateArtifactRef:
    return ActualCashReportGateArtifactRef(
        artifact_role=role,
        path=path.as_posix(),
        sha256=sha256_file(path),
        schema_version=schema_version,
    )


def _ref_from_profit_core_ref(ref: ProfitCoreArtifactRef) -> ActualCashReportGateArtifactRef:
    return ActualCashReportGateArtifactRef(
        artifact_role=ref.artifact_role,
        path=ref.path,
        sha256=ref.sha256,
        schema_version=ref.schema_version,
    )


def _blocker(
    code: str,
    message: str,
    source: str,
    severity: Literal["block", "wait", "kill"],
) -> ActualCashReportGateBlocker:
    return ActualCashReportGateBlocker(
        blocker_code=code,
        message=message,
        source=source,
        severity=severity,
    )


def _decimal_string(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return decimal_to_json_string(value)


def _decimal_or_none(value: str | None) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _decimal_from_policy(value: Decimal | str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ActualCashReportGateError("policy threshold must be a decimal string") from exc


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    return ensure_utc_aware("recorded_at", value)


__all__ = [
    "ActualCashReportGateArtifactRef",
    "ActualCashReportGateBlocker",
    "ActualCashReportGateError",
    "ActualCashReportGateOutputExistsError",
    "ActualCashReportGatePolicy",
    "ActualCashReportGateWriteResult",
    "ProfitCoreActualCashReportDecision",
    "ProfitCoreActualCashReportGate",
    "ProfitCoreActualCashReportStatus",
    "build_actual_cash_report_gate",
    "build_and_write_actual_cash_report_gate",
]
