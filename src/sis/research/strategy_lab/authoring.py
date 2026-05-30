from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Literal, cast

import polars as pl
from pydantic import BaseModel, Field, model_validator
import yaml

from sis.backtest.bridge import run_backtest_bridge_for_signals
from sis.backtest.signals import ResearchSignal
from sis.research.signal_builder import _legacy_export
from sis.research.strategy_lab.candidates import TradeCandidate
from sis.research.strategy_lab.paper_candidate_pack import PaperCandidatePack
from sis.research.strategy_lab.paper_intent_preview import PaperIntentPreview
from sis.research.strategy_lab.promotion_decision import PromotionDecision
from sis.research.strategy_lab.signal_artifact import (
    StrategySignalManifest,
    empty_signal_artifact_run_id,
    empty_strategy_signal_frame,
    file_sha256,
    signal_artifact_run_id,
    strategy_signal_manifest_path,
    write_strategy_signal_manifest,
)
from sis.research.strategy_lab.signal_frame import validate_strategy_signal_frame
from sis.research.strategy_lab.specs import SymbolBinding
from sis.research.strategy_lab.trial_ledger import TrialLedger, TrialRecord

ALLOWED_OPERATORS = {"gt", "gte", "lt", "lte", "eq", "neq", "is_true", "is_false", "between"}
VALID_THROUGH = {"signals", "backtest", "paper-preview"}


def _stable_digest(payload: object) -> str:
    text = json.dumps(payload, ensure_ascii=True, sort_keys=True, default=str)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


class AuthoringExperiment(BaseModel):
    strategy_id: str
    strategy_family: str = "declarative"
    strategy_version: str = "v1"
    description: str | None = None
    symbol_bindings: list[SymbolBinding]
    run_profile_id: str = "strategy_lab_research_only"

    @model_validator(mode="after")
    def validate_experiment(self) -> AuthoringExperiment:
        for name in ("strategy_id", "strategy_family", "strategy_version", "run_profile_id"):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"experiment.{name} must be non-empty")
        if not self.symbol_bindings:
            raise ValueError("experiment.symbol_bindings must include at least one binding")
        return self


class AuthoringData(BaseModel):
    feature_panel_path: str = "data/research/feature_panel.parquet"
    quote_data_path: str = "data/normalized/quotes.parquet"
    cost_model_path: str = "data/research/venue_cost_matrix.csv"


class Condition(BaseModel):
    column: str
    op: Literal["gt", "gte", "lt", "lte", "eq", "neq", "is_true", "is_false", "between"]
    value: Any = None

    @model_validator(mode="after")
    def validate_condition(self) -> Condition:
        if not self.column.strip():
            raise ValueError("rule condition column must be non-empty")
        if self.op == "between":
            if not isinstance(self.value, list | tuple) or len(self.value) != 2:
                raise ValueError(f"{self.column}: between requires a two-item value")
        if self.op in {"gt", "gte", "lt", "lte", "eq", "neq"} and self.value is None:
            raise ValueError(f"{self.column}: {self.op} requires value")
        return self


