from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sis.strategy_idea_seeds.common.models import SHA256_PATTERN


SOURCE_KEYS = (
    "candles_5m",
    "funding_rows",
    "ticker_rows",
    "mark_index_history",
    "open_interest_history",
    "trade_tape_history",
    "order_book_history",
    "liquidation_history",
)


class SourceCapabilityClass(StrEnum):
    HISTORICAL = "HISTORICAL"
    SNAPSHOT_ONLY = "SNAPSHOT_ONLY"
    FORWARD_ONLY = "FORWARD_ONLY"
    MISSING = "MISSING"
    INVALID = "INVALID"
    UNKNOWN = "UNKNOWN"


class SourceUsableFor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    technical_concept_generation: bool
    ml_historical_feature: bool
    llm_context: bool
    direct_evidence_claim: Literal[False] = False


class SourceCapability(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_key: str
    capability: SourceCapabilityClass
    row_count: int = Field(ge=0)
    fields_present: list[str]
    artifact_paths: list[str]
    artifact_hashes: list[str]
    manifest_path: str | None = None
    reason_codes: list[str]
    usable_for: SourceUsableFor

    @model_validator(mode="after")
    def validate_hashes(self) -> SourceCapability:
        if len(self.artifact_paths) != len(self.artifact_hashes):
            raise ValueError("artifact_paths and artifact_hashes must align")
        for value in self.artifact_hashes:
            if not value.startswith("sha256:") or len(value) != len("sha256:") + 64:
                raise ValueError("artifact hash must be sha256")
        return self


class SourceCapabilitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["strategy_idea_seed_source_capabilities.v1"] = (
        "strategy_idea_seed_source_capabilities.v1"
    )
    source_root: str
    source_root_hash: str = Field(pattern=SHA256_PATTERN)
    capabilities: list[SourceCapability]

    @model_validator(mode="after")
    def validate_source_keys(self) -> SourceCapabilitySnapshot:
        keys = [item.source_key for item in self.capabilities]
        if keys != list(SOURCE_KEYS):
            raise ValueError("capabilities must contain all source keys in canonical order")
        return self
