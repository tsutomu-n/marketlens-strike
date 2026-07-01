from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.models import ID_PATTERN
from sis.edge_candidates import PROFIT_CORE_RISK_TAKER_SPRINT_ISOLATION_SCHEMA_VERSION
from sis.edge_candidates.multiplicity import TrialMultiplicityAccount
from sis.edge_candidates.protocol import (
    CandidateGeneratorType,
    CandidateProtocolManifest,
    CandidateProtocolMode,
)
from sis.strategy_idea_candidates.models import StrategyIdeaCandidateSet
from sis.strategy_inputs.io import read_mapping_file, write_json_artifact
from sis.strategy_inputs.models import ProducerInfo


BROAD_SPRINT_GENERATOR_TYPES = {
    CandidateGeneratorType.LIMITED_RANDOM,
    CandidateGeneratorType.LIGHT_GA,
    CandidateGeneratorType.RANKING_OR_NO_TRADE_FILTER,
}


class PromotionDebtCode(StrEnum):
    RE_REGISTER_UNDER_VERIFICATION_THROUGHPUT = "RE_REGISTER_UNDER_VERIFICATION_THROUGHPUT"
    DO_NOT_REUSE_SPRINT_HOLDOUT = "DO_NOT_REUSE_SPRINT_HOLDOUT"
    ATTACH_DEFAULT_MULTIPLICITY_ACCOUNT = "ATTACH_DEFAULT_MULTIPLICITY_ACCOUNT"
    PASS_BACKTEST_KILL_GATE_UNDER_DEFAULT_THRESHOLDS = (
        "PASS_BACKTEST_KILL_GATE_UNDER_DEFAULT_THRESHOLDS"
    )
    PASS_VIRTUAL_EXECUTION_GATE_UNDER_DEFAULT_PIPELINE = (
        "PASS_VIRTUAL_EXECUTION_GATE_UNDER_DEFAULT_PIPELINE"
    )
    RISK_TAKER_REVIEW_WITHOUT_LIVE_PERMISSION = "RISK_TAKER_REVIEW_WITHOUT_LIVE_PERMISSION"


class SprintPromotionDebt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    debt_code: PromotionDebtCode
    status: Literal["OUTSTANDING"] = "OUTSTANDING"
    blocks_actual_cash: Literal[True] = True
    message: str

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("promotion debt message must not be empty")
        return stripped


