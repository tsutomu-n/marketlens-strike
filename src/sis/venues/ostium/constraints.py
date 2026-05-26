from __future__ import annotations

import hashlib
import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from sis.storage.jsonl_store import write_json

DEFAULT_LATEST_PRICES_ENDPOINT = "https://api.ostium.io/PricePublish/latest-prices"
DEFAULT_LATEST_PRICE_ENDPOINT = "https://api.ostium.io/PricePublish/latest-price"
DEFAULT_TRADING_HOURS_ENDPOINT = "https://api.ostium.io/trading-hours/asset-schedule"
COLLECTOR_VERSION = "ostium_read_only_constraints_v1"


def _sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


def _schema_shape(value: Any) -> Any:
    if isinstance(value, list):
        return [_schema_shape(value[0])] if value else []
    if isinstance(value, dict):
        return {key: _schema_shape(value[key]) for key in sorted(value)}
    return type(value).__name__


def _raw_envelope(*, endpoint: str, payload: Any, source: str) -> dict[str, Any]:
    return {
        "recv_ts_ms": int(datetime.now(timezone.utc).timestamp() * 1000),
        "source_ts": None,
        "source": source,
        "source_endpoint": endpoint,
        "body_digest": _sha256_json(payload),
        "schema_digest": _sha256_json(_schema_shape(payload)),
        "collector_version": COLLECTOR_VERSION,
        "raw": payload,
    }


def _fetch_json(client: httpx.Client, endpoint: str, *, params: dict[str, str] | None = None) -> Any:
    response = client.get(endpoint, params=params)
    response.raise_for_status()
    return response.json()


def _sdk_status() -> dict[str, Any]:
    try:
        version = importlib.metadata.version("ostium-python-sdk")
    except importlib.metadata.PackageNotFoundError:
        return {
            "available": False,
            "version": None,
            "status": "missing_dependency",
            "notes": ["install ostium-python-sdk for Python SDK read-only evidence"],
        }
    return {
        "available": True,
        "version": version,
        "status": "available",
        "notes": ["python_sdk_dependency_available", "private_key_not_used"],
    }


def _price_items(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    prices = payload.get("prices", payload.get("data", payload))
    if isinstance(prices, list):
        return [item for item in prices if isinstance(item, dict)]
    if isinstance(prices, dict):
        result = []
        for key, value in prices.items():
            if isinstance(value, dict):
                row = dict(value)
                row.setdefault("asset", key)
                result.append(row)
        return result
    return []


def _asset_status(asset: str, latest_prices_payload: Any, trading_hours_payload: Any) -> dict[str, Any]:
    items = _price_items(latest_prices_payload)
    item = next(
        (
            row
            for row in items
            if str(row.get("asset") or row.get("pair") or row.get("symbol") or "").upper()
            in {asset.upper(), asset.replace("/", "-").upper()}
        ),
        {},
    )
    is_market_open = item.get("isMarketOpen")
    is_day_trading_closed = item.get("isDayTradingClosed")
    if is_market_open is False or is_day_trading_closed is True:
        market_state = "closed"
    elif is_market_open is True:
        market_state = "open"
    else:
        market_state = "unknown"
    return {
        "asset": asset,
        "market_state": market_state,
        "market_close_is_missing_data": False,
        "oracle_ts_ms": item.get("timestampSeconds"),
        "has_bid_ask": item.get("bid") is not None and item.get("ask") is not None,
        "latest_price_observed": bool(item),
        "trading_hours_observed": trading_hours_payload is not None,
        "is_market_open": is_market_open,
        "is_day_trading_closed": is_day_trading_closed,
    }


def write_ostium_constraint_artifact(
    *,
    data_dir: Path,
    run_id: str,
    assets: tuple[str, ...] = ("SPX", "NDX", "XAU"),
    latest_prices_endpoint: str = DEFAULT_LATEST_PRICES_ENDPOINT,
    latest_price_endpoint: str = DEFAULT_LATEST_PRICE_ENDPOINT,
    trading_hours_endpoint: str = DEFAULT_TRADING_HOURS_ENDPOINT,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20)
    day = datetime.now(timezone.utc).date().isoformat()
    root = data_dir / "raw/sidecar/ostium-constraints" / day
    try:
        latest_prices = _fetch_json(http_client, latest_prices_endpoint)
        write_json(
            root / f"{run_id}_latest_prices.json",
            _raw_envelope(
                endpoint=latest_prices_endpoint,
                payload=latest_prices,
                source="ostium_latest_prices_v1",
            ),
        )

        asset_payloads: dict[str, Any] = {}
        trading_hours_payloads: dict[str, Any] = {}
        for asset in assets:
            asset_payloads[asset] = _fetch_json(http_client, latest_price_endpoint, params={"asset": asset})
            trading_hours_payloads[asset] = _fetch_json(
                http_client,
                trading_hours_endpoint,
                params={"asset": asset},
            )
            write_json(
                root / f"{run_id}_latest_price_{asset}.json",
                _raw_envelope(
                    endpoint=latest_price_endpoint,
                    payload=asset_payloads[asset],
                    source="ostium_latest_price_asset_v1",
                ),
            )
            write_json(
                root / f"{run_id}_trading_hours_{asset}.json",
                _raw_envelope(
                    endpoint=trading_hours_endpoint,
                    payload=trading_hours_payloads[asset],
                    source="ostium_trading_hours_v1",
                ),
            )
    finally:
        if owns_client:
            http_client.close()

    sdk = _sdk_status()
    asset_statuses = [
        _asset_status(asset, latest_prices, trading_hours_payloads.get(asset)) for asset in assets
    ]
    failures = []
    if not sdk["available"]:
        failures.append("python_sdk_read_only_unavailable")
    if any(not item["latest_price_observed"] for item in asset_statuses):
        failures.append("latest_price_missing_for_asset")
    if any(not item["trading_hours_observed"] for item in asset_statuses):
        failures.append("trading_hours_missing_for_asset")

    artifact = {
        "run_id": run_id,
        "venue": "ostium",
        "collector_version": COLLECTOR_VERSION,
        "source": "ostium_read_only_constraints_v1",
        "python_sdk": sdk,
        "slippage_rule": {
            "non_market_open_trade_slippage_required": 0,
            "status": "execution_constraint_documented",
            "tested_by_trade": False,
        },
        "assets": asset_statuses,
        "constraint_status": "pass" if not failures else "failed",
        "failures": failures,
    }
    artifact_path = root / f"{run_id}.json"
    write_json(artifact_path, artifact)
    summary_path = data_dir / "ops" / f"ostium_constraints_{run_id}.json"
    write_json(
        summary_path,
        {
            **artifact,
            "artifact_path": str(artifact_path),
            "summary_path": str(summary_path),
        },
    )
    return {**artifact, "artifact_path": str(artifact_path), "summary_path": str(summary_path)}

