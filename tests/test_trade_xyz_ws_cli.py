from __future__ import annotations

from pathlib import Path

from support.cli import invoke_cli
from support.cli import normalized_stdout


def _write_registry(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        (
            '[{"venue":"trade_xyz","canonical_symbol":"SP500","venue_symbol":"SP500","asset_class":"index",'
            '"dex":"xyz","coin":"xyz:SP500","asset_id":130001,"real_market_symbol":"SPY",'
            '"api_readable":true,"api_orderable":true,"active":true}]'
        ),
        encoding="utf-8",
    )


def test_collect_trade_xyz_ws_dry_run(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    _write_registry(registry)
    result = invoke_cli(
        [
            "collect-trade-xyz-ws",
            "--registry-path",
            str(registry),
            "--dry-run",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )
    stdout = normalized_stdout(result)
    assert result.exit_code == 0
    assert "dry_run=true" in stdout
    assert "ws_url=" in stdout
    assert "subscriptions=" in stdout
    assert "output_dir=" in stdout


def test_collect_trade_xyz_ws_rejects_invalid_subscription(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"
    registry = data_dir / "registry/trade_xyz_instrument_registry.json"
    _write_registry(registry)
    result = invoke_cli(
        [
            "collect-trade-xyz-ws",
            "--registry-path",
            str(registry),
            "--subscriptions",
            "bbo,invalid",
            "--dry-run",
        ],
        env={"SIS_DATA_DIR": str(data_dir)},
    )
    stdout = normalized_stdout(result)
    assert result.exit_code == 2
    assert "unsupported subscriptions" in stdout
