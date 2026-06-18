from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field

from sis.strategy_stage.models import StageProducer


class ViewerArtifactFormat(StrEnum):
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


class ViewerSourceArtifact(BaseModel):
    artifact_key: str
    path: str
    sha256: str
    artifact_format: ViewerArtifactFormat
    schema_version: str | None = None
    title: str
    status: str | None = None
    boundary_violations: list[str] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
    preview: str | None = None


class StrategyWorkbenchViewerManifest(BaseModel):
    schema_version: Literal["strategy_workbench_viewer.v1"] = "strategy_workbench_viewer.v1"
    viewer_id: str
    created_at: datetime
    producer: StageProducer
    source_artifacts: list[ViewerSourceArtifact]
    html_report_path: str
    html_report_hash: str
    artifact_count: int
    boundary_violation_count: int
    paper_execution_allowed: Literal[False] = False
    live_allowed: Literal[False] = False
    wallet_used: Literal[False] = False
    signing_used: Literal[False] = False
    exchange_write_used: Literal[False] = False
