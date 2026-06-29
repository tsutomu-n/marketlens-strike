from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.models import (
    CandidateBoundary,
    SelectionAdjustedMetricsStatus,
    SelectionPolicy,
    StrategyIdeaCandidateSet,
)
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import ProducerInfo


SELECTION_METRICS_SCHEMA_VERSION = "strategy_idea_candidate_selection_metrics.v1"
_P_VALUE_KEYS = ("validation_p_value", "p_value", "raw_p_value")
_RAW_METRIC_KEYS = (
    "validation_sharpe",
    "validation_return",
    "estimated_net_edge_bps",
    "estimated_round_trip_cost_usd",
)


class CandidateSelectionMetricAdjustment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    status: SelectionAdjustedMetricsStatus
    raw_metric_name: str | None = None
    raw_metric_value: float | None = None
    raw_p_value: float | None = None
    benjamini_hochberg_q_value: float | None = None
    trial_count_total: int = Field(ge=0)
    method_status: dict[str, str]
    known_gaps: list[str]


class StrategyIdeaCandidateSelectionMetricsReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_candidate_selection_metrics.v1"] = (
        SELECTION_METRICS_SCHEMA_VERSION
    )
    report_id: str
    generated_at: datetime
    producer: ProducerInfo
    candidate_set_id: str
    status_counts: dict[str, int]
    adjustments: list[CandidateSelectionMetricAdjustment]
    known_gaps: list[str]
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime) -> str:
        return _serialize_datetime(value)

    @field_validator("report_id", "candidate_set_id")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("id fields must not be empty")
        return stripped


@dataclass(frozen=True)
class StrategyIdeaCandidateSelectionMetricsWriteResult:
    report: StrategyIdeaCandidateSelectionMetricsReport
    report_path: Path
    markdown_path: Path
    report_sha256: str


class StrategyIdeaCandidateSelectionMetricsOutputExistsError(ValueError):
    pass


def apply_selection_adjusted_metrics(
    candidate_set: StrategyIdeaCandidateSet,
    *,
    generated_at: datetime | str | None = None,
) -> tuple[StrategyIdeaCandidateSet, StrategyIdeaCandidateSelectionMetricsReport]:
    report = build_selection_adjusted_metrics_report(
        candidate_set,
        generated_at=generated_at,
    )
    by_candidate_id = {item.candidate_id: item for item in report.adjustments}
    updated_candidates = []
    for candidate in candidate_set.candidate_inventory:
        adjustment = by_candidate_id[candidate.idea_candidate_id]
        raw_metrics = dict(candidate.raw_validation_metrics)
        raw_metrics["selection_adjusted_metrics"] = {
            "status": adjustment.status.value,
            "raw_metric_name": adjustment.raw_metric_name,
            "raw_metric_value": adjustment.raw_metric_value,
            "raw_p_value": adjustment.raw_p_value,
            "benjamini_hochberg_q_value": adjustment.benjamini_hochberg_q_value,
            "trial_count_total": adjustment.trial_count_total,
            "method_status": adjustment.method_status,
            "known_gaps": adjustment.known_gaps,
            "proof_status": "not_alpha_or_profit_proof",
        }
        updated_candidates.append(
            candidate.model_copy(
                update={
                    "raw_validation_metrics": raw_metrics,
                    "selection_adjusted_metrics_status": adjustment.status,
                }
            )
        )

    known_gaps = [
        gap
        for gap in candidate_set.selection_policy.known_gaps
        if "selection-adjusted metrics are NOT_IMPLEMENTED" not in gap
        and "selection-adjusted metrics are not implemented" not in gap
    ]
    known_gaps.append(
        "selection-adjusted metrics engine ran; DSR, PBO, and Reality Check remain "
        "NOT_ESTIMABLE unless required return series or fold data are supplied."
    )
    selection_policy = candidate_set.selection_policy.model_copy(
        update={"known_gaps": list(dict.fromkeys(known_gaps))}
    )
    return (
        candidate_set.model_copy(
            update={
                "candidate_inventory": updated_candidates,
                "selection_policy": SelectionPolicy.model_validate(
                    selection_policy.model_dump(mode="json")
                ),
            }
        ),
        report,
    )


