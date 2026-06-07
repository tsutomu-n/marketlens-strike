from __future__ import annotations

import pytest
from pydantic import ValidationError

from sis.research.hypothesis.variable_contracts import VariableInventory
from sis.research.hypothesis.variable_loader import load_variable_inventory
from research.helpers import CONFIG_DIR


def test_variable_inventory_loads_initial_variables() -> None:
    inventory = load_variable_inventory(CONFIG_DIR / "variable_inventory.yaml")

    assert inventory.variables["qqq_open_to_close_return"].temporal_class == "t_after_close"
    assert inventory.variables["open_gap_residual"].role_candidates == ["treatment_candidate"]


def test_variable_inventory_rejects_missing_lineage_and_unknown_temporal_class() -> None:
    with pytest.raises(ValidationError):
        VariableInventory.model_validate(
            {
                "schema_version": "research_variable_inventory.v1",
                "variables": {
                    "x": {
                        "temporal_class": "t_after_open",
                        "role_candidates": ["observed_proxy"],
                    }
                },
            }
        )


def test_variable_inventory_loader_rejects_duplicate_yaml_variable_id(tmp_path) -> None:
    path = tmp_path / "variable_inventory.yaml"
    path.write_text(
        "\n".join(
            [
                "schema_version: research_variable_inventory.v1",
                "variables:",
                "  x:",
                "    source_symbol: QQQ",
                "    temporal_class: t_after_open",
                "    role_candidates:",
                "      - observed_proxy",
                "  x:",
                "    source_symbol: SPY",
                "    temporal_class: t_after_open",
                "    role_candidates:",
                "      - observed_proxy",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="duplicate key"):
        load_variable_inventory(path)
    with pytest.raises(ValidationError):
        VariableInventory.model_validate(
            {
                "schema_version": "research_variable_inventory.v1",
                "variables": {
                    "x": {
                        "source_symbol": "QQQ",
                        "temporal_class": "tomorrow",
                        "role_candidates": ["observed_proxy"],
                    }
                },
            }
        )
