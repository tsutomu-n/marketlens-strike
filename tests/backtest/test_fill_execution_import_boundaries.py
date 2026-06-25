from __future__ import annotations

import ast
from pathlib import Path


def _imported_names(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
    return names


def test_runner_delegates_fill_execution_details() -> None:
    runner_imports = _imported_names(Path("src/sis/backtest/engine/runner.py"))
    execution_imports = _imported_names(Path("src/sis/backtest/engine/run_execution.py"))
    pending_fill_imports = _imported_names(
        Path("src/sis/backtest/engine/pending_fill_execution.py")
    )

    assert "execute_backtest_rows" in runner_imports
    assert "_apply_pending_order_fill" not in runner_imports
    assert "_apply_pending_order_fill" in execution_imports
    assert "_fill_order" not in runner_imports
    assert "resolve_market_like_fill_price" not in runner_imports
    assert "calculate_market_like_fee" not in runner_imports
    assert "evaluate_open_fill_gate" not in runner_imports
    assert "evaluate_close_fill_gate" not in runner_imports
    assert "_fill_order" in pending_fill_imports
