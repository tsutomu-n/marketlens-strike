from __future__ import annotations

import asyncio
import hashlib
import importlib
import importlib.metadata
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from sis.storage.jsonl_store import write_json
from sis.venues.archive.ostium.probe import OSTIUM_PRICES_ENDPOINT

DEFAULT_LATEST_PRICES_ENDPOINT = "https://metadata-backend.ostium.io/PricePublish/latest-prices"
DEFAULT_LATEST_PRICE_ENDPOINT = "https://metadata-backend.ostium.io/PricePublish/latest-price"
DEFAULT_TRADING_HOURS_ENDPOINT = "https://metadata-backend.ostium.io/trading-hours/asset-schedule"
DEFAULT_BUILDER_PRICES_ENDPOINT = OSTIUM_PRICES_ENDPOINT
COLLECTOR_VERSION = "ostium_read_only_constraints_v2"

ASSET_ALIASES: dict[str, dict[str, str]] = {
    "SPX": {
        "canonical_symbol": "SPX_EQUIV",
        "venue_pair": "SPX-USD",
        "legacy_asset_param": "SPXUSD",
        "from": "SPX",
        "to": "USD",
    },
    "SPX_EQUIV": {
        "canonical_symbol": "SPX_EQUIV",
        "venue_pair": "SPX-USD",
        "legacy_asset_param": "SPXUSD",
        "from": "SPX",
        "to": "USD",
    },
    "US500": {
        "canonical_symbol": "SPX_EQUIV",
        "venue_pair": "US500-USD",
        "legacy_asset_param": "US500USD",
        "from": "US500",
        "to": "USD",
    },
    "NDX": {
        "canonical_symbol": "NDX_EQUIV",
        "venue_pair": "NDX-USD",
        "legacy_asset_param": "NDXUSD",
        "from": "NDX",
        "to": "USD",
    },
    "NDX_EQUIV": {
        "canonical_symbol": "NDX_EQUIV",
        "venue_pair": "NDX-USD",
        "legacy_asset_param": "NDXUSD",
        "from": "NDX",
        "to": "USD",
    },
    "US100": {
        "canonical_symbol": "NDX_EQUIV",
        "venue_pair": "US100-USD",
        "legacy_asset_param": "US100USD",
        "from": "US100",
        "to": "USD",
    },
    "XAU": {
        "canonical_symbol": "XAU",
        "venue_pair": "XAU-USD",
        "legacy_asset_param": "XAUUSD",
        "from": "XAU",
        "to": "USD",
    },
    "XAUUSD": {
        "canonical_symbol": "XAU",
        "venue_pair": "XAU-USD",
        "legacy_asset_param": "XAUUSD",
        "from": "XAU",
        "to": "USD",
    },
}


def _asset_config(asset: str) -> dict[str, str]:
    key = asset.upper().replace("/", "").replace("-", "")
    if key in ASSET_ALIASES:
        return {"requested_asset": asset, **ASSET_ALIASES[key]}
    if key.endswith("USD") and len(key) > 3:
        base = key[:-3]
        return {
            "requested_asset": asset,
            "canonical_symbol": base,
            "venue_pair": f"{base}-USD",
            "legacy_asset_param": key,
            "from": base,
            "to": "USD",
        }
    return {
        "requested_asset": asset,
        "canonical_symbol": key,
        "venue_pair": f"{key}-USD",
        "legacy_asset_param": f"{key}USD",
        "from": key,
        "to": "USD",
    }


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


def _write_raw_artifact(path: Path, *, endpoint: str, payload: Any, source: str) -> dict[str, Any]:
    envelope = _raw_envelope(endpoint=endpoint, payload=payload, source=source)
    write_json(path, envelope)
    return {
        "path": str(path),
        "endpoint": endpoint,
        "body_digest": envelope["body_digest"],
        "schema_digest": envelope["schema_digest"],
    }


def _fetch_json(client: httpx.Client, endpoint: str, *, params: dict[str, str] | None = None) -> Any:
    response = client.get(endpoint, params=params)
    response.raise_for_status()
    return response.json()


def _fetch_json_or_error(client: httpx.Client, endpoint: str, *, params: dict[str, str] | None = None) -> Any:
    try:
        return _fetch_json(client, endpoint, params=params)
    except httpx.HTTPError as exc:
        return {
            "fetch_status": "failed",
            "error": str(exc),
            "endpoint": endpoint,
            "params": params or {},
        }


