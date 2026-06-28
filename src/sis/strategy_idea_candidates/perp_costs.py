from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from sis.backtest.artifact_io import sha256_file
from sis.strategy_idea_candidates.models import (
    CandidateBoundary,
    StrategyIdeaCandidate,
    StrategyIdeaCandidateSet,
)
from sis.strategy_inputs.io import write_json_artifact, write_text_artifact
from sis.strategy_inputs.models import ProducerInfo


PERP_COST_ESTIMATES_SCHEMA_VERSION = "strategy_idea_candidate_perp_cost_estimates.v1"


class StrategyIdeaCandidatePerpCostEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate_id: str
    family: str
    evidence_level: Literal["local_parameter_estimate"] = "local_parameter_estimate"
    venue: str
    product_type: str
    side_bias: str
    margin_mode: str
    margin_coin: str
    leverage: float
    notional_usd: float
    max_daily_loss_usd: float
    fee_model_ref: str
    fee_rate: float
    round_trip_fee_usd: float
    funding_assumption: str
    funding_rate_bps_per_8h: float
    funding_estimate_usd: float
    slippage_model_ref: str
    slippage_bps: float
    slippage_estimate_usd: float
    stress_slippage_bps: float
    stress_slippage_estimate_usd: float
    liquidation_buffer_bps: float
    liquidation_buffer_status: Literal["RECORDED", "MISSING_OR_INVALID"]
    estimated_round_trip_cost_usd: float
    stress_round_trip_cost_usd: float
    actual_cash_result_usd: None = None
    known_gaps: list[str]

    @field_validator("candidate_id", "family", "venue", "product_type")
    @classmethod
    def validate_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("text fields must not be empty")
        return stripped


class StrategyIdeaCandidatePerpCostEstimateReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_candidate_perp_cost_estimates.v1"] = (
        PERP_COST_ESTIMATES_SCHEMA_VERSION
    )
    report_id: str
    generated_at: datetime
    producer: ProducerInfo
    candidate_set_id: str
    estimates: list[StrategyIdeaCandidatePerpCostEstimate]
    summary: dict[str, Any]
    known_gaps: list[str]
    boundary: CandidateBoundary = Field(default_factory=CandidateBoundary)

    @field_serializer("generated_at")
    def serialize_generated_at(self, value: datetime) -> str:
        return _serialize_datetime(value)


@dataclass(frozen=True)
class StrategyIdeaCandidatePerpCostEstimateWriteResult:
    report: StrategyIdeaCandidatePerpCostEstimateReport
    report_path: Path
    markdown_path: Path
    report_sha256: str


class StrategyIdeaCandidatePerpCostEstimateOutputExistsError(ValueError):
    pass


def is_perp_candidate(candidate: StrategyIdeaCandidate) -> bool:
    return candidate.family.startswith("perp_") or (
        candidate.parameter_set.get("product_type") == "USDT-FUTURES"
    )


def apply_perp_cost_estimates(
    candidate_set: StrategyIdeaCandidateSet,
    *,
    generated_at: datetime | str | None = None,
) -> tuple[StrategyIdeaCandidateSet, StrategyIdeaCandidatePerpCostEstimateReport]:
    report = build_perp_cost_estimate_report(candidate_set, generated_at=generated_at)
    by_candidate_id = {estimate.candidate_id: estimate for estimate in report.estimates}
    updated_candidates = []
    for candidate in candidate_set.candidate_inventory:
        estimate = by_candidate_id.get(candidate.idea_candidate_id)
        if estimate is None:
            updated_candidates.append(candidate)
            continue
        raw_metrics = dict(candidate.raw_validation_metrics)
        raw_metrics["perp_cost_estimate"] = estimate.model_dump(mode="json")
        raw_metrics["estimated_round_trip_cost_usd"] = estimate.estimated_round_trip_cost_usd
        raw_metrics["stress_round_trip_cost_usd"] = estimate.stress_round_trip_cost_usd
        updated_candidates.append(candidate.model_copy(update={"raw_validation_metrics": raw_metrics}))
    return candidate_set.model_copy(update={"candidate_inventory": updated_candidates}), report


