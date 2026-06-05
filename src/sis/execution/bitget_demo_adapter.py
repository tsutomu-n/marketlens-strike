from __future__ import annotations

import base64
import hashlib
import hmac
import os
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sis.execution.base import (
    AdapterActionResult,
    AdapterFillSnapshot,
    AdapterOrderEstimate,
    AdapterOrderStatus,
    AdapterPositionSnapshot,
    OrderIntent,
)

BITGET_DEMO_REQUIRED_ENV: tuple[str, ...] = (
    "BITGET_DEMO_API_KEY",
    "BITGET_DEMO_API_SECRET",
    "BITGET_DEMO_PASSPHRASE",
)
BITGET_DEMO_REST_BASE_URL = "https://api.bitget.com"
BITGET_DEMO_WS_PUBLIC_ENDPOINT = "wss://wspap.bitget.com/v2/ws/public"
BITGET_DEMO_WS_PRIVATE_ENDPOINT = "wss://wspap.bitget.com/v2/ws/private"
BITGET_DEMO_PAPER_HEADER = "paptrading"
BITGET_DEMO_PAPER_HEADER_VALUE = "1"


@dataclass(frozen=True)
class BitgetDemoCredentials:
    api_key: str
    api_secret: str
    passphrase: str


def missing_bitget_demo_env(env: Mapping[str, str] | None = None) -> list[str]:
    source = os.environ if env is None else env
    return [key for key in BITGET_DEMO_REQUIRED_ENV if not source.get(key, "").strip()]


def bitget_demo_credentials_from_env(
    env: Mapping[str, str] | None = None,
) -> BitgetDemoCredentials | None:
    source = os.environ if env is None else env
    if missing_bitget_demo_env(source):
        return None
    return BitgetDemoCredentials(
        api_key=source["BITGET_DEMO_API_KEY"].strip(),
        api_secret=source["BITGET_DEMO_API_SECRET"].strip(),
        passphrase=source["BITGET_DEMO_PASSPHRASE"].strip(),
    )