def _is_fetch_error(payload: Any) -> bool:
    return isinstance(payload, dict) and payload.get("fetch_status") == "failed"


async def _call_async_or_value(value: Any) -> Any:
    if hasattr(value, "__await__"):
        return await value
    return value


async def _run_sdk_read_only_probe() -> dict[str, Any]:
    version = importlib.metadata.version("ostium-python-sdk")
    module = importlib.import_module("ostium_python_sdk")
    sdk_cls = getattr(module, "OstiumSDK")
    network_config = getattr(module, "NetworkConfig")
    config = network_config.mainnet() if hasattr(network_config, "mainnet") else network_config.testnet()
    sdk = sdk_cls(config)

    if getattr(sdk, "price", None) is not None and hasattr(sdk.price, "get_latest_prices"):
        payload = await _call_async_or_value(sdk.price.get_latest_prices())
        count = len(payload) if isinstance(payload, list) else None
        return {
            "available": True,
            "version": version,
            "status": "read_only_probe_passed",
            "method": "price.get_latest_prices",
            "observed_count": count,
            "private_key_used": False,
            "notes": ["python_sdk_read_only_probe_passed", "private_key_not_used"],
        }

    if hasattr(sdk, "get_formatted_pairs_details"):
        payload = await _call_async_or_value(
            sdk.get_formatted_pairs_details(including_current_price_and_market_status=True)
        )
        count = len(payload) if isinstance(payload, list) else None
        return {
            "available": True,
            "version": version,
            "status": "read_only_probe_passed",
            "method": "get_formatted_pairs_details",
            "observed_count": count,
            "private_key_used": False,
            "notes": ["python_sdk_read_only_probe_passed", "private_key_not_used"],
        }

    return {
        "available": True,
        "version": version,
        "status": "read_only_probe_unavailable",
        "method": None,
        "observed_count": None,
        "private_key_used": False,
        "notes": ["python_sdk_loaded_but_no_supported_read_method"],
    }


def _sdk_status(*, sdk_probe: Callable[[], dict[str, Any]] | None = None) -> dict[str, Any]:
    if sdk_probe is not None:
        return sdk_probe()
    try:
        return asyncio.run(_run_sdk_read_only_probe())
    except importlib.metadata.PackageNotFoundError:
        return {
            "available": False,
            "version": None,
            "status": "missing_dependency",
            "method": None,
            "observed_count": None,
            "private_key_used": False,
            "notes": ["install ostium-python-sdk for Python SDK read-only evidence"],
        }
    except Exception as exc:  # pragma: no cover - exact SDK/network failures vary live.
        version = None
        try:
            version = importlib.metadata.version("ostium-python-sdk")
        except importlib.metadata.PackageNotFoundError:
            pass
        return {
            "available": version is not None,
            "version": version,
            "status": "read_only_probe_failed",
            "method": None,
            "observed_count": None,
            "private_key_used": False,
            "error": str(exc),
            "notes": ["python_sdk_read_only_probe_failed", "private_key_not_used"],
        }


