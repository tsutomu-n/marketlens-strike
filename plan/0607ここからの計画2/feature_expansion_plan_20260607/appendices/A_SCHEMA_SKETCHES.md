<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# Appendix A: Schema Sketches

この付録は実装スケッチである。正本は実装後の Pydantic model と JSON Schema とする。

## CoreDag Pydantic sketch

```python
from typing import Literal
from pydantic import BaseModel, Field

NodeRole = Literal[
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

TemporalLayer = Literal[
    "t_prev_close",
    "t_pre_open",
    "t_open_observed",
    "t_open_plus_buffer",
    "t_after_close",
    "provider_dependent",
]

class DagNode(BaseModel):
    node_id: str = Field(min_length=1)
    role: NodeRole
    variable_ref: str | None = None
    proxy: str | None = None
    temporal_layer: TemporalLayer | None = None
    required: bool = True
    notes: list[str] = Field(default_factory=list)

class DagEdge(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    rationale: str = Field(min_length=1)

class ForbiddenEdge(BaseModel):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    reason: str = Field(min_length=1)

class CoreDag(BaseModel):
    schema_version: Literal["core_dag.v1"]
    dag_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    scope_id: str = Field(min_length=1)
    nodes: list[DagNode]
    edges: list[DagEdge]
    forbidden_edges: list[ForbiddenEdge] = Field(default_factory=list)
    counter_dag_refs: list[str] = Field(default_factory=list)
```

## JSON Schema policy

```text
JSON Schemaは薄いguard。
詳細validationはPydantic modelとvalidator/linterで行う。
```

## Lint result sketch

```python
class LintIssue(BaseModel):
    severity: Literal["error", "warning"]
    rule_id: str
    message: str
    node_id: str | None = None
    edge: tuple[str, str] | None = None

class LintReport(BaseModel):
    dag_id: str
    error_count: int
    warning_count: int
    issues: list[LintIssue]
```
