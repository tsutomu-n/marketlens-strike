from __future__ import annotations

import pytest
from pydantic import ValidationError

from sis.research.hypothesis.temporal_contracts import TemporalAvailability
from sis.research.hypothesis.temporal_validator import forbidden_layer_edge_pairs
from sis.research.hypothesis.yaml_io import load_yaml_mapping
from research.helpers import CONFIG_DIR


def test_temporal_availability_loads_forbidden_future_to_signal_rule() -> None:
    temporal = TemporalAvailability.model_validate(
        load_yaml_mapping(CONFIG_DIR / "temporal_availability.yaml")
    )

    assert temporal.layer_for_variable("qqq_open_to_close_return") == "t_after_close"
    assert temporal.layer_for_variable("open_gap_residual") == "t_after_open"
    assert ("t_after_close", "t_after_open") in forbidden_layer_edge_pairs(temporal)


def test_temporal_availability_rejects_unknown_layer_and_duplicate_variable() -> None:
    with pytest.raises(ValidationError):
        TemporalAvailability.model_validate(
            {"schema_version": "research_temporal_availability.v1", "layers": {"bad": ["x"]}}
        )

    with pytest.raises(ValidationError):
        TemporalAvailability.model_validate(
            {
                "schema_version": "research_temporal_availability.v1",
                "layers": {
                    "t_pre_open": ["x"],
                    "t_after_open": ["x"],
                },
            }
        )
