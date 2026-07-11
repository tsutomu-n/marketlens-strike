from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
from typing import Any, Literal, cast

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.crypto_perp.clock import ensure_utc_aware, serialize_utc_z
from sis.crypto_perp.io import file_artifact_ref, write_json_artifact, write_text_artifact
from sis.crypto_perp.models import CryptoPerpBoundary, CryptoPerpProducer, stable_hash


NO_CASH_BACKTEST_GATE_SCHEMA_VERSION = "crypto_perp_no_cash_backtest_gate.v1"
NO_CASH_BACKTEST_GATE_PRODUCER = "crypto-perp-no-cash-backtest-gate"
NO_CASH_BACKTEST_GATE_ARTIFACT_NAMES = (
    "no_cash_backtest_gate.json",
    "no_cash_backtest_gate.md",
)
MIN_EVENTS_FOR_GATE = 30
MIN_SIMULATED_TRADES = 10
MAX_LARGEST_LOSS_TO_TOTAL_RESULT_RATIO = Decimal("0.5")
MAX_DRAWDOWN_TO_TOTAL_RESULT_RATIO = Decimal("1")
REQUIRE_BOOKS_TRADES_REPLAY = False
_OPTIONAL_MARKET_SOURCES = ("books", "trades", "replay")
_CRITICAL_SIGNAL_SOURCES = ("event", "bars", "ticker", "funding")

NoCashBacktestGateDecision = Literal[
    "NO_CASH_BACKTEST_COLLECT_MORE_DATA",
    "NO_CASH_BACKTEST_REVISE",
    "NO_CASH_BACKTEST_REJECT",
    "NO_CASH_BACKTEST_HOLD",
]
BlockerScope = Literal["input", "candidate", "event", "source", "metric"]


