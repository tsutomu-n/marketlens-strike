from __future__ import annotations

import typer
from typer.testing import CliRunner

from research.helpers import CONFIG_DIR
from sis.commands.research_dag import register_research_dag_commands


def test_research_dag_command_group_registers_standalone() -> None:
    app = typer.Typer(no_args_is_help=True)
    register_research_dag_commands(app)

    result = CliRunner().invoke(
        app,
        ["research-layer22-validate", "--root", str(CONFIG_DIR)],
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in result.stdout
    assert "dag_id=HYP-NDX-001" in result.stdout
