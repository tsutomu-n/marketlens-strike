from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.crypto_perp.cash_ledger import CryptoPerpCashLedger
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN, decimal_to_json_string
from sis.crypto_perp.tournament import TournamentEventResult
from sis.edge_candidates import PROFIT_CORE_TINY_ACTUAL_CASH_MEASUREMENT_SCHEMA_VERSION
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact
from sis.strategy_inputs.models import ProducerInfo


class ProfitCoreTinyActualCashMeasurementStatus(StrEnum):
    RECORDED_ACTUAL_CASH_REQUIRES_REPORT_GATE = "RECORDED_ACTUAL_CASH_REQUIRES_REPORT_GATE"
    BLOCKED_HUMAN_APPROVAL = "BLOCKED_HUMAN_APPROVAL"
    BLOCKED_UPSTREAM = "BLOCKED_UPSTREAM"
    BLOCKED_NON_ACTUAL_CASH_BASIS = "BLOCKED_NON_ACTUAL_CASH_BASIS"
    BLOCKED_MISSING_NO_TRADE_COMPARISON = "BLOCKED_MISSING_NO_TRADE_COMPARISON"
    BLOCKED_FLAT_RECONCILIATION = "BLOCKED_FLAT_RECONCILIATION"
    BLOCKED_STOP_CONDITION = "BLOCKED_STOP_CONDITION"
    BLOCKED_CANDIDATE_LINEAGE = "BLOCKED_CANDIDATE_LINEAGE"


class TinyActualCashArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_role: str
    path: str
    sha256: str
    schema_version: str | None = None

    @field_validator("artifact_role", "path", "sha256")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("artifact ref text fields must not be empty")
        return stripped


class TinyActualCashBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    blocker_code: str
    message: str
    source: str

    @field_validator("blocker_code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("blocker_code must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("message", "source")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("blocker text fields must not be empty")
        return stripped


class ProfitCoreTinyActualCashMeasurement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["profit_core_tiny_actual_cash_measurement.v1"] = (
        PROFIT_CORE_TINY_ACTUAL_CASH_MEASUREMENT_SCHEMA_VERSION
    )
    measurement_id: str
    recorded_at: datetime
    producer: ProducerInfo
    candidate_id: str
    measurement_status: ProfitCoreTinyActualCashMeasurementStatus
    blockers: list[TinyActualCashBlocker] = Field(default_factory=list)
    source_refs: list[TinyActualCashArtifactRef] = Field(min_length=11)
    readiness_packet_ref: TinyActualCashArtifactRef
    external_venue_adapter_ref: TinyActualCashArtifactRef
    human_approval_ref: TinyActualCashArtifactRef
    order_intent_ref: TinyActualCashArtifactRef
    submitted_order_ref: TinyActualCashArtifactRef
    fills_ref: TinyActualCashArtifactRef
    fee_funding_ref: TinyActualCashArtifactRef
    cash_ledger_ref: TinyActualCashArtifactRef
    actual_cash_rows_ref: TinyActualCashArtifactRef
    flat_reconciliation_ref: TinyActualCashArtifactRef
    stop_condition_ref: TinyActualCashArtifactRef
    event_set: list[str]
    action_set: list[str]
    row_count: int = Field(ge=0)
    actual_cash_result_usd: str | None
    cash_ledger_actual_cash_result_usd: str
    no_trade_comparison_present: bool
    flat_reconciled: bool
    stop_conditions_respected: bool
    actual_cash: bool
    cash_metric_basis: Literal["actual_cash", "blocked"] = "blocked"
    order_submitted_by_this_command: Literal[False] = False
    network_attempted: Literal[False] = False
    credentials_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
    live_order_submitted: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    boundary: dict[str, bool] = Field(
        default_factory=lambda: {
            "order_submitted_by_this_command": False,
            "network_attempted": False,
            "credentials_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
        }
    )

    @field_validator("measurement_id", "candidate_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("id fields must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("recorded_at", mode="before")
    @classmethod
    def validate_recorded_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("recorded_at", value)

    @field_validator("boundary")
    @classmethod
    def validate_boundary(cls, value: dict[str, bool]) -> dict[str, bool]:
        expected = {
            "order_submitted_by_this_command": False,
            "network_attempted": False,
            "credentials_used": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
        }
        if value != expected:
            raise ValueError("boundary must keep recording command side effects false")
        return value

    @field_serializer("recorded_at")
    def serialize_recorded_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class TinyActualCashMeasurementWriteResult:
    measurement: ProfitCoreTinyActualCashMeasurement
    measurement_path: Path
    measurement_sha256: str


class TinyActualCashMeasurementError(ValueError):
    pass


class TinyActualCashMeasurementOutputExistsError(TinyActualCashMeasurementError):
    pass


def build_tiny_actual_cash_measurement(
    *,
    readiness_packet_path: Path,
    external_venue_adapter_path: Path,
    human_approval_path: Path,
    order_intent_path: Path,
    submitted_order_path: Path,
    fills_path: Path,
    fee_funding_path: Path,
    cash_ledger_path: Path,
    actual_cash_rows_path: Path,
    flat_reconciliation_path: Path,
    stop_condition_path: Path,
    recorded_at: datetime | str | None = None,
) -> ProfitCoreTinyActualCashMeasurement:
    readiness = read_mapping_file(readiness_packet_path)
    adapter = read_mapping_file(external_venue_adapter_path)
    approval = read_mapping_file(human_approval_path)
    order_intent = read_mapping_file(order_intent_path)
    submitted_order = read_mapping_file(submitted_order_path)
    fills = read_mapping_file(fills_path)
    fee_funding = read_mapping_file(fee_funding_path)
    flat = read_mapping_file(flat_reconciliation_path)
    stop = read_mapping_file(stop_condition_path)
    ledger = CryptoPerpCashLedger.model_validate(read_mapping_file(cash_ledger_path))
    rows = _read_actual_cash_rows(actual_cash_rows_path)
    candidate_id = _candidate_id_from_readiness(readiness)
    blockers = _derive_blockers(
        candidate_id=candidate_id,
        readiness=readiness,
        adapter=adapter,
        approval=approval,
        order_intent=order_intent,
        submitted_order=submitted_order,
        fills=fills,
        fee_funding=fee_funding,
        flat=flat,
        stop=stop,
        ledger=ledger,
        rows=rows,
    )
    status = _derive_status(blockers)
    complete = (
        status
        is ProfitCoreTinyActualCashMeasurementStatus.RECORDED_ACTUAL_CASH_REQUIRES_REPORT_GATE
    )
    event_set = sorted({row.event_id for row in rows})
    action_set = sorted({str(row.action) for row in rows})
    rows_total = _rows_actual_cash_total(rows)
    refs = [
        _artifact_ref("readiness_packet", readiness_packet_path, _schema_version(readiness)),
        _artifact_ref(
            "external_venue_adapter",
            external_venue_adapter_path,
            _schema_version(adapter),
        ),
        _artifact_ref("human_approval", human_approval_path, _schema_version(approval)),
        _artifact_ref("order_intent", order_intent_path, _schema_version(order_intent)),
        _artifact_ref("submitted_order", submitted_order_path, _schema_version(submitted_order)),
        _artifact_ref("fills", fills_path, _schema_version(fills)),
        _artifact_ref("fee_funding", fee_funding_path, _schema_version(fee_funding)),
        _artifact_ref("cash_ledger", cash_ledger_path, ledger.schema_version),
        _artifact_ref("actual_cash_rows", actual_cash_rows_path, None),
        _artifact_ref(
            "flat_reconciliation",
            flat_reconciliation_path,
            _schema_version(flat),
        ),
        _artifact_ref("stop_condition", stop_condition_path, _schema_version(stop)),
    ]
    measurement_id = str(
        approval.get("measurement_id")
        or readiness.get("measurement_id")
        or f"{candidate_id}-tiny-actual-cash-measurement"
    )
    return ProfitCoreTinyActualCashMeasurement(
        measurement_id=measurement_id,
        recorded_at=_coerce_datetime(recorded_at),
        producer=ProducerInfo(command="edge-candidate-tiny-actual-cash-measurement-record"),
        candidate_id=candidate_id,
        measurement_status=status,
        blockers=blockers,
        source_refs=refs,
        readiness_packet_ref=refs[0],
        external_venue_adapter_ref=refs[1],
        human_approval_ref=refs[2],
        order_intent_ref=refs[3],
        submitted_order_ref=refs[4],
        fills_ref=refs[5],
        fee_funding_ref=refs[6],
        cash_ledger_ref=refs[7],
        actual_cash_rows_ref=refs[8],
        flat_reconciliation_ref=refs[9],
        stop_condition_ref=refs[10],
        event_set=event_set,
        action_set=action_set,
        row_count=len(rows),
        actual_cash_result_usd=decimal_to_json_string(rows_total)
        if rows_total is not None
        else None,
        cash_ledger_actual_cash_result_usd=decimal_to_json_string(ledger.actual_cash_result_usd),
        no_trade_comparison_present=_has_no_trade_same_event_set(rows),
        flat_reconciled=_flat_reconciled(flat),
        stop_conditions_respected=_stop_conditions_complete(stop),
        actual_cash=complete,
        cash_metric_basis="actual_cash" if complete else "blocked",
    )


def build_and_write_tiny_actual_cash_measurement(
    *,
    readiness_packet_path: Path,
    external_venue_adapter_path: Path,
    human_approval_path: Path,
    order_intent_path: Path,
    submitted_order_path: Path,
    fills_path: Path,
    fee_funding_path: Path,
    cash_ledger_path: Path,
    actual_cash_rows_path: Path,
    flat_reconciliation_path: Path,
    stop_condition_path: Path,
    out_dir: Path,
    recorded_at: datetime | str | None = None,
    replace_existing: bool = False,
) -> TinyActualCashMeasurementWriteResult:
    measurement_path = out_dir / "profit_core_tiny_actual_cash_measurement.json"
    if measurement_path.exists() and not replace_existing:
        raise TinyActualCashMeasurementOutputExistsError(
            f"output already exists: {measurement_path}"
        )
    measurement = build_tiny_actual_cash_measurement(
        readiness_packet_path=readiness_packet_path,
        external_venue_adapter_path=external_venue_adapter_path,
        human_approval_path=human_approval_path,
        order_intent_path=order_intent_path,
        submitted_order_path=submitted_order_path,
        fills_path=fills_path,
        fee_funding_path=fee_funding_path,
        cash_ledger_path=cash_ledger_path,
        actual_cash_rows_path=actual_cash_rows_path,
        flat_reconciliation_path=flat_reconciliation_path,
        stop_condition_path=stop_condition_path,
        recorded_at=recorded_at,
    )
    write_json_artifact(measurement_path, measurement.model_dump(mode="json"))
    return TinyActualCashMeasurementWriteResult(
        measurement=measurement,
        measurement_path=measurement_path,
        measurement_sha256=sha256_file(measurement_path),
    )


def _derive_blockers(
    *,
    candidate_id: str,
    readiness: dict[str, Any],
    adapter: dict[str, Any],
    approval: dict[str, Any],
    order_intent: dict[str, Any],
    submitted_order: dict[str, Any],
    fills: dict[str, Any],
    fee_funding: dict[str, Any],
    flat: dict[str, Any],
    stop: dict[str, Any],
    ledger: CryptoPerpCashLedger,
    rows: list[TournamentEventResult],
) -> list[TinyActualCashBlocker]:
    if not _human_approval_complete(approval, candidate_id):
        return [
            _blocker(
                "HUMAN_APPROVAL_NOT_PRESENT",
                "Human approval artifact is missing or not approved for tiny actual cash.",
                "human_approval",
            )
        ]
    if not _upstream_complete(readiness, adapter):
        return [
            _blocker(
                "UPSTREAM_NOT_COMPLETE",
                "P9 readiness or P10 external adapter evidence is not complete.",
                "upstream",
            )
        ]
    if not _candidate_lineage_matches(
        candidate_id,
        adapter,
        order_intent,
        submitted_order,
        fills,
        fee_funding,
        flat,
        stop,
    ):
        return [
            _blocker(
                "CANDIDATE_LINEAGE_MISMATCH",
                "Candidate ids do not match across P11 input artifacts.",
                "candidate_lineage",
            )
        ]
    if not _submitted_order_actual_cash(submitted_order) or not _actual_cash_evidence(
        fills, fee_funding
    ):
        return [
            _blocker(
                "NON_ACTUAL_CASH_BASIS",
                "Submitted order, fills, or fee/funding evidence is not actual cash.",
                "actual_cash_evidence",
            )
        ]
    if not _rows_are_actual_cash(rows):
        return [
            _blocker(
                "NON_ACTUAL_CASH_BASIS",
                "Actual cash rows must all use cash_metric_basis=actual_cash.",
                "actual_cash_rows",
            )
        ]
    if not _has_no_trade_same_event_set(rows):
        return [
            _blocker(
                "NO_TRADE_COMPARISON_MISSING",
                "NO_TRADE comparison must exist for each actual cash event.",
                "actual_cash_rows",
            )
        ]
    rows_total = _rows_actual_cash_total(rows)
    if rows_total != ledger.actual_cash_result_usd:
        return [
            _blocker(
                "CASH_LEDGER_RESULT_MISMATCH",
                "Actual cash rows total must match cash ledger actual_cash_result_usd.",
                "cash_ledger",
            )
        ]
    if not _flat_reconciled(flat):
        return [
            _blocker(
                "FLAT_RECONCILIATION_MISSING",
                "Flat reconciliation must confirm no open position and cash ledger reconciliation.",
                "flat_reconciliation",
            )
        ]
    if not _stop_conditions_complete(stop):
        return [
            _blocker(
                "STOP_CONDITION_INCOMPLETE",
                "Loss, venue, credential, legal, and respected stop conditions are required.",
                "stop_condition",
            )
        ]
    return []


def _derive_status(
    blockers: list[TinyActualCashBlocker],
) -> ProfitCoreTinyActualCashMeasurementStatus:
    if not blockers:
        return ProfitCoreTinyActualCashMeasurementStatus.RECORDED_ACTUAL_CASH_REQUIRES_REPORT_GATE
    code = blockers[0].blocker_code
    if code == "HUMAN_APPROVAL_NOT_PRESENT":
        return ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_HUMAN_APPROVAL
    if code == "UPSTREAM_NOT_COMPLETE":
        return ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_UPSTREAM
    if code == "NON_ACTUAL_CASH_BASIS":
        return ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_NON_ACTUAL_CASH_BASIS
    if code == "NO_TRADE_COMPARISON_MISSING":
        return ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_MISSING_NO_TRADE_COMPARISON
    if code == "FLAT_RECONCILIATION_MISSING":
        return ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_FLAT_RECONCILIATION
    if code == "STOP_CONDITION_INCOMPLETE":
        return ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_STOP_CONDITION
    return ProfitCoreTinyActualCashMeasurementStatus.BLOCKED_CANDIDATE_LINEAGE


def _human_approval_complete(approval: dict[str, Any], candidate_id: str) -> bool:
    return (
        approval.get("approved") is True
        and approval.get("approval_scope") == "tiny_actual_cash_measurement"
        and approval.get("candidate_id") == candidate_id
    )


def _upstream_complete(readiness: dict[str, Any], adapter: dict[str, Any]) -> bool:
    return (
        readiness.get("readiness_status") == "PACKET_COMPLETE_REQUIRES_HUMAN_APPROVAL"
        and adapter.get("adapter_status") == "RECORDED_EXTERNAL_READ_ONLY_REQUIRES_HUMAN_REVIEW"
    )


def _candidate_lineage_matches(candidate_id: str, *payloads: dict[str, Any]) -> bool:
    return all(payload.get("candidate_id") == candidate_id for payload in payloads)


def _submitted_order_actual_cash(submitted_order: dict[str, Any]) -> bool:
    return (
        submitted_order.get("actual_cash") is True
        and submitted_order.get("paper") is False
        and submitted_order.get("demo") is False
        and submitted_order.get("testnet") is False
        and submitted_order.get("source_kind") == "actual_exchange_order"
    )


def _actual_cash_evidence(fills: dict[str, Any], fee_funding: dict[str, Any]) -> bool:
    return (
        fills.get("actual_cash") is True
        and bool(fills.get("fills"))
        and fee_funding.get("actual_cash") is True
        and "total_fees_usd" in fee_funding
        and "total_funding_usd" in fee_funding
    )


def _rows_are_actual_cash(rows: list[TournamentEventResult]) -> bool:
    return bool(rows) and all(
        row.cash_metric_basis == "actual_cash" and row.actual_cash_result_usd is not None
        for row in rows
    )


def _has_no_trade_same_event_set(rows: list[TournamentEventResult]) -> bool:
    event_set = {row.event_id for row in rows}
    no_trade_events = {row.event_id for row in rows if row.action == "NO_TRADE"}
    action_events = {row.event_id for row in rows if row.action != "NO_TRADE"}
    return bool(event_set) and event_set == no_trade_events and event_set == action_events


def _rows_actual_cash_total(rows: list[TournamentEventResult]) -> Decimal | None:
    if not _rows_are_actual_cash(rows):
        return None
    return sum((row.actual_cash_result_usd or Decimal("0") for row in rows), Decimal("0"))


def _flat_reconciled(flat: dict[str, Any]) -> bool:
    return (
        flat.get("reconciled_flat") is True
        and flat.get("open_position_count") == 0
        and flat.get("cash_ledger_reconciled") is True
    )


def _stop_conditions_complete(stop: dict[str, Any]) -> bool:
    return all(
        stop.get(key) is True
        for key in (
            "loss_stop_defined",
            "venue_stop_defined",
            "credential_stop_defined",
            "legal_stop_defined",
            "stop_conditions_respected",
        )
    )


def _read_actual_cash_rows(path: Path) -> list[TournamentEventResult]:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise TinyActualCashMeasurementError("actual cash rows file is empty")
    try:
        if text.startswith("["):
            raw_rows = json.loads(text)
        else:
            raw_rows = [json.loads(line) for line in text.splitlines() if line.strip()]
    except json.JSONDecodeError as exc:
        raise TinyActualCashMeasurementError(
            "actual cash rows must be JSONL or JSON array"
        ) from exc
    if not isinstance(raw_rows, list):
        raise TinyActualCashMeasurementError("actual cash rows must be a list")
    return [TournamentEventResult.model_validate(row) for row in raw_rows]


def _candidate_id_from_readiness(readiness: dict[str, Any]) -> str:
    candidate_id = str(readiness.get("candidate_id") or "").strip()
    if not ID_PATTERN.fullmatch(candidate_id):
        raise TinyActualCashMeasurementError("readiness packet candidate_id is missing")
    return candidate_id


def _schema_version(payload: dict[str, Any]) -> str | None:
    value = payload.get("schema_version")
    return value if isinstance(value, str) and value else None


def _artifact_ref(
    role: str,
    path: Path,
    schema_version: str | None,
) -> TinyActualCashArtifactRef:
    return TinyActualCashArtifactRef(
        artifact_role=role,
        path=path.as_posix(),
        sha256=sha256_file(path),
        schema_version=schema_version,
    )


def _blocker(code: str, message: str, source: str) -> TinyActualCashBlocker:
    return TinyActualCashBlocker(blocker_code=code, message=message, source=source)


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    return ensure_utc_aware("recorded_at", value)


__all__ = [
    "ProfitCoreTinyActualCashMeasurement",
    "ProfitCoreTinyActualCashMeasurementStatus",
    "TinyActualCashArtifactRef",
    "TinyActualCashBlocker",
    "TinyActualCashMeasurementError",
    "TinyActualCashMeasurementOutputExistsError",
    "TinyActualCashMeasurementWriteResult",
    "build_and_write_tiny_actual_cash_measurement",
    "build_tiny_actual_cash_measurement",
]
