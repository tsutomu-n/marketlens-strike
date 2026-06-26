from __future__ import annotations

from typing import Any

import typer


def kill_switch_status_lines(status: dict[str, Any]) -> list[str]:
    return [
        f"enabled={status.get('enabled')}",
        f"path={status.get('path')}",
    ]


def echo_kill_switch_status(status: dict[str, Any]) -> None:
    for line in kill_switch_status_lines(status):
        typer.echo(line)
