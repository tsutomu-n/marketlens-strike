from __future__ import annotations

import pytest
from pydantic import ValidationError

from sis.research.hypothesis.scope_contracts import ResearchScope
from sis.research.hypothesis.scope_loader import load_scope
from research.helpers import CONFIG_DIR


def test_scope_config_loads_and_excludes_order_paths() -> None:
    scope = load_scope(CONFIG_DIR / "scope.yaml")

    assert scope.included.primary == ["NDX", "QQQ"]
    assert "TradeXYZ_order_execution" in scope.excluded
    assert "live_trading" in scope.excluded
    assert scope.policy.external_api_allowed is False


def test_scope_rejects_empty_included_or_excluded() -> None:
    with pytest.raises(ValidationError):
        ResearchScope.model_validate(
            {
                "schema_version": "research_scope.v1",
                "scope_id": "S",
                "name": "bad",
                "included": {"primary": []},
                "excluded": [],
            }
        )
