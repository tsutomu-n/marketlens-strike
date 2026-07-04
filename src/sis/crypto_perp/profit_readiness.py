from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.bias_guards import build_bias_guard
from sis.crypto_perp.cash_ledger import CashLedgerEntry, CryptoPerpCashLedger
from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.edge_scorer import build_edge_score
from sis.crypto_perp.events import CryptoPerpEvent
from sis.crypto_perp.features import build_feature_pack
from sis.crypto_perp.models import (
    CryptoPerpBoundary,
    CryptoPerpProducer,
    DecimalValue,
    decimal_to_json_string,
    stable_hash,
)
from sis.crypto_perp.outcomes import CryptoPerpOutcome
from sis.crypto_perp.replay import build_replay_slice
from sis.crypto_perp.source_availability import build_source_availability
from sis.crypto_perp.tiny_live_shadow import CryptoPerpTinyLiveShadow, build_tiny_live_shadow
from sis.crypto_perp.tournament import (
    TOURNAMENT_ACTIONS,
    CryptoPerpTournamentReport,
    TournamentAction,
    TournamentEventResult,
    build_tournament_report,
)
from sis.crypto_perp.tournament_gate import CryptoPerpTournamentGate, build_tournament_gate
from sis.crypto_perp.tournament_rows import build_cost_aware_tournament_rows


INVENTORY_SCHEMA_VERSION = "crypto_perp_profit_readiness_inventory.v1"
PLAN_SCHEMA_VERSION = "crypto_perp_profit_readiness_plan.v1"
RUN_SCHEMA_VERSION = "crypto_perp_profit_readiness_run.v1"
ACTUAL_ROWS_SUMMARY_SCHEMA_VERSION = "crypto_perp_actual_cash_rows_summary.v1"
REPORT_GATE_RUN_SCHEMA_VERSION = "crypto_perp_actual_cash_report_gate_run.v1"
REVIEW_PACKET_SCHEMA_VERSION = "crypto_perp_tiny_live_review_packet.v1"
SHADOW_READINESS_SCHEMA_VERSION = "crypto_perp_tiny_live_shadow_readiness.v1"
ASSIGNMENT_SCHEMA_VERSION = "crypto_perp_actual_cash_assignment.v1"


REAL_SCHEMA_CATEGORIES: dict[str, str] = {
    "crypto_perp_event.v1": "event",
    "crypto_perp_outcome.v1": "outcome",
    "crypto_perp_source_availability.v1": "source_availability",
    "crypto_perp_replay_slice.v1": "replay_slice",
    "crypto_perp_feature_pack.v1": "feature_pack",
    "crypto_perp_edge_score.v1": "edge_score",
    "crypto_perp_tournament_rows.v2": "rows_v2",
    "crypto_perp_bias_guard.v1": "bias_guard",
    "crypto_perp_cash_ledger.v1": "cash_ledger",
    "crypto_perp_live_measurement.v1": "live_measurement",
    INVENTORY_SCHEMA_VERSION: "profit_readiness_inventory",
    PLAN_SCHEMA_VERSION: "profit_readiness_plan",
    RUN_SCHEMA_VERSION: "profit_readiness_run",
}
DOGFOOD_SCHEMA_MARKERS = ("status", "viewer", "dogfood", "daily_brief", "workbench")


class ProfitReadinessInventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    schema_version: str | None
    category: Literal[
        "event",
        "outcome",
        "source_availability",
        "replay_slice",
        "feature_pack",
        "edge_score",
        "rows_v2",
        "bias_guard",
        "cash_ledger",
        "live_measurement",
        "profit_readiness_inventory",
        "profit_readiness_plan",
        "profit_readiness_run",
        "dogfood_status_viewer",
        "unknown",
        "invalid_json",
    ]
    artifact_id: str | None = None
    event_id: str | None = None
    matured_outcome: bool = False
    reason: str | None = None