def sign_bitget_demo_request(
    *,
    api_secret: str,
    timestamp_ms: str,
    method: str,
    request_path: str,
    query_string: str = "",
    body: str = "",
) -> str:
    query = f"?{query_string}" if query_string else ""
    content = f"{timestamp_ms}{method.upper()}{request_path}{query}{body}"
    digest = hmac.new(
        api_secret.encode("utf-8"),
        content.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.b64encode(digest).decode("ascii")


def build_bitget_demo_headers(
    credentials: BitgetDemoCredentials,
    *,
    timestamp_ms: str,
    method: str,
    request_path: str,
    query_string: str = "",
    body: str = "",
) -> dict[str, str]:
    return {
        "ACCESS-KEY": credentials.api_key,
        "ACCESS-SIGN": sign_bitget_demo_request(
            api_secret=credentials.api_secret,
            timestamp_ms=timestamp_ms,
            method=method,
            request_path=request_path,
            query_string=query_string,
            body=body,
        ),
        "ACCESS-TIMESTAMP": timestamp_ms,
        "ACCESS-PASSPHRASE": credentials.passphrase,
        "Content-Type": "application/json",
        "locale": "en-US",
        BITGET_DEMO_PAPER_HEADER: BITGET_DEMO_PAPER_HEADER_VALUE,
    }


def _as_mapping(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    data = payload.get("data")
    if isinstance(data, list):
        first = data[0] if data else {}
        return first if isinstance(first, Mapping) else {}
    if isinstance(data, Mapping):
        return data
    return payload


def _optional_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def parse_bitget_demo_order_status(payload: Mapping[str, Any]) -> AdapterOrderStatus:
    row = _as_mapping(payload)
    quantity = (
        row.get("size") or row.get("quantity") or row.get("baseVolume") or row.get("filledQty")
    )
    order_id = row.get("orderId") or row.get("order_id") or row.get("clientOid")
    return AdapterOrderStatus(
        venue="bitget_demo",
        order_id=str(order_id or "unknown"),
        canonical_symbol=(
            str(row.get("symbol") or row.get("instId")).upper()
            if row.get("symbol") or row.get("instId")
            else None
        ),
        side=str(row.get("side")).lower() if row.get("side") is not None else None,
        quantity=_optional_float(quantity),
        status=str(row.get("status") or row.get("state") or "unknown"),
        notes=["bitget_demo", "parsed_response"],
    )


def parse_bitget_demo_fill(payload: Mapping[str, Any]) -> AdapterFillSnapshot:
    row = _as_mapping(payload)
    fill_id = row.get("tradeId") or row.get("fillId") or row.get("id") or row.get("orderId")
    quantity = row.get("size") or row.get("quantity") or row.get("baseVolume")
    price = row.get("price") or row.get("fillPrice")
    return AdapterFillSnapshot(
        venue="bitget_demo",
        fill_id=str(fill_id or "unknown"),
        order_id=str(row.get("orderId")) if row.get("orderId") is not None else None,
        canonical_symbol=(
            str(row.get("symbol") or row.get("instId")).upper()
            if row.get("symbol") or row.get("instId")
            else None
        ),
        side=str(row.get("side")).lower() if row.get("side") is not None else None,
        quantity=_optional_float(quantity),
        price=_optional_float(price),
        status=str(row.get("status") or row.get("state") or "unknown"),
        ts_fill=(
            str(row.get("fillTime") or row.get("cTime") or row.get("uTime"))
            if row.get("fillTime") or row.get("cTime") or row.get("uTime")
            else None
        ),
        notes=["bitget_demo", "parsed_response"],
    )


class BitgetDemoAdapter:
    adapter_name = "bitget_demo"

    def __init__(
        self,
        *,
        credentials: BitgetDemoCredentials | None,
        missing_env: list[str] | None = None,
    ) -> None:
        self._credentials = credentials
        self._missing_env = missing_env or []

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> BitgetDemoAdapter:
        source = os.environ if env is None else env
        return cls(
            credentials=bitget_demo_credentials_from_env(source),
            missing_env=missing_bitget_demo_env(source),
        )

    def read_balance(self) -> dict:
        return self.healthcheck() | {
            "balance_status": "not_read",
            "read_only_network_probe": "not_executed",
        }

    def read_positions(self) -> list[AdapterPositionSnapshot]:
        return []

    def estimate_order(self, intent: OrderIntent) -> AdapterOrderEstimate:
        return AdapterOrderEstimate(
            venue=self.adapter_name,
            canonical_symbol=intent.canonical_symbol.upper(),
            side=intent.side.lower(),
            estimated_entry_price=None,
            estimated_cost_bps=None,
            price_reference="unavailable",
            notes=[
                "bitget_demo_mock_first",
                "external_write_disabled",
                "read_only_network_probe_not_executed",
            ],
        )

    def read_order_status(self, order_id: str) -> AdapterOrderStatus:
        return AdapterOrderStatus(
            venue=self.adapter_name,
            order_id=order_id,
            canonical_symbol=None,
            side=None,
            quantity=None,
            status="read_only_not_executed",
            notes=["bitget_demo_mock_first", "external_write_disabled"],
        )

    def read_order_statuses(self, limit: int | None = None) -> list[AdapterOrderStatus]:
        del limit
        return []

    def read_fills(self, limit: int | None = None) -> list[AdapterFillSnapshot]:
        del limit
        return []

    def cancel_order(self, order_id: str) -> AdapterActionResult:
        return AdapterActionResult(
            venue=self.adapter_name,
            action="cancel_order",
            target=order_id,
            success=False,
            status="external_write_disabled",
            notes=["bitget_demo_mock_first", "no_exchange_write"],
        )

    def close_position(self, canonical_symbol: str, side: str | None = None) -> AdapterActionResult:
        target = canonical_symbol.upper()
        if side:
            target = f"{target}:{side.lower()}"
        return AdapterActionResult(
            venue=self.adapter_name,
            action="close_position",
            target=target,
            success=False,
            status="external_write_disabled",
            notes=["bitget_demo_mock_first", "no_exchange_write"],
        )

    def healthcheck(self) -> dict:
        return {
            "adapter_name": self.adapter_name,
            "venue": self.adapter_name,
            "available": self._credentials is not None,
            "credential_status": "present" if self._credentials else "missing",
            "missing_env": self._missing_env,
            "rest_base_url": BITGET_DEMO_REST_BASE_URL,
            "ws_public_endpoint": BITGET_DEMO_WS_PUBLIC_ENDPOINT,
            "ws_private_endpoint": BITGET_DEMO_WS_PRIVATE_ENDPOINT,
            "paptrading_header": f"{BITGET_DEMO_PAPER_HEADER}=1",
            "external_write_enabled": False,
            "exchange_write_used": False,
            "read_only_network_probe": "not_executed",
        }