class EntryRules(BaseModel):
    all: list[Condition] = Field(default_factory=list)
    any: list[Condition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_entry(self) -> EntryRules:
        if not self.all and not self.any:
            raise ValueError("rules.entry must include at least one all/any condition")
        return self


class ScoreTerm(BaseModel):
    column: str
    weight: float = 1.0


class WeightedScore(BaseModel):
    weighted_sum: list[ScoreTerm] = Field(default_factory=list)


class AuthoringRules(BaseModel):
    side: Literal["long", "short"] = "long"
    timeframe: str = "4h"
    entry: EntryRules
    score: WeightedScore = Field(default_factory=WeightedScore)
    confidence: float = 0.7
    reason_code: str = "declarative_rule"

    @model_validator(mode="after")
    def validate_rules(self) -> AuthoringRules:
        if not self.timeframe.strip():
            raise ValueError("rules.timeframe must be non-empty")
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError("rules.confidence must be between 0 and 1")
        if not self.reason_code.strip():
            raise ValueError("rules.reason_code must be non-empty")
        return self


class AuthoringBacktest(BaseModel):
    split_method: Literal["single_window", "purged_walk_forward"] = "purged_walk_forward"
    era_unit: Literal["trading_day", "week", "month"] = "trading_day"
    label_horizon_minutes: int = 240
    purge_minutes: int = 0
    embargo_minutes: int = 0
    min_trade_count: int = 1
    primary_metric: str = "total_return"
    pass_thresholds: dict[str, float] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_backtest(self) -> AuthoringBacktest:
        if self.label_horizon_minutes <= 0:
            raise ValueError("backtest.label_horizon_minutes must be positive")
        if self.purge_minutes < 0 or self.embargo_minutes < 0:
            raise ValueError("backtest purge/embargo minutes must be >= 0")
        if self.min_trade_count < 0:
            raise ValueError("backtest.min_trade_count must be >= 0")
        return self


class AuthoringPromotion(BaseModel):
    default_decision: Literal["hold", "reject"] = "hold"
    allow_paper_preview: bool = True


class StrategyAuthoringSpec(BaseModel):
    schema_version: Literal["strategy_authoring_spec.v1"]
    experiment: AuthoringExperiment
    data: AuthoringData = Field(default_factory=AuthoringData)
    rules: AuthoringRules
    backtest: AuthoringBacktest = Field(default_factory=AuthoringBacktest)
    promotion: AuthoringPromotion = Field(default_factory=AuthoringPromotion)


class StrategyAuthoringValidationError(ValueError):
    pass


def load_authoring_spec(path: Path) -> StrategyAuthoringSpec:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise StrategyAuthoringValidationError("spec must be a YAML object")
    return StrategyAuthoringSpec.model_validate(payload)


def template_yaml() -> str:
    return """schema_version: strategy_authoring_spec.v1
experiment:
  strategy_id: trend_pullback_user_v1
  strategy_family: trend_pullback
  strategy_version: v1
  description: Long only trend pullback example for Strategy Lab paper research.
  symbol_bindings:
    - execution_venue: trade_xyz
      execution_symbol: XYZ100
      real_market_symbol: QQQ
      asset_class: equity_index
      country: US
      currency: USD
  run_profile_id: strategy_lab_research_only
data:
  feature_panel_path: data/research/feature_panel.parquet
  quote_data_path: data/normalized/quotes.parquet
  cost_model_path: data/research/venue_cost_matrix.csv
rules:
  side: long
  timeframe: 4h
  entry:
    all:
      - column: trade_allowed
        op: is_true
      - column: close_above_sma20
        op: is_true
      - column: vix_level
        op: lt
        value: 30
    any:
      - column: research_return_1d
        op: gt
        value: 0
      - column: research_return_4h
        op: gt
        value: 0
  score:
    weighted_sum:
      - column: research_return_1d
        weight: 10
      - column: source_confidence
        weight: 0.5
  confidence: 0.7
  reason_code: trend_pullback_authoring_v1
backtest:
  split_method: purged_walk_forward
  era_unit: trading_day
  label_horizon_minutes: 240
  purge_minutes: 0
  embargo_minutes: 0
  min_trade_count: 1
  primary_metric: total_return
  pass_thresholds:
    max_drawdown: -0.2
promotion:
  default_decision: hold
  allow_paper_preview: true
"""


def write_template(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(template_yaml(), encoding="utf-8")
    return path


def _resolve_path(raw: str, data_dir: Path) -> Path:
    path = Path(raw)
    if path.is_absolute():
        return path
    if path.parts and path.parts[0] == "data":
        return data_dir.parent / path
    return path


def _required_columns(spec: StrategyAuthoringSpec) -> set[str]:
    columns = {"ts", "canonical_symbol"}
    for cond in [*spec.rules.entry.all, *spec.rules.entry.any]:
        columns.add(cond.column)
    for term in spec.rules.score.weighted_sum:
        columns.add(term.column)
    return columns


def validate_authoring_inputs(spec: StrategyAuthoringSpec, *, data_dir: Path) -> list[str]:
    errors: list[str] = []
    feature_path = _resolve_path(spec.data.feature_panel_path, data_dir)
    if not feature_path.exists():
        errors.append(f"feature_panel_path not found: {feature_path}")
        return errors
    try:
        feature = pl.read_parquet(feature_path, n_rows=1)
    except Exception as exc:  # pragma: no cover - polars gives version-specific exceptions
        errors.append(f"feature_panel_path is not readable parquet: {exc}")
        return errors
    missing = sorted(_required_columns(spec).difference(feature.columns))
    if missing:
        errors.append(f"feature panel missing columns: {missing}")
    symbols = {binding.real_market_symbol for binding in spec.experiment.symbol_bindings}
    if "canonical_symbol" in feature.columns:
        full = pl.read_parquet(feature_path, columns=["canonical_symbol"])
        observed = {str(value).upper() for value in full.get_column("canonical_symbol").to_list()}
        missing_symbols = sorted(symbols.difference(observed))
        if missing_symbols:
            errors.append(f"feature panel missing real_market_symbol rows: {missing_symbols}")
    return errors


def _condition_passes(row: dict[str, Any], condition: Condition) -> bool:
    value = row.get(condition.column)
    if condition.op == "is_true":
        return value is True
    if condition.op == "is_false":
        return value is False
    if value is None:
        return False
    target = condition.value
    if condition.op == "gt":
        return value > target
    if condition.op == "gte":
        return value >= target
    if condition.op == "lt":
        return value < target
    if condition.op == "lte":
        return value <= target
    if condition.op == "eq":
        return value == target
    if condition.op == "neq":
        return value != target
    if condition.op == "between":
        low, high = target
        return low <= value <= high
    raise StrategyAuthoringValidationError(f"Unsupported operator: {condition.op}")


def _entry_passes(row: dict[str, Any], entry: EntryRules) -> bool:
    all_pass = all(_condition_passes(row, condition) for condition in entry.all)
    any_pass = (
        True if not entry.any else any(_condition_passes(row, condition) for condition in entry.any)
    )
    return all_pass and any_pass


def _score(row: dict[str, Any], score: WeightedScore) -> float | None:
    if not score.weighted_sum:
        return None
    total = 0.0
    used = False
    for term in score.weighted_sum:
        value = row.get(term.column)
        if isinstance(value, int | float):
            total += float(value) * term.weight
            used = True
    return total if used else None


def _rank_score(raw_score: float | None) -> float | None:
    if raw_score is None:
        return None
    return max(0.0, min(1.0, raw_score))


def _float_or_default(value: object, default: float) -> float:
    if isinstance(value, int | float):
        return float(value)
    return default


def _tail_bucket(rank_score: float | None) -> str:
    if rank_score is None:
        return "none"
    if rank_score >= 0.8:
        return "top"
    if rank_score <= 0.2:
        return "bottom"
    return "middle"


def _signal_id(spec: StrategyAuthoringSpec, row: dict[str, Any], binding: SymbolBinding) -> str:
    return _stable_digest(
        {
            "strategy_id": spec.experiment.strategy_id,
            "ts": row.get("ts"),
            "execution_symbol": binding.execution_symbol,
            "side": spec.rules.side,
            "reason_code": spec.rules.reason_code,
        }
    )


def build_authoring_signals(
    spec: StrategyAuthoringSpec, *, data_dir: Path
) -> tuple[pl.DataFrame, StrategySignalManifest]:
    errors = validate_authoring_inputs(spec, data_dir=data_dir)
    if errors:
        raise StrategyAuthoringValidationError("; ".join(errors))
    feature_path = _resolve_path(spec.data.feature_panel_path, data_dir)
    feature = pl.read_parquet(feature_path)
    bindings = {binding.real_market_symbol: binding for binding in spec.experiment.symbol_bindings}
    rows: list[dict[str, Any]] = []
    generated_at = datetime.now(timezone.utc)
    for row in feature.sort(["canonical_symbol", "ts"]).to_dicts():
        symbol = str(row.get("canonical_symbol") or "").upper()
        binding = bindings.get(symbol)
        if binding is None or not _entry_passes(row, spec.rules.entry):
            continue
        raw_score = _score(row, spec.rules.score)
        rank = _rank_score(raw_score)
        rows.append(
            {
                "schema_version": "strategy_signal.v1",
                "signal_id": _signal_id(spec, row, binding),
                "generated_at": generated_at,
                "strategy_id": spec.experiment.strategy_id,
                "strategy_family": spec.experiment.strategy_family,
                "strategy_version": spec.experiment.strategy_version,
                "trial_id": None,
                "parameter_hash": _stable_digest(spec.model_dump(mode="json")),
                "ts_signal": row["ts"],
                "timeframe": spec.rules.timeframe,
                "execution_venue": binding.execution_venue,
                "execution_symbol": binding.execution_symbol,
                "real_market_symbol": binding.real_market_symbol,
                "side": spec.rules.side,
                "raw_score": raw_score,
                "rank_score": rank,
                "percentile_rank": rank,
                "tail_bucket": _tail_bucket(rank),
                "confidence": spec.rules.confidence,
                "source_confidence": row.get("source_confidence"),
                "venue_quality_score": row.get("venue_quality_score"),
                "feature_snapshot_ref": None,
                "quote_ref": None,
                "tracking_ref": None,
                "reason_codes": [spec.rules.reason_code],
                "block_reasons": [],
            }
        )
    frame = (
        empty_strategy_signal_frame()
        if not rows
        else validate_strategy_signal_frame(
            pl.DataFrame(rows), symbol_bindings=spec.experiment.symbol_bindings
        )
    )
    feature_hash = file_sha256(feature_path)
    run_id = (
        empty_signal_artifact_run_id(
            generator_id="strategy_authoring",
            strategy_id=spec.experiment.strategy_id,
            strategy_family=spec.experiment.strategy_family,
            strategy_version=spec.experiment.strategy_version,
            symbol_bindings=spec.experiment.symbol_bindings,
            feature_panel_sha256=feature_hash,
        )
        if frame.is_empty()
        else signal_artifact_run_id(frame)
    )
    manifest = StrategySignalManifest(
        schema_version="strategy_signal_manifest.v1",
        generated_at=generated_at,
        generator_id="strategy_authoring",
        strategy_id=spec.experiment.strategy_id,
        strategy_family=spec.experiment.strategy_family,
        strategy_version=spec.experiment.strategy_version,
        symbol_bindings=spec.experiment.symbol_bindings,
        feature_panel_sha256=feature_hash,
        signal_count=frame.height,
        signal_artifact_run_id=run_id,
        generator_parameters={
            "authoring_schema_version": spec.schema_version,
            "reason_code": spec.rules.reason_code,
        },
    )
    return frame, manifest


def write_authoring_signal_artifacts(
    frame: pl.DataFrame, manifest: StrategySignalManifest, *, data_dir: Path
) -> dict[str, Path]:
    parquet_out = data_dir / "research/strategy_signals.parquet"
    jsonl_out = data_dir / "research/strategy_signals.jsonl"
    legacy_out = data_dir / "research/signals.csv"
    parquet_out.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(parquet_out)
    with jsonl_out.open("w", encoding="utf-8") as handle:
        for row in frame.to_dicts():
            handle.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
    _legacy_export(frame).write_csv(legacy_out)
    write_strategy_signal_manifest(manifest, strategy_signal_manifest_path(data_dir))
    return {
        "signals_parquet": parquet_out,
        "signals_jsonl": jsonl_out,
        "legacy_csv": legacy_out,
        "manifest": strategy_signal_manifest_path(data_dir),
    }


def strategy_signals_to_research_signals(frame: pl.DataFrame) -> list[ResearchSignal]:
    if frame.is_empty():
        return []
    return [
        ResearchSignal(
            ts_signal=row["ts_signal"],
            canonical_symbol=str(row["execution_symbol"]).upper(),
            side=str(row["side"]).lower(),
            timeframe=str(row["timeframe"]).lower(),
            signal_strength=row.get("raw_score"),
        )
        for row in frame.sort(["ts_signal", "signal_id"]).to_dicts()
        if str(row.get("side") or "").lower() in {"long", "short"}
    ]


def explain_authoring_spec(spec: StrategyAuthoringSpec, *, data_dir: Path) -> str:
    errors = validate_authoring_inputs(spec, data_dir=data_dir)
    required_columns = sorted(_required_columns(spec))
    bindings = ", ".join(
        f"{item.real_market_symbol}->{item.execution_symbol}@{item.execution_venue}"
        for item in spec.experiment.symbol_bindings
    )
    conditions = [*spec.rules.entry.all, *spec.rules.entry.any]
    condition_lines = "\n".join(
        f"- {condition.column} {condition.op} {condition.value if condition.value is not None else ''}".rstrip()
        for condition in conditions
    )
    score_lines = (
        "\n".join(f"- {term.column} * {term.weight}" for term in spec.rules.score.weighted_sum)
        or "- no weighted score; raw/rank score will be null"
    )
    status = "ok" if not errors else "invalid"
    error_lines = "\n".join(f"- {error}" for error in errors) or "- none"
    return (
        "# Strategy Authoring Explain\n\n"
        f"- status: {status}\n"
        f"- schema_version: {spec.schema_version}\n"
        f"- strategy_id: {spec.experiment.strategy_id}\n"
        f"- paper_only: true\n"
        f"- live_order_submitted: false\n"
        f"- symbol_bindings: {bindings}\n"
        f"- side: {spec.rules.side}\n"
        f"- timeframe: {spec.rules.timeframe}\n"
        f"- feature_panel_path: {_resolve_path(spec.data.feature_panel_path, data_dir)}\n"
        f"- quote_data_path: {_resolve_path(spec.data.quote_data_path, data_dir)}\n"
        f"- cost_model_path: {_resolve_path(spec.data.cost_model_path, data_dir)}\n"
        "\n## Required Feature Columns\n\n"
        + "\n".join(f"- {column}" for column in required_columns)
        + "\n\n## Entry Conditions\n\n"
        + condition_lines
        + "\n\n## Score\n\n"
        + score_lines
        + "\n\n## Backtest\n\n"
        f"- split_method: {spec.backtest.split_method}\n"
        f"- era_unit: {spec.backtest.era_unit}\n"
        f"- label_horizon_minutes: {spec.backtest.label_horizon_minutes}\n"
        f"- min_trade_count: {spec.backtest.min_trade_count}\n"
        "\n## Validation Errors\n\n" + error_lines + "\n"
    )


def _metrics_json(
    metrics: list[Any], summary: dict[str, Any], spec: StrategyAuthoringSpec
) -> dict[str, Any]:
    return {
        "schema_version": "strategy_authoring_backtest_result.v1",
        "strategy_id": spec.experiment.strategy_id,
        "paper_only": True,
        "live_order_submitted": False,
        "summary": summary,
        "metrics": [asdict(item) for item in metrics],
    }


def _aggregate_backtest_metrics(metrics: list[Any]) -> dict[str, float | int | None]:
    if not metrics:
        return {
            "trade_count": 0,
            "total_return": 0.0,
            "max_drawdown": None,
            "cost_drag_bps": 0.0,
            "stale_rejected_count": 0,
            "halt_rejected_count": 0,
        }
    return {
        "trade_count": sum(item.trade_count for item in metrics),
        "total_return": sum(item.total_return for item in metrics),
        "max_drawdown": min(item.max_drawdown for item in metrics),
        "cost_drag_bps": sum(item.cost_drag_bps for item in metrics),
        "stale_rejected_count": sum(item.stale_rejected_count for item in metrics),
        "halt_rejected_count": sum(item.halt_rejected_count for item in metrics),
    }


def _threshold_passes(metric_name: str, actual: float | int | None, threshold: float) -> bool:
    if actual is None:
        return False
    if metric_name in {"cost_drag_bps", "stale_rejected_count", "halt_rejected_count"}:
        return float(actual) <= threshold
    return float(actual) >= threshold


def _evaluate_pass_thresholds(
    spec: StrategyAuthoringSpec, aggregate_metrics: dict[str, float | int | None]
) -> dict[str, dict[str, float | int | bool | None]]:
    results: dict[str, dict[str, float | int | bool | None]] = {}
    for metric_name, threshold in spec.backtest.pass_thresholds.items():
        actual = aggregate_metrics.get(metric_name)
        results[metric_name] = {
            "actual": actual,
            "threshold": threshold,
            "passed": _threshold_passes(metric_name, actual, threshold),
        }
    return results


def run_authoring_backtest(
    spec: StrategyAuthoringSpec, frame: pl.DataFrame, *, data_dir: Path
) -> tuple[list[Any], dict[str, Any]]:
    quote_path = _resolve_path(spec.data.quote_data_path, data_dir)
    cost_path = _resolve_path(spec.data.cost_model_path, data_dir)
    signals = strategy_signals_to_research_signals(frame)
    metrics, _records, summary = run_backtest_bridge_for_signals(
        quote_path,
        signals,
        cost_matrix_path=cost_path if cost_path.exists() else None,
        exit_model="fixed_horizon",
        holding_horizon_minutes=spec.backtest.label_horizon_minutes,
    )
    aggregate_metrics = _aggregate_backtest_metrics(metrics)
    threshold_results = _evaluate_pass_thresholds(spec, aggregate_metrics)
    pass_all_thresholds = all(bool(result["passed"]) for result in threshold_results.values())
    summary["authoring_split_method"] = spec.backtest.split_method
    summary["authoring_era_unit"] = spec.backtest.era_unit
    summary["min_trade_count"] = spec.backtest.min_trade_count
    summary["aggregate_metrics"] = aggregate_metrics
    summary["pass_thresholds"] = threshold_results
    summary["pass_all_thresholds"] = pass_all_thresholds
    summary["pass_min_trade_count"] = (
        aggregate_metrics["trade_count"] or 0
    ) >= spec.backtest.min_trade_count
    summary["backtest_passed"] = summary["pass_min_trade_count"] and pass_all_thresholds
    return metrics, summary


def write_authoring_backtest_outputs(
    spec: StrategyAuthoringSpec, metrics: list[Any], summary: dict[str, Any], *, data_dir: Path
) -> dict[str, Path]:
    metrics_path = data_dir / "research/strategy_backtest_metrics.json"
    report_path = data_dir / "reports/strategy_backtest_report.md"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = _metrics_json(metrics, summary, spec)
    metrics_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    rows = "\n".join(
        f"| {item.venue} | {item.canonical_symbol} | {item.trade_count} | {item.total_return:.6f} | {item.max_drawdown:.6f} | {item.cost_drag_bps:.2f} |"
        for item in metrics
    )
    report_path.write_text(
        "# Strategy Authoring Backtest Report\n\n"
        "paper_only: true\n\n"
        f"- strategy_id: {spec.experiment.strategy_id}\n"
        f"- signals_considered: {summary.get('signals_considered')}\n"
        f"- executed_count: {summary.get('executed_count')}\n"
        f"- pass_min_trade_count: {summary.get('pass_min_trade_count')}\n\n"
        f"- pass_all_thresholds: {summary.get('pass_all_thresholds')}\n"
        f"- backtest_passed: {summary.get('backtest_passed')}\n\n"
        "| Venue | Symbol | Trades | Total Return | Max Drawdown | Cost Drag bps |\n"
        "|---|---:|---:|---:|---:|---:|\n"
        f"{rows}\n",
        encoding="utf-8",
    )
    return {"metrics": metrics_path, "report": report_path}


def write_authoring_paper_preview_outputs(
    spec: StrategyAuthoringSpec,
    frame: pl.DataFrame,
    summary: dict[str, Any],
    *,
    data_dir: Path,
) -> dict[str, Path]:
    now = datetime.now(timezone.utc)
    parameter_hash = _stable_digest(spec.model_dump(mode="json"))
    run_id = signal_artifact_run_id(frame) if not frame.is_empty() else parameter_hash
    trial_id = f"trial-{run_id}"
    trial_group_id = f"trial-group-{run_id}"
    selected_rows = frame.sort(["ts_signal", "signal_id"]).to_dicts()[:1]
    selected_signal_ids = [str(row["signal_id"]) for row in selected_rows]
    selected = bool(selected_signal_ids) and bool(summary.get("backtest_passed", False))
    record = TrialRecord(
        schema_version="trial_record.v1",
        trial_id=trial_id,
        trial_group_id=trial_group_id,
        trial_index=0,
        strategy_id=spec.experiment.strategy_id,
        strategy_family=spec.experiment.strategy_family,
        strategy_version=spec.experiment.strategy_version,
        evaluation_plan_id="strategy_authoring_v1",
        data_snapshot_id="data-snap-current",
        feature_snapshot_id="feature-snap-current",
        parameter_hash=parameter_hash,
        parameter_count=1,
        parameter_space_hash="strategy-authoring-yaml-v1",
        random_seed=None,
        git_sha=None,
        signal_count=frame.height,
        candidate_count=frame.height,
        paper_candidate_count=len(selected_signal_ids) if selected else 0,
        executed_count=0,
        blocked_count=0 if selected else 1,
        no_signal_count=0 if selected_signal_ids else 1,
        blocked_reason_counts={} if selected else {"not_selected": 1},
        metrics={**summary, "selected_signal_ids": selected_signal_ids if selected else []},
        baseline_strategy_id=None,
        baseline_delta_metrics={},
        selected_for_next_stage=selected,
        rejection_reasons=[] if selected else ["insufficient_trades_or_no_signal"],
    )
    ledger_path = data_dir / "research/trial_ledger.jsonl"
    ledger = TrialLedger(ledger_path)
    existing_ids = {item.trial_id for item in ledger.read_all()}
    if record.trial_id not in existing_ids:
        ledger.append(record)

    candidates: list[TradeCandidate] = []
    selected_candidate_ids: list[str] = []
    rejected_candidate_ids: list[str] = []
    rows_for_candidates = selected_rows if selected_rows else [{}]
    for row in rows_for_candidates:
        candidate_id = (
            f"candidate-{trial_id}-{row['signal_id']}" if row else f"candidate-{trial_id}-no-signal"
        )
        status = "candidate" if selected else ("no_signal" if not row else "hold")
        binding = spec.experiment.symbol_bindings[0]
        execution_venue = cast(
            Literal["trade_xyz"], row.get("execution_venue") if row else binding.execution_venue
        )
        side = cast(
            Literal["long", "short", "none"], row.get("side") if selected and row else "none"
        )
        tail_bucket = cast(
            Literal["top", "middle", "bottom", "none"],
            row.get("tail_bucket") if selected and row else "none",
        )
        confidence = _float_or_default(row.get("confidence") if selected and row else None, 0.0)
        candidate = TradeCandidate(
            schema_version="trade_candidate.v1",
            candidate_id=candidate_id,
            generated_at=now,
            signal_id=str(row.get("signal_id")) if row else None,
            strategy_id=spec.experiment.strategy_id,
            trial_id=trial_id,
            execution_venue=execution_venue,
            execution_symbol=str(row.get("execution_symbol") or binding.execution_symbol),
            real_market_symbol=str(row.get("real_market_symbol") or binding.real_market_symbol),
            side=side,
            timeframe=str(row.get("timeframe") or spec.rules.timeframe),
            status=status,
            raw_score=row.get("raw_score") if row else None,
            rank_score=row.get("rank_score") if selected and row else None,
            percentile_rank=row.get("percentile_rank") if selected and row else None,
            tail_bucket=tail_bucket,
            confidence=confidence,
            entry_reason_codes=list(row.get("reason_codes") or []) if selected and row else [],
            block_reasons=[] if selected else record.rejection_reasons,
            feature_snapshot_ref=row.get("feature_snapshot_ref") if row else None,
            quote_ref=row.get("quote_ref") if row else None,
            tracking_ref=row.get("tracking_ref") if row else None,
        )
        candidates.append(candidate)
        (selected_candidate_ids if selected else rejected_candidate_ids).append(candidate_id)

    pack = PaperCandidatePack(
        schema_version="paper_candidate_pack.v1",
        pack_id=f"paper-pack-{run_id}",
        generated_at=now,
        evaluation_plan_id="strategy_authoring_v1",
        data_snapshot_id="data-snap-current",
        feature_snapshot_id="feature-snap-current",
        trial_group_id=trial_group_id,
        candidates=candidates,
        selected_candidate_ids=selected_candidate_ids,
        rejected_candidate_ids=rejected_candidate_ids,
        selection_policy={
            "source": "strategy_authoring",
            "default_decision": spec.promotion.default_decision,
        },
        reason_codes=["strategy_authoring_v1"],
        block_reasons=[] if selected else record.rejection_reasons,
    )
    pack_path = data_dir / "research/paper_candidate_pack.json"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(pack.model_dump_json(indent=2), encoding="utf-8")

    decision = PromotionDecision(
        schema_version="promotion_decision.v1",
        promotion_id=f"promotion-{run_id}",
        generated_at=now,
        source_pack_id=pack.pack_id,
        reviewer=None,
        from_stage="strategy_lab",
        to_stage="paper_observation",
        decision=spec.promotion.default_decision,
        required_evidence=["trial_ledger", "paper_candidate_pack"],
        observed_evidence=["trial_ledger", "paper_candidate_pack"],
        approval_reasons=[],
        rejection_reasons=["operator_review_required"],
    )
    decision_path = data_dir / "research/promotion_decision.json"
    decision_path.write_text(decision.model_dump_json(indent=2), encoding="utf-8")

    intents: list[PaperIntentPreview] = []
    preview_path = data_dir / "bot/paper_intent_preview.json"
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.write_text(
        json.dumps([intent.model_dump(mode="json") for intent in intents], indent=2),
        encoding="utf-8",
    )
    report_path = data_dir / "reports/paper_intent_preview.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "# Paper Intent Preview\n\n"
        "- source: strategy_authoring\n"
        f"- decision: {decision.decision}\n"
        f"- intents: {len(intents)}\n"
        "- paper_only: true\n",
        encoding="utf-8",
    )
    return {
        "trial_ledger": ledger_path,
        "paper_candidate_pack": pack_path,
        "promotion_decision": decision_path,
        "paper_intent_preview": preview_path,
        "paper_intent_preview_report": report_path,
    }


def write_authoring_run_summary(
    spec: StrategyAuthoringSpec,
    *,
    data_dir: Path,
    through: str,
    artifacts: dict[str, Path],
    signal_count: int,
) -> Path:
    out = data_dir / "research/strategy_authoring_run.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps(
            {
                "schema_version": "strategy_authoring_run.v1",
                "strategy_id": spec.experiment.strategy_id,
                "through": through,
                "signal_count": signal_count,
                "paper_only": True,
                "live_order_submitted": False,
                "artifacts": {key: str(value) for key, value in artifacts.items()},
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out
