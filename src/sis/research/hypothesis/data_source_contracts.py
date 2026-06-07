from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SourceTier = Literal["defined", "optional_provider_dependent", "deferred"]


class DataSourceDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1)
    source_tier: SourceTier
    default_proxy_for: list[str] = Field(default_factory=list)
    provider_name: str | None = None
    responsibility: str | None = None
    notes: str | None = None


class DataSourceRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["research_data_sources.v1"]
    sources: dict[str, DataSourceDefinition] = Field(min_length=1)

    def tier_for_symbol(self, source_symbol: str | None) -> SourceTier | None:
        if source_symbol is None:
            return None
        source = self.sources.get(source_symbol)
        return source.source_tier if source is not None else None
