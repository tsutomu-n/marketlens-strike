from __future__ import annotations

from pathlib import Path


CONFIG_DIR = Path("configs/research_layer_2_2/ndx")


def core_dag_payload() -> dict[str, object]:
    return {
        "schema_version": "core_dag.v1",
        "dag_id": "TEST-DAG",
        "name": "test_dag",
        "scope_id": "TEST_SCOPE",
        "nodes": [
            {"id": "treatment", "role": "treatment_candidate"},
            {"id": "outcome", "role": "outcome"},
            {"id": "confounder", "role": "confounder"},
        ],
        "edges": [
            {"from": "confounder", "to": "treatment"},
            {"from": "treatment", "to": "outcome"},
        ],
    }
