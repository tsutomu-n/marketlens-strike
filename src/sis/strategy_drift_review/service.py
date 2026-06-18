from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from sis.backtest.artifact_io import read_json_object, sha256_file
from sis.strategy_drift_review.models import (
    DriftBacktestSummary,
    DriftMetrics,
    DriftReviewAction,
    DriftReviewSourceArtifact,
    DriftReviewStatus,
    DriftRuntimeSummary,
    PaperVsBacktestDriftReview,
)
from sis.strategy_drift_review.rendering import render_drift_review_markdown
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_review.provenance import (
    boundary_true_paths,
    detect_json_schema_version,
    repo_relative_path,
)
from sis.strategy_runtime_observation.models import StrategyRuntimeObservationManifest
from sis.strategy_stage.models import StageCondition, StageProducer


@dataclass(frozen=True)
class DriftReviewBuildResult:
    review: PaperVsBacktestDriftReview
    review_path: Path
    report_path: Path


class StrategyDriftReviewError(ValueError):
    pass


class StrategyDriftReviewOutputExistsError(StrategyDriftReviewError):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _condition(
    condition_id: str,
    passed: bool,
    observed: Any,
    required: Any,
    *,
    severity: Literal["error", "warning"] = "error",
) -> StageCondition:
    return StageCondition(
        condition_id=condition_id,
        passed=passed,
        observed=str(observed),
        required=str(required),
        severity=severity,
    )


def _source_artifact(artifact_key: str, path: Path) -> DriftReviewSourceArtifact:
    return DriftReviewSourceArtifact(
        artifact_key=artifact_key,
        path=repo_relative_path(path),
        sha256=sha256_file(path),
        schema_version=detect_json_schema_version(path),
    )


