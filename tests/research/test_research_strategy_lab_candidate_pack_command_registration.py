from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.research_strategy_lab_candidate_pack import (
    register_research_strategy_lab_candidate_pack_commands,
)
from support.cli import normalized_stdout


def test_research_strategy_lab_candidate_pack_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_research_strategy_lab_candidate_pack_commands(app)

    result = CliRunner().invoke(app, ["build-paper-candidate-pack", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "build-paper-candidate-pack" in stdout
    assert "--trial-ledger" in stdout
    assert "--trial-group-id" in stdout
