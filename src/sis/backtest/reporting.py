from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable


def write_markdown_report(path: Path, lines: Iterable[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def bool_line(label: str, value: bool) -> str:
    return f"- {label}: {str(value).lower()}"


def kv_line(label: str, value: Any) -> str:
    return f"- {label}: {value}"