class SprintArtifactRef(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    artifact_role: str
    path: str
    sha256: str
    schema_version: str | None = None

    @field_validator("artifact_role", "path")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("artifact ref text fields must not be empty")
        return stripped


class RiskTakerSprintIsolation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["profit_core_risk_taker_sprint_isolation.v1"] = (
        PROFIT_CORE_RISK_TAKER_SPRINT_ISOLATION_SCHEMA_VERSION
    )
    isolation_id: str
    recorded_at: datetime
    producer: ProducerInfo
    protocol_id: str
    candidate_set_id: str
    multiplicity_account_id: str
    mode: Literal["risk_taker_sprint"] = "risk_taker_sprint"
    output_label: Literal["SPECULATIVE_SPRINT"] = "SPECULATIVE_SPRINT"
    sealed_holdout_window_id: str
    protocol_ref: SprintArtifactRef
    candidate_set_ref: SprintArtifactRef
    search_ledger_ref: SprintArtifactRef
    multiplicity_account_ref: SprintArtifactRef
    family_count: int = Field(ge=0)
    candidate_count_total: int = Field(ge=0)
    candidate_count_shortlisted: int = Field(ge=0)
    candidate_count_rejected: int = Field(ge=0)
    search_ledger_row_count: int = Field(ge=0)
    generator_types: list[str] = Field(default_factory=list)
    generator_constraints: dict[str, str] = Field(default_factory=dict)
    default_aggregate_inclusion_allowed: Literal[False] = False
    default_aggregate_candidate_count: Literal[0] = 0
    verification_throughput_reregistration_required: Literal[True] = True
    actual_cash_direct_promotion_allowed: Literal[False] = False
    tiny_live_direct_promotion_allowed: Literal[False] = False
    separate_ledger: Literal[True] = True
    separate_holdout: Literal[True] = True
    separate_multiplicity_account: Literal[True] = True
    promotion_debt: list[SprintPromotionDebt] = Field(min_length=1)
    boundary: dict[str, bool] = Field(
        default_factory=lambda: {
            "actual_cash": False,
            "permits_live_order": False,
            "permits_paper_order": False,
            "permits_tiny_live": False,
            "permits_actual_cash": False,
            "production_exchange_write_used": False,
            "live_order_submitted": False,
            "wallet_used": False,
            "signing_used": False,
            "default_aggregate_mixed": False,
            "sprint_positive_result_promoted": False,
        }
    )

    @field_validator(
        "isolation_id",
        "protocol_id",
        "candidate_set_id",
        "multiplicity_account_id",
        "sealed_holdout_window_id",
    )
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

    @field_serializer("recorded_at")
    def serialize_recorded_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class RiskTakerSprintIsolationWriteResult:
    isolation: RiskTakerSprintIsolation
    isolation_path: Path
    isolation_sha256: str


class RiskTakerSprintIsolationError(ValueError):
    pass


class RiskTakerSprintIsolationOutputExistsError(RiskTakerSprintIsolationError):
    pass


def build_risk_taker_sprint_isolation(
    *,
    protocol_path: Path,
    candidate_set_path: Path,
    search_ledger_path: Path,
    multiplicity_account_path: Path,
    recorded_at: datetime | str | None = None,
) -> RiskTakerSprintIsolation:
    protocol = CandidateProtocolManifest.model_validate(read_mapping_file(protocol_path))
    candidate_set = StrategyIdeaCandidateSet.model_validate(read_mapping_file(candidate_set_path))
    multiplicity = TrialMultiplicityAccount.model_validate(
        read_mapping_file(multiplicity_account_path)
    )
    search_ledger_rows = _read_search_ledger_rows(search_ledger_path)
    _validate_sprint_inputs(
        protocol=protocol,
        candidate_set=candidate_set,
        multiplicity=multiplicity,
        search_ledger_rows=search_ledger_rows,
    )
    generator_types = [family.generator_type.value for family in protocol.families]
    return RiskTakerSprintIsolation(
        isolation_id=f"{protocol.protocol_id}-risk-taker-sprint-isolation",
        recorded_at=_coerce_datetime(recorded_at),
        producer=ProducerInfo(command="edge-candidate-risk-taker-sprint-isolation-record"),
        protocol_id=protocol.protocol_id,
        candidate_set_id=candidate_set.candidate_set_id,
        multiplicity_account_id=multiplicity.account_id,
        sealed_holdout_window_id=protocol.sealed_holdout_definition.window_id,
        protocol_ref=_artifact_ref(
            "risk_taker_sprint_protocol", protocol_path, protocol.schema_version
        ),
        candidate_set_ref=_artifact_ref(
            "risk_taker_sprint_candidate_set",
            candidate_set_path,
            candidate_set.schema_version,
        ),
        search_ledger_ref=_artifact_ref(
            "risk_taker_sprint_search_ledger", search_ledger_path, None
        ),
        multiplicity_account_ref=_artifact_ref(
            "risk_taker_sprint_multiplicity_account",
            multiplicity_account_path,
            multiplicity.schema_version,
        ),
        family_count=multiplicity.family_count,
        candidate_count_total=candidate_set.search_ledger_summary.candidate_count_total,
        candidate_count_shortlisted=candidate_set.search_ledger_summary.candidate_count_shortlisted,
        candidate_count_rejected=candidate_set.search_ledger_summary.candidate_count_rejected,
        search_ledger_row_count=len(search_ledger_rows),
        generator_types=generator_types,
        generator_constraints=_generator_constraints(protocol),
        promotion_debt=_promotion_debt(),
    )


def build_and_write_risk_taker_sprint_isolation(
    *,
    protocol_path: Path,
    candidate_set_path: Path,
    search_ledger_path: Path,
    multiplicity_account_path: Path,
    out_dir: Path,
    recorded_at: datetime | str | None = None,
    replace_existing: bool = False,
) -> RiskTakerSprintIsolationWriteResult:
    isolation_path = out_dir / "profit_core_risk_taker_sprint_isolation.json"
    if isolation_path.exists() and not replace_existing:
        raise RiskTakerSprintIsolationOutputExistsError(f"output already exists: {isolation_path}")
    isolation = build_risk_taker_sprint_isolation(
        protocol_path=protocol_path,
        candidate_set_path=candidate_set_path,
        search_ledger_path=search_ledger_path,
        multiplicity_account_path=multiplicity_account_path,
        recorded_at=recorded_at,
    )
    write_json_artifact(isolation_path, isolation.model_dump(mode="json"))
    return RiskTakerSprintIsolationWriteResult(
        isolation=isolation,
        isolation_path=isolation_path,
        isolation_sha256=sha256_file(isolation_path),
    )


def _validate_sprint_inputs(
    *,
    protocol: CandidateProtocolManifest,
    candidate_set: StrategyIdeaCandidateSet,
    multiplicity: TrialMultiplicityAccount,
    search_ledger_rows: list[dict[str, Any]],
) -> None:
    if protocol.mode is not CandidateProtocolMode.RISK_TAKER_SPRINT:
        raise RiskTakerSprintIsolationError("expected risk_taker_sprint protocol")
    if protocol.mode_isolation is not True:
        raise RiskTakerSprintIsolationError("risk_taker_sprint protocol requires mode_isolation")
    if multiplicity.mode is not CandidateProtocolMode.RISK_TAKER_SPRINT:
        raise RiskTakerSprintIsolationError("multiplicity account must be risk_taker_sprint")
    if (
        multiplicity.candidate_count_total
        != candidate_set.search_ledger_summary.candidate_count_total
    ):
        raise RiskTakerSprintIsolationError("multiplicity candidate_count_total mismatch")
    if (
        multiplicity.candidate_count_shortlisted
        != candidate_set.search_ledger_summary.candidate_count_shortlisted
    ):
        raise RiskTakerSprintIsolationError("multiplicity candidate_count_shortlisted mismatch")
    if multiplicity.family_count != candidate_set.search_ledger_summary.family_count:
        raise RiskTakerSprintIsolationError("multiplicity family_count mismatch")
    _validate_search_ledger(candidate_set=candidate_set, rows=search_ledger_rows)
    if any(row.get("uses_sealed_test_for_selection") is True for row in search_ledger_rows):
        raise RiskTakerSprintIsolationError("sprint search ledger used sealed test for selection")
    if candidate_set.search_ledger_summary.success_only_reporting:
        raise RiskTakerSprintIsolationError(
            "sprint candidate set must not use success-only reporting"
        )
    if candidate_set.search_ledger_summary.sealed_test_used_for_selection:
        raise RiskTakerSprintIsolationError(
            "sprint candidate set must not use sealed test selection"
        )
    if any(family.generator_type in BROAD_SPRINT_GENERATOR_TYPES for family in protocol.families):
        benchmark = protocol.objective.get("benchmark")
        if benchmark != "NO_TRADE":
            raise RiskTakerSprintIsolationError(
                "risk_taker_sprint broad generators require NO_TRADE benchmark"
            )


def _validate_search_ledger(
    *,
    candidate_set: StrategyIdeaCandidateSet,
    rows: list[dict[str, Any]],
) -> None:
    candidate_ids = {candidate.idea_candidate_id for candidate in candidate_set.candidate_inventory}
    row_candidate_ids = {
        row.get("candidate_id") for row in rows if isinstance(row.get("candidate_id"), str)
    }
    if len(rows) != len(candidate_ids) or row_candidate_ids != candidate_ids:
        raise RiskTakerSprintIsolationError(
            "search ledger candidate ids must match candidate set inventory"
        )


def _read_search_ledger_rows(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RiskTakerSprintIsolationError(f"failed to read search ledger {path}: {exc}") from exc
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise RiskTakerSprintIsolationError(
                f"invalid JSONL row in search ledger at line {line_number}"
            ) from exc
        if not isinstance(payload, dict):
            raise RiskTakerSprintIsolationError(
                f"search ledger row must be an object at line {line_number}"
            )
        rows.append(payload)
    return rows


def _generator_constraints(protocol: CandidateProtocolManifest) -> dict[str, str]:
    constraints: dict[str, str] = {}
    for family in protocol.families:
        if family.generator_type in BROAD_SPRINT_GENERATOR_TYPES:
            constraints[family.generator_type.value] = "ranking_or_no_trade_filter_only"
    return constraints


def _promotion_debt() -> list[SprintPromotionDebt]:
    messages = {
        PromotionDebtCode.RE_REGISTER_UNDER_VERIFICATION_THROUGHPUT: (
            "Re-register the candidate under verification_throughput before promotion."
        ),
        PromotionDebtCode.DO_NOT_REUSE_SPRINT_HOLDOUT: (
            "Do not reuse the sprint sealed holdout for default promotion proof."
        ),
        PromotionDebtCode.ATTACH_DEFAULT_MULTIPLICITY_ACCOUNT: (
            "Attach a fresh verification_throughput multiplicity account."
        ),
        PromotionDebtCode.PASS_BACKTEST_KILL_GATE_UNDER_DEFAULT_THRESHOLDS: (
            "Pass the default backtest kill gate under conservative thresholds."
        ),
        PromotionDebtCode.PASS_VIRTUAL_EXECUTION_GATE_UNDER_DEFAULT_PIPELINE: (
            "Pass the default virtual execution gate before any execution promotion."
        ),
        PromotionDebtCode.RISK_TAKER_REVIEW_WITHOUT_LIVE_PERMISSION: (
            "Record risk-taker review without granting live, tiny-live, or actual-cash permission."
        ),
    }
    return [
        SprintPromotionDebt(debt_code=code, message=message) for code, message in messages.items()
    ]


def _artifact_ref(role: str, path: Path, schema_version: str | None) -> SprintArtifactRef:
    return SprintArtifactRef(
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
    "PromotionDebtCode",
    "RiskTakerSprintIsolation",
    "RiskTakerSprintIsolationError",
    "RiskTakerSprintIsolationOutputExistsError",
    "RiskTakerSprintIsolationWriteResult",
    "SprintArtifactRef",
    "SprintPromotionDebt",
    "build_and_write_risk_taker_sprint_isolation",
    "build_risk_taker_sprint_isolation",
]
