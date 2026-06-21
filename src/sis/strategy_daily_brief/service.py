from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from sis.backtest.artifact_io import sha256_file
from sis.strategy_daily_brief.models import (
    DailyBriefItem,
    DailyBriefItemCategory,
    DailyBriefItemSeverity,
    DailyBriefSourceArtifact,
    DailyBriefSummary,
    StrategyDailyBrief,
)
from sis.strategy_daily_brief.rendering import render_strategy_daily_brief_markdown
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_review.provenance import (
    boundary_true_paths,
    repo_relative_path,
)
from sis.strategy_stage.models import StageProducer


@dataclass(frozen=True)
class StrategyDailyBriefResult:
    brief: StrategyDailyBrief
    brief_path: Path
    report_path: Path


class StrategyDailyBriefError(ValueError):
    pass


class StrategyDailyBriefOutputExistsError(StrategyDailyBriefError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _json_paths(data_dir: Path) -> list[Path]:
    return sorted(path for path in data_dir.rglob("*.json") if path.is_file())


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise StrategyDailyBriefError(f"invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise StrategyDailyBriefError("expected JSON object")
    return payload


def _source_artifact(path: Path, payload: dict[str, Any]) -> DailyBriefSourceArtifact:
    schema_version = payload.get("schema_version")
    return DailyBriefSourceArtifact(
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=schema_version if isinstance(schema_version, str) else None,
    )


def _first_string(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _item(
    *,
    category: DailyBriefItemCategory,
    severity: DailyBriefItemSeverity,
    path: Path,
    payload: dict[str, Any] | None,
    reason: str,
    status: str | None = None,
    action: str | None = None,
) -> DailyBriefItem:
    schema_version = None
    strategy_id = None
    sha256 = None
    if payload is not None:
        schema = payload.get("schema_version")
        schema_version = schema if isinstance(schema, str) else None
        strategy_id = _first_string(payload, ("strategy_id", "case_id", "review_id"))
        sha256 = sha256_file(path)
    return DailyBriefItem(
        category=category,
        severity=severity,
        path=repo_relative_path(path),
        schema_version=schema_version,
        strategy_id=strategy_id,
        status=status or (_status(payload) if payload is not None else None),
        action=action or (_action(payload) if payload is not None else None),
        reason=reason,
        sha256=sha256,
    )


def _status(payload: dict[str, Any]) -> str | None:
    return _first_string(
        payload,
        (
            "decision",
            "review_status",
            "ingest_status",
            "plan_status",
            "decision_status",
            "gate_status",
            "request_status",
            "handoff_status",
            "validation_status",
        ),
    )


def _action(payload: dict[str, Any]) -> str | None:
    return _first_string(payload, ("recommended_action", "next_action", "request_status"))


def _is_pending_human_review(payload: dict[str, Any]) -> bool:
    schema = payload.get("schema_version")
    if schema == "strategy_live_observation_manifest.v1":
        return payload.get("ingest_status") in {
            "LIVE_OBSERVATION_INGESTED",
            "BLOCKED_CANARY",
            "BLOCKED_BOUNDARY_VIOLATION",
        }
    if schema == "strategy_scale_decision.v1":
        return payload.get("decision_status") == "READY_FOR_HUMAN_SCALE_REVIEW"
    if schema == "strategy_next_scale_plan.v1":
        return payload.get("plan_status") == "READY_FOR_HUMAN_NEXT_SCALE_REVIEW"
    if schema == "crypto_perp_tournament_gate.v1":
        return payload.get("gate_status") == "READY_FOR_HUMAN_TINY_LIVE_REVIEW"
    values = [value for value in (_status(payload), _action(payload)) if value]
    return any("HUMAN" in value or value == "PAPER_OBSERVATION_CANDIDATE" for value in values)


def _normal_gap_reasons(payload: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    summary = payload.get("paper_evidence_summary")
    if isinstance(summary, dict):
        for key in ("normal_fills", "normal_trading_days"):
            gap = summary.get(key)
            if isinstance(gap, dict):
                remaining = gap.get("remaining")
                if isinstance(remaining, int) and remaining > 0:
                    reasons.append(f"{key}.remaining={remaining}")
    for condition in payload.get("failed_conditions", []):
        if isinstance(condition, dict):
            condition_id = condition.get("condition_id")
            if condition_id in {"normal_fills_for_policy", "normal_trading_days_for_policy"}:
                reasons.append(str(condition_id))
    return sorted(set(reasons))


def _learning_pending(payload: dict[str, Any]) -> bool:
    schema = payload.get("schema_version")
    status = _status(payload)
    return (schema == "strategy_revision_request.v1" and status == "READY_FOR_HUMAN_REVIEW") or (
        schema == "strategy_authoring_update_handoff.v1"
        and status == "READY_FOR_HUMAN_AUTHORING_UPDATE"
    )


def _crypto_perp_gate_follow_up(payload: dict[str, Any]) -> str | None:
    if payload.get("schema_version") != "crypto_perp_tournament_gate.v1":
        return None
    status = payload.get("gate_status")
    action = payload.get("recommended_action")
    if not isinstance(status, str):
        return "missing gate_status"
    if status == "READY_FOR_HUMAN_TINY_LIVE_REVIEW":
        return "human tiny live review preparation is required before any live measurement"
    if isinstance(action, str) and action:
        return f"crypto perp tournament gate follow-up: {action}"
    return f"crypto perp tournament gate follow-up: {status}"


def _items_for_payload(path: Path, payload: dict[str, Any]) -> list[DailyBriefItem]:
    items: list[DailyBriefItem] = []
    schema = payload.get("schema_version")
    if not isinstance(schema, str):
        items.append(
            _item(
                category=DailyBriefItemCategory.BROKEN_ARTIFACT,
                severity=DailyBriefItemSeverity.WARNING,
                path=path,
                payload=payload,
                reason="missing schema_version",
            )
        )

    boundary_paths = boundary_true_paths(payload)
    for boundary_path in boundary_paths:
        items.append(
            _item(
                category=DailyBriefItemCategory.BOUNDARY_VIOLATION,
                severity=DailyBriefItemSeverity.ERROR,
                path=path,
                payload=payload,
                reason=f"boundary true flag: {boundary_path}",
            )
        )

    if _is_pending_human_review(payload):
        items.append(
            _item(
                category=DailyBriefItemCategory.PENDING_HUMAN_REVIEW,
                severity=DailyBriefItemSeverity.WARNING,
                path=path,
                payload=payload,
                reason="human review or human action is required",
            )
        )

    for reason in _normal_gap_reasons(payload):
        items.append(
            _item(
                category=DailyBriefItemCategory.NORMAL_PAPER_GAP,
                severity=DailyBriefItemSeverity.WARNING,
                path=path,
                payload=payload,
                reason=reason,
            )
        )

    gate_reason = _crypto_perp_gate_follow_up(payload)
    if gate_reason is not None:
        severity = (
            DailyBriefItemSeverity.INFO
            if payload.get("gate_status") == "READY_FOR_HUMAN_TINY_LIVE_REVIEW"
            else DailyBriefItemSeverity.WARNING
        )
        items.append(
            _item(
                category=DailyBriefItemCategory.CRYPTO_PERP_GATE_FOLLOW_UP,
                severity=severity,
                path=path,
                payload=payload,
                reason=gate_reason,
            )
        )

    if (
        schema == "strategy_stage_decision.v1"
        and payload.get("decision") == "READY_FOR_DRIFT_REVIEW"
    ):
        items.append(
            _item(
                category=DailyBriefItemCategory.DRIFT_REVIEW_NEEDED,
                severity=DailyBriefItemSeverity.INFO,
                path=path,
                payload=payload,
                reason="stage decision is ready for drift review",
            )
        )

    if _learning_pending(payload):
        items.append(
            _item(
                category=DailyBriefItemCategory.LEARNING_REQUEST_PENDING,
                severity=DailyBriefItemSeverity.WARNING,
                path=path,
                payload=payload,
                reason="learning or authoring update requires human follow-up",
            )
        )
    return items


def _summary(*, scanned_count: int, items: list[DailyBriefItem]) -> DailyBriefSummary:
    counts = Counter(item.category for item in items)
    return DailyBriefSummary(
        scanned_json_count=scanned_count,
        broken_artifact_count=counts[DailyBriefItemCategory.BROKEN_ARTIFACT],
        pending_human_review_count=counts[DailyBriefItemCategory.PENDING_HUMAN_REVIEW],
        crypto_perp_gate_follow_up_count=counts[DailyBriefItemCategory.CRYPTO_PERP_GATE_FOLLOW_UP],
        normal_paper_gap_count=counts[DailyBriefItemCategory.NORMAL_PAPER_GAP],
        drift_review_needed_count=counts[DailyBriefItemCategory.DRIFT_REVIEW_NEEDED],
        learning_request_pending_count=counts[DailyBriefItemCategory.LEARNING_REQUEST_PENDING],
        boundary_violation_count=counts[DailyBriefItemCategory.BOUNDARY_VIOLATION],
        total_item_count=len(items),
    )


def build_strategy_daily_brief(
    *,
    data_dir: Path,
    out_dir: Path,
    replace_existing: bool = False,
    generated_at: datetime | None = None,
) -> StrategyDailyBriefResult:
    if not data_dir.exists():
        raise FileNotFoundError(f"data_dir missing: {data_dir}")
    if not data_dir.is_dir():
        raise StrategyDailyBriefError(f"data_dir is not a directory: {data_dir}")

    source_artifacts: list[DailyBriefSourceArtifact] = []
    items: list[DailyBriefItem] = []
    paths = _json_paths(data_dir)
    for path in paths:
        try:
            payload = _read_json_object(path)
        except StrategyDailyBriefError as exc:
            items.append(
                _item(
                    category=DailyBriefItemCategory.BROKEN_ARTIFACT,
                    severity=DailyBriefItemSeverity.ERROR,
                    path=path,
                    payload=None,
                    reason=str(exc),
                )
            )
            continue
        source_artifacts.append(_source_artifact(path, payload))
        items.extend(_items_for_payload(path, payload))

    brief = StrategyDailyBrief(
        generated_at=generated_at or _utc_now(),
        producer=StageProducer(command="strategy-daily-brief"),
        data_dir=repo_relative_path(data_dir),
        source_artifacts=source_artifacts,
        summary=_summary(scanned_count=len(paths), items=items),
        items=sorted(items, key=lambda item: (item.category.value, item.severity.value, item.path)),
    )

    brief_path = out_dir / "strategy_daily_brief.json"
    report_path = out_dir / "strategy_daily_brief.md"
    if not replace_existing and (brief_path.exists() or report_path.exists()):
        raise StrategyDailyBriefOutputExistsError(
            f"output already exists: {repo_relative_path(out_dir)}"
        )
    write_json_artifact(brief_path, brief.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_strategy_daily_brief_markdown(brief))
    return StrategyDailyBriefResult(brief=brief, brief_path=brief_path, report_path=report_path)
