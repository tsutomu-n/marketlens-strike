from __future__ import annotations

import typer


def alert_output_text(rendered_text: str) -> str:
    return rendered_text


def echo_alert_output(rendered_text: str) -> None:
    typer.echo(alert_output_text(rendered_text))
