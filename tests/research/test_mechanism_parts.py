from __future__ import annotations

import pytest
from pydantic import ValidationError

from sis.research.hypothesis.mechanism_contracts import MechanismPartsRegistry
from sis.research.hypothesis.mechanism_loader import load_mechanism_parts
from research.helpers import CONFIG_DIR


def test_mechanism_parts_load_initial_library() -> None:
    registry = load_mechanism_parts(CONFIG_DIR / "mechanism_parts.yaml")

    assert len(registry.parts) == 10
    assert registry.parts[0].role_hint == "confounder"


def test_mechanism_parts_reject_duplicate_unknown_role_and_empty_proxies() -> None:
    base = {
        "schema_version": "research_mechanism_parts.v1",
        "parts": [
            {"part_id": "P1", "name": "one", "role_hint": "confounder", "proxies": ["x"]},
            {"part_id": "P1", "name": "two", "role_hint": "confounder", "proxies": ["y"]},
        ],
    }
    with pytest.raises(ValidationError):
        MechanismPartsRegistry.model_validate(base)

    with pytest.raises(ValidationError):
        MechanismPartsRegistry.model_validate(
            {
                "schema_version": "research_mechanism_parts.v1",
                "parts": [{"part_id": "P", "name": "x", "role_hint": "bad", "proxies": ["x"]}],
            }
        )

    with pytest.raises(ValidationError):
        MechanismPartsRegistry.model_validate(
            {
                "schema_version": "research_mechanism_parts.v1",
                "parts": [{"part_id": "P", "name": "x", "role_hint": "confounder", "proxies": []}],
            }
        )
