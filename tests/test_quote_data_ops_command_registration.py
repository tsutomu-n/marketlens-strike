from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.quotes_data_ops import register_quote_data_ops_commands
from support.cli import normalized_stdout


def test_quote_data_ops_commands_register_standalone() -> None:
    app = typer.Typer()
    register_quote_data_ops_commands(app)

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "build-trade-xyz-session-state" in stdout
    assert "collect-trade-xyz-funding-history" in stdout
    assert "build-trade-xyz-funding-events-from-history" in stdout
    assert "build-trade-xyz-data-readiness" in stdout
