from __future__ import annotations

import typer
from typer.testing import CliRunner

from sis.commands.research_strategy_lab import register_research_strategy_lab_commands
from support.cli import normalized_stdout


def test_research_strategy_lab_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_research_strategy_lab_commands(app, recommended_read_order_fn=lambda _: [])

    result = CliRunner().invoke(app, ["evaluate-strategy-lab", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0, result.stdout
    assert "evaluate-strategy-lab" in stdout
    assert "--rank-thresholds" in stdout