def _float_or_none(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _int_or_zero(value: Any) -> int:
    return int(value) if isinstance(value, int) and value >= 0 else 0


def _read_backtest_summary(path: Path) -> tuple[dict[str, Any], DriftBacktestSummary]:
    payload = read_json_object(path)
    if payload.get("schema_version") != "strategy_authoring_backtest_result.v1":
        raise StrategyDriftReviewError("backtest result schema_version mismatch")
    summary = payload.get("summary")
    metrics = payload.get("metrics")
    if not isinstance(summary, dict) or not isinstance(metrics, list):
        raise StrategyDriftReviewError("backtest result missing summary or metrics")
    metric_rows = [row for row in metrics if isinstance(row, dict)]
    trade_count = sum(_int_or_zero(row.get("trade_count")) for row in metric_rows)
    total_return = sum(_float_or_none(row.get("total_return")) or 0.0 for row in metric_rows)
    drawdowns = [
        value
        for row in metric_rows
        if (value := _float_or_none(row.get("max_drawdown"))) is not None
    ]
    executed_summary = summary.get("executed_signal_summary")
    if not isinstance(executed_summary, dict):
        executed_summary = {}
    return payload, DriftBacktestSummary(
        strategy_id=str(payload.get("strategy_id") or ""),
        backtest_passed=bool(summary.get("backtest_passed")),
        signals_considered=_int_or_zero(summary.get("signals_considered")),
        executed_count=_int_or_zero(summary.get("executed_count")),
        blocked_count=_int_or_zero(summary.get("blocked_count")),
        trade_count=trade_count,
        total_return=total_return,
        max_drawdown=min(drawdowns) if drawdowns else None,
        win_rate=_float_or_none(executed_summary.get("win_rate")),
    )


def _read_runtime_summary(path: Path) -> tuple[dict[str, Any], DriftRuntimeSummary]:
    payload = read_json_object(path)
    try:
        manifest = StrategyRuntimeObservationManifest.model_validate(payload)
    except (ValidationError, ValueError) as exc:
        raise StrategyDriftReviewError(f"invalid runtime observation manifest: {exc}") from exc
    summary = manifest.summary
    return payload, DriftRuntimeSummary(
        strategy_id=manifest.strategy_id,
        session_id=manifest.session_id,
        source_stage=manifest.source_stage,
        ingest_status=manifest.ingest_status,
        ledger_entry_count=summary.ledger_entry_count,
        paper_fill_count=summary.paper_fill_count,
        blocked_count=summary.blocked_count,
        no_fill_count=summary.no_fill_count,
        max_observed_spread_bps=summary.max_observed_spread_bps,
        max_observed_quote_age_ms=summary.max_observed_quote_age_ms,
        pnl_available=summary.pnl_available,
        pnl_unavailable_reason=summary.pnl_unavailable_reason,
        realized_pnl_usd_total=summary.realized_pnl_usd_total,
        gross_pnl_usd_total=summary.gross_pnl_usd_total,
        fee_usd_total=summary.fee_usd_total,
        slippage_usd_total=summary.slippage_usd_total,
        avg_slippage_bps=summary.avg_slippage_bps,
        max_abs_slippage_bps=summary.max_abs_slippage_bps,
        avg_fill_price_drift_bps=summary.avg_fill_price_drift_bps,
        max_abs_fill_price_drift_bps=summary.max_abs_fill_price_drift_bps,
        filled_notional_usd_total=summary.filled_notional_usd_total,
        order_lifecycle_counts=summary.order_lifecycle_counts,
    )


def _drift_metrics(
    backtest: DriftBacktestSummary | None, runtime: DriftRuntimeSummary | None
) -> DriftMetrics:
    if runtime is None:
        return DriftMetrics()
    denominator = runtime.ledger_entry_count
    runtime_return = (
        runtime.realized_pnl_usd_total / runtime.filled_notional_usd_total
        if runtime.realized_pnl_usd_total is not None
        and runtime.filled_notional_usd_total is not None
        and runtime.filled_notional_usd_total > 0
        else None
    )
    backtest_return = backtest.total_return if backtest is not None else None
    return DriftMetrics(
        runtime_to_backtest_trade_count_ratio=(
            runtime.paper_fill_count / backtest.trade_count
            if backtest is not None and backtest.trade_count > 0
            else None
        ),
        runtime_blocked_rate=runtime.blocked_count / denominator if denominator else None,
        runtime_no_fill_rate=runtime.no_fill_count / denominator if denominator else None,
        max_observed_spread_bps=runtime.max_observed_spread_bps,
        max_observed_quote_age_ms=runtime.max_observed_quote_age_ms,
        pnl_drift_available=runtime.pnl_available and runtime_return is not None,
        backtest_total_return=backtest_return,
        runtime_return_on_filled_notional=runtime_return,
        runtime_vs_backtest_return_drift=(
            runtime_return - backtest_return
            if runtime_return is not None and backtest_return is not None
            else None
        ),
        runtime_realized_pnl_usd_total=runtime.realized_pnl_usd_total,
        runtime_fee_usd_total=runtime.fee_usd_total,
        runtime_slippage_usd_total=runtime.slippage_usd_total,
        runtime_avg_slippage_bps=runtime.avg_slippage_bps,
        runtime_max_abs_slippage_bps=runtime.max_abs_slippage_bps,
        runtime_avg_fill_price_drift_bps=runtime.avg_fill_price_drift_bps,
        runtime_max_abs_fill_price_drift_bps=runtime.max_abs_fill_price_drift_bps,
    )


def _status_for(
    *,
    boundary_failed: bool,
    backtest: DriftBacktestSummary | None,
    runtime: DriftRuntimeSummary | None,
) -> DriftReviewStatus:
    if boundary_failed:
        return DriftReviewStatus.BLOCKED_BOUNDARY_VIOLATION
    if backtest is None:
        return DriftReviewStatus.NEEDS_BACKTEST_RESULT
    if runtime is None or runtime.ingest_status == "EMPTY_LEDGER":
        return DriftReviewStatus.NEEDS_RUNTIME_OBSERVATION
    return DriftReviewStatus.READY_FOR_HUMAN_DRIFT_REVIEW


def _recommended_action(
    status: DriftReviewStatus,
    *,
    runtime: DriftRuntimeSummary | None,
    metrics: DriftMetrics,
    max_no_fill_rate: float,
    max_blocked_rate: float,
    max_spread_bps: float | None,
    max_return_drift: float | None,
) -> DriftReviewAction:
    if status is DriftReviewStatus.BLOCKED_BOUNDARY_VIOLATION:
        return DriftReviewAction.REPAIR_ARTIFACTS
    if status in {
        DriftReviewStatus.NEEDS_BACKTEST_RESULT,
        DriftReviewStatus.NEEDS_RUNTIME_OBSERVATION,
    }:
        return DriftReviewAction.EXTEND_OBSERVATION
    if runtime is None:
        return DriftReviewAction.EXTEND_OBSERVATION
    if metrics.runtime_no_fill_rate is not None and metrics.runtime_no_fill_rate > max_no_fill_rate:
        return DriftReviewAction.REVISE_STRATEGY
    if metrics.runtime_blocked_rate is not None and metrics.runtime_blocked_rate > max_blocked_rate:
        return DriftReviewAction.REVISE_STRATEGY
    if (
        max_spread_bps is not None
        and runtime.max_observed_spread_bps is not None
        and runtime.max_observed_spread_bps > max_spread_bps
    ):
        return DriftReviewAction.REVISE_STRATEGY
    if (
        max_return_drift is not None
        and metrics.runtime_vs_backtest_return_drift is not None
        and abs(metrics.runtime_vs_backtest_return_drift) > max_return_drift
    ):
        return DriftReviewAction.REVISE_STRATEGY
    return DriftReviewAction.HUMAN_REVIEW_REQUIRED


def build_drift_review(
    *,
    strategy_id: str | None,
    backtest_result_path: Path,
    runtime_observation_path: Path,
    out_dir: Path,
    max_no_fill_rate: float = 0.5,
    max_blocked_rate: float = 0.5,
    max_spread_bps: float | None = None,
    max_return_drift: float | None = None,
    replace_existing: bool = False,
    created_at: datetime | None = None,
) -> DriftReviewBuildResult:
    if not backtest_result_path.exists():
        raise FileNotFoundError(f"backtest result missing: {backtest_result_path}")
    if not runtime_observation_path.exists():
        raise FileNotFoundError(f"runtime observation missing: {runtime_observation_path}")
    if not (0 <= max_no_fill_rate <= 1):
        raise StrategyDriftReviewError("max_no_fill_rate must be between 0 and 1")
    if not (0 <= max_blocked_rate <= 1):
        raise StrategyDriftReviewError("max_blocked_rate must be between 0 and 1")
    if max_spread_bps is not None and max_spread_bps < 0:
        raise StrategyDriftReviewError("max_spread_bps must be >= 0")
    if max_return_drift is not None and max_return_drift < 0:
        raise StrategyDriftReviewError("max_return_drift must be >= 0")

    backtest_payload, backtest_summary = _read_backtest_summary(backtest_result_path)
    runtime_payload, runtime_summary = _read_runtime_summary(runtime_observation_path)
    selected_strategy_id = (
        strategy_id or runtime_summary.strategy_id or backtest_summary.strategy_id
    )
    if not selected_strategy_id:
        raise StrategyDriftReviewError("strategy_id is required")

    boundary_violations = [
        *boundary_true_paths(backtest_payload),
        *boundary_true_paths(runtime_payload),
    ]
    metrics = _drift_metrics(backtest_summary, runtime_summary)
    conditions = [
        _condition(
            "strategy_id_matches",
            backtest_summary.strategy_id == runtime_summary.strategy_id == selected_strategy_id,
            f"backtest={backtest_summary.strategy_id}, runtime={runtime_summary.strategy_id}, selected={selected_strategy_id}",
            "all strategy_id values match",
        ),
        _condition(
            "backtest_no_live_order",
            backtest_payload.get("live_order_submitted") is False,
            backtest_payload.get("live_order_submitted"),
            False,
        ),
        _condition(
            "runtime_ingested",
            runtime_summary.ingest_status == "INGESTED",
            runtime_summary.ingest_status,
            "INGESTED",
        ),
        _condition(
            "runtime_has_fills",
            runtime_summary.paper_fill_count > 0,
            runtime_summary.paper_fill_count,
            "> 0",
            severity="warning",
        ),
        _condition(
            "runtime_pnl_available",
            runtime_summary.pnl_available,
            runtime_summary.pnl_unavailable_reason or runtime_summary.pnl_available,
            "runtime observation includes realized paper PnL",
            severity="warning",
        ),
        _condition(
            "runtime_no_fill_rate_within_limit",
            metrics.runtime_no_fill_rate is not None
            and metrics.runtime_no_fill_rate <= max_no_fill_rate,
            metrics.runtime_no_fill_rate,
            f"<= {max_no_fill_rate}",
        ),
        _condition(
            "runtime_blocked_rate_within_limit",
            metrics.runtime_blocked_rate is not None
            and metrics.runtime_blocked_rate <= max_blocked_rate,
            metrics.runtime_blocked_rate,
            f"<= {max_blocked_rate}",
        ),
    ]
    if max_spread_bps is not None:
        conditions.append(
            _condition(
                "runtime_spread_within_limit",
                runtime_summary.max_observed_spread_bps is not None
                and runtime_summary.max_observed_spread_bps <= max_spread_bps,
                runtime_summary.max_observed_spread_bps,
                f"<= {max_spread_bps}",
            )
        )
    if max_return_drift is not None:
        conditions.append(
            _condition(
                "runtime_return_drift_within_limit",
                metrics.runtime_vs_backtest_return_drift is not None
                and abs(metrics.runtime_vs_backtest_return_drift) <= max_return_drift,
                metrics.runtime_vs_backtest_return_drift,
                f"abs(return drift) <= {max_return_drift}",
            )
        )
    if boundary_violations:
        conditions.append(
            _condition(
                "no_boundary_violation",
                False,
                ", ".join(boundary_violations),
                "no true live/wallet/signing/write flags",
            )
        )

    error_conditions = [item for item in conditions if item.severity == "error"]
    failed_conditions = [item for item in error_conditions if not item.passed]
    passed_conditions = [item for item in conditions if item.passed]
    warning_conditions = [item for item in conditions if item.severity == "warning"]
    status = _status_for(
        boundary_failed=bool(boundary_violations),
        backtest=backtest_summary,
        runtime=runtime_summary,
    )
    review = PaperVsBacktestDriftReview(
        strategy_id=selected_strategy_id,
        created_at=created_at or _utc_now(),
        producer=StageProducer(command="strategy-drift-review"),
        review_status=status,
        recommended_action=_recommended_action(
            status,
            runtime=runtime_summary,
            metrics=metrics,
            max_no_fill_rate=max_no_fill_rate,
            max_blocked_rate=max_blocked_rate,
            max_spread_bps=max_spread_bps,
            max_return_drift=max_return_drift,
        ),
        source_artifacts=[
            _source_artifact("strategy_authoring_backtest_result", backtest_result_path),
            _source_artifact("strategy_runtime_observation_manifest", runtime_observation_path),
        ],
        backtest_summary=backtest_summary,
        runtime_summary=runtime_summary,
        drift_metrics=metrics,
        passed_conditions=passed_conditions,
        failed_conditions=failed_conditions,
        warning_conditions=warning_conditions,
    )

    review_path = out_dir / "paper_vs_backtest_drift_review.json"
    report_path = out_dir / "paper_vs_backtest_drift_review.md"
    if not replace_existing and (review_path.exists() or report_path.exists()):
        raise StrategyDriftReviewOutputExistsError(
            f"output already exists: {repo_relative_path(out_dir)}"
        )
    write_json_artifact(review_path, review.model_dump(mode="json", exclude_none=True))
    write_text_artifact(report_path, render_drift_review_markdown(review))
    return DriftReviewBuildResult(review=review, review_path=review_path, report_path=report_path)
