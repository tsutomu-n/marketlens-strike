from __future__ import annotations

import json

from sis.research.dag.counter import load_counter_dag_registry
from sis.research.dag.export import export_core_dag_artifacts
from sis.research.dag.linter import lint_core_dag
from sis.research.dag.loader import load_core_dag
from sis.research.hypothesis.temporal_contracts import TemporalAvailability
from sis.research.hypothesis.variable_loader import load_variable_inventory
from sis.research.hypothesis.yaml_io import load_yaml_mapping
from research.helpers import CONFIG_DIR


def test_core_dag_export_writes_json_mermaid_markdown_and_report(tmp_path) -> None:
    dag = load_core_dag(CONFIG_DIR / "core_dag.yaml")
    inventory = load_variable_inventory(CONFIG_DIR / "variable_inventory.yaml")
    counter_dags = load_counter_dag_registry(CONFIG_DIR / "counter_dags.yaml")
    temporal = TemporalAvailability.model_validate(
        load_yaml_mapping(CONFIG_DIR / "temporal_availability.yaml")
    )
    result = export_core_dag_artifacts(
        dag,
        inventory=inventory,
        counter_dags=counter_dags,
        lint_issues=lint_core_dag(dag, temporal=temporal),
        out_dir=tmp_path / "research/ndx",
        report_path=tmp_path / "reports/ndx_core_dag_report.md",
    )

    payload = json.loads(result.json_path.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "core_dag.v1"
    assert payload["dag_id"] == "HYP-NDX-001"
    assert "flowchart" in result.mermaid_path.read_text(encoding="utf-8")
    assert "BroadMarketOnlyDAG" in result.counter_dags_path.read_text(encoding="utf-8")
    assert "DAGは真因果の証明ではない" in result.report_path.read_text(encoding="utf-8")
