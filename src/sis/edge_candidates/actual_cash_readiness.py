from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN
from sis.edge_candidates import PROFIT_CORE_ACTUAL_CASH_READINESS_PACKET_SCHEMA_VERSION
from sis.edge_candidates.adversarial_review import ProfitCoreAdversarialReview
from sis.edge_candidates.evidence_packet import ProfitCoreEvidencePacket
from sis.edge_candidates.risk_taker_sprint_isolation import RiskTakerSprintIsolation
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact
from sis.strategy_inputs.models import ProducerInfo


SENSITIVE_KEY_FRAGMENTS = {
    "api_key",
    "password",
    "private_key",
    "secret",
    "seed_phrase",
    "token",
    "credential_value",
}


class ProfitCoreActualCashReadinessStatus(StrEnum):
    PACKET_COMPLETE_REQUIRES_HUMAN_APPROVAL = "PACKET_COMPLETE_REQUIRES_HUMAN_APPROVAL"
    BLOCKED_READINESS_CONTROLS = "BLOCKED_READINESS_CONTROLS"
    BLOCKED_ADVERSARIAL_REVIEW = "BLOCKED_ADVERSARIAL_REVIEW"
    BLOCKED_PROMOTION_DEBT = "BLOCKED_PROMOTION_DEBT"


class ActualCashReadinessArtifactRef(BaseModel):
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


class ActualCashReadinessRiskLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_notional_usd: str
    max_daily_loss_usd: str
    max_order_count: int = Field(ge=1)
    max_position_count: int = Field(ge=1)
    leverage_cap: str

    @field_validator("max_notional_usd", "max_daily_loss_usd", "leverage_cap", mode="before")
    @classmethod
    def validate_positive_decimal(cls, value: Any, info) -> str:
        return _positive_decimal_string(value, label=info.field_name)


