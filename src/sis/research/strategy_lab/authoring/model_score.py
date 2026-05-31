from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, cast

import polars as pl
import yaml

from sis.research.strategy_lab.authoring.confirmation import _apply_confirmation_panels
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.linear_algebra import _solve_linear_system
from sis.research.strategy_lab.authoring.contracts.spec import StrategyAuthoringSpec
from sis.research.strategy_lab.authoring.features import _apply_derived_features
from sis.research.strategy_lab.authoring.validation import _resolve_path


def train_authoring_linear_model_score(
    spec: StrategyAuthoringSpec,
    *,
    data_dir: Path,
    target_column: str,
    feature_columns: list[str],
    ridge_lambda: float = 1e-6,
    activation: Literal["identity", "sigmoid", "tanh", "clamp_0_1"] = "identity",
    missing_value: float | None = None,
) -> dict[str, Any]:
    if not target_column.strip():
        raise StrategyAuthoringValidationError("target_column must be non-empty")
    if not feature_columns or any(not column.strip() for column in feature_columns):
        raise StrategyAuthoringValidationError("feature_columns must be non-empty")
    if ridge_lambda < 0:
        raise StrategyAuthoringValidationError("ridge_lambda must be >= 0")

    feature_path = _resolve_path(spec.data.feature_panel_path, data_dir)
    if not feature_path.exists():
        raise FileNotFoundError(f"feature_panel_path not found: {feature_path}")
    frame = _apply_derived_features(
        _apply_confirmation_panels(pl.read_parquet(feature_path), spec, data_dir=data_dir),
        spec,
    )
    required = {"canonical_symbol", target_column, *feature_columns}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise StrategyAuthoringValidationError(f"feature panel missing model columns: {missing}")

    symbols = {binding.real_market_symbol for binding in spec.experiment.symbol_bindings}
    rows: list[tuple[list[float], float]] = []
    for row in frame.to_dicts():
        if str(row.get("canonical_symbol") or "").upper() not in symbols:
            continue
        target = row.get(target_column)
        values = [row.get(column) for column in feature_columns]
        if not isinstance(target, int | float):
            continue
        if not all(isinstance(value, int | float) for value in values):
            continue
        numeric_values = cast(list[int | float], values)
        rows.append(([1.0, *[float(value) for value in numeric_values]], float(target)))
    if len(rows) < len(feature_columns) + 1:
        raise StrategyAuthoringValidationError(
            "not enough numeric rows to train linear model score"
        )

    dimension = len(feature_columns) + 1
    xtx = [[0.0 for _ in range(dimension)] for _ in range(dimension)]
    xty = [0.0 for _ in range(dimension)]
    for features, target in rows:
        for left in range(dimension):
            xty[left] += features[left] * target
            for right in range(dimension):
                xtx[left][right] += features[left] * features[right]
    for index in range(1, dimension):
        xtx[index][index] += ridge_lambda

    coefficients = _solve_linear_system(xtx, xty)
    model_score = {
        "model_type": "linear",
        "intercept": coefficients[0],
        "activation": activation,
        "missing_value": missing_value,
        "coefficients": [
            {"column": column, "weight": weight}
            for column, weight in zip(feature_columns, coefficients[1:], strict=True)
        ],
    }
    return {
        "schema_version": "strategy_authoring_model_score.v1",
        "paper_only": True,
        "live_order_submitted": False,
        "strategy_id": spec.experiment.strategy_id,
        "target_column": target_column,
        "row_count": len(rows),
        "ridge_lambda": ridge_lambda,
        "model_score": model_score,
    }


def write_authoring_model_score_outputs(
    spec: StrategyAuthoringSpec,
    payload: dict[str, Any],
    *,
    data_dir: Path,
    out_spec: Path | None = None,
) -> dict[str, Path]:
    payload_path = data_dir / "research/strategy_authoring_model_score.json"
    payload_path.parent.mkdir(parents=True, exist_ok=True)
    payload_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    outputs = {"model_score": payload_path}
    if out_spec is not None:
        spec_payload = spec.model_dump(mode="json")
        spec_payload.setdefault("rules", {}).setdefault("score", {})["model_score"] = payload[
            "model_score"
        ]
        out_spec.parent.mkdir(parents=True, exist_ok=True)
        out_spec.write_text(yaml.safe_dump(spec_payload, sort_keys=False), encoding="utf-8")
        outputs["spec"] = out_spec
    return outputs
