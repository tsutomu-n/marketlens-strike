from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN
from sis.edge_candidates import PROFIT_CORE_EXTERNAL_VENUE_ADAPTER_RUN_SCHEMA_VERSION
from sis.edge_candidates.virtual_execution_gate import (
    VirtualExecutionGateDecision,
    VirtualExecutionGateState,
)
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact
from sis.strategy_inputs.models import ProducerInfo


REQUIRED_BITGET_DOC_IDS = {
    "bitget_demo_rest_api",
    "bitget_request_interaction_rate_limit",
    "bitget_terms_of_use",
}
SENSITIVE_KEY_FRAGMENTS = {
    "access-key",
    "access-sign",
    "access-passphrase",
    "api-key",
    "api_key",
    "apikey",
    "passphrase",
    "password",
    "private_key",
    "secret",
    "signature",
    "token",
}
REDACTED_VALUES = {"[REDACTED]", "REDACTED", "***"}


class ProfitCoreExternalVenueAdapterStatus(StrEnum):
    RECORDED_EXTERNAL_READ_ONLY_REQUIRES_HUMAN_REVIEW = (
        "RECORDED_EXTERNAL_READ_ONLY_REQUIRES_HUMAN_REVIEW"
    )
    BLOCKED_NETWORK_OPT_IN = "BLOCKED_NETWORK_OPT_IN"
    BLOCKED_RECORDED_RESPONSE_MISSING = "BLOCKED_RECORDED_RESPONSE_MISSING"
    BLOCKED_OFFICIAL_DOCS_VERIFICATION = "BLOCKED_OFFICIAL_DOCS_VERIFICATION"
    BLOCKED_LOCAL_VIRTUAL_GATE = "BLOCKED_LOCAL_VIRTUAL_GATE"
    BLOCKED_BOUNDARY_VIOLATION = "BLOCKED_BOUNDARY_VIOLATION"


class ExternalVenueAdapterArtifactRef(BaseModel):
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


class ExternalVenueAdapterBlocker(BaseModel):
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


class ExternalVenueOfficialDocRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    doc_id: str
    url: str
    verified_at_jst: str
    finding_summary: str

    @field_validator("doc_id")
    @classmethod
    def validate_doc_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("doc_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped.startswith("https://"):
            raise ValueError("official doc url must be https")
        return stripped

    @field_validator("verified_at_jst", "finding_summary")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("official doc text fields must not be empty")
        return stripped


class ExternalVenueRecordedHTTP(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str
    endpoint_id: str
    method: Literal["GET"]
    url: str
    request_headers: dict[str, str] = Field(default_factory=dict)
    request_params: dict[str, str] = Field(default_factory=dict)
    status_code: int = Field(ge=100, le=599)
    response_body_sha256: str
    recorded_at: datetime
    source_kind: Literal["manual_recorded_response", "fixture_recorded_response"]
    raw_response_body_stored: Literal[False] = False

    @field_validator("record_id", "endpoint_id")
    @classmethod
    def validate_ids(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("record ids must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped.startswith("https://"):
            raise ValueError("recorded http url must be https")
        return stripped

    @field_validator("request_headers", "request_params", mode="before")
    @classmethod
    def normalize_mapping(cls, value: Any) -> dict[str, str]:
        if value is None:
            return {}
        if not isinstance(value, dict):
            raise ValueError("request mappings must be objects")
        return {str(key): str(item) for key, item in value.items()}

    @field_validator("response_body_sha256")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped.startswith("sha256:") or len(stripped) != 71:
            raise ValueError("response_body_sha256 must be sha256:<64 hex chars>")
        return stripped

    @field_validator("recorded_at", mode="before")
    @classmethod
    def validate_recorded_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("recorded_at", value)

    @field_serializer("recorded_at")
    def serialize_recorded_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


class ExternalVenueRateLimitPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_requests_per_second: int = Field(ge=1)
    source_doc_id: str

    @field_validator("source_doc_id")
    @classmethod
    def validate_source_doc_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("source_doc_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped


class ExternalVenueCredentialPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    credentials_required: Literal[False]
    credentials_used: Literal[False]
    credential_values_redacted: Literal[True]


class ExternalVenueAdapterPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    run_id: str
    venue: Literal["bitget"]
    adapter_mode: Literal["public_read_only"]
    network_opt_in: bool
    official_doc_refs: list[ExternalVenueOfficialDocRef] = Field(default_factory=list)
    recorded_http: list[ExternalVenueRecordedHTTP] = Field(default_factory=list)
    rate_limit_policy: ExternalVenueRateLimitPolicy
    operator_jurisdiction_recheck_required: Literal[True]
    credential_policy: ExternalVenueCredentialPolicy

    @field_validator("run_id")
    @classmethod
    def validate_run_id(cls, value: str) -> str:
        stripped = value.strip()
        if not ID_PATTERN.fullmatch(stripped):
            raise ValueError("run_id must match ^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
        return stripped


class ProfitCoreExternalVenueAdapterRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["profit_core_external_venue_adapter_run.v1"] = (
        PROFIT_CORE_EXTERNAL_VENUE_ADAPTER_RUN_SCHEMA_VERSION
    )
    run_id: str
    recorded_at: datetime
    producer: ProducerInfo
    candidate_id: str
    venue: Literal["bitget"]
    adapter_mode: Literal["public_read_only"]
    adapter_status: ProfitCoreExternalVenueAdapterStatus
    blockers: list[ExternalVenueAdapterBlocker] = Field(default_factory=list)
    source_refs: list[ExternalVenueAdapterArtifactRef] = Field(min_length=2)
    virtual_gate_ref: ExternalVenueAdapterArtifactRef
    adapter_plan_ref: ExternalVenueAdapterArtifactRef
    official_doc_refs: list[ExternalVenueOfficialDocRef]
    recorded_http: list[ExternalVenueRecordedHTTP]
    rate_limit_policy: ExternalVenueRateLimitPolicy
    operator_jurisdiction_recheck_required: Literal[True]
    network_opt_in: bool
    network_attempted: Literal[False] = False
    credentials_required: Literal[False] = False
    credentials_used: Literal[False] = False
    credential_values_redacted: Literal[True] = True
    external_read_recorded: bool
    external_write_used: Literal[False] = False
    exchange_write_allowed: Literal[False] = False
    order_submit_allowed: Literal[False] = False
    live_order_submitted: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    actual_cash: Literal[False] = False
    demo_or_testnet_result_is_actual_cash: Literal[False] = False
    profit_evidence: Literal[False] = False
    boundary: dict[str, bool] = Field(
        default_factory=lambda: {
            "network_attempted": False,
            "credentials_used": False,
            "external_write_used": False,
            "exchange_write_allowed": False,
            "order_submit_allowed": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "actual_cash": False,
            "demo_or_testnet_result_is_actual_cash": False,
            "profit_evidence": False,
        }
    )

    @field_validator("run_id", "candidate_id")
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
            "network_attempted": False,
            "credentials_used": False,
            "external_write_used": False,
            "exchange_write_allowed": False,
            "order_submit_allowed": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "actual_cash": False,
            "demo_or_testnet_result_is_actual_cash": False,
            "profit_evidence": False,
        }
        if value != expected:
            raise ValueError("boundary must keep external write/live/actual-cash fields false")
        return value

    @field_serializer("recorded_at")
    def serialize_recorded_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class ExternalVenueAdapterRunWriteResult:
    run: ProfitCoreExternalVenueAdapterRun
    run_path: Path
    run_sha256: str


class ExternalVenueAdapterRunError(ValueError):
    pass


class ExternalVenueAdapterRunOutputExistsError(ExternalVenueAdapterRunError):
    pass


def build_external_venue_adapter_run(
    *,
    virtual_gate_path: Path,
    adapter_plan_path: Path,
    recorded_at: datetime | str | None = None,
) -> ProfitCoreExternalVenueAdapterRun:
    virtual_gate = VirtualExecutionGateDecision.model_validate(read_mapping_file(virtual_gate_path))
    raw_plan = read_mapping_file(adapter_plan_path)
    secret_hits = _find_unredacted_sensitive_values(raw_plan.get("recorded_http", []))
    if secret_hits:
        raise ExternalVenueAdapterRunError(
            "adapter plan contains secret-like recorded HTTP material: " + ", ".join(secret_hits)
        )
    adapter_plan = ExternalVenueAdapterPlan.model_validate(raw_plan)
    blockers = _derive_blockers(virtual_gate=virtual_gate, adapter_plan=adapter_plan)
    adapter_status = _derive_status(blockers)
    refs = [
        _artifact_ref("virtual_gate", virtual_gate_path, virtual_gate.schema_version),
        _artifact_ref("adapter_plan", adapter_plan_path, None),
    ]
    return ProfitCoreExternalVenueAdapterRun(
        run_id=adapter_plan.run_id,
        recorded_at=_coerce_datetime(recorded_at),
        producer=ProducerInfo(command="edge-candidate-external-venue-adapter-record"),
        candidate_id=virtual_gate.candidate_id,
        venue=adapter_plan.venue,
        adapter_mode=adapter_plan.adapter_mode,
        adapter_status=adapter_status,
        blockers=blockers,
        source_refs=refs,
        virtual_gate_ref=refs[0],
        adapter_plan_ref=refs[1],
        official_doc_refs=adapter_plan.official_doc_refs,
        recorded_http=adapter_plan.recorded_http,
        rate_limit_policy=adapter_plan.rate_limit_policy,
        operator_jurisdiction_recheck_required=(
            adapter_plan.operator_jurisdiction_recheck_required
        ),
        network_opt_in=adapter_plan.network_opt_in,
        credentials_required=adapter_plan.credential_policy.credentials_required,
        credentials_used=adapter_plan.credential_policy.credentials_used,
        credential_values_redacted=adapter_plan.credential_policy.credential_values_redacted,
        external_read_recorded=bool(adapter_plan.recorded_http),
    )


def build_and_write_external_venue_adapter_run(
    *,
    virtual_gate_path: Path,
    adapter_plan_path: Path,
    out_dir: Path,
    recorded_at: datetime | str | None = None,
    replace_existing: bool = False,
) -> ExternalVenueAdapterRunWriteResult:
    run_path = out_dir / "profit_core_external_venue_adapter_run.json"
    if run_path.exists() and not replace_existing:
        raise ExternalVenueAdapterRunOutputExistsError(f"output already exists: {run_path}")
    run = build_external_venue_adapter_run(
        virtual_gate_path=virtual_gate_path,
        adapter_plan_path=adapter_plan_path,
        recorded_at=recorded_at,
    )
    write_json_artifact(run_path, run.model_dump(mode="json"))
    return ExternalVenueAdapterRunWriteResult(
        run=run,
        run_path=run_path,
        run_sha256=sha256_file(run_path),
    )


def _derive_blockers(
    *,
    virtual_gate: VirtualExecutionGateDecision,
    adapter_plan: ExternalVenueAdapterPlan,
) -> list[ExternalVenueAdapterBlocker]:
    blockers: list[ExternalVenueAdapterBlocker] = []
    if virtual_gate.gate_state is not VirtualExecutionGateState.LOCAL_MOCK_VERIFIED:
        blockers.append(
            ExternalVenueAdapterBlocker(
                blocker_code="LOCAL_VIRTUAL_GATE_NOT_VERIFIED",
                message="External venue adapter evidence requires LOCAL_MOCK_VERIFIED first.",
                source="virtual_gate",
            )
        )
    if not _required_docs_present(adapter_plan.official_doc_refs):
        blockers.append(
            ExternalVenueAdapterBlocker(
                blocker_code="OFFICIAL_DOC_VERIFICATION_INCOMPLETE",
                message="Bitget official docs verification refs are incomplete.",
                source="adapter_plan",
            )
        )
    if not adapter_plan.network_opt_in:
        blockers.append(
            ExternalVenueAdapterBlocker(
                blocker_code="NETWORK_OPT_IN_REQUIRED",
                message="External venue evidence requires explicit network opt-in metadata.",
                source="adapter_plan",
            )
        )
    if not adapter_plan.recorded_http:
        blockers.append(
            ExternalVenueAdapterBlocker(
                blocker_code="RECORDED_REQUEST_RESPONSE_REQUIRED",
                message="Recorded request/response artifact is required.",
                source="adapter_plan",
            )
        )
    if adapter_plan.credential_policy.credentials_used:
        blockers.append(
            ExternalVenueAdapterBlocker(
                blocker_code="CREDENTIAL_USE_NOT_ALLOWED",
                message="P10 public read-only adapter evidence must not use credentials.",
                source="adapter_plan",
            )
        )
    return blockers


def _derive_status(
    blockers: list[ExternalVenueAdapterBlocker],
) -> ProfitCoreExternalVenueAdapterStatus:
    blocker_codes = {blocker.blocker_code for blocker in blockers}
    if "LOCAL_VIRTUAL_GATE_NOT_VERIFIED" in blocker_codes:
        return ProfitCoreExternalVenueAdapterStatus.BLOCKED_LOCAL_VIRTUAL_GATE
    if "CREDENTIAL_USE_NOT_ALLOWED" in blocker_codes:
        return ProfitCoreExternalVenueAdapterStatus.BLOCKED_BOUNDARY_VIOLATION
    if "OFFICIAL_DOC_VERIFICATION_INCOMPLETE" in blocker_codes:
        return ProfitCoreExternalVenueAdapterStatus.BLOCKED_OFFICIAL_DOCS_VERIFICATION
    if "NETWORK_OPT_IN_REQUIRED" in blocker_codes:
        return ProfitCoreExternalVenueAdapterStatus.BLOCKED_NETWORK_OPT_IN
    if "RECORDED_REQUEST_RESPONSE_REQUIRED" in blocker_codes:
        return ProfitCoreExternalVenueAdapterStatus.BLOCKED_RECORDED_RESPONSE_MISSING
    return ProfitCoreExternalVenueAdapterStatus.RECORDED_EXTERNAL_READ_ONLY_REQUIRES_HUMAN_REVIEW


def _required_docs_present(refs: list[ExternalVenueOfficialDocRef]) -> bool:
    return REQUIRED_BITGET_DOC_IDS.issubset({ref.doc_id for ref in refs})


def _find_unredacted_sensitive_values(payload: Any, prefix: str = "") -> list[str]:
    hits: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            key_text = str(key)
            key_path = f"{prefix}.{key_text}" if prefix else key_text
            if _is_sensitive_key(key_text) and str(value) not in REDACTED_VALUES:
                hits.append(key_path)
            hits.extend(_find_unredacted_sensitive_values(value, key_path))
    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            hits.extend(_find_unredacted_sensitive_values(item, f"{prefix}[{index}]"))
    return hits


def _is_sensitive_key(key: str) -> bool:
    lowered = key.lower().replace("_", "-")
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


def _artifact_ref(
    role: str,
    path: Path,
    schema_version: str | None,
) -> ExternalVenueAdapterArtifactRef:
    return ExternalVenueAdapterArtifactRef(
        artifact_role=role,
        path=path.as_posix(),
        sha256=sha256_file(path),
        schema_version=schema_version,
    )


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    return ensure_utc_aware("recorded_at", value)


__all__ = [
    "ExternalVenueAdapterArtifactRef",
    "ExternalVenueAdapterBlocker",
    "ExternalVenueAdapterPlan",
    "ExternalVenueAdapterRunError",
    "ExternalVenueAdapterRunOutputExistsError",
    "ExternalVenueAdapterRunWriteResult",
    "ExternalVenueCredentialPolicy",
    "ExternalVenueOfficialDocRef",
    "ExternalVenueRateLimitPolicy",
    "ExternalVenueRecordedHTTP",
    "ProfitCoreExternalVenueAdapterRun",
    "ProfitCoreExternalVenueAdapterStatus",
    "build_and_write_external_venue_adapter_run",
    "build_external_venue_adapter_run",
]
