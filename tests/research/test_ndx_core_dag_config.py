from __future__ import annotations

from sis.research.dag.counter import load_counter_dag_registry, validate_counter_dag_refs
from sis.research.dag.linter import lint_core_dag, raise_for_lint_errors
from sis.research.dag.loader import load_core_dag
from sis.research.dag.validator import validate_core_dag
from sis.research.hypothesis.temporal_contracts import TemporalAvailability
from sis.research.hypothesis.yaml_io import load_yaml_mapping
from research.helpers import CONFIG_DIR


def test_ndx_core_dag_config_validate_lint_and_counter_refs_pass() -> None:
    dag = load_core_dag(CONFIG_DIR / "core_dag.yaml")
    temporal = TemporalAvailability.model_validate(
        load_yaml_mapping(CONFIG_DIR / "temporal_availability.yaml")
    )
    counter_dags = load_counter_dag_registry(CONFIG_DIR / "counter_dags.yaml")

    validate_core_dag(dag)
    issues = lint_core_dag(dag, temporal=temporal)
    raise_for_lint_errors(issues)
    validate_counter_dag_refs(dag, counter_dags)

    assert dag.dag_id == "HYP-NDX-001"
    assert {node.id for node in dag.nodes} >= {"open_gap_residual", "qqq_open_to_close_return"}
