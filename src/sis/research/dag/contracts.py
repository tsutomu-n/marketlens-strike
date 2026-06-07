from __future__ import annotations

from typing import Literal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sis.research.hypothesis.role_contracts import CausalRoleName


class DagNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    role: CausalRoleName


class DagEdge(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_node: str = Field(alias="from", min_length=1)
    to: str = Field(min_length=1)
    reason: str | None = None

    @property
    def key(self) -> tuple[str, str]:
        return (self.from_node, self.to)


class DataRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    variable_id: str = Field(min_length=1)
    source_symbol: str | None = None
    formula: str | None = None
    temporal_class: str
    provider_candidates: list[str] = Field(default_factory=list)


class CoreDag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["core_dag.v1"]
    dag_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    scope_id: str = Field(min_length=1)
    nodes: list[DagNode] = Field(min_length=1)
    edges: list[DagEdge] = Field(min_length=1)
    forbidden_edges: list[DagEdge] = Field(default_factory=list)
    counter_dag_refs: list[str] = Field(default_factory=list)
    data_requirements: list[DataRequirement] = Field(default_factory=list)

    @model_validator(mode="after")
    def reject_duplicate_nodes(self) -> Self:
        seen: set[str] = set()
        duplicates: list[str] = []
        for node in self.nodes:
            if node.id in seen and node.id not in duplicates:
                duplicates.append(node.id)
            seen.add(node.id)
        if duplicates:
            raise ValueError("duplicate node ids: " + ", ".join(duplicates))
        return self

    def role_by_node_id(self) -> dict[str, CausalRoleName]:
        return {node.id: node.role for node in self.nodes}

    def node_ids(self) -> set[str]:
        return {node.id for node in self.nodes}
