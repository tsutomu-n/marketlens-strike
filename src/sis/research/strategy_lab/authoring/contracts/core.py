from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from sis.research.strategy_lab.specs import SymbolBinding


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


class ConfirmationPanel(BaseModel):
    path: str
    prefix: str
    max_age_minutes: int | None = None

    @model_validator(mode="after")
    def validate_confirmation_panel(self) -> ConfirmationPanel:
        if not self.path.strip():
            raise ValueError("data.confirmation_panels[].path must be non-empty")
        if not self.prefix.strip():
            raise ValueError("data.confirmation_panels[].prefix must be non-empty")
        self.prefix = self.prefix.strip()
        if self.prefix in {"ts", "canonical_symbol"}:
            raise ValueError("data.confirmation_panels[].prefix is reserved")
        if self.max_age_minutes is not None and self.max_age_minutes <= 0:
            raise ValueError("data.confirmation_panels[].max_age_minutes must be positive")
        return self


class AuthoringData(BaseModel):
    feature_panel_path: str = "data/research/feature_panel.parquet"
    quote_data_path: str = "data/normalized/quotes.parquet"
    cost_model_path: str = "data/research/venue_cost_matrix.csv"
    confirmation_panels: list[ConfirmationPanel] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_data(self) -> AuthoringData:
        prefixes = [panel.prefix for panel in self.confirmation_panels]
        if len(prefixes) != len(set(prefixes)):
            raise ValueError("data.confirmation_panels prefixes must be unique")
        return self


class Condition(BaseModel):
    column: str
    op: Literal[
        "gt",
        "gte",
        "lt",
        "lte",
        "eq",
        "neq",
        "is_true",
        "is_false",
        "between",
        "in",
        "not_in",
        "crosses_above",
        "crosses_below",
        "rising",
        "falling",
        "consecutive_gt",
        "consecutive_gte",
        "consecutive_lt",
        "consecutive_lte",
        "consecutive_eq",
        "consecutive_neq",
    ]
    value: Any = None
    value_column: str | None = None
    window: int | None = None

    @model_validator(mode="after")
    def validate_condition(self) -> Condition:
        if not self.column.strip():
            raise ValueError("rule condition column must be non-empty")
        if self.window is not None and self.window <= 0:
            raise ValueError(f"{self.column}: condition window must be positive")
        if self.value_column is not None and not self.value_column.strip():
            raise ValueError(f"{self.column}: value_column must be non-empty when set")
        if self.op in {"is_true", "is_false"} and self.value_column is not None:
            raise ValueError(f"{self.column}: {self.op} does not support value_column")
        if self.op in {"rising", "falling"}:
            if self.value is not None or self.value_column is not None:
                raise ValueError(f"{self.column}: {self.op} does not support value targets")
            return self
        if self.op == "between":
            if self.value_column is not None:
                raise ValueError(f"{self.column}: between does not support value_column")
            if not isinstance(self.value, list | tuple) or len(self.value) != 2:
                raise ValueError(f"{self.column}: between requires a two-item value")
        if self.op in {"in", "not_in"}:
            if self.value_column is not None:
                raise ValueError(f"{self.column}: {self.op} does not support value_column")
            if not isinstance(self.value, list | tuple | set) or len(self.value) == 0:
                raise ValueError(f"{self.column}: {self.op} requires a non-empty value list")
        if self.op in {"gt", "gte", "lt", "lte", "eq", "neq"}:
            has_value = self.value is not None
            has_value_column = self.value_column is not None
            if has_value == has_value_column:
                raise ValueError(
                    f"{self.column}: {self.op} requires exactly one of value or value_column"
                )
        if self.op in {
            "crosses_above",
            "crosses_below",
            "consecutive_gt",
            "consecutive_gte",
            "consecutive_lt",
            "consecutive_lte",
            "consecutive_eq",
            "consecutive_neq",
        }:
            has_value = self.value is not None
            has_value_column = self.value_column is not None
            if has_value == has_value_column:
                raise ValueError(
                    f"{self.column}: {self.op} requires exactly one of value or value_column"
                )
            if self.op.startswith("consecutive_") and self.window is None:
                raise ValueError(f"{self.column}: {self.op} requires condition window")
        return self


class EntryRules(BaseModel):
    all: list[Condition] = Field(default_factory=list)
    any: list[Condition] = Field(default_factory=list)
    none: list[Condition] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_entry(self) -> EntryRules:
        if not self.all and not self.any and not self.none:
            raise ValueError("rules.entry must include at least one all/any/none condition")
        return self


class ScoreTerm(BaseModel):
    column: str
    weight: float = 1.0

    @model_validator(mode="after")
    def validate_score_term(self) -> ScoreTerm:
        if not self.column.strip():
            raise ValueError("rules.score term column must be non-empty")
        if not math.isfinite(self.weight):
            raise ValueError("rules.score term weight must be finite")
        return self


class ModelScore(BaseModel):
    model_type: Literal["linear"] = "linear"
    intercept: float = 0.0
    coefficients: list[ScoreTerm] = Field(default_factory=list)
    activation: Literal["identity", "sigmoid", "tanh", "clamp_0_1"] = "identity"
    missing_value: float | None = None

    @model_validator(mode="after")
    def validate_model_score(self) -> ModelScore:
        if not math.isfinite(self.intercept):
            raise ValueError("rules.score.model_score.intercept must be finite")
        if self.missing_value is not None and not math.isfinite(self.missing_value):
            raise ValueError("rules.score.model_score.missing_value must be finite")
        if not self.coefficients:
            raise ValueError("rules.score.model_score.coefficients must not be empty")
        return self


class ScoreRules(BaseModel):
    weighted_sum: list[ScoreTerm] = Field(default_factory=list)
    model_score: ModelScore | None = None

    @property
    def enabled(self) -> bool:
        return bool(self.weighted_sum) or self.model_score is not None
