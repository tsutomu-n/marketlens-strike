from __future__ import annotations

from sis.research.dag.counter import load_counter_dag_registry, validate_counter_dag_refs
from sis.research.dag.contracts import CoreDag
from sis.research.dag.loader import load_core_dag
from research.helpers import CONFIG_DIR
from research.helpers import core_dag_payload


def test_counter_dag_registry_has_required_six_counter_dags() -> None:
    dag = load_core_dag(CONFIG_DIR / "core_dag.yaml")
    registry = load_counter_dag_registry(CONFIG_DIR / "counter_dags.yaml")

    validate_counter_dag_refs(dag, registry)

    assert len(registry.counter_dags) >= 6
    assert set(dag.counter_dag_refs) <= set(registry.by_id())


def test_counter_dag_refs_are_required_for_validated_core_dag() -> None:
    registry = load_counter_dag_registry(CONFIG_DIR / "counter_dags.yaml")
    payload = core_dag_payload()
    payload["dag_id"] = "HYP-NDX-001"
    dag = CoreDag.model_validate(payload)

    try:
        validate_counter_dag_refs(dag, registry)
    except ValueError as exc:
        assert "requires counter_dag_refs" in str(exc)
    else:
        raise AssertionError("expected missing counter_dag_refs to fail")