class NoCashBacktestGateBlocker(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scope: BlockerScope
    code: str
    message: str
    event_id: str | None = None
    source_type: str | None = None
    metric: str | None = None


class NoCashBacktestGateArtifact(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["crypto_perp_no_cash_backtest_gate.v1"] = (
        NO_CASH_BACKTEST_GATE_SCHEMA_VERSION
    )
    artifact_id: str
    created_at: datetime
    producer: CryptoPerpProducer
    source_refs: list[dict[str, str]]
    boundary: CryptoPerpBoundary = Field(default_factory=CryptoPerpBoundary)
    gate_decision: NoCashBacktestGateDecision
    reason_codes: list[str]
    blockers: list[NoCashBacktestGateBlocker]
    known_gaps: list[str]
    thresholds: dict[str, Any]
    summary: dict[str, Any]
    input_artifacts: dict[str, str]
    permits_paper_order: Literal[False] = False
    paper_permission_granted: Literal[False] = False
    permits_live_order: Literal[False] = False
    actual_cash_used: Literal[False] = False
    profit_proven: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
    live_order_submitted: Literal[False] = False

    @field_validator("created_at", mode="before")
    @classmethod
    def validate_created_at(cls, value: datetime | str) -> datetime:
        return ensure_utc_aware("created_at", value)

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime) -> str:
        return serialize_utc_z(value)


@dataclass(frozen=True)
class NoCashBacktestGateResult:
    paths: dict[str, Path]
    gate: NoCashBacktestGateArtifact


@dataclass(frozen=True)
class GateThresholds:
    min_events_for_gate: int = MIN_EVENTS_FOR_GATE
    min_simulated_trades: int = MIN_SIMULATED_TRADES
    max_largest_loss_to_total_result_ratio: Decimal = MAX_LARGEST_LOSS_TO_TOTAL_RESULT_RATIO
    max_drawdown_to_total_result_ratio: Decimal = MAX_DRAWDOWN_TO_TOTAL_RESULT_RATIO
    require_books_trades_replay: bool = REQUIRE_BOOKS_TRADES_REPLAY

    def as_json(self) -> dict[str, Any]:
        return {
            "min_events_for_gate": self.min_events_for_gate,
            "min_simulated_trades": self.min_simulated_trades,
            "max_largest_loss_to_total_result_ratio": str(
                self.max_largest_loss_to_total_result_ratio
            ),
            "max_drawdown_to_total_result_ratio": str(self.max_drawdown_to_total_result_ratio),
            "require_books_trades_replay": self.require_books_trades_replay,
        }


def _json_ready(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _mapping(value: object) -> Mapping[str, Any]:
    return cast(Mapping[str, Any], value) if isinstance(value, Mapping) else {}


def _decimal(value: object, default: Decimal = Decimal("0")) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return default


def _int(value: object, default: int = 0) -> int:
    if isinstance(value, bool) or value is None:
        return default
    try:
        return int(str(value))
    except ValueError:
        return default


def _unique(values: Sequence[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _blocker(
    scope: BlockerScope,
    code: str,
    message: str,
    *,
    event_id: str | None = None,
    source_type: str | None = None,
    metric: str | None = None,
) -> NoCashBacktestGateBlocker:
    return NoCashBacktestGateBlocker(
        scope=scope,
        code=code,
        message=message,
        event_id=event_id,
        source_type=source_type,
        metric=metric,
    )


def _source_ref(path: Path) -> dict[str, str]:
    return file_artifact_ref(path)


def _read_json_mapping(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None, "missing"
    except json.JSONDecodeError:
        return None, "invalid_json"
    if not isinstance(payload, dict):
        return None, "not_object"
    return payload, None


def _missing_sources(ledger: Mapping[str, Any]) -> list[NoCashBacktestGateBlocker]:
    blockers: list[NoCashBacktestGateBlocker] = []
    rows = ledger.get("rows", [])
    if not isinstance(rows, list):
        return blockers
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        source_type = str(row.get("source_type", ""))
        if source_type not in _OPTIONAL_MARKET_SOURCES:
            continue
        if row.get("is_available") is True:
            continue
        blockers.append(
            _blocker(
                "source",
                f"{source_type.upper()}_SOURCE_MISSING",
                f"{source_type} source is missing and remains a known gap",
                event_id=str(row.get("event_id")) if row.get("event_id") is not None else None,
                source_type=source_type,
            )
        )
    return blockers


def _critical_missing_sources(ledger: Mapping[str, Any]) -> list[NoCashBacktestGateBlocker]:
    rows = ledger.get("rows", [])
    if not isinstance(rows, list):
        return []
    counts: Counter[str] = Counter()
    reasons: dict[str, set[str]] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        source_type = str(row.get("source_type", ""))
        if source_type not in _CRITICAL_SIGNAL_SOURCES:
            continue
        if row.get("is_available") is True:
            continue
        counts[source_type] += 1
        reason = str(row.get("missing_reason") or f"{source_type.upper()}_SOURCE_MISSING")
        reasons.setdefault(source_type, set()).add(reason)
    blockers: list[NoCashBacktestGateBlocker] = []
    for source_type in sorted(counts):
        reason_text = ", ".join(sorted(reasons.get(source_type, set())))
        blockers.append(
            _blocker(
                "source",
                f"CRITICAL_SIGNAL_SOURCE_MISSING_{source_type.upper()}",
                f"critical signal source {source_type} is missing for {counts[source_type]} rows: {reason_text}",
                source_type=source_type,
                metric="critical_missing_count",
            )
        )
    return blockers


def _no_trade_not_beaten(backtest_summary: Mapping[str, Any]) -> bool:
    beats = backtest_summary.get("beats_no_trade")
    if isinstance(beats, bool):
        return not beats
    return _decimal(backtest_summary.get("total_result_usd")) <= 0


def _largest_loss_ratio(backtest: Mapping[str, Any], total: Decimal) -> Decimal:
    if total <= 0:
        return Decimal("0")
    results = backtest.get("results", [])
    if not isinstance(results, list):
        return Decimal("0")
    losses = [
        _decimal(row.get("result_usd"))
        for row in results
        if isinstance(row, Mapping) and _decimal(row.get("result_usd")) < 0
    ]
    if not losses:
        return Decimal("0")
    return abs(min(losses)) / total


def build_no_cash_backtest_gate(
    *,
    decision: Mapping[str, Any] | None,
    data_availability: Mapping[str, Any] | None,
    backtest: Mapping[str, Any] | None,
    stress: Mapping[str, Any] | None,
    rolling_stability: Mapping[str, Any] | None,
    created_at: datetime | str,
    input_artifacts: Mapping[str, str],
    source_refs: Sequence[dict[str, str]] | None = None,
    thresholds: GateThresholds = GateThresholds(),
) -> NoCashBacktestGateArtifact:
    created = ensure_utc_aware("created_at", created_at)
    blockers: list[NoCashBacktestGateBlocker] = []
    known_gaps: list[str] = []

    if decision is None:
        blockers.append(
            _blocker(
                "input", "DECISION_INPUT_MISSING_OR_INVALID", "decision input is missing or invalid"
            )
        )
        decision = {}
    if data_availability is None:
        blockers.append(
            _blocker(
                "input",
                "DATA_AVAILABILITY_INPUT_MISSING_OR_INVALID",
                "source availability ledger is missing or invalid",
            )
        )
        data_availability = {}
    if backtest is None:
        blockers.append(
            _blocker(
                "input",
                "BACKTEST_INPUT_MISSING_OR_INVALID",
                "backtest result is missing or invalid",
            )
        )
        backtest = {}
    if stress is None:
        blockers.append(
            _blocker(
                "input", "STRESS_INPUT_MISSING_OR_INVALID", "stress result is missing or invalid"
            )
        )
        stress = {}
    if rolling_stability is None:
        blockers.append(
            _blocker(
                "input",
                "ROLLING_STABILITY_INPUT_MISSING_OR_INVALID",
                "rolling stability result is missing or invalid",
            )
        )
        rolling_stability = {}

    decision_summary = _mapping(decision.get("summary"))
    evidence = decision.get("evidence_grade_summary")
    evidence_summary = _mapping(evidence)
    ledger_summary = _mapping(data_availability.get("summary"))
    backtest_summary = _mapping(backtest.get("summary"))
    stress_summary = _mapping(stress.get("summary"))

    candidate_decision = str(decision.get("decision", "UNKNOWN"))
    event_count = _int(decision.get("event_count", ledger_summary.get("event_count")))
    outcome_count = _int(decision.get("outcome_count"))
    critical_missing_count = _int(
        evidence_summary.get("critical_missing_count", ledger_summary.get("critical_missing_count"))
    )
    future_signal_source_count = _int(
        evidence_summary.get(
            "future_signal_source_count", ledger_summary.get("future_signal_source_count")
        )
    )
    executed_trade_count = _int(
        evidence_summary.get("simulated_trade_count", backtest_summary.get("executed_trade_count"))
    )
    unknown_count = _int(backtest_summary.get("unknown_count"))
    blocked_missing_action_row_count = _int(
        backtest_summary.get("blocked_missing_action_row_count")
    )
    no_trade_count = _int(backtest_summary.get("no_trade_count"))
    total_result = _decimal(backtest_summary.get("total_result_usd"))
    stress_total = _decimal(stress_summary.get("total_result_usd"))
    max_drawdown = _decimal(backtest_summary.get("max_drawdown_usd"))
    rolling_status = str(rolling_stability.get("status", "missing"))
    pbo_status = str(decision_summary.get("pbo_status", "missing"))
    bias_guard_status = str(decision_summary.get("bias_guard_status", "missing"))
    guard_stop_reasons = [
        str(value) for value in decision_summary.get("bias_guard_stop_reasons", []) if value
    ]
    guard_warning_codes = [
        str(value) for value in decision_summary.get("bias_guard_warning_codes", []) if value
    ]
    known_gaps.extend(guard_warning_codes)
    overall_grade = str(evidence_summary.get("overall_grade", "missing"))
    largest_loss_ratio = _largest_loss_ratio(backtest, total_result)

    if evidence is None:
        blockers.append(
            _blocker(
                "candidate",
                "EVIDENCE_GRADE_SUMMARY_MISSING_LEGACY_COMPATIBILITY",
                "legacy v1 decision has no evidence_grade_summary; gate keeps compatibility but cannot hold",
            )
        )
    if bias_guard_status == "BLOCKED":
        blockers.append(
            _blocker(
                "metric",
                "BIAS_GUARD_BLOCKED",
                "bias guard blocked the candidate",
                metric="bias_guard_status",
            )
        )
        blockers.extend(
            _blocker("metric", reason, "bias guard stop reason", metric="bias_guard_status")
            for reason in guard_stop_reasons
        )
    elif bias_guard_status != "PASS":
        blockers.append(
            _blocker(
                "metric",
                "BIAS_GUARD_STATUS_MISSING_OR_UNKNOWN",
                "bias guard status is missing, not run, or unknown",
                metric="bias_guard_status",
            )
        )

    if candidate_decision == "BACKTEST_COLLECT_MORE_DATA":
        blockers.append(
            _blocker(
                "candidate",
                "BACKTEST_CANDIDATE_PACK_COLLECT_MORE_DATA",
                "candidate pack decision is BACKTEST_COLLECT_MORE_DATA",
            )
        )
    elif candidate_decision == "BACKTEST_REVISE":
        blockers.append(
            _blocker(
                "candidate", "BACKTEST_CANDIDATE_PACK_REVISE", "candidate pack requires revision"
            )
        )
    elif candidate_decision == "BACKTEST_REJECT":
        blockers.append(
            _blocker("candidate", "BACKTEST_CANDIDATE_PACK_REJECT", "candidate pack rejected")
        )
    elif candidate_decision != "BACKTEST_CANDIDATE_HOLD":
        blockers.append(
            _blocker(
                "candidate",
                "BACKTEST_CANDIDATE_PACK_STATUS_MISSING_OR_UNKNOWN",
                "candidate pack decision is missing or unknown",
            )
        )

    if candidate_decision != "BACKTEST_CANDIDATE_HOLD":
        existing_blocker_codes = {blocker.code for blocker in blockers}
        candidate_reason_codes = decision.get("reason_codes", [])
        if isinstance(candidate_reason_codes, Sequence) and not isinstance(
            candidate_reason_codes, str
        ):
            for value in candidate_reason_codes:
                code = str(value)
                if code and code not in existing_blocker_codes:
                    blockers.append(
                        _blocker(
                            "candidate",
                            code,
                            "candidate pack non-HOLD reason",
                        )
                    )
                    existing_blocker_codes.add(code)

    allowed_evidence_grades = {
        "insufficient_source_for_local_simulation",
        "local_simulation_with_recomputed_minimal_artifacts",
        "local_simulation_from_existing_artifacts",
    }
    if evidence is not None and overall_grade not in allowed_evidence_grades:
        blockers.append(
            _blocker(
                "candidate",
                "EVIDENCE_GRADE_STATUS_MISSING_OR_UNKNOWN",
                "evidence grade is missing or unknown",
            )
        )
    if overall_grade == "insufficient_source_for_local_simulation":
        blockers.append(
            _blocker(
                "candidate",
                "INSUFFICIENT_SOURCE_FOR_LOCAL_SIMULATION",
                "evidence grade says source is insufficient for local simulation",
            )
        )
    critical_source_blockers = _critical_missing_sources(data_availability)
    if critical_missing_count > 0 or critical_source_blockers:
        blockers.append(
            _blocker(
                "source", "CRITICAL_SIGNAL_SOURCE_MISSING", "critical signal source is missing"
            )
        )
        blockers.extend(critical_source_blockers)
    if future_signal_source_count > 0:
        blockers.append(
            _blocker(
                "source", "FUTURE_SIGNAL_SOURCE_USED", "future signal source availability detected"
            )
        )
    if event_count < thresholds.min_events_for_gate:
        blockers.append(
            _blocker(
                "event",
                "MIN_EVENTS_FOR_GATE_NOT_MET",
                "event sample is below no-cash backtest gate threshold",
                metric="event_count",
            )
        )
    if rolling_status in {"sample_insufficient", "missing"}:
        blockers.append(
            _blocker(
                "metric",
                "ROLLING_STABILITY_SAMPLE_INSUFFICIENT",
                "rolling stability is sample insufficient or missing",
                metric="rolling_stability.status",
            )
        )
    elif rolling_status != "complete":
        blockers.append(
            _blocker(
                "metric",
                "ROLLING_STABILITY_STATUS_UNKNOWN",
                "rolling stability status is unknown",
                metric="rolling_stability.status",
            )
        )
    if pbo_status in {"NOT_ESTIMABLE", "missing"}:
        blockers.append(
            _blocker(
                "metric",
                "PBO_NOT_ESTIMABLE_OR_MISSING",
                "PBO status is not estimable or missing",
                metric="pbo_status",
            )
        )
    elif pbo_status in {"INPUT_THRESHOLD_MET", "ESTIMATED"}:
        blockers.append(
            _blocker(
                "metric",
                "PBO_NOT_COMPUTED",
                "PBO input threshold is met but no PBO value was computed",
                metric="pbo_status",
            )
        )
    elif pbo_status != "COMPUTED_PASS":
        blockers.append(
            _blocker("metric", "PBO_FAILED", "PBO status is not passing", metric="pbo_status")
        )

    optional_source_gaps = _missing_sources(data_availability)
    if thresholds.require_books_trades_replay:
        blockers.extend(optional_source_gaps)
    else:
        known_gaps.extend(blocker.code for blocker in optional_source_gaps)

    collect_codes = {
        "DECISION_INPUT_MISSING_OR_INVALID",
        "DATA_AVAILABILITY_INPUT_MISSING_OR_INVALID",
        "BACKTEST_INPUT_MISSING_OR_INVALID",
        "STRESS_INPUT_MISSING_OR_INVALID",
        "ROLLING_STABILITY_INPUT_MISSING_OR_INVALID",
        "EVIDENCE_GRADE_SUMMARY_MISSING_LEGACY_COMPATIBILITY",
        "EVIDENCE_GRADE_STATUS_MISSING_OR_UNKNOWN",
        "BACKTEST_CANDIDATE_PACK_COLLECT_MORE_DATA",
        "INSUFFICIENT_SOURCE_FOR_LOCAL_SIMULATION",
        "CRITICAL_SIGNAL_SOURCE_MISSING",
        "FUTURE_SIGNAL_SOURCE_USED",
        "MIN_EVENTS_FOR_GATE_NOT_MET",
        "ROLLING_STABILITY_SAMPLE_INSUFFICIENT",
        "PBO_NOT_ESTIMABLE_OR_MISSING",
        "PBO_NOT_COMPUTED",
        "BIAS_GUARD_STATUS_MISSING_OR_UNKNOWN",
        "BACKTEST_CANDIDATE_PACK_STATUS_MISSING_OR_UNKNOWN",
        "ROLLING_STABILITY_STATUS_UNKNOWN",
    }
    reject_blockers: list[NoCashBacktestGateBlocker] = []
    revise_blockers: list[NoCashBacktestGateBlocker] = []

    if total_result <= 0:
        reject_blockers.append(
            _blocker(
                "metric", "BACKTEST_TOTAL_NOT_POSITIVE", "after-cost backtest total is not positive"
            )
        )
    if stress_total <= 0:
        reject_blockers.append(
            _blocker("metric", "STRESS_TOTAL_NOT_POSITIVE", "stress total is not positive")
        )
    if _no_trade_not_beaten(backtest_summary):
        reject_blockers.append(
            _blocker(
                "metric",
                "NO_TRADE_NOT_BEATEN_AFTER_COST",
                "NO_TRADE baseline is not beaten by selected simulated actions",
            )
        )
    if (
        total_result > 0
        and abs(max_drawdown) > total_result * thresholds.max_drawdown_to_total_result_ratio
    ):
        reject_blockers.append(
            _blocker(
                "metric", "DRAWDOWN_TOO_LARGE_FOR_TOTAL_RESULT", "drawdown exceeds gate threshold"
            )
        )
    if largest_loss_ratio > thresholds.max_largest_loss_to_total_result_ratio:
        reject_blockers.append(
            _blocker(
                "metric",
                "LARGEST_LOSS_CONCENTRATION_TOO_HIGH",
                "largest loss concentration exceeds gate threshold",
            )
        )

    if executed_trade_count < thresholds.min_simulated_trades:
        revise_blockers.append(
            _blocker(
                "metric",
                "MIN_SIMULATED_TRADES_NOT_MET",
                "simulated trade count is below gate threshold",
                metric="executed_trade_count",
            )
        )
    if executed_trade_count == 0:
        revise_blockers.append(
            _blocker("metric", "NO_EXECUTABLE_SIMULATED_TRADES", "no executable simulated trades")
        )
    if unknown_count > 0:
        revise_blockers.append(
            _blocker("event", "SELECTED_ACTION_UNKNOWN", "selected action has UNKNOWN rows")
        )
    if blocked_missing_action_row_count > 0:
        revise_blockers.append(
            _blocker("event", "ACTION_ROWS_MISSING", "action rows are missing for selected actions")
        )

    deduplicated_blockers: list[NoCashBacktestGateBlocker] = []
    seen_blockers: set[tuple[object, ...]] = set()
    for blocker in blockers:
        identity = (
            blocker.code,
            blocker.event_id,
            blocker.source_type,
        )
        if identity not in seen_blockers:
            deduplicated_blockers.append(blocker)
            seen_blockers.add(identity)
    blockers = deduplicated_blockers
    blocker_codes = {blocker.code for blocker in blockers}
    if "BIAS_GUARD_BLOCKED" in blocker_codes:
        gate_decision: NoCashBacktestGateDecision = "NO_CASH_BACKTEST_REJECT"
    elif any(blocker.code == "BACKTEST_CANDIDATE_PACK_REJECT" for blocker in blockers):
        gate_decision = "NO_CASH_BACKTEST_REJECT"
    elif blocker_codes.intersection(collect_codes):
        gate_decision = "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    elif any(blocker.code == "BACKTEST_CANDIDATE_PACK_REVISE" for blocker in blockers):
        gate_decision = "NO_CASH_BACKTEST_REVISE"
    elif blockers:
        gate_decision = "NO_CASH_BACKTEST_COLLECT_MORE_DATA"
    elif reject_blockers:
        blockers.extend(reject_blockers)
        gate_decision = "NO_CASH_BACKTEST_REJECT"
    elif revise_blockers:
        blockers.extend(revise_blockers)
        gate_decision = "NO_CASH_BACKTEST_REVISE"
    else:
        gate_decision = "NO_CASH_BACKTEST_HOLD"

    if gate_decision == "NO_CASH_BACKTEST_HOLD":
        reason_codes = [
            "NO_CASH_BACKTEST_GATE_HOLD_FOR_HUMAN_REVIEW",
            "PAPER_PERMISSION_NOT_GRANTED",
            "ACTUAL_CASH_NOT_IN_SCOPE",
        ]
    else:
        reason_codes = _unique([blocker.code for blocker in blockers])

    known_gaps.extend(str(value) for value in evidence_summary.get("known_limits", []) if value)
    known_gaps.append("PAPER_PERMISSION_NOT_GRANTED")
    known_gaps.append("ACTUAL_CASH_NOT_IN_SCOPE")
    known_gaps.append("WALLET_SIGNING_EXCHANGE_WRITE_NOT_IN_SCOPE")

    summary = {
        "candidate_decision": candidate_decision,
        "event_count": event_count,
        "outcome_count": outcome_count,
        "critical_missing_count": critical_missing_count,
        "future_signal_source_count": future_signal_source_count,
        "executed_trade_count": executed_trade_count,
        "no_trade_count": no_trade_count,
        "unknown_count": unknown_count,
        "blocked_missing_action_row_count": blocked_missing_action_row_count,
        "total_result_usd": str(total_result),
        "stress_total_result_usd": str(stress_total),
        "max_drawdown_usd": str(max_drawdown),
        "largest_loss_to_total_result_ratio": str(largest_loss_ratio),
        "rolling_stability_status": rolling_status,
        "pbo_status": pbo_status,
        "bias_guard_status": bias_guard_status,
        "bias_guard_warning_codes": guard_warning_codes,
        "paper_permission_granted": False,
        "actual_cash_used": False,
    }
    payload_for_hash = [
        NO_CASH_BACKTEST_GATE_SCHEMA_VERSION,
        serialize_utc_z(created),
        gate_decision,
        reason_codes,
        [blocker.model_dump(mode="json") for blocker in blockers],
        summary,
        thresholds.as_json(),
        dict(input_artifacts),
    ]
    return NoCashBacktestGateArtifact(
        artifact_id=stable_hash(payload_for_hash),
        created_at=created,
        producer=CryptoPerpProducer(command=NO_CASH_BACKTEST_GATE_PRODUCER),
        source_refs=[dict(ref) for ref in source_refs or []],
        gate_decision=gate_decision,
        reason_codes=reason_codes,
        blockers=blockers,
        known_gaps=_unique(known_gaps),
        thresholds=thresholds.as_json(),
        summary=_json_ready(summary),
        input_artifacts=dict(input_artifacts),
    )


def render_no_cash_backtest_gate_markdown(artifact: NoCashBacktestGateArtifact) -> str:
    blocker_lines = [f"- `{blocker.code}`: {blocker.message}" for blocker in artifact.blockers]
    if not blocker_lines:
        blocker_lines = ["- none"]
    return "\n".join(
        [
            "# Crypto Perp No-Cash Backtest Gate",
            "",
            f"- created_at: `{serialize_utc_z(artifact.created_at)}`",
            f"- gate_decision: `{artifact.gate_decision}`",
            f"- blocker_count: `{len(artifact.blockers)}`",
            "- paper_permission_granted: `false`",
            "- permits_paper_order: `false`",
            "- actual_cash_used: `false`",
            "- permits_live_order: `false`",
            "- wallet_used: `false`",
            "- signing_used: `false`",
            "- exchange_write_used: `false`",
            "",
            "## Blockers",
            "",
            *blocker_lines,
            "",
            "This artifact is a no-cash local simulation gate before human review for Paper Observation. It does not grant paper order permission, prove profit, use actual cash, or permit live orders.",
        ]
    )


def write_no_cash_backtest_gate(
    *,
    decision_path: Path,
    data_availability_path: Path,
    backtest_path: Path,
    stress_path: Path,
    rolling_stability_path: Path,
    out_dir: Path,
    created_at: datetime | str,
    thresholds: GateThresholds = GateThresholds(),
) -> NoCashBacktestGateResult:
    inputs = {
        "decision": decision_path,
        "data_availability": data_availability_path,
        "backtest": backtest_path,
        "stress": stress_path,
        "rolling_stability": rolling_stability_path,
    }
    payloads: dict[str, dict[str, Any] | None] = {}
    source_refs: list[dict[str, str]] = []
    input_artifacts: dict[str, str] = {name: path.as_posix() for name, path in inputs.items()}
    for name, path in inputs.items():
        payload, error = _read_json_mapping(path)
        payloads[name] = payload
        if error is not None:
            input_artifacts[f"{name}_error"] = error
            continue
        source_refs.append(_source_ref(path))
    gate = build_no_cash_backtest_gate(
        decision=payloads["decision"],
        data_availability=payloads["data_availability"],
        backtest=payloads["backtest"],
        stress=payloads["stress"],
        rolling_stability=payloads["rolling_stability"],
        created_at=created_at,
        input_artifacts=input_artifacts,
        source_refs=source_refs,
        thresholds=thresholds,
    )
    json_path = out_dir / "no_cash_backtest_gate.json"
    md_path = out_dir / "no_cash_backtest_gate.md"
    write_json_artifact(json_path, gate.model_dump(mode="json"))
    write_text_artifact(md_path, render_no_cash_backtest_gate_markdown(gate))
    return NoCashBacktestGateResult(
        paths={
            "no_cash_backtest_gate.json": json_path,
            "no_cash_backtest_gate.md": md_path,
        },
        gate=gate,
    )