class ActualCashReadinessAccountControls(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    isolated_margin_required: Literal[True]
    withdrawal_disabled_required: Literal[True]
    ip_restriction_required: Literal[True]
    credential_storage_confirmed: bool
    credential_created: Literal[False] = False
    credential_used: Literal[False] = False
    credential_use_allowed: Literal[False] = False


class ActualCashReadinessOperationalControls(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    flat_reconciliation_steps: list[str] = Field(default_factory=list)
    rollback_steps: list[str] = Field(default_factory=list)
    kill_switch_steps: list[str] = Field(default_factory=list)
    stop_conditions: list[str] = Field(default_factory=list)

    @field_validator(
        "flat_reconciliation_steps",
        "rollback_steps",
        "kill_switch_steps",
        "stop_conditions",
    )
    @classmethod
    def validate_text_list(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value)


class ActualCashReadinessVenueTermsJurisdictionRecheck(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    required: Literal[True]
    official_docs_required: Literal[True]
    jurisdiction_acknowledged: bool
    user_account_conditions_required: Literal[True]
    notes: list[str] = Field(default_factory=list)

    @field_validator("notes")
    @classmethod
    def validate_notes(cls, value: list[str]) -> list[str]:
        return _clean_text_list(value)


class ActualCashReadinessApprovalControls(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    human_approval_required: Literal[True]
    approval_artifact_required: Literal[True]
    dry_run_first_required: Literal[True]


class ActualCashReadinessPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    measurement_id: str
    risk_limits: ActualCashReadinessRiskLimits
    account_controls: ActualCashReadinessAccountControls
    operational_controls: ActualCashReadinessOperationalControls
    venue_terms_jurisdiction_recheck: ActualCashReadinessVenueTermsJurisdictionRecheck
    approval_controls: ActualCashReadinessApprovalControls

    @field_validator("measurement_id")
    @classmethod
    def validate_measurement_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("measurement_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped


class ActualCashReadinessBlocker(BaseModel):
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


class ProfitCoreActualCashReadinessPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["profit_core_actual_cash_readiness_packet.v1"] = (
        PROFIT_CORE_ACTUAL_CASH_READINESS_PACKET_SCHEMA_VERSION
    )
    packet_id: str
    recorded_at: datetime
    producer: ProducerInfo
    candidate_id: str
    measurement_id: str
    source_refs: list[ActualCashReadinessArtifactRef] = Field(min_length=3)
    evidence_packet_ref: ActualCashReadinessArtifactRef
    adversarial_review_ref: ActualCashReadinessArtifactRef
    readiness_plan_ref: ActualCashReadinessArtifactRef
    risk_sprint_isolation_ref: ActualCashReadinessArtifactRef | None = None
    readiness_status: ProfitCoreActualCashReadinessStatus
    blockers: list[ActualCashReadinessBlocker] = Field(default_factory=list)
    risk_limits: ActualCashReadinessRiskLimits
    account_controls: ActualCashReadinessAccountControls
    operational_controls: ActualCashReadinessOperationalControls
    venue_terms_jurisdiction_recheck: ActualCashReadinessVenueTermsJurisdictionRecheck
    approval_controls: ActualCashReadinessApprovalControls
    requires_human_approval: Literal[True] = True
    packet_is_execution_permission: Literal[False] = False
    actual_cash_execution_allowed: Literal[False] = False
    tiny_live_allowed: Literal[False] = False
    paper_execution_allowed: Literal[False] = False
    credential_created: Literal[False] = False
    credential_used: Literal[False] = False
    credential_use_allowed: Literal[False] = False
    exchange_write_used: Literal[False] = False
    exchange_write_allowed: Literal[False] = False
    live_order_submitted: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    external_send_performed: Literal[False] = False
    boundary: dict[str, bool] = Field(
        default_factory=lambda: {
            "actual_cash_execution_allowed": False,
            "tiny_live_allowed": False,
            "paper_execution_allowed": False,
            "credential_created": False,
            "credential_used": False,
            "credential_use_allowed": False,
            "exchange_write_used": False,
            "exchange_write_allowed": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "external_send_performed": False,
            "packet_is_execution_permission": False,
        }
    )

    @field_validator("packet_id", "candidate_id", "measurement_id")
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
            "actual_cash_execution_allowed": False,
            "tiny_live_allowed": False,
            "paper_execution_allowed": False,
            "credential_created": False,
            "credential_used": False,
            "credential_use_allowed": False,
            "exchange_write_used": False,
            "exchange_write_allowed": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "external_send_performed": False,
            "packet_is_execution_permission": False,
        }
        if value != expected:
            raise ValueError("boundary must keep all actual-cash execution permissions false")
        return value

    @field_serializer("recorded_at")
    def serialize_recorded_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class ActualCashReadinessPacketWriteResult:
    packet: ProfitCoreActualCashReadinessPacket
    packet_path: Path
    packet_sha256: str


class ActualCashReadinessPacketError(ValueError):
    pass


class ActualCashReadinessPacketOutputExistsError(ActualCashReadinessPacketError):
    pass


def build_actual_cash_readiness_packet(
    *,
    evidence_packet_path: Path,
    adversarial_review_path: Path,
    readiness_plan_path: Path,
    risk_sprint_isolation_path: Path | None,
    recorded_at: datetime | str | None = None,
) -> ProfitCoreActualCashReadinessPacket:
    evidence_packet = ProfitCoreEvidencePacket.model_validate(
        read_mapping_file(evidence_packet_path)
    )
    adversarial_review = ProfitCoreAdversarialReview.model_validate(
        read_mapping_file(adversarial_review_path)
    )
    if evidence_packet.candidate_id != adversarial_review.candidate_id:
        raise ActualCashReadinessPacketError(
            "evidence packet and adversarial review candidate_id mismatch"
        )
    raw_plan = read_mapping_file(readiness_plan_path)
    secret_hits = _find_sensitive_keys(raw_plan)
    if secret_hits:
        raise ActualCashReadinessPacketError(
            "readiness plan contains secret-like key material: " + ", ".join(secret_hits)
        )
    readiness_plan = ActualCashReadinessPlan.model_validate(raw_plan)
    risk_sprint_isolation = _read_optional_risk_sprint_isolation(risk_sprint_isolation_path)
    blockers = _derive_blockers(
        adversarial_review=adversarial_review,
        readiness_plan=readiness_plan,
        risk_sprint_isolation=risk_sprint_isolation,
    )
    readiness_status = _derive_status(blockers)
    refs = [
        _artifact_ref(
            "evidence_packet",
            evidence_packet_path,
            evidence_packet.schema_version,
        ),
        _artifact_ref(
            "adversarial_review",
            adversarial_review_path,
            adversarial_review.schema_version,
        ),
        _artifact_ref("readiness_plan", readiness_plan_path, None),
    ]
    risk_sprint_ref = None
    if risk_sprint_isolation_path is not None and risk_sprint_isolation is not None:
        risk_sprint_ref = _artifact_ref(
            "risk_sprint_isolation",
            risk_sprint_isolation_path,
            risk_sprint_isolation.schema_version,
        )
        refs.append(risk_sprint_ref)
    return ProfitCoreActualCashReadinessPacket(
        packet_id=f"{evidence_packet.candidate_id}-actual-cash-readiness-packet",
        recorded_at=_coerce_datetime(recorded_at),
        producer=ProducerInfo(command="edge-candidate-actual-cash-readiness-packet-build"),
        candidate_id=evidence_packet.candidate_id,
        measurement_id=readiness_plan.measurement_id,
        source_refs=refs,
        evidence_packet_ref=refs[0],
        adversarial_review_ref=refs[1],
        readiness_plan_ref=refs[2],
        risk_sprint_isolation_ref=risk_sprint_ref,
        readiness_status=readiness_status,
        blockers=blockers,
        risk_limits=readiness_plan.risk_limits,
        account_controls=readiness_plan.account_controls,
        operational_controls=readiness_plan.operational_controls,
        venue_terms_jurisdiction_recheck=readiness_plan.venue_terms_jurisdiction_recheck,
        approval_controls=readiness_plan.approval_controls,
    )


def build_and_write_actual_cash_readiness_packet(
    *,
    evidence_packet_path: Path,
    adversarial_review_path: Path,
    readiness_plan_path: Path,
    risk_sprint_isolation_path: Path | None,
    out_dir: Path,
    recorded_at: datetime | str | None = None,
    replace_existing: bool = False,
) -> ActualCashReadinessPacketWriteResult:
    packet_path = out_dir / "profit_core_actual_cash_readiness_packet.json"
    if packet_path.exists() and not replace_existing:
        raise ActualCashReadinessPacketOutputExistsError(f"output already exists: {packet_path}")
    packet = build_actual_cash_readiness_packet(
        evidence_packet_path=evidence_packet_path,
        adversarial_review_path=adversarial_review_path,
        readiness_plan_path=readiness_plan_path,
        risk_sprint_isolation_path=risk_sprint_isolation_path,
        recorded_at=recorded_at,
    )
    write_json_artifact(packet_path, packet.model_dump(mode="json"))
    return ActualCashReadinessPacketWriteResult(
        packet=packet,
        packet_path=packet_path,
        packet_sha256=sha256_file(packet_path),
    )


def _derive_blockers(
    *,
    adversarial_review: ProfitCoreAdversarialReview,
    readiness_plan: ActualCashReadinessPlan,
    risk_sprint_isolation: RiskTakerSprintIsolation | None,
) -> list[ActualCashReadinessBlocker]:
    blockers: list[ActualCashReadinessBlocker] = []
    if adversarial_review.hard_blocker_count > 0:
        blockers.append(
            ActualCashReadinessBlocker(
                blocker_code="ADVERSARIAL_REVIEW_HARD_BLOCKER",
                message="Adversarial review has machine-checkable hard blockers.",
                source="adversarial_review",
            )
        )
    blockers.extend(_readiness_control_blockers(readiness_plan))
    if risk_sprint_isolation is not None and any(
        debt.blocks_actual_cash for debt in risk_sprint_isolation.promotion_debt
    ):
        blockers.append(
            ActualCashReadinessBlocker(
                blocker_code="RISK_TAKER_SPRINT_PROMOTION_DEBT",
                message="Risk-taker sprint promotion debt blocks actual-cash readiness.",
                source="risk_sprint_isolation",
            )
        )
    return blockers


def _readiness_control_blockers(
    readiness_plan: ActualCashReadinessPlan,
) -> list[ActualCashReadinessBlocker]:
    blockers: list[ActualCashReadinessBlocker] = []
    controls = readiness_plan.operational_controls
    if not controls.stop_conditions:
        blockers.append(
            _control_blocker("MISSING_STOP_CONDITION", "Stop conditions must be explicit.")
        )
    if not controls.flat_reconciliation_steps:
        blockers.append(
            _control_blocker(
                "MISSING_FLAT_RECONCILIATION",
                "Flat reconciliation steps must be explicit.",
            )
        )
    if not controls.rollback_steps:
        blockers.append(_control_blocker("MISSING_ROLLBACK_PLAN", "Rollback steps are missing."))
    if not controls.kill_switch_steps:
        blockers.append(_control_blocker("MISSING_KILL_SWITCH", "Kill switch steps are missing."))
    if not readiness_plan.account_controls.credential_storage_confirmed:
        blockers.append(
            _control_blocker(
                "MISSING_CREDENTIAL_STORAGE_CONFIRMATION",
                "Credential storage confirmation is missing.",
            )
        )
    if not readiness_plan.venue_terms_jurisdiction_recheck.jurisdiction_acknowledged:
        blockers.append(
            _control_blocker(
                "JURISDICTION_RECHECK_NOT_ACKNOWLEDGED",
                "Jurisdiction recheck must be acknowledged before approval input is complete.",
            )
        )
    return blockers


def _derive_status(
    blockers: list[ActualCashReadinessBlocker],
) -> ProfitCoreActualCashReadinessStatus:
    blocker_codes = {blocker.blocker_code for blocker in blockers}
    if "ADVERSARIAL_REVIEW_HARD_BLOCKER" in blocker_codes:
        return ProfitCoreActualCashReadinessStatus.BLOCKED_ADVERSARIAL_REVIEW
    if "RISK_TAKER_SPRINT_PROMOTION_DEBT" in blocker_codes:
        return ProfitCoreActualCashReadinessStatus.BLOCKED_PROMOTION_DEBT
    if blockers:
        return ProfitCoreActualCashReadinessStatus.BLOCKED_READINESS_CONTROLS
    return ProfitCoreActualCashReadinessStatus.PACKET_COMPLETE_REQUIRES_HUMAN_APPROVAL


def _control_blocker(code: str, message: str) -> ActualCashReadinessBlocker:
    return ActualCashReadinessBlocker(
        blocker_code=code,
        message=message,
        source="readiness_plan",
    )


def _read_optional_risk_sprint_isolation(path: Path | None) -> RiskTakerSprintIsolation | None:
    if path is None:
        return None
    return RiskTakerSprintIsolation.model_validate(read_mapping_file(path))


def _find_sensitive_keys(payload: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            key_path = f"{prefix}.{key_text}" if prefix else key_text
            lowered = key_text.lower()
            if any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS):
                hits.append(key_path)
            hits.extend(_find_sensitive_keys(value, key_path))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            hits.extend(_find_sensitive_keys(item, f"{prefix}[{index}]"))
    return hits


def _artifact_ref(
    role: str,
    path: Path,
    schema_version: str | None,
) -> ActualCashReadinessArtifactRef:
    return ActualCashReadinessArtifactRef(
        artifact_role=role,
        path=path.as_posix(),
        sha256=sha256_file(path),
        schema_version=schema_version,
    )


def _positive_decimal_string(value: Any, *, label: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError(f"{label} must not be empty")
    try:
        decimal = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"{label} must be a decimal string") from exc
    if decimal <= 0:
        raise ValueError(f"{label} must be positive")
    return format(decimal.normalize(), "f")


def _clean_text_list(value: list[str]) -> list[str]:
    cleaned: list[str] = []
    for item in value:
        stripped = item.strip()
        if not stripped:
            raise ValueError("list items must not be empty")
        cleaned.append(stripped)
    return cleaned


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    return ensure_utc_aware("recorded_at", value)


__all__ = [
    "ActualCashReadinessAccountControls",
    "ActualCashReadinessApprovalControls",
    "ActualCashReadinessArtifactRef",
    "ActualCashReadinessBlocker",
    "ActualCashReadinessOperationalControls",
    "ActualCashReadinessPacketError",
    "ActualCashReadinessPacketOutputExistsError",
    "ActualCashReadinessPacketWriteResult",
    "ActualCashReadinessPlan",
    "ActualCashReadinessRiskLimits",
    "ActualCashReadinessVenueTermsJurisdictionRecheck",
    "ProfitCoreActualCashReadinessPacket",
    "ProfitCoreActualCashReadinessStatus",
    "build_actual_cash_readiness_packet",
    "build_and_write_actual_cash_readiness_packet",
]
