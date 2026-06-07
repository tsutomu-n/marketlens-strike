from __future__ import annotations

from sis.research.dag.data_requirements import build_data_requirements
from sis.research.dag.loader import load_core_dag
from sis.research.hypothesis.variable_loader import load_variable_inventory
from research.helpers import CONFIG_DIR


def test_data_requirements_include_known_factor_sources_without_fetching_data() -> None:
    dag = load_core_dag(CONFIG_DIR / "core_dag.yaml")
    inventory = load_variable_inventory(CONFIG_DIR / "variable_inventory.yaml")

    requirements = build_data_requirements(dag, inventory)
    source_symbols = {item.source_symbol for item in requirements}

    assert {"QQQ", "SPY", "SMH", "VIX", "DGS10"} <= source_symbols
    assert "AAPL_MSFT_NVDA_AMZN_META_GOOGL_AVGO" in source_symbols
