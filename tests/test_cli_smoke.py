from typer.testing import CliRunner

from sis.cli import app


runner = CliRunner()


def test_help_smoke() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "probe" in result.stdout


def test_check_timeframe_cli_blocks_scalping() -> None:
    result = runner.invoke(app, ["check-timeframe", "1m"])
    assert result.exit_code == 2
    assert "BLOCK_SCALPING_TIMEFRAME" in result.stdout

