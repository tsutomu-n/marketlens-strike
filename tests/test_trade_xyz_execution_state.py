from __future__ import annotations

from pathlib import Path

from sis.commands.execution_artifacts import _write_execution_snapshot
from sis.venues.trade_xyz.execution_state import build_trade_xyz_execution_state_surface


class FakeExecutionStateClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.closed = False

    def clearinghouse_state(self, user: str) -> dict:
        self.calls.append(f"clearinghouse_state:{user}")
        return {
            "marginSummary": {
                "accountValue": "1200.5",
                "totalRawUsd": "1180.0",
                "totalMarginUsed": "125.25",
                "totalNtlPos": "2500.0",
            },
            "withdrawable": "1000.0",
            "assetPositions": [
                {
                    "position": {
                        "coin": "xyz:NVDA",
                        "szi": "2",
                        "positionValue": "1000",
                        "unrealizedPnl": "10.5",
                        "returnOnEquity": "0.02",
                        "leverage": {"value": "2"},
                        "liquidationPx": "75",
                        "maxLeverage": 5,
                        "marginUsed": "125.25",
                        "cumFunding": {"allTime": "1.25"},
                    }
                }
            ],
            "time": 1780000000000,
        }

    def open_orders(self, user: str) -> list[dict]:
        self.calls.append(f"open_orders:{user}")
        return [{"oid": 42, "coin": "xyz:NVDA", "status": "open"}]

    def user_fills(self, user: str) -> list[dict]:
        self.calls.append(f"user_fills:{user}")
        return [{"hash": "fill-1", "oid": 42, "coin": "xyz:NVDA", "side": "B"}]

    def close(self) -> None:
        self.closed = True


def _write_registry(data_dir: Path) -> None:
    registry_path = data_dir / "registry/trade_xyz_instrument_registry.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("[]", encoding="utf-8")


def test_trade_xyz_execution_state_surface_requires_public_user_address(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS", raising=False)
    monkeypatch.delenv("SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS", raising=False)
    _write_registry(tmp_path)

    surface = build_trade_xyz_execution_state_surface(tmp_path)

    assert surface["venue"] == "trade_xyz"
    assert surface["registry_exists"] is True
    assert surface["collector_status"] == "not_connected"
    assert surface["collector_reason"] == "trade_xyz_execution_state_user_address_missing"
    assert surface["required_env"] == [
        "SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS",
        "SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS",
    ]
    assert surface["external_api_used"] is False
    assert surface["wallet_used"] is False
    assert surface["signing_used"] is False
    assert surface["exchange_write_used"] is False


def test_trade_xyz_execution_state_surface_is_opt_in_before_network(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS", "0xabc")
    monkeypatch.delenv("SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED", raising=False)
    client = FakeExecutionStateClient()

    surface = build_trade_xyz_execution_state_surface(tmp_path, client=client)

    assert surface["collector_status"] == "not_connected"
    assert surface["collector_reason"] == "trade_xyz_execution_state_collector_opt_in_required"
    assert surface["user_address_configured"] is True
    assert surface["user_address_sha256"]
    assert client.calls == []
    assert surface["external_api_used"] is False


def test_trade_xyz_execution_state_surface_collects_read_only_state(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS", "0xabc")
    monkeypatch.setenv("SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED", "1")
    client = FakeExecutionStateClient()

    surface = build_trade_xyz_execution_state_surface(tmp_path, client=client)

    assert client.calls == [
        "clearinghouse_state:0xabc",
        "open_orders:0xabc",
        "user_fills:0xabc",
    ]
    assert surface["collector_status"] == "connected"
    assert surface["collector_reason"] is None
    assert surface["balance_snapshot_exists"] is True
    assert surface["positions_snapshot_exists"] is True
    assert surface["fills_snapshot_exists"] is True
    assert surface["order_status_snapshot_exists"] is True
    assert surface["positions_count"] == 1
    assert surface["fills_count"] == 1
    assert surface["order_status_count"] == 1
    assert surface["equity"] == 1200.5
    assert surface["available_cash"] == 1000.0
    assert surface["margin_used"] == 125.25
    assert surface["notional_usd"] == 2500.0
    assert surface["unrealized_pnl"] == 10.5
    assert surface["positions_notional_usd_total"] == 1000.0
    assert surface["positions_average_leverage"] == 2.0
    assert surface["latest_order_id"] == "42"
    assert surface["latest_order_status"] == "open"
    assert surface["latest_fill_id"] == "fill-1"
    assert surface["request_metadata"] == [
        {
            "endpoint_type": "info",
            "request_type": "clearinghouseState",
            "row_count": 1,
            "rate_limit_weight_assumption": "unknown_info_endpoint_weight",
        },
        {
            "endpoint_type": "info",
            "request_type": "openOrders",
            "row_count": 1,
            "rate_limit_weight_assumption": "unknown_info_endpoint_weight",
        },
        {
            "endpoint_type": "info",
            "request_type": "userFills",
            "row_count": 1,
            "rate_limit_weight_assumption": "unknown_info_endpoint_weight",
        },
    ]
    assert surface["external_api_used"] is True
    assert surface["wallet_used"] is False
    assert surface["signing_used"] is False
    assert surface["exchange_write_used"] is False


def test_trade_xyz_execution_state_surface_classifies_api_error(tmp_path, monkeypatch) -> None:
    class ErrorClient(FakeExecutionStateClient):
        def clearinghouse_state(self, user: str) -> dict:
            raise TimeoutError("timeout")

    monkeypatch.setenv("SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS", "0xabc")
    monkeypatch.setenv("SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED", "1")

    surface = build_trade_xyz_execution_state_surface(tmp_path, client=ErrorClient())

    assert surface["collector_status"] == "unavailable"
    assert surface["collector_reason"] == "trade_xyz_execution_state_collector_timeout"
    assert surface["error_class"] == "timeout"
    assert surface["external_api_used"] is True


def test_execution_snapshot_writer_reports_trade_xyz_missing_user_address(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS", raising=False)
    monkeypatch.delenv("SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS", raising=False)
    monkeypatch.delenv("SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED", raising=False)
    _write_registry(tmp_path)

    _out, summary_out, report = _write_execution_snapshot(tmp_path)

    assert "snapshot_reason: trade_xyz_execution_state_user_address_missing" in report
    payload = summary_out.read_text(encoding="utf-8")
    assert (
        '"execution_snapshot_reason": "trade_xyz_execution_state_user_address_missing"' in payload
    )
    assert '"external_api_used": false' in payload
    assert '"wallet_used": false' in payload
    assert '"signing_used": false' in payload
    assert '"exchange_write_used": false' in payload