def _price_items(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
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


def _item_keys(row: dict[str, Any]) -> set[str]:
    keys = set()
    for key in ("asset", "pair", "symbol", "ticker"):
        value = row.get(key)
        if isinstance(value, str) and value:
            keys.add(value.upper())
            keys.add(value.replace("-", "").replace("/", "").upper())
    from_symbol = row.get("from")
    to_symbol = row.get("to")
    if isinstance(from_symbol, str) and isinstance(to_symbol, str):
        keys.add(f"{from_symbol}-{to_symbol}".upper())
        keys.add(f"{from_symbol}{to_symbol}".upper())
    return keys


def _asset_status(
    asset: str,
    latest_prices_payload: Any,
    builder_prices_payload: Any,
    trading_hours_payload: Any,
) -> dict[str, Any]:
    config = _asset_config(asset)
    expected = {
        config["requested_asset"].upper(),
        config["canonical_symbol"].upper(),
        config["venue_pair"].upper(),
        config["venue_pair"].replace("-", "").upper(),
        config["legacy_asset_param"].upper(),
    }
    legacy_item = next((row for row in _price_items(latest_prices_payload) if _item_keys(row) & expected), {})
    builder_item = next((row for row in _price_items(builder_prices_payload) if _item_keys(row) & expected), {})
    item = legacy_item or builder_item
    is_market_open = item.get("isMarketOpen")
    is_day_trading_closed = item.get("isDayTradingClosed")
    if is_market_open is False or is_day_trading_closed is True:
        market_state = "closed"
    elif is_market_open is True:
        market_state = "open"
    else:
        market_state = "unknown"
    return {
        **config,
        "market_state": market_state,
        "market_close_is_missing_data": False,
        "oracle_ts_ms": item.get("timestampSeconds"),
        "has_bid_ask": item.get("bid") is not None and item.get("ask") is not None,
        "latest_price_observed": bool(legacy_item),
        "builder_price_observed": bool(builder_item),
        "trading_hours_observed": trading_hours_payload is not None and not _is_fetch_error(trading_hours_payload),
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
    builder_prices_endpoint: str = DEFAULT_BUILDER_PRICES_ENDPOINT,
    client: httpx.Client | None = None,
    sdk_probe: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    owns_client = client is None
    http_client = client or httpx.Client(timeout=20)
    day = datetime.now(timezone.utc).date().isoformat()
    root = data_dir / "raw/sidecar/ostium-constraints" / day
    try:
        latest_prices = _fetch_json(http_client, latest_prices_endpoint)
        latest_prices_ref = _write_raw_artifact(
            root / f"{run_id}_latest_prices.json",
            endpoint=latest_prices_endpoint,
            payload=latest_prices,
            source="ostium_latest_prices_legacy_v1",
        )
        builder_prices = _fetch_json(http_client, builder_prices_endpoint)
        builder_prices_ref = _write_raw_artifact(
            root / f"{run_id}_builder_prices.json",
            endpoint=builder_prices_endpoint,
            payload=builder_prices,
            source="ostium_builder_prices_v1",
        )

        asset_payloads: dict[str, Any] = {}
        trading_hours_payloads: dict[str, Any] = {}
        latest_price_refs: dict[str, dict[str, Any]] = {}
        trading_hours_refs: dict[str, dict[str, Any]] = {}
        asset_configs = [_asset_config(asset) for asset in assets]
        for config in asset_configs:
            asset = config["requested_asset"]
            legacy_asset_param = config["legacy_asset_param"]
            asset_payloads[asset] = _fetch_json_or_error(
                http_client,
                latest_price_endpoint,
                params={"asset": legacy_asset_param},
            )
            trading_hours_payloads[asset] = _fetch_json_or_error(
                http_client,
                trading_hours_endpoint,
                params={"asset": legacy_asset_param},
            )
            safe_name = legacy_asset_param.replace("/", "_").replace("-", "_")
            latest_price_refs[asset] = _write_raw_artifact(
                root / f"{run_id}_latest_price_{safe_name}.json",
                endpoint=latest_price_endpoint,
                payload=asset_payloads[asset],
                source="ostium_latest_price_asset_legacy_v1",
            )
            trading_hours_refs[asset] = _write_raw_artifact(
                root / f"{run_id}_trading_hours_{safe_name}.json",
                endpoint=trading_hours_endpoint,
                payload=trading_hours_payloads[asset],
                source="ostium_trading_hours_legacy_v1",
            )
    finally:
        if owns_client:
            http_client.close()

    sdk = _sdk_status(sdk_probe=sdk_probe)
    asset_statuses = [
        {
            **_asset_status(asset, latest_prices, builder_prices, trading_hours_payloads.get(asset)),
            "latest_price_artifact": latest_price_refs.get(asset),
            "trading_hours_artifact": trading_hours_refs.get(asset),
        }
        for asset in assets
    ]
    failures = []
    if sdk.get("status") != "read_only_probe_passed":
        failures.append("python_sdk_read_only_probe_failed")
    if any(not item["latest_price_observed"] for item in asset_statuses):
        failures.append("latest_price_missing_for_asset")
    if any(not item["builder_price_observed"] for item in asset_statuses):
        failures.append("builder_price_missing_for_asset")
    if any(not item["trading_hours_observed"] for item in asset_statuses):
        failures.append("trading_hours_missing_for_asset")

    artifact = {
        "run_id": run_id,
        "venue": "ostium",
        "collector_version": COLLECTOR_VERSION,
        "source": "ostium_read_only_constraints_v2",
        "python_sdk": sdk,
        "builder_prices_artifact": builder_prices_ref,
        "legacy_latest_prices_artifact": latest_prices_ref,
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
