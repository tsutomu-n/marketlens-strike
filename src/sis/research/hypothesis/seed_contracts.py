from __future__ import annotations

from typing import Literal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchSeed(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    status: Literal["seed_only"]
    scope: str = Field(min_length=1)
    intuition: str = Field(min_length=1)
    candidate_known_factors: list[str] = Field(min_length=1)
    candidate_treatment: list[str] = Field(default_factory=list)
    candidate_outcome: list[str] = Field(min_length=1)
    next_layer: str = Field(min_length=1)


class SeedRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["research_seed_registry.v1"]
    seeds: list[ResearchSeed] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_seed_ids(self) -> Self:
        seen: set[str] = set()
        duplicates: list[str] = []
        for seed in self.seeds:
            if seed.seed_id in seen and seed.seed_id not in duplicates:
                duplicates.append(seed.seed_id)
            seen.add(seed.seed_id)
        if duplicates:
            raise ValueError(f"duplicate seed_id values: {', '.join(duplicates)}")
        return self

