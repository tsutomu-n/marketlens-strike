from __future__ import annotations

from collections.abc import Sequence

import click
from click.testing import Result
from typer.testing import CliRunner

from sis.cli import app

CLI_TEST_ENV = {
    "COLUMNS": "120",
    "LINES": "40",
    "NO_COLOR": "1",
    "TERM": "dumb",
    "TTY_COMPATIBLE": "0",
    "TTY_INTERACTIVE": "0",
}


def invoke_cli(args: Sequence[str]) -> Result:
    return CliRunner().invoke(
        app,
        list(args),
        env=CLI_TEST_ENV,
        terminal_width=120,
        color=False,
    )


def normalized_stdout(result: Result) -> str:
    return click.unstyle(result.stdout).replace("\r\n", "\n")


def normalized_output(result: Result) -> str:
    return click.unstyle(result.output).replace("\r\n", "\n")
