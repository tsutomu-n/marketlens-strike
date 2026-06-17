from __future__ import annotations

from pathlib import Path

from sis.storage.jsonl_store import read_json
from support.cli import invoke_cli
from support.cli import normalized_stdout


def test_venue_read_only_probe_cli_writes_fixture_only_artifacts(tmp_path: Path) -> None:
    data_dir = tmp_path / "data"

    result = invoke_cli(
        ["venue-read-only-probe"],
        env={
            "SIS_DATA_DIR": str(data_dir),
            "BITGET_DEMO_API_KEY": "",
            "BITGET_DEMO_API_SECRET": "super-secret-value",
            "BITGET_DEMO_PASSPHRASE": "super-passphrase",
            "HYPERLIQUID_PRIVATE_KEY": "super-private-key",
        },
    )
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "status=fixture_only" in stdout
    assert "venue_count=4" in stdout
    assert "external_api_used=False" in stdout
    assert "credentials_used=False" in stdout
    assert "wallet_used=False" in stdout
    assert "signing_used=False" in stdout
    assert "exchange_write_used=False" in stdout
    assert "network_attempted=False" in stdout
    assert "super-secret-value" not in stdout
    assert "super-passphrase" not in stdout
    assert "super-private-key" not in stdout

    summary_path = data_dir / "ops/venue_read_only_probe_summary.json"
    report_path = data_dir / "reports/venue_read_only_probe.md"
    assert f"summary_path={summary_path}" in stdout
    assert f"report_path={report_path}" in stdout
    assert summary_path.exists()
    assert report_path.exists()

    summary = read_json(summary_path)
    assert isinstance(summary, dict)
    assert summary["schema_version"] == "venue_read_only_probe_summary.v1"
    assert summary["status"] == "fixture_only"
    assert summary["venue_count"] == 4
    assert summary["network_attempted"] is False
    rows = {row["venue_id"]: row for row in summary["venues"]}
    assert rows["bitget_futures"]["read_only_probe_status"] == "blocked_by_capability"
    assert rows["hyperliquid_perp"]["read_only_probe_status"] == "blocked_by_capability"

    report = report_path.read_text(encoding="utf-8")
    assert "no network attempted" in report
    assert "not paper / live permission" in report
