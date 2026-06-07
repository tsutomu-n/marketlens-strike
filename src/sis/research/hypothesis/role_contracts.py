from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CausalRoleName = Literal[
    "treatment_candidate",
    "outcome",
    "confounder",
    "mediator",
    "moderator",
    "modeled_latent",
    "observed_proxy",
    "selection_mechanism",
    "data_quality",
    "neutralizer",
]


class CausalRoleRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["research_causal_roles.v1"]
    roles: dict[str, CausalRoleName] = Field(min_length=1)
