from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_live_observation.models import (
    LiveObservationIngestStatus,
    LiveObservationSourceArtifact,
    LiveObservationSummary,
    StrategyLiveObservationManifest,
)
from sis.strategy_live_observation.rendering import render_live_observation_markdown
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_stage.models import StageProducer


@dataclass(frozen=True)
class StrategyLiveObservationResult:
    manifest: StrategyLiveObservationManifest
    manifest_path: Path
    report_path: Path


class StrategyLiveObservationError(ValueError):
    pass


class StrategyLiveObservationOutputExistsError(StrategyLiveObservationError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _source_artifact(artifact_key: str, path: Path) -> LiveObservationSourceArtifact:
    return LiveObservationSourceArtifact(
        artifact_key=artifact_key,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=detect_json_schema_version(path),
    )


def _as_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _as_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _summary_from_audit(payload: dict[str, Any]) -> LiveObservationSummary:
    status = _as_str(payload.get("status"))
    if status is None:
        raise StrategyLiveObservationError("audit bundle missing status")
    blocked_reasons = [
        str(item)
        for item in payload.get("blocked_reasons", [])
        if isinstance(item, str) and item.strip()
    ]
    request = _as_dict(payload.get("request"))
    actions = _as_dict(payload.get("actions"))
    account = _as_dict(payload.get("account"))
    order_status = _as_str(actions.get("order_status"))
    order_submit_status = _as_str(actions.get("order_submit_status"))
    cancel_status = _as_str(actions.get("cancel_status"))
    close_status = _as_str(actions.get("close_status"))
    return LiveObservationSummary(
        canary_status=status,
        blocked_reasons=blocked_reasons,
        canonical_symbol=_as_str(request.get("canonical_symbol")),
        side=_as_str(request.get("side")),
        quantity=_as_float(request.get("quantity")),
        limit_price=_as_float(request.get("limit_price")),
        notional_usd=_as_float(request.get("notional_usd")),
        leverage=_as_float(request.get("leverage")),
        schedule_cancel_status=_as_str(actions.get("schedule_cancel_status")),
        order_submit_status=order_submit_status,
        order_status=order_status,
        cancel_status=cancel_status,
        close_status=close_status,
        actual_fill_observed=order_status == "filled",
        rejection_observed=status == "order_rejected" or order_submit_status == "rejected",
        cancel_observed=cancel_status is not None,
        close_submitted=close_status is not None,
        max_loss_breach_observed="BLOCK_DAILY_LOSS_LIMIT" in blocked_reasons,
        account_snapshot_present=bool(account),
        account_equity=_as_float(account.get("equity")),
        account_available_cash=_as_float(account.get("available_cash")),
    )


def _ingest_status(
    *, boundary_violations: list[str], canary_status: str
) -> LiveObservationIngestStatus:
    if boundary_violations:
        return LiveObservationIngestStatus.BLOCKED_BOUNDARY_VIOLATION
    if canary_status.startswith("blocked"):
        return LiveObservationIngestStatus.BLOCKED_CANARY
    return LiveObservationIngestStatus.LIVE_OBSERVATION_INGESTED


def ingest_strategy_live_observation(
    *,
    strategy_id: str,
    audit_bundle_path: Path,
    out_dir: Path,
    report_path: Path | None = None,
    micro_live_plan_path: Path | None = None,
    observation_id: str | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> StrategyLiveObservationResult:
    if not audit_bundle_path.exists():
        raise FileNotFoundError(f"audit bundle missing: {audit_bundle_path}")
    if report_path is not None and not report_path.exists():
        raise FileNotFoundError(f"report missing: {report_path}")
    if micro_live_plan_path is not None and not micro_live_plan_path.exists():
        raise FileNotFoundError(f"micro live plan missing: {micro_live_plan_path}")

    payload = read_json_object(audit_bundle_path)
    if payload.get("operation") != "micro_live_canary":
        raise StrategyLiveObservationError("audit bundle operation must be micro_live_canary")
    boundary_violations = boundary_true_paths(payload)
    summary = _summary_from_audit(payload)
    selected_observation_id = observation_id or f"{strategy_id}-live-observation"
    source_artifacts = [
        _source_artifact("micro_live_canary_audit_bundle", audit_bundle_path),
        *([_source_artifact("micro_live_canary_report", report_path)] if report_path else []),
        *(
            [_source_artifact("micro_live_plan", micro_live_plan_path)]
            if micro_live_plan_path
            else []
        ),
    ]
    manifest = StrategyLiveObservationManifest(
        strategy_id=strategy_id,
        observation_id=selected_observation_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-live-observation-ingest"),
        ingest_status=_ingest_status(
            boundary_violations=boundary_violations,
            canary_status=summary.canary_status,
        ),
        source_artifacts=source_artifacts,
        summary=summary,
    )
    manifest_dir = out_dir / strategy_id
    manifest_path = manifest_dir / "strategy_live_observation_manifest.json"
    markdown_path = manifest_dir / "strategy_live_observation.md"
    if not replace_existing and (manifest_path.exists() or markdown_path.exists()):
        raise StrategyLiveObservationOutputExistsError(
            f"output already exists: {repo_relative_path(manifest_dir)}"
        )
    try:
        write_json_artifact(manifest_path, manifest.model_dump(mode="json", exclude_none=True))
        write_text_artifact(markdown_path, render_live_observation_markdown(manifest))
    except ValidationError as exc:
        raise StrategyLiveObservationError(f"invalid live observation manifest: {exc}") from exc
    return StrategyLiveObservationResult(
        manifest=manifest,
        manifest_path=manifest_path,
        report_path=markdown_path,
    )
