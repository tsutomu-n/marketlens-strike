from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import yaml

from sis.research.dag.contracts import CoreDag
from sis.research.dag.counter import CounterDagRegistry
from sis.research.dag.data_requirements import build_data_requirements
from sis.research.dag.linter import DagLintIssue
from sis.research.dag.report import render_core_dag_report
from sis.research.hypothesis.variable_contracts import VariableInventory


@dataclass(frozen=True)
class CoreDagExportResult:
    json_path: Path
    mermaid_path: Path
    counter_dags_path: Path
    data_requirements_path: Path
    report_path: Path


def export_core_dag_artifacts(
    dag: CoreDag,
    *,
    inventory: VariableInventory,
    counter_dags: CounterDagRegistry,
    lint_issues: list[DagLintIssue],
    out_dir: Path,
    report_path: Path,
) -> CoreDagExportResult:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "core_dag.json"
    mermaid_path = out_dir / "core_dag.mmd"
    counter_dags_path = out_dir / "counter_dags.md"
    data_requirements_path = out_dir / "data_requirements.yaml"

    data_requirements = build_data_requirements(dag, inventory)
    dag_payload = dag.model_copy(update={"data_requirements": data_requirements})
    json_path.write_text(
        json.dumps(dag_payload.model_dump(mode="json", by_alias=True), indent=2) + "\n",
        encoding="utf-8",
    )
    mermaid_path.write_text(render_mermaid(dag), encoding="utf-8")
    counter_dags_path.write_text(render_counter_dags(counter_dags), encoding="utf-8")
    data_requirements_path.write_text(
        yaml.safe_dump(
            [item.model_dump(mode="json") for item in data_requirements],
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    report_path.write_text(
        render_core_dag_report(
            dag,
            inventory=inventory,
            counter_dags=counter_dags,
            lint_issues=lint_issues,
        ),
        encoding="utf-8",
    )
    return CoreDagExportResult(
        json_path=json_path,
        mermaid_path=mermaid_path,
        counter_dags_path=counter_dags_path,
        data_requirements_path=data_requirements_path,
        report_path=report_path,
    )


def render_mermaid(dag: CoreDag) -> str:
    lines = ["flowchart TD"]
    for node in dag.nodes:
        lines.append(f"  {node.id}[\"{node.id}\\n{node.role}\"]")
    for edge in dag.edges:
        lines.append(f"  {edge.from_node} --> {edge.to}")
    return "\n".join(lines) + "\n"


def render_counter_dags(registry: CounterDagRegistry) -> str:
    lines = ["# Counter DAGs", ""]
    for item in registry.counter_dags:
        lines.extend(
            [
                f"## {item.id}",
                "",
                item.description,
                "",
                f"Changed assumption: {item.changed_assumption}",
                "",
            ]
        )
    return "\n".join(lines)
