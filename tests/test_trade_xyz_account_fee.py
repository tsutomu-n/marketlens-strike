from datetime import UTC, datetime
from pathlib import Path

from jsonschema import validate
from typer.testing import CliRunner

from sis.cli import app
from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.account_fee import collect_trade_xyz_account_fee_snapshot


class FakeTradeXyzClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.requests: list[str] = []

    def user_fees(self, user: str) -> dict:
        self.requests.append(user)
        return self.payload


def test_collect_trade_xyz_account_fee_snapshot_writes_redacted_manifest(tmp_path) -> None:
    data_dir = tmp_path / "data"
    client = FakeTradeXyzClient(
        {
            "dailyUserVlm": [{"date": "2026-05-31", "userCross": "1", "userAdd": "2"}],
            "feeSchedule": {"cross": "0.00045", "add": "0.00015"},
            "userCrossRate": "0.000315",
            "userAddRate": "0.000105",
            "activeReferralDiscount": "0.0",
            "activeStakingDiscount": {"bpsOfMaxSupply": "4.7", "discount": "0.3"},
        }
    )

    manifest = collect_trade_xyz_account_fee_snapshot(
        data_dir=data_dir,
        user_address="0xABC",
        client=client,  # type: ignore[arg-type]
        snapshot_ts=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert client.requests == ["0xabc"]
    assert manifest["status"] == "pass"
    assert manifest["parsed"]["user_taker_fee_bps"] == 3.15
    assert manifest["parsed"]["user_maker_fee_bps"] == 1.05
    assert manifest["parsed"]["active_staking_discount"] == 0.3
    assert "0xABC" not in str(manifest)
    assert "0xabc" not in str(manifest)
    raw_artifact_path = Path(manifest["raw_artifact_path"])
    assert raw_artifact_path.exists()
    raw_artifact = read_json(raw_artifact_path)
    assert "payload" in raw_artifact
    assert "0xABC" not in str(raw_artifact)
    assert "0xabc" not in str(raw_artifact)
    validate(manifest, read_json(Path("schemas/trade_xyz_account_fee_manifest.v1.schema.json")))


def test_collect_trade_xyz_account_fee_cli_help_includes_read_only_command() -> None:
    result = CliRunner().invoke(app, ["collect-trade-xyz-account-fee", "--help"])

    assert result.exit_code == 0
    assert "--user-address" in result.stdout
    assert "Public Hyperliquid user address" in result.stdout
