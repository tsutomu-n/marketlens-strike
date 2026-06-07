from __future__ import annotations

from typing import Literal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


TemporalClass = Literal[
    "t_prev_close",
    "t_pre_open",
    "t_open",
    "t_after_open",
    "t_after_close",
]


class ForbiddenLayerEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_layer: TemporalClass = Field(alias="from")
    to: TemporalClass
    reason: str = Field(min_length=1)


class TemporalAvailability(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal["research_temporal_availability.v1"]
    layers: dict[TemporalClass, list[str]] = Field(min_length=1)
    forbidden_layer_edges: list[ForbiddenLayerEdge] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_duplicate_variable_layers(self) -> Self:
        seen: dict[str, str] = {}
        duplicates: list[str] = []
        for layer, variables in self.layers.items():
            for variable_id in variables:
                previous_layer = seen.get(variable_id)
                if previous_layer is not None:
                    duplicates.append(f"{variable_id} in {previous_layer} and {layer}")
                seen[variable_id] = str(layer)
        if duplicates:
            raise ValueError("duplicate variable temporal layers: " + ", ".join(duplicates))
        return self

    def layer_for_variable(self, variable_id: str) -> TemporalClass | None:
        for layer, variables in self.layers.items():
            if variable_id in variables:
                return layer
        return None