def build_perp_cost_estimate_report(
    candidate_set: StrategyIdeaCandidateSet,
    *,
    generated_at: datetime | str | None = None,
) -> StrategyIdeaCandidatePerpCostEstimateReport:
    timestamp = _coerce_datetime(generated_at)
    estimates = [
        perp_cost_estimate_from_candidate(candidate)
        for candidate in candidate_set.candidate_inventory
        if is_perp_candidate(candidate)
    ]
    known_gaps = ["ESTIMATE_NOT_ACTUAL_CASH"]
    for estimate in estimates:
        known_gaps.extend(estimate.known_gaps)
    known_gaps = list(dict.fromkeys(known_gaps))
    summary = {
        "candidate_set_id": candidate_set.candidate_set_id,
        "estimate_count": len(estimates),
        "actual_cash_result_available": False,
        "total_estimated_round_trip_cost_usd": round(
            sum(estimate.estimated_round_trip_cost_usd for estimate in estimates),
            8,
        ),
        "total_stress_round_trip_cost_usd": round(
            sum(estimate.stress_round_trip_cost_usd for estimate in estimates),
            8,
        ),
        "known_gap_count": len(known_gaps),
    }
    return StrategyIdeaCandidatePerpCostEstimateReport(
        report_id=f"{candidate_set.candidate_set_id}-perp-cost-estimates",
        generated_at=timestamp,
        producer=ProducerInfo(command="strategy-idea-candidates-perp-cost-estimates"),
        candidate_set_id=candidate_set.candidate_set_id,
        estimates=estimates,
        summary=summary,
        known_gaps=known_gaps,
    )


def perp_cost_estimate_from_candidate(
    candidate: StrategyIdeaCandidate,
) -> StrategyIdeaCandidatePerpCostEstimate:
    return perp_cost_estimate_from_parameter_set(
        candidate_id=candidate.idea_candidate_id,
        family=candidate.family,
        parameter_set=candidate.parameter_set,
    )


def perp_cost_estimate_from_parameter_set(
    *,
    candidate_id: str,
    family: str,
    parameter_set: dict[str, Any],
) -> StrategyIdeaCandidatePerpCostEstimate:
    notional = _positive_float(parameter_set.get("max_position_notional_usd"), default=0.0)
    leverage = _positive_float(parameter_set.get("leverage"), default=0.0)
    fee_rate = _fee_rate(parameter_set.get("fee_model_ref"))
    slippage_bps = _slippage_bps(parameter_set)
    stress_slippage_bps = slippage_bps * 2
    funding_bps = _funding_bps(parameter_set)
    liquidation_buffer = _positive_float(parameter_set.get("liquidation_buffer_bps"), default=0.0)
    round_trip_fee = notional * fee_rate * 2
    funding = notional * abs(funding_bps) / 10000
    slippage = notional * abs(slippage_bps) / 10000
    stress_slippage = notional * abs(stress_slippage_bps) / 10000
    cost = round_trip_fee + funding + slippage
    stress_cost = round_trip_fee + funding + stress_slippage
    known_gaps = ["ESTIMATE_NOT_ACTUAL_CASH"]
    if "funding_rate_bps_per_8h" not in parameter_set:
        known_gaps.append("FUNDING_RATE_NUMERIC_INPUT_NOT_PROVIDED")
    if "slippage_bps" not in parameter_set:
        known_gaps.append("SLIPPAGE_BPS_NUMERIC_INPUT_NOT_PROVIDED")
    if liquidation_buffer <= 0:
        known_gaps.append("LIQUIDATION_BUFFER_MISSING_OR_INVALID")
    return StrategyIdeaCandidatePerpCostEstimate(
        candidate_id=candidate_id,
        family=family,
        venue=str(parameter_set.get("venue") or ""),
        product_type=str(parameter_set.get("product_type") or ""),
        side_bias=str(parameter_set.get("side_bias") or ""),
        margin_mode=str(parameter_set.get("margin_mode") or ""),
        margin_coin=str(parameter_set.get("margin_coin") or ""),
        leverage=leverage,
        notional_usd=notional,
        max_daily_loss_usd=_positive_float(parameter_set.get("max_daily_loss_usd"), default=0.0),
        fee_model_ref=str(parameter_set.get("fee_model_ref") or ""),
        fee_rate=fee_rate,
        round_trip_fee_usd=round(round_trip_fee, 8),
        funding_assumption=str(parameter_set.get("funding_assumption") or ""),
        funding_rate_bps_per_8h=funding_bps,
        funding_estimate_usd=round(funding, 8),
        slippage_model_ref=str(parameter_set.get("slippage_model_ref") or ""),
        slippage_bps=slippage_bps,
        slippage_estimate_usd=round(slippage, 8),
        stress_slippage_bps=stress_slippage_bps,
        stress_slippage_estimate_usd=round(stress_slippage, 8),
        liquidation_buffer_bps=liquidation_buffer,
        liquidation_buffer_status="RECORDED"
        if liquidation_buffer > 0
        else "MISSING_OR_INVALID",
        estimated_round_trip_cost_usd=round(cost, 8),
        stress_round_trip_cost_usd=round(stress_cost, 8),
        known_gaps=list(dict.fromkeys(known_gaps)),
    )


