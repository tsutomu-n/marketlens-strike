from __future__ import annotations

import ast
from pathlib import Path


def test_compiler_callers_import_block_trade_row_from_trade_blocking() -> None:
    root = Path("src/sis/research/strategy_lab/authoring/compiler")
    offenders: list[str] = []
    for path in sorted(root.glob("*.py")):
        if path.name == "common.py":
            continue
        module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(module):
            if not isinstance(node, ast.ImportFrom):
                continue
            if node.module != "sis.research.strategy_lab.authoring.compiler.common":
                continue
            if any(alias.name == "_block_trade_row" for alias in node.names):
                offenders.append(str(path))

    assert offenders == []
