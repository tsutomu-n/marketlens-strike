from __future__ import annotations

import pytest
from pydantic import ValidationError

from sis.research.hypothesis.data_source_contracts import DataSourceRegistry
from sis.research.hypothesis.data_source_loader import load_data_source_registry
from research.helpers import CONFIG_DIR


def test_data_source_contract_separates_ndx_qqq_and_nq_responsibilities() -> None:
    registry = load_data_source_registry(CONFIG_DIR / "data_sources.yaml")

    assert registry.sources["QQQ"].default_proxy_for == [
        "actual_open_gap",
        "open_to_close_outcome",
    ]
    assert registry.sources["NQ"].source_tier == "optional_provider_dependent"
    assert registry.sources["NDX"].source_tier == "deferred"


def test_data_source_contract_rejects_unknown_tier() -> None:
    with pytest.raises(ValidationError):
        DataSourceRegistry.model_validate(
            {
                "schema_version": "research_data_sources.v1",
                "sources": {
                    "QQQ": {
                        "description": "proxy",
                        "source_tier": "required",
                        "default_proxy_for": ["actual_open_gap"],
                    }
                },
            }
        )
