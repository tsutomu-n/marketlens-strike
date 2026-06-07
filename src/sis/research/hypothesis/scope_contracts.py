from __future__ import annotations

from typing import Literal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScopeIncluded(BaseModel):
    model_config = ConfigDict(extra="forbid")

    primary: list[str] = Field(min_length=1)
    future_optional: list[str] = Field(default_factory=list)
    known_factors: list[str] = Field(default_factory=list)


class ScopePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    external_api_allowed: bool = False
    strategy_lab_export_allowed: bool = False
    paper_preview_allowed: bool = False


class ResearchScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["research_scope.v1"]
    scope_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    included: ScopeIncluded
    excluded: list[str] = Field(min_length=1)
    policy: ScopePolicy = Field(default_factory=ScopePolicy)

    @model_validator(mode="after")
    def validate_boundaries(self) -> Self:
        if self.policy.external_api_allowed:
            raise ValueError("Layer 2.2 scope must not allow external API calls.")
        if self.policy.strategy_lab_export_allowed:
            raise ValueError("Layer 2.2 scope must not allow Strategy Lab export.")
        if self.policy.paper_preview_allowed:
            raise ValueError("Layer 2.2 scope must not allow paper preview.")
        return self