def write_strategy_idea_candidate_perp_cost_estimate_report(
    *,
    report: StrategyIdeaCandidatePerpCostEstimateReport,
    out_dir: Path,
    replace_existing: bool = False,
) -> StrategyIdeaCandidatePerpCostEstimateWriteResult:
    report_path = out_dir / "perp_cost_estimates.json"
    markdown_path = out_dir / "perp_cost_estimates.md"
    if not replace_existing and (report_path.exists() or markdown_path.exists()):
        raise StrategyIdeaCandidatePerpCostEstimateOutputExistsError(
            f"output already exists: {out_dir}"
        )
    write_json_artifact(report_path, report.model_dump(mode="json", exclude_none=True))
    write_text_artifact(markdown_path, render_perp_cost_estimates_markdown(report))
    return StrategyIdeaCandidatePerpCostEstimateWriteResult(
        report=report,
        report_path=report_path,
        markdown_path=markdown_path,
        report_sha256=sha256_file(report_path),
    )


def render_perp_cost_estimates_markdown(
    report: StrategyIdeaCandidatePerpCostEstimateReport,
) -> str:
    lines = [
        f"# Perp Cost Estimates: {report.candidate_set_id}",
        "",
        f"- estimate_count: `{len(report.estimates)}`",
        "- evidence_level: `local_parameter_estimate`",
        "- actual_cash_result_available: `false`",
        "- permits_live_order: `false`",
        "- exchange_write_used: `false`",
        "",
        "## Estimates",
        "",
        "| candidate_id | side_bias | notional_usd | est_cost_usd | stress_cost_usd | liquidation_buffer_bps |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for estimate in report.estimates:
        lines.append(
            "| "
            f"`{estimate.candidate_id}` | "
            f"`{estimate.side_bias}` | "
            f"`{estimate.notional_usd}` | "
            f"`{estimate.estimated_round_trip_cost_usd}` | "
            f"`{estimate.stress_round_trip_cost_usd}` | "
            f"`{estimate.liquidation_buffer_bps}` |"
        )
    if report.known_gaps:
        lines.extend(["", "## Known Gaps", ""])
        lines.extend(f"- `{gap}`" for gap in report.known_gaps)
    return "\n".join(lines) + "\n"


def _fee_rate(fee_model_ref: Any) -> float:
    if fee_model_ref == "bitget_usdt_futures_maker_fee_estimate":
        return 0.0002
    if fee_model_ref == "bitget_usdt_futures_taker_fee_estimate":
        return 0.0006
    return 0.0006


def _slippage_bps(parameter_set: dict[str, Any]) -> float:
    explicit = _coerce_float(parameter_set.get("slippage_bps"))
    if explicit is not None:
        return max(0.0, explicit)
    if parameter_set.get("slippage_model_ref") == "bps_stress_model":
        return 2.0
    return 0.0


def _funding_bps(parameter_set: dict[str, Any]) -> float:
    explicit = _coerce_float(parameter_set.get("funding_rate_bps_per_8h"))
    if explicit is not None:
        return explicit
    threshold = _coerce_float(parameter_set.get("funding_rate_threshold_bps"))
    return abs(threshold) if threshold is not None else 0.0


def _positive_float(value: Any, *, default: float) -> float:
    parsed = _coerce_float(value)
    if parsed is None:
        return default
    return max(0.0, parsed)


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
