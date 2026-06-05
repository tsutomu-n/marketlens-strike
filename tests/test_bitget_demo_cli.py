from __future__ import annotations

from pathlib import Path

from sis.storage.jsonl_store import read_json
from support.cli import invoke_cli, normalized_stdout


def test_bitget_demo_smoke_blocks_without_credentials(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    result = invoke_cli(
        ["bitget-demo-smoke"],
        env={
            "SIS_DATA_DIR": str(data_dir),
            "BITGET_DEMO_API_KEY": "",
            "BITGET_DEMO_API_SECRET": "",
            "BITGET_DEMO_PASSPHRASE": "",
        },
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 2
    assert "status=blocked" in stdout
    assert "venue=bitget_demo" in stdout
    assert "available=False" in stdout
    assert "credential_status=missing" in stdout
    assert (
        "missing_env=BITGET_DEMO_API_KEY,BITGET_DEMO_API_SECRET,BITGET_DEMO_PASSPHRASE"
    ) in stdout
    assert "paptrading_header=paptrading=1" in stdout
    assert "external_write_enabled=False" in stdout
    assert "exchange_write_used=False" in stdout

    summary_path = data_dir / "ops/bitget_demo_smoke_summary.json"
    report_path = data_dir / "reports/bitget_demo_smoke.md"
    assert summary_path.exists()
    assert report_path.exists()
    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    assert summary["schema_version"] == "bitget_demo_smoke_summary.v1"
    assert summary["status"] == "blocked"
    assert summary["external_write_enabled"] is False
    assert summary["exchange_write_used"] is False


def test_bitget_demo_smoke_configured_with_demo_credentials(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    result = invoke_cli(
        ["bitget-demo-smoke"],
        env={
            "SIS_DATA_DIR": str(data_dir),
            "BITGET_DEMO_API_KEY": "key",
            "BITGET_DEMO_API_SECRET": "secret",
            "BITGET_DEMO_PASSPHRASE": "passphrase",
        },
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "status=configured" in stdout
    assert "available=True" in stdout
    assert "credential_status=present" in stdout
    assert "missing_env=" in stdout
    assert "secret" not in stdout
    summary = read_json(data_dir / "ops/bitget_demo_smoke_summary.json")
    assert isinstance(summary, dict)
    assert summary["status"] == "configured"
    assert summary["read_only_network_probe"] == "not_executed"
