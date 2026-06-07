from __future__ import annotations

from typing import Literal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sis.research.hypothesis.role_contracts import CausalRoleName
from sis.research.hypothesis.temporal_contracts import TemporalClass


class VariableDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str | None = None
    source_symbol: str | None = None
    formula: str | None = None
    proxy: str | None = None
    temporal_class: TemporalClass
    role_candidates: list[CausalRoleName] = Field(min_length=1)

    @model_validator(mode="after")
    def require_data_lineage(self) -> Self:
        if not any((self.source_symbol, self.formula, self.proxy)):
            raise ValueError("variable requires at least one of source_symbol, formula, or proxy")
        return self


class VariableInventory(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["research_variable_inventory.v1"]
    variables: dict[str, VariableDefinition] = Field(min_length=1)

