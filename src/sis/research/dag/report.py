from __future__ import annotations

from sis.research.dag.contracts import CoreDag
from sis.research.dag.counter import CounterDagRegistry
from sis.research.dag.data_requirements import build_data_requirements
from sis.research.dag.linter import DagLintIssue
from sis.research.hypothesis.variable_contracts import VariableInventory


def render_core_dag_report(
    dag: CoreDag,
    *,
    inventory: VariableInventory,
    counter_dags: CounterDagRegistry,
    lint_issues: list[DagLintIssue],
) -> str:
    data_requirements = build_data_requirements(dag, inventory)
    lines = [
        "# NDX Core DAG Report",
        "",
        "DAGは真因果の証明ではない。これは研究仮説をレビュー可能にするartifactである。",
        "",
        f"- dag_id: {dag.dag_id}",
        f"- name: {dag.name}",
        f"- node_count: {len(dag.nodes)}",
        f"- edge_count: {len(dag.edges)}",
        f"- counter_dag_count: {len(counter_dags.counter_dags)}",
        "",
        "## Lint Result",
        "",
    ]
    if lint_issues:
        for issue in lint_issues:
            lines.append(f"- {issue.severity}: {issue.rule_id}: {issue.message}")
    else:
        lines.append("- pass")
    lines.extend(["", "## Data Requirements", ""])
    for item in data_requirements:
        source = item.source_symbol or "derived"
        providers = ",".join(item.provider_candidates) if item.provider_candidates else "none"
        lines.append(f"- {item.variable_id}: source={source}; providers={providers}")
    lines.extend(["", "## Counter DAGs", ""])
    for item in counter_dags.counter_dags:
        lines.append(f"- {item.id}: {item.changed_assumption}")
    return "\n".join(lines) + "\n"

