from __future__ import annotations

import pytest
from pydantic import ValidationError

from sis.research.hypothesis.seed_contracts import SeedRegistry
from sis.research.hypothesis.seed_loader import load_seed_registry
from research.helpers import CONFIG_DIR


def test_seed_registry_loads_three_initial_seeds() -> None:
    registry = load_seed_registry(CONFIG_DIR / "seed_registry.yaml")

    assert [seed.seed_id for seed in registry.seeds] == [
        "NDX-SEED-001",
        "NDX-SEED-002",
        "NDX-SEED-003",
    ]


def test_seed_registry_rejects_duplicate_seed_id_and_missing_next_layer() -> None:
    payload = {
        "schema_version": "research_seed_registry.v1",
        "seeds": [
            {
                "seed_id": "S1",
                "name": "one",
                "status": "seed_only",
                "scope": "SCOPE",
                "intuition": "x",
                "candidate_known_factors": ["a"],
                "candidate_outcome": ["y"],
                "next_layer": "layer_2_0_variable_inventory",
            },
            {
                "seed_id": "S1",
                "name": "two",
                "status": "seed_only",
                "scope": "SCOPE",
                "intuition": "x",
                "candidate_known_factors": ["a"],
                "candidate_outcome": ["y"],
                "next_layer": "layer_2_0_variable_inventory",
            },
        ],
    }
    with pytest.raises(ValidationError):
        SeedRegistry.model_validate(payload)

    missing_next_layer = dict(payload)
    missing_next_layer["seeds"] = [dict(payload["seeds"][0])]
    del missing_next_layer["seeds"][0]["next_layer"]
    with pytest.raises(ValidationError):
        SeedRegistry.model_validate(missing_next_layer)