def build_selection_adjusted_metrics_report(
    candidate_set: StrategyIdeaCandidateSet,
    *,
    generated_at: datetime | str | None = None,
) -> StrategyIdeaCandidateSelectionMetricsReport:
    timestamp = _coerce_datetime(generated_at)
    p_values: dict[str, float] = {}
    raw_values: dict[str, tuple[str, float] | None] = {}
    for candidate in candidate_set.candidate_inventory:
        raw_values[candidate.idea_candidate_id] = _first_raw_metric(
            candidate.raw_validation_metrics
        )
        p_value = _first_p_value(candidate.raw_validation_metrics)
        if p_value is not None:
            p_values[candidate.idea_candidate_id] = p_value

    q_values = _benjamini_hochberg_q_values(p_values)
    adjustments: list[CandidateSelectionMetricAdjustment] = []
    for candidate in candidate_set.candidate_inventory:
        raw_pair = raw_values[candidate.idea_candidate_id]
        p_value = p_values.get(candidate.idea_candidate_id)
        q_value = q_values.get(candidate.idea_candidate_id)
        status = (
            SelectionAdjustedMetricsStatus.AVAILABLE
            if q_value is not None
            else SelectionAdjustedMetricsStatus.NOT_ESTIMABLE
        )
        known_gaps = _known_gaps_for_adjustment(raw_pair=raw_pair, p_value=p_value)
        adjustments.append(
            CandidateSelectionMetricAdjustment(
                candidate_id=candidate.idea_candidate_id,
                status=status,
                raw_metric_name=raw_pair[0] if raw_pair is not None else None,
                raw_metric_value=raw_pair[1] if raw_pair is not None else None,
                raw_p_value=p_value,
                benjamini_hochberg_q_value=q_value,
                trial_count_total=candidate_set.search_ledger_summary.trial_count_total,
                method_status={
                    "benjamini_hochberg_fdr": "AVAILABLE"
                    if q_value is not None
                    else "NOT_ESTIMABLE: raw p-value missing",
                    "deflated_sharpe_ratio": (
                        "NOT_ESTIMABLE: requires return distribution, Sharpe inputs, "
                        "and trial distribution"
                    ),
                    "probability_of_backtest_overfitting": (
                        "NOT_ESTIMABLE: requires fold-by-candidate outcome matrix"
                    ),
                    "white_reality_check": (
                        "NOT_ESTIMABLE: requires bootstrap-ready return series by candidate"
                    ),
                },
                known_gaps=known_gaps,
            )
        )
    counts = Counter(adjustment.status.value for adjustment in adjustments)
    report_gaps = sorted({gap for adjustment in adjustments for gap in adjustment.known_gaps})
    if not adjustments:
        report_gaps.append("NO_CANDIDATES_TO_ADJUST")
    return StrategyIdeaCandidateSelectionMetricsReport(
        report_id=f"{candidate_set.candidate_set_id}-selection-metrics",
        generated_at=timestamp,
        producer=ProducerInfo(command="strategy-idea-candidates-selection-metrics"),
        candidate_set_id=candidate_set.candidate_set_id,
        status_counts=dict(sorted(counts.items())),
        adjustments=adjustments,
        known_gaps=report_gaps,
    )


def write_strategy_idea_candidate_selection_metrics_report(
    *,
    report: StrategyIdeaCandidateSelectionMetricsReport,
    out_dir: Path,
    replace_existing: bool = False,
) -> StrategyIdeaCandidateSelectionMetricsWriteResult:
    report_path = out_dir / "selection_metrics.json"
    markdown_path = out_dir / "selection_metrics.md"
    if not replace_existing and (report_path.exists() or markdown_path.exists()):
        raise StrategyIdeaCandidateSelectionMetricsOutputExistsError(
            f"output already exists: {out_dir}"
        )
    write_json_artifact(report_path, report.model_dump(mode="json", exclude_none=True))
    write_text_artifact(markdown_path, render_selection_metrics_markdown(report))
    return StrategyIdeaCandidateSelectionMetricsWriteResult(
        report=report,
        report_path=report_path,
        markdown_path=markdown_path,
        report_sha256=sha256_file(report_path),
    )


def render_selection_metrics_markdown(
    report: StrategyIdeaCandidateSelectionMetricsReport,
) -> str:
    lines = [
        f"# Selection Metrics: {report.candidate_set_id}",
        "",
        f"- schema_version: `{report.schema_version}`",
        "- proof_status: `not_alpha_or_profit_proof`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
        "",
        "## Status Counts",
        "",
    ]
    for status, count in sorted(report.status_counts.items()):
        lines.append(f"- `{status}`: `{count}`")
    lines.extend(["", "## Adjustments", ""])
    for adjustment in report.adjustments:
        lines.append(
            "- "
            f"`{adjustment.candidate_id}` "
            f"status=`{adjustment.status.value}` "
            f"raw_p_value=`{adjustment.raw_p_value}` "
            f"bh_q=`{adjustment.benjamini_hochberg_q_value}`"
        )
    if report.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in report.known_gaps)
    return "\n".join(lines) + "\n"


def _first_p_value(raw_metrics: dict[str, Any]) -> float | None:
    for key in _P_VALUE_KEYS:
        value = _coerce_float(raw_metrics.get(key))
        if value is not None:
            if not 0 <= value <= 1:
                raise ValueError(f"{key} must be between 0 and 1")
            return value
    return None


def _first_raw_metric(raw_metrics: dict[str, Any]) -> tuple[str, float] | None:
    for key in _RAW_METRIC_KEYS:
        value = _coerce_float(raw_metrics.get(key))
        if value is not None:
            return key, value
    return None


def _coerce_float(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _benjamini_hochberg_q_values(p_values: dict[str, float]) -> dict[str, float]:
    if not p_values:
        return {}
    ordered = sorted(p_values.items(), key=lambda item: item[1])
    total = len(ordered)
    raw_q: dict[str, float] = {}
    for rank, (candidate_id, p_value) in enumerate(ordered, start=1):
        raw_q[candidate_id] = min(1.0, p_value * total / rank)
    monotonic_q: dict[str, float] = {}
    running = 1.0
    for candidate_id, _p_value in reversed(ordered):
        running = min(running, raw_q[candidate_id])
        monotonic_q[candidate_id] = running
    return monotonic_q


def _known_gaps_for_adjustment(
    *,
    raw_pair: tuple[str, float] | None,
    p_value: float | None,
) -> list[str]:
    gaps = [
        "DSR_NOT_ESTIMABLE_RETURN_DISTRIBUTION_MISSING",
        "PBO_NOT_ESTIMABLE_FOLD_OUTCOMES_MISSING",
        "WHITE_REALITY_CHECK_NOT_ESTIMABLE_BOOTSTRAP_SERIES_MISSING",
    ]
    if raw_pair is None:
        gaps.append("RAW_SELECTION_METRIC_MISSING")
    if p_value is None:
        gaps.append("RAW_P_VALUE_MISSING_FOR_BH_FDR")
    return gaps


def _coerce_datetime(value: datetime | str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    else:
        parsed = value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _serialize_datetime(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
