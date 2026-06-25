from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import typer


def recommended_read_order_lines(
    data_dir: Path,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> list[str]:
    return [
        f"recommended_read_order_{index}={item}"
        for index, item in enumerate(recommended_read_order_fn(data_dir), start=1)
    ]


def echo_recommended_read_order(
    data_dir: Path,
    recommended_read_order_fn: Callable[[Path], list[str]],
) -> None:
    for line in recommended_read_order_lines(data_dir, recommended_read_order_fn):
        typer.echo(line)
