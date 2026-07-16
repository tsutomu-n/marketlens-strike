from __future__ import annotations

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_SOURCE_ROOT = REPO_ROOT / "tests/fixtures/strategy_idea_seeds/a1_source_root"
MECHANISM_PACK = (
    REPO_ROOT / "configs/strategy_idea_seeds/mechanisms/crowding_volatility_release_v1.yaml"
)
OPERATOR_CATALOG = REPO_ROOT / "configs/strategy_idea_seeds/operator_catalog_v1.yaml"


@pytest.fixture
def fixture_source_root() -> Path:
    return FIXTURE_SOURCE_ROOT
