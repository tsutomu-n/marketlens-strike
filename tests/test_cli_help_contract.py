from __future__ import annotations

import ast
from pathlib import Path

import click
from typer.main import get_command

from sis.cli import app
from support.cli import invoke_cli
from support.cli import normalized_stdout

IMPORTANT_HELP_COMMANDS = (
    "collect-trade-xyz-account-fee",
    "collect-trade-xyz-data-cycle",
    "collect-trade-xyz-real-market-reference",
    "collect-trade-xyz-signal-candles",
    "collect-trade-xyz-historical-l2-archive",
)


def test_important_commands_help_is_renderable() -> None:
    for command in IMPORTANT_HELP_COMMANDS:
        result = invoke_cli([command, "--help"])
        stdout = normalized_stdout(result)

        assert result.exit_code == 0, command
        assert "Usage:" in stdout
        assert command in stdout


def test_collect_trade_xyz_account_fee_registers_user_address_option() -> None:
    root_command = get_command(app)
    account_fee_command = root_command.commands["collect-trade-xyz-account-fee"]
    option_names = {
        option
        for parameter in account_fee_command.params
        if isinstance(parameter, click.Option)
        for option in parameter.opts
    }

    assert "--user-address" in option_names


def test_cli_help_tests_do_not_assert_raw_stdout() -> None:
    offenders: list[str] = []
    for path in Path("tests").rglob("test_*.py"):
        if path == Path(__file__):
            continue
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            source = ast.get_source_segment(text, node) or ""
            if "--help" not in source:
                continue
            if "result.stdout" not in source and "result.output" not in source:
                continue
            if "normalized_stdout" in source or "normalized_output" in source:
                continue
            offenders.append(f"{path}:{node.lineno}")

    assert not offenders, "Use support.cli.normalized_stdout/output: " + ", ".join(offenders)
