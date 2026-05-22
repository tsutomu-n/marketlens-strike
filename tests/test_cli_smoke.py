from typer.testing import CliRunner

from sis.cli import app


runner = CliRunner()


def test_help_smoke() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "probe" in result.stdout
    assert "build-backtest" in result.stdout
    assert "log-quotes" in result.stdout


def test_check_timeframe_cli_blocks_scalping() -> None:
    result = runner.invoke(app, ["check-timeframe", "1m"])
    assert result.exit_code == 2
    assert "BLOCK_SCALPING_TIMEFRAME" in result.stdout


def test_implementation_status_reports_complete_scope() -> None:
    result = runner.invoke(app, ["implementation-status"])
    assert result.exit_code == 0
    assert "Backtest bridge" in result.stdout
    assert "Ostium liquidation reference" in result.stdout
    assert "PARTIAL" not in result.stdout


def test_diagnose_quotes_exits_when_no_quotes() -> None:
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["diagnose-quotes"], env={"SIS_DATA_DIR": "tmp_data"})
        assert result.exit_code == 2
        assert "No quote rows found for diagnostics." in result.stdout


def test_market_session_cli_for_qqq() -> None:
    result = runner.invoke(app, ["market-session", "--venue", "gtrade", "--symbol", "QQQ"])
    assert result.exit_code == 0
    assert "symbol=QQQ" in result.stdout
    assert "calendar=XNYS" in result.stdout
    assert "next_open_jst=" in result.stdout


def test_next_live_window_cli_for_xau() -> None:
    result = runner.invoke(app, ["next-live-window", "--venue", "gtrade", "--symbol", "XAU"])
    assert result.exit_code == 0
    assert "symbol=XAU" in result.stdout
    assert "calendar=GTRADE_COMMODITY" in result.stdout
    assert "recommended_start_jst=" in result.stdout
