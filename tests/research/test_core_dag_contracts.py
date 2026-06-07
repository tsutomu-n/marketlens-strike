from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from sis.research.dag.contracts import CoreDag
from research.helpers import core_dag_payload


def test_core_dag_contract_accepts_minimal_payload_and_schema_file_exists() -> None:
    dag = CoreDag.model_validate(core_dag_payload())

    assert dag.dag_id == "TEST-DAG"
    assert dag.edges[0].from_node == "confounder"
    assert json.loads(Path("schemas/core_dag.v1.schema.json").read_text())["title"] == "Core DAG v1"


def test_core_dag_contract_rejects_duplicate_node_ids() -> None:
    payload = core_dag_payload()
    payload["nodes"] = [
        {"id": "x", "role": "confounder"},
        {"id": "x", "role": "outcome"},
    ]

    with pytest.raises(ValidationError):
        CoreDag.model_validate(payload)
