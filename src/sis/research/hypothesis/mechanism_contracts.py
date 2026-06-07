from __future__ import annotations

from typing import Literal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sis.research.hypothesis.role_contracts import CausalRoleName


class MechanismPart(BaseModel):
    model_config = ConfigDict(extra="forbid")

    part_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    role_hint: CausalRoleName
    proxies: list[str] = Field(min_length=1)


class MechanismPartsRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["research_mechanism_parts.v1"]
    parts: list[MechanismPart] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_part_ids(self) -> Self:
        seen: set[str] = set()
        duplicates: list[str] = []
        for part in self.parts:
            if part.part_id in seen and part.part_id not in duplicates:
                duplicates.append(part.part_id)
            seen.add(part.part_id)
        if duplicates:
            raise ValueError(f"duplicate part_id values: {', '.join(duplicates)}")
        return self
