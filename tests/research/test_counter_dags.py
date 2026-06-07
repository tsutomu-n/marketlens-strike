from __future__ import annotations

from sis.research.dag.counter import load_counter_dag_registry, validate_counter_dag_refs
from sis.research.dag.loader import load_core_dag
from research.helpers import CONFIG_DIR


def test_counter_dag_registry_has_required_six_counter_dags() -> None:
    dag = load_core_dag(CONFIG_DIR / "core_dag.yaml")
    registry = load_counter_dag_registry(CONFIG_DIR / "counter_dags.yaml")

    validate_counter_dag_refs(dag, registry)

    assert len(registry.counter_dags) >= 6
    assert set(dag.counter_dag_refs) <= set(registry.by_id())
