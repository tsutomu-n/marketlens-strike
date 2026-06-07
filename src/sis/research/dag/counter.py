from __future__ import annotations

from pathlib import Path
from typing import Literal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sis.research.dag.contracts import CoreDag
from sis.research.hypothesis.yaml_io import load_yaml_mapping


class CounterDag(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    changed_assumption: str = Field(min_length=1)
    risk: str = Field(min_length=1)
    proxy: str = Field(min_length=1)
    refutation_test_hint: str = Field(min_length=1)


class CounterDagRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["counter_dag_registry.v1"]
    dag_id: str = Field(min_length=1)
    counter_dags: list[CounterDag] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_counter_dags(self) -> Self:
        seen: set[str] = set()
        duplicates: list[str] = []
        for item in self.counter_dags:
            if item.id in seen and item.id not in duplicates:
                duplicates.append(item.id)
            seen.add(item.id)
        if duplicates:
            raise ValueError("duplicate counter DAG ids: " + ", ".join(duplicates))
        return self

    def by_id(self) -> dict[str, CounterDag]:
        return {item.id: item for item in self.counter_dags}


def load_counter_dag_registry(path: Path) -> CounterDagRegistry:
    return CounterDagRegistry.model_validate(load_yaml_mapping(path))


def validate_counter_dag_refs(dag: CoreDag, registry: CounterDagRegistry) -> None:
    if dag.dag_id != registry.dag_id:
        raise ValueError(f"counter DAG registry dag_id mismatch: {registry.dag_id} != {dag.dag_id}")
    if not dag.counter_dag_refs:
        raise ValueError("core DAG requires counter_dag_refs")
    registered = set(registry.by_id())
    missing = sorted(set(dag.counter_dag_refs) - registered)
    if missing:
        raise ValueError("core DAG references unknown counter DAGs: " + ", ".join(missing))
