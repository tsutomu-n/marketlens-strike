from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from sis.models import InstrumentSpec


def normalize_symbol(value: str | None) -> str | None:
    if not value:
        return None
    return value.removeprefix("xyz:").upper()


def source_ts_ms_from_payload(payload: dict[str, Any]) -> int | None:
    for key in ("time", "ts", "timestamp"):
        value = payload.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
    return None


def extract_l2_payload(row: dict[str, Any]) -> dict[str, Any] | None:
    if isinstance(row.get("levels"), list):
        return row
    for key in ("data", "book", "l2Book", "payload"):
        value = row.get(key)
        if isinstance(value, dict) and isinstance(value.get("levels"), list):
            return value
    return None


def load_l2_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            payload = json.loads(line)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def coerce_asset_ctx_value(value: str) -> Any:
    stripped = value.strip()
    if not stripped:
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped


def load_asset_ctxs(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    with path.open("r", encoding="utf-8", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        if sample.lstrip().startswith(("{", "[")):
            payload = json.load(handle)
            items = payload if isinstance(payload, list) else payload.get("ctxs", [])
            result: dict[str, dict[str, Any]] = {}
            for item in items if isinstance(items, list) else []:
                if not isinstance(item, dict):
                    continue
                symbol = normalize_symbol(
                    str(
                        item.get("coin")
                        or item.get("name")
                        or item.get("symbol")
                        or item.get("canonical_symbol")
                        or ""
                    )
                )
                if symbol:
                    result[symbol] = item
            return result
        reader = csv.DictReader(handle)
        result: dict[str, dict[str, Any]] = {}
        for row in reader:
            symbol = normalize_symbol(
                row.get("coin")
                or row.get("name")
                or row.get("symbol")
                or row.get("canonical_symbol")
                or ""
            )
            if not symbol:
                continue
            if row.get("ctx"):
                parsed_ctx = coerce_asset_ctx_value(str(row["ctx"]))
                if isinstance(parsed_ctx, dict):
                    result[symbol] = parsed_ctx
                    continue
            result[symbol] = {
                key: coerce_asset_ctx_value(value)
                for key, value in row.items()
                if value is not None and value != ""
            }
        return result


def resolve_instrument(
    instruments: list[InstrumentSpec],
    *,
    canonical_symbol: str | None,
    coin: str | None,
) -> InstrumentSpec:
    by_symbol = {item.canonical_symbol.upper(): item for item in instruments}
    by_coin = {str(item.coin).upper(): item for item in instruments if item.coin}
    if canonical_symbol and canonical_symbol.upper() in by_symbol:
        return by_symbol[canonical_symbol.upper()]
    if coin and coin.upper() in by_coin:
        return by_coin[coin.upper()]
    if coin and (normalized := normalize_symbol(coin)) and normalized in by_symbol:
        return by_symbol[normalized]
    raise ValueError("historical archive symbol was not found in Trade[XYZ] registry")


def archive_quote_output_path(data_dir: Path, item: dict[str, Any]) -> Path:
    date_part = str(item.get("date") or "unknown").replace("-", "")
    hour = str(item.get("hour") if item.get("hour") is not None else "unknown")
    coin = str(item.get("coin") or "unknown").replace("/", "_").replace(":", "_")
    return data_dir / "raw/quotes/trade_xyz" / f"historical_archive_{date_part}_{hour}_{coin}.jsonl"