class ProfitReadinessInventory(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_profit_readiness_inventory.v1"] = INVENTORY_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    data_dir: str
    inventory_status: Literal["READY_FOR_LOCAL_PLAN", "BLOCKED_MISSING_EVENT_OR_OUTCOME"]
    items: list[ProfitReadinessInventoryItem]
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class ProfitReadinessPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_profit_readiness_plan.v1"] = PLAN_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    plan_status: Literal[
        "READY_FOR_LOCAL_RUN",
        "BLOCKED_MISSING_EVENT_OR_OUTCOME",
        "BLOCKED_MULTIPLE_EVENT_OR_OUTCOME_CANDIDATES",
    ]
    event_path: str | None
    outcome_path: str | None
    runnable_commands: list[str]
    blockers: list[str]
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class ProfitReadinessRunManifest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_profit_readiness_run.v1"] = RUN_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    run_id: str
    event_id: str
    outcome_id: str
    status: Literal["complete", "blocked"]
    artifacts: dict[str, str]
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class ActualCashAssignmentRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str
    action: TournamentAction
    pod_id: str | None = None
    market_adjusted_return: DecimalValue = Decimal("0")
    operator_time_minutes: DecimalValue = Decimal("0")
    near_miss: bool = False

    @field_validator("event_id")
    @classmethod
    def validate_event_id(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("event_id must not be empty")
        return stripped

    @field_validator("pod_id")
    @classmethod
    def validate_pod_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("pod_id must not be empty when provided")
        return stripped

    @field_validator("operator_time_minutes")
    @classmethod
    def validate_time(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("operator_time_minutes must be non-negative")
        return value


class ActualCashRowsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_actual_cash_rows_summary.v1"] = (
        ACTUAL_ROWS_SUMMARY_SCHEMA_VERSION
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    row_count: int = Field(ge=0)
    event_count: int = Field(ge=0)
    action_set: list[TournamentAction]
    rows_path: str
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class ActualCashReportGateRun(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_actual_cash_report_gate_run.v1"] = (
        REPORT_GATE_RUN_SCHEMA_VERSION
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    report_id: str
    gate_id: str
    status: Literal["ready_for_human_review", "blocked"]
    gate_status: str
    artifacts: dict[str, str]
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class TinyLiveReviewPacket(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_tiny_live_review_packet.v1"] = REVIEW_PACKET_SCHEMA_VERSION
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    packet_id: str
    report_id: str
    gate_id: str
    packet_status: Literal["READY_FOR_HUMAN_REVIEW", "BLOCKED_BY_TOURNAMENT_GATE"]
    requires_explicit_approval: Literal[True] = True
    live_order_allowed: Literal[False] = False
    exchange_write_allowed: Literal[False] = False
    approval_granted: Literal[False] = False
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


class TinyLiveShadowReadiness(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_tiny_live_shadow_readiness.v1"] = (
        SHADOW_READINESS_SCHEMA_VERSION
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    readiness_id: str
    packet_id: str
    status: Literal[
        "READY_FOR_TINY_LIVE_SHADOW", "BLOCKED_BY_REVIEW_PACKET", "BLOCKED_BY_PREFLIGHT"
    ]
    shadow_preflight_status: str
    blockers: list[str]
    live_order_allowed: Literal[False] = False
    exchange_write_allowed: Literal[False] = False
    requires_explicit_approval: Literal[True] = True
    shadow_artifact: CryptoPerpTinyLiveShadow
    known_gaps: list[str]
    summary: dict[str, Any]

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_timestamp(self, value: datetime) -> str:
        return serialize_utc_z(value)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_rows_or_array(path: Path) -> list[Any]:
    text = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return list(payload["rows"])
    if isinstance(payload, list):
        return payload
    raise ValueError(f"expected JSON array, JSON object with rows, or JSONL: {path}")


def _sha_ref(path: Path, schema_version: str | None = None) -> dict[str, str]:
    ref = {"path": path.as_posix(), "sha256": "sha256:" + stable_hash([path.read_text("utf-8")])}
    if schema_version:
        ref["schema_version"] = schema_version
    return ref


def _known_artifact_id(payload: dict[str, Any]) -> str | None:
    for key in (
        "artifact_id",
        "inventory_id",
        "plan_id",
        "run_id",
        "slice_id",
        "feature_pack_id",
        "score_id",
        "rows_id",
        "guard_id",
        "ledger_id",
        "measurement_id",
    ):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def _classify_json(path: Path, payload: Any) -> ProfitReadinessInventoryItem:
    if not isinstance(payload, dict):
        return ProfitReadinessInventoryItem(
            path=path.as_posix(),
            schema_version=None,
            category="unknown",
            reason="JSON_TOP_LEVEL_NOT_OBJECT",
        )
    raw_schema = payload.get("schema_version")
    schema_version = raw_schema if isinstance(raw_schema, str) else None
    category = REAL_SCHEMA_CATEGORIES.get(schema_version or "")
    if category == "event":
        event = CryptoPerpEvent.model_validate(payload)
        return ProfitReadinessInventoryItem(
            path=path.as_posix(),
            schema_version=schema_version,
            category="event",
            artifact_id=event.artifact_id,
            event_id=event.event_id,
        )
    if category == "outcome":
        outcome = CryptoPerpOutcome.model_validate(payload)
        matured = any(horizon.matured for horizon in outcome.horizons)
        return ProfitReadinessInventoryItem(
            path=path.as_posix(),
            schema_version=schema_version,
            category="outcome",
            artifact_id=outcome.artifact_id,
            event_id=outcome.event_id,
            matured_outcome=matured,
            reason=None if matured else "OUTCOME_NOT_MATURED",
        )
    if category == "profit_readiness_run":
        run = ProfitReadinessRunManifest.model_validate(payload)
        return ProfitReadinessInventoryItem(
            path=path.as_posix(),
            schema_version=schema_version,
            category="profit_readiness_run",
            artifact_id=run.run_id,
            event_id=run.event_id,
            reason=None,
        )
    if category is not None:
        return ProfitReadinessInventoryItem(
            path=path.as_posix(),
            schema_version=schema_version,
            category=cast(
                Literal[
                    "source_availability",
                    "replay_slice",
                    "feature_pack",
                    "edge_score",
                    "rows_v2",
                    "bias_guard",
                    "cash_ledger",
                    "live_measurement",
                    "profit_readiness_inventory",
                    "profit_readiness_plan",
                    "profit_readiness_run",
                ],
                category,
            ),
            artifact_id=_known_artifact_id(payload),
            event_id=str(payload.get("event_id")) if payload.get("event_id") else None,
        )
    lowered = f"{schema_version or ''} {path.as_posix()}".lower()
    if any(marker in lowered for marker in DOGFOOD_SCHEMA_MARKERS):
        return ProfitReadinessInventoryItem(
            path=path.as_posix(),
            schema_version=schema_version,
            category="dogfood_status_viewer",
            artifact_id=str(payload.get("artifact_id")) if payload.get("artifact_id") else None,
            reason="DOGFOOD_STATUS_VIEWER_NOT_PROFIT_EVIDENCE",
        )
    return ProfitReadinessInventoryItem(
        path=path.as_posix(),
        schema_version=schema_version,
        category="unknown",
        artifact_id=str(payload.get("artifact_id")) if payload.get("artifact_id") else None,
        reason="UNKNOWN_SCHEMA_VERSION",
    )


def build_profit_readiness_inventory(
    *,
    data_dir: Path,
    created_at: datetime | str,
) -> ProfitReadinessInventory:
    created = ensure_utc_aware("created_at", created_at)
    items: list[ProfitReadinessInventoryItem] = []
    known_gaps: list[str] = []
    for path in sorted(data_dir.rglob("*.json")) if data_dir.exists() else []:
        try:
            items.append(_classify_json(path, _load_json(path)))
        except json.JSONDecodeError as exc:
            items.append(
                ProfitReadinessInventoryItem(
                    path=path.as_posix(),
                    schema_version=None,
                    category="invalid_json",
                    reason=f"INVALID_JSON:{exc.msg}",
                )
            )
        except Exception as exc:
            items.append(
                ProfitReadinessInventoryItem(
                    path=path.as_posix(),
                    schema_version=None,
                    category="unknown",
                    reason=f"INVALID_ARTIFACT:{exc}",
                )
            )
    event_items = [item for item in items if item.category == "event"]
    matured_outcomes = [
        item for item in items if item.category == "outcome" and item.matured_outcome
    ]
    if not event_items or not matured_outcomes:
        known_gaps.append("BLOCKED_MISSING_EVENT_OR_OUTCOME")
    for item in items:
        if item.category in {"invalid_json", "unknown", "dogfood_status_viewer"} and item.reason:
            known_gaps.append(item.reason)
    summary = {
        "event_count": len(event_items),
        "outcome_count": len(matured_outcomes),
        "source_availability_count": sum(
            1 for item in items if item.category == "source_availability"
        ),
        "replay_slice_count": sum(1 for item in items if item.category == "replay_slice"),
        "feature_pack_count": sum(1 for item in items if item.category == "feature_pack"),
        "edge_score_count": sum(1 for item in items if item.category == "edge_score"),
        "rows_v2_count": sum(1 for item in items if item.category == "rows_v2"),
        "bias_guard_count": sum(1 for item in items if item.category == "bias_guard"),
        "cash_ledger_count": sum(1 for item in items if item.category == "cash_ledger"),
        "live_measurement_count": sum(1 for item in items if item.category == "live_measurement"),
        "profit_readiness_inventory_count": sum(
            1 for item in items if item.category == "profit_readiness_inventory"
        ),
        "profit_readiness_plan_count": sum(
            1 for item in items if item.category == "profit_readiness_plan"
        ),
        "profit_readiness_run_count": sum(
            1 for item in items if item.category == "profit_readiness_run"
        ),
        "dogfood_status_viewer_count": sum(
            1 for item in items if item.category == "dogfood_status_viewer"
        ),
        "unknown_count": sum(1 for item in items if item.category == "unknown"),
        "invalid_json_count": sum(1 for item in items if item.category == "invalid_json"),
        "has_real_event_and_outcome": bool(event_items and matured_outcomes),
    }
    status: Literal["READY_FOR_LOCAL_PLAN", "BLOCKED_MISSING_EVENT_OR_OUTCOME"] = (
        "READY_FOR_LOCAL_PLAN"
        if event_items and matured_outcomes
        else "BLOCKED_MISSING_EVENT_OR_OUTCOME"
    )
    return ProfitReadinessInventory(
        artifact_id=stable_hash(
            [
                "crypto-perp-profit-readiness-inventory",
                data_dir.as_posix(),
                serialize_utc_z(created),
                [item.model_dump(mode="json") for item in items],
            ]
        ),
        created_at=created,
        producer=CryptoPerpProducer(command="crypto-perp-profit-readiness-inventory"),
        source_refs=[],
        data_dir=data_dir.as_posix(),
        inventory_status=status,
        items=items,
        known_gaps=list(dict.fromkeys(known_gaps)),
        summary=summary,
    )


def build_profit_readiness_plan(
    *,
    inventory: ProfitReadinessInventory,
    created_at: datetime | str,
    out_dir: Path = Path("data/crypto_perp/profit_readiness_run/latest"),
    notional_usd: Decimal = Decimal("100"),
) -> ProfitReadinessPlan:
    created = ensure_utc_aware("created_at", created_at)
    events = [item for item in inventory.items if item.category == "event"]
    outcomes = [
        item for item in inventory.items if item.category == "outcome" and item.matured_outcome
    ]
    blockers: list[str] = []
    if not events or not outcomes:
        blockers.append("BLOCKED_MISSING_EVENT_OR_OUTCOME")
    if len(events) > 1 or len(outcomes) > 1:
        blockers.append("BLOCKED_MULTIPLE_EVENT_OR_OUTCOME_CANDIDATES")
    event_path = events[0].path if len(events) == 1 else None
    outcome_path = outcomes[0].path if len(outcomes) == 1 else None
    if blockers:
        status: Literal[
            "READY_FOR_LOCAL_RUN",
            "BLOCKED_MISSING_EVENT_OR_OUTCOME",
            "BLOCKED_MULTIPLE_EVENT_OR_OUTCOME_CANDIDATES",
        ] = (
            "BLOCKED_MULTIPLE_EVENT_OR_OUTCOME_CANDIDATES"
            if "BLOCKED_MULTIPLE_EVENT_OR_OUTCOME_CANDIDATES" in blockers
            else "BLOCKED_MISSING_EVENT_OR_OUTCOME"
        )
        commands: list[str] = []
    else:
        status = "READY_FOR_LOCAL_RUN"
        commands = [
            "uv run sis crypto-perp-profit-readiness-run-local "
            f"--event {event_path} --outcome {outcome_path} --out {out_dir.as_posix()} "
            f"--notional-usd {decimal_to_json_string(notional_usd)}"
        ]
    return ProfitReadinessPlan(
        artifact_id=stable_hash(
            [
                "crypto-perp-profit-readiness-plan",
                inventory.artifact_id,
                serialize_utc_z(created),
                commands,
                blockers,
            ]
        ),
        created_at=created,
        producer=CryptoPerpProducer(command="crypto-perp-profit-readiness-plan"),
        source_refs=[
            {
                "path": "inventory",
                "sha256": inventory.artifact_id,
                "schema_version": inventory.schema_version,
            }
        ],
        plan_status=status,
        event_path=event_path,
        outcome_path=outcome_path,
        runnable_commands=commands,
        blockers=list(dict.fromkeys(blockers)),
        known_gaps=list(dict.fromkeys([*inventory.known_gaps, *blockers])),
        summary={
            "event_candidate_count": len(events),
            "outcome_candidate_count": len(outcomes),
            "runnable_command_count": len(commands),
            "blocker_count": len(blockers),
        },
    )


def build_profit_readiness_run(
    *,
    event: CryptoPerpEvent,
    outcome: CryptoPerpOutcome,
    created_at: datetime | str,
    out: Path,
    event_path: Path,
    outcome_path: Path,
    notional_usd: Decimal,
) -> ProfitReadinessRunManifest:
    if outcome.event_id != event.event_id:
        raise ValueError("event and outcome event_id must match")
    created = ensure_utc_aware("created_at", created_at)
    source = build_source_availability(
        event=event,
        created_at=created,
        available_sources={"outcome": True},
        row_counts={"outcome": 1},
        source_refs=[_sha_ref(outcome_path, outcome.schema_version)],
    )
    replay = build_replay_slice(
        event=event,
        created_at=created,
        included_sources=["event", "outcome"],
        row_counts={"event": 1, "outcome": 1},
    )
    feature = build_feature_pack(event=event, source_availability=source, created_at=created)
    edge = build_edge_score(feature_pack=feature, source_availability=source, created_at=created)
    rows = build_cost_aware_tournament_rows(
        outcomes=[outcome],
        created_at=created,
        notional_usd=notional_usd,
        source_refs=[_sha_ref(outcome_path, outcome.schema_version)],
    )
    guard = build_bias_guard(
        rows=rows.rows,
        created_at=created,
        source_refs=[
            {
                "path": "tournament_rows_v2.json",
                "sha256": rows.artifact_id,
                "schema_version": rows.schema_version,
            }
        ],
        known_gaps=rows.known_gaps,
    )
    artifacts = {
        "source_availability": (out / "source_availability.json").as_posix(),
        "replay_slice": (out / "replay_slice.json").as_posix(),
        "feature_pack": (out / "feature_pack.json").as_posix(),
        "edge_score": (out / "edge_score.json").as_posix(),
        "tournament_rows_v2": (out / "tournament_rows_v2.json").as_posix(),
        "bias_guard": (out / "bias_guard.json").as_posix(),
    }
    known_gaps = list(
        dict.fromkeys(
            [
                *source.known_gaps,
                *replay.known_gaps,
                *feature.known_gaps,
                *edge.known_gaps,
                *rows.known_gaps,
                *guard.known_gaps,
            ]
        )
    )
    status: Literal["complete", "blocked"] = (
        "blocked" if guard.guard_status == "BLOCKED" else "complete"
    )
    return ProfitReadinessRunManifest(
        artifact_id=stable_hash(
            [
                "crypto-perp-profit-readiness-run",
                event.event_id,
                outcome.outcome_id,
                serialize_utc_z(created),
                artifacts,
                known_gaps,
            ]
        ),
        created_at=created,
        producer=CryptoPerpProducer(command="crypto-perp-profit-readiness-run-local"),
        source_refs=[
            _sha_ref(event_path, event.schema_version),
            _sha_ref(outcome_path, outcome.schema_version),
        ],
        run_id=stable_hash(
            [
                "crypto-perp-profit-readiness-run-id",
                event.event_id,
                outcome.outcome_id,
                serialize_utc_z(created),
            ]
        ),
        event_id=event.event_id,
        outcome_id=outcome.outcome_id,
        status=status,
        artifacts=artifacts,
        known_gaps=known_gaps,
        summary={
            "event_id": event.event_id,
            "outcome_id": outcome.outcome_id,
            "guard_status": guard.guard_status,
            "known_gap_count": len(known_gaps),
            "network_attempted": False,
            "exchange_write_used": False,
            "live_order_submitted": False,
        },
    )


def actual_cash_rows_from_ledger(
    *,
    ledger: CryptoPerpCashLedger,
    assignments: Sequence[ActualCashAssignmentRow],
    created_at: datetime | str,
    rows_path: Path,
    source_refs: Sequence[dict[str, str]],
) -> tuple[list[TournamentEventResult], ActualCashRowsSummary]:
    created = ensure_utc_aware("created_at", created_at)
    assignment_map = {(row.event_id, row.action): row for row in assignments}
    event_ids = sorted({row.event_id for row in assignments})
    for event_id in event_ids:
        missing = [
            action for action in TOURNAMENT_ACTIONS if (event_id, action) not in assignment_map
        ]
        if missing:
            raise ValueError(f"event {event_id} missing actions: {', '.join(missing)}")
    rows: list[TournamentEventResult] = []
    for event_id in event_ids:
        for action in TOURNAMENT_ACTIONS:
            assignment = assignment_map[(event_id, action)]
            if action == "NO_TRADE":
                cash = Decimal("0")
            else:
                if assignment.pod_id is None:
                    raise ValueError(f"{event_id} {action} requires pod_id")
                matched = [
                    entry
                    for entry in ledger.entries
                    if entry.event_id == event_id and entry.pod_id == assignment.pod_id
                ]
                if not matched:
                    raise ValueError(
                        f"{event_id} {action} has no ledger entries for pod_id {assignment.pod_id}"
                    )
                cash = sum((entry.amount_usd for entry in matched), Decimal("0"))
            rows.append(
                TournamentEventResult(
                    event_id=event_id,
                    action=action,
                    cash_metric_value_usd=cash,
                    actual_cash_result_usd=cash,
                    cash_metric_basis="actual_cash",
                    market_adjusted_return=assignment.market_adjusted_return,
                    operator_time_minutes=assignment.operator_time_minutes,
                    near_miss=assignment.near_miss,
                )
            )
    summary = ActualCashRowsSummary(
        artifact_id=stable_hash(
            [
                "crypto-perp-actual-cash-rows",
                ledger.artifact_id,
                [row.model_dump(mode="json") for row in assignments],
                serialize_utc_z(created),
            ]
        ),
        created_at=created,
        producer=CryptoPerpProducer(command="crypto-perp-actual-cash-rows-build"),
        source_refs=list(source_refs),
        row_count=len(rows),
        event_count=len(event_ids),
        action_set=list(TOURNAMENT_ACTIONS),
        rows_path=rows_path.as_posix(),
        known_gaps=[],
        summary={
            "ledger_id": ledger.ledger_id,
            "event_count": len(event_ids),
            "row_count": len(rows),
            "cash_metric_basis": "actual_cash",
        },
    )
    return rows, summary


def build_actual_cash_report_gate_run(
    *,
    rows: Sequence[TournamentEventResult],
    report_id: str,
    min_events: int,
    created_at: datetime | str,
    source_refs: Sequence[dict[str, str]],
    artifacts: dict[str, str],
) -> tuple[CryptoPerpTournamentReport, CryptoPerpTournamentGate, ActualCashReportGateRun]:
    created = ensure_utc_aware("created_at", created_at)
    report = build_tournament_report(
        report_id=report_id,
        generated_at=created,
        rows=rows,
        min_events=min_events,
        source_refs=source_refs,
        producer_command="crypto-perp-actual-cash-report-gate",
    )
    if not report.actual_cash:
        raise ValueError("actual-cash report/gate helper requires actual_cash=true")
    gate = build_tournament_gate(
        report=report,
        created_at=created,
        source_refs=[
            {
                "path": artifacts["tournament_report"],
                "sha256": report.artifact_id,
                "schema_version": report.schema_version,
            }
        ],
        producer_command="crypto-perp-actual-cash-report-gate",
    )
    status: Literal["ready_for_human_review", "blocked"] = (
        "ready_for_human_review"
        if gate.gate_status == "READY_FOR_HUMAN_TINY_LIVE_REVIEW"
        else "blocked"
    )
    manifest = ActualCashReportGateRun(
        artifact_id=stable_hash(
            ["crypto-perp-actual-cash-report-gate", report.artifact_id, gate.artifact_id]
        ),
        created_at=created,
        producer=CryptoPerpProducer(command="crypto-perp-actual-cash-report-gate"),
        source_refs=list(source_refs),
        report_id=report.report_id,
        gate_id=gate.gate_id,
        status=status,
        gate_status=gate.gate_status,
        artifacts=artifacts,
        known_gaps=list(dict.fromkeys([*report.known_gaps, *gate.known_gaps])),
        summary={
            "report_id": report.report_id,
            "gate_status": gate.gate_status,
            "status": status,
            "actual_cash": report.actual_cash,
        },
    )
    return report, gate, manifest


def build_tiny_live_review_packet(
    *,
    report: CryptoPerpTournamentReport,
    gate: CryptoPerpTournamentGate,
    created_at: datetime | str,
    source_refs: Sequence[dict[str, str]],
) -> TinyLiveReviewPacket:
    if gate.report_id != report.report_id:
        raise ValueError("gate report_id must match report")
    created = ensure_utc_aware("created_at", created_at)
    status: Literal["READY_FOR_HUMAN_REVIEW", "BLOCKED_BY_TOURNAMENT_GATE"] = (
        "READY_FOR_HUMAN_REVIEW"
        if gate.gate_status == "READY_FOR_HUMAN_TINY_LIVE_REVIEW"
        else "BLOCKED_BY_TOURNAMENT_GATE"
    )
    packet_id = stable_hash(
        [
            "crypto-perp-tiny-live-review-packet",
            report.artifact_id,
            gate.artifact_id,
            serialize_utc_z(created),
        ]
    )
    known_gaps = list(dict.fromkeys([*report.known_gaps, *gate.known_gaps]))
    if status != "READY_FOR_HUMAN_REVIEW":
        known_gaps.append("BLOCKED_BY_TOURNAMENT_GATE")
    return TinyLiveReviewPacket(
        artifact_id=stable_hash(["crypto-perp-tiny-live-review-packet-artifact", packet_id]),
        created_at=created,
        producer=CryptoPerpProducer(command="crypto-perp-tiny-live-review-packet"),
        source_refs=list(source_refs),
        packet_id=packet_id,
        report_id=report.report_id,
        gate_id=gate.gate_id,
        packet_status=status,
        known_gaps=list(dict.fromkeys(known_gaps)),
        summary={
            "packet_status": status,
            "gate_status": gate.gate_status,
            "leader_action": report.leader_action,
            "event_count": report.event_count,
            "requires_explicit_approval": True,
            "live_order_allowed": False,
            "exchange_write_allowed": False,
        },
    )


def build_tiny_live_shadow_readiness(
    *,
    packet: TinyLiveReviewPacket,
    account_snapshot: Any,
    order_preview: Any,
    created_at: datetime | str,
    source_refs: Sequence[dict[str, str]],
) -> TinyLiveShadowReadiness:
    created = ensure_utc_aware("created_at", created_at)
    shadow = build_tiny_live_shadow(
        account_snapshot=account_snapshot,
        order_preview=order_preview,
        created_at=created,
        producer_command="crypto-perp-tiny-live-shadow-readiness",
    )
    blockers = list(shadow.blockers)
    if packet.packet_status != "READY_FOR_HUMAN_REVIEW":
        blockers.append("REVIEW_PACKET_NOT_READY_FOR_HUMAN_REVIEW")
        status: Literal[
            "READY_FOR_TINY_LIVE_SHADOW", "BLOCKED_BY_REVIEW_PACKET", "BLOCKED_BY_PREFLIGHT"
        ] = "BLOCKED_BY_REVIEW_PACKET"
    elif shadow.preflight_status != "PASS":
        status = "BLOCKED_BY_PREFLIGHT"
    else:
        status = "READY_FOR_TINY_LIVE_SHADOW"
    readiness_id = stable_hash(
        [
            "crypto-perp-tiny-live-shadow-readiness",
            packet.packet_id,
            shadow.artifact_id,
            serialize_utc_z(created),
        ]
    )
    known_gaps = list(dict.fromkeys([*packet.known_gaps, *shadow.known_gaps]))
    return TinyLiveShadowReadiness(
        artifact_id=stable_hash(["crypto-perp-tiny-live-shadow-readiness-artifact", readiness_id]),
        created_at=created,
        producer=CryptoPerpProducer(command="crypto-perp-tiny-live-shadow-readiness"),
        source_refs=list(source_refs),
        readiness_id=readiness_id,
        packet_id=packet.packet_id,
        status=status,
        shadow_preflight_status=shadow.preflight_status,
        blockers=list(dict.fromkeys(blockers)),
        shadow_artifact=shadow,
        known_gaps=known_gaps,
        summary={
            "status": status,
            "shadow_preflight_status": shadow.preflight_status,
            "blocker_count": len(set(blockers)),
            "live_order_allowed": False,
            "exchange_write_allowed": False,
            "requires_explicit_approval": True,
        },
    )


def parse_cash_ledger_entries(path: Path) -> list[CashLedgerEntry]:
    return [CashLedgerEntry.model_validate(item) for item in _read_rows_or_array(path)]


def parse_assignments(path: Path) -> list[ActualCashAssignmentRow]:
    return [ActualCashAssignmentRow.model_validate(item) for item in _read_rows_or_array(path)]


def parse_tournament_rows(path: Path) -> list[TournamentEventResult]:
    rows = [TournamentEventResult.model_validate(item) for item in _read_rows_or_array(path)]
    if any(row.cash_metric_basis != "actual_cash" for row in rows):
        raise ValueError("actual-cash report/gate helper requires actual cash rows")
    return rows
