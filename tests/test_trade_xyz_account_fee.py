from datetime import UTC, datetime
from pathlib import Path

from jsonschema import validate

from sis.storage.jsonl_store import read_json
from sis.venues.trade_xyz.account_fee import collect_trade_xyz_account_fee_snapshot
from support.cli import invoke_cli
from support.cli import normalized_stdout

TEST_USER_ADDRESS = "0x1111111111111111111111111111111111111111"


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
        user_address=TEST_USER_ADDRESS,
        client=client,  # type: ignore[arg-type]
        snapshot_ts=datetime(2026, 5, 31, tzinfo=UTC),
    )

    assert client.requests == [TEST_USER_ADDRESS]
    assert manifest["status"] == "pass"
    assert manifest["parsed"]["user_taker_fee_bps"] == 3.15
    assert manifest["parsed"]["user_maker_fee_bps"] == 1.05
    assert manifest["parsed"]["active_staking_discount"] == 0.3
    assert TEST_USER_ADDRESS not in str(manifest)
    raw_artifact_path = Path(manifest["raw_artifact_path"])
    assert raw_artifact_path.exists()
    raw_artifact = read_json(raw_artifact_path)
    assert "payload" in raw_artifact
    assert TEST_USER_ADDRESS not in str(raw_artifact)
    validate(manifest, read_json(Path("schemas/trade_xyz_account_fee_manifest.v1.schema.json")))


def test_collect_trade_xyz_account_fee_snapshot_rejects_invalid_address(tmp_path) -> None:
    data_dir = tmp_path / "data"
    client = FakeTradeXyzClient({"userCrossRate": "0.000315", "userAddRate": "0.000105"})

    try:
        collect_trade_xyz_account_fee_snapshot(
            data_dir=data_dir,
            user_address="0xABC",
            client=client,  # type: ignore[arg-type]
            snapshot_ts=datetime(2026, 5, 31, tzinfo=UTC),
        )
    except ValueError as exc:
        assert "42-character 0x-prefixed hexadecimal address" in str(exc)
    else:  # pragma: no cover - defensive assertion shape
        raise AssertionError("expected invalid address to be rejected")
    assert client.requests == []


def test_collect_trade_xyz_account_fee_cli_help_includes_read_only_command() -> None:
    result = invoke_cli(["collect-trade-xyz-account-fee", "--help"])
    stdout = normalized_stdout(result)

    assert result.exit_code == 0
    assert "--user-address" in stdout
    assert "Public Hyperliquid user address" in stdout
