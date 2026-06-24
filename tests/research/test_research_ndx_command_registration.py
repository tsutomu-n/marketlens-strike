from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.research_ndx import register_research_ndx_commands
from support.cli import normalized_stdout


def test_research_ndx_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_research_ndx_commands(app)

    result = CliRunner().invoke(app, ["research-ndx-source-resolve", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0, result.stdout
    assert "research-ndx-source-resolve" in stdout
    assert "--artifact-dir" in stdout
