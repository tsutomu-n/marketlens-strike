from __future__ import annotations

import ast
from pathlib import Path


def test_required_columns_delegates_multi_leg_column_collection() -> None:
    path = Path("src/sis/research/strategy_lab/authoring/required_columns.py")
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    direct_leg_references = [
        node.attr
        for node in ast.walk(module)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "leg"
    ]

    assert direct_leg_references == []
