from __future__ import annotations

import pytest

from sis.research.dag.contracts import CoreDag
from sis.research.dag.errors import CoreDagValidationError
from sis.research.dag.validator import validate_core_dag
from research.helpers import core_dag_payload


def test_core_dag_validator_accepts_valid_payload() -> None:
    validate_core_dag(CoreDag.model_validate(core_dag_payload()))


def test_core_dag_validator_rejects_unknown_node_self_loop_and_duplicate_edge() -> None:
    payload = core_dag_payload()
    payload["edges"] = [
        {"from": "missing", "to": "treatment"},
        {"from": "treatment", "to": "treatment"},
        {"from": "treatment", "to": "outcome"},
        {"from": "treatment", "to": "outcome"},
    ]

    with pytest.raises(CoreDagValidationError) as exc_info:
        validate_core_dag(CoreDag.model_validate(payload))

    message = str(exc_info.value)
    assert "unknown from node" in message
    assert "self-loop" in message
    assert "duplicate edge" in message
