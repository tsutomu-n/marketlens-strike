from __future__ import annotations

from pathlib import Path
from typing import Any

from sis.models import InstrumentSpec, Venue
from sis.storage.jsonl_store import read_json, write_json
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.models import TradeXyzAssetResolution, TradeXyzRegistryBuildResult

EXCLUDED_ACTIVE_SYMBOLS = {"MSTR", "COIN", "CRCL", "XAU", "WTI", "JPY", "BTC"}


def resolve_asset_id(perp_dex_index: int, index_in_meta: int) -> int:
    return 100000 + perp_dex_index * 10000 + index_in_meta


def load_trade_xyz_seed(seed_path: Path) -> list[InstrumentSpec]:
    payload = read_json(seed_path)
    if not isinstance(payload, dict):
        raise ValueError("seed payload must be an object")
    venues = payload.get("venues", {})
    if not isinstance(venues, dict):
        raise ValueError("seed payload missing venues object")
    rows = venues.get("trade_xyz", [])
    if not isinstance(rows, list):
        raise ValueError("seed payload venues.trade_xyz must be a list")
    return [InstrumentSpec.model_validate(row) for row in rows if isinstance(row, dict)]


def load_trade_xyz_registry(path: Path) -> list[InstrumentSpec]:
    payload = read_json(path)
    if not isinstance(payload, list):
        raise ValueError("trade_xyz registry must be a JSON array of InstrumentSpec rows")
    return [InstrumentSpec.model_validate(row) for row in payload if isinstance(row, dict)]


def _extract_perp_dex_index(meta_payload: dict[str, Any]) -> int | None:
    candidates = [
        meta_payload.get("perp_dex_index"),
        meta_payload.get("perpDexIndex"),
        meta_payload.get("perpIndex"),
    ]
    nested = meta_payload.get("meta")
    if isinstance(nested, dict):
        candidates.extend(
            [nested.get("perp_dex_index"), nested.get("perpDexIndex"), nested.get("perpIndex")]
        )
    for value in candidates:
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return None


def _extract_perp_dex_index_from_perp_dexs(
    perp_dexs_payload: list[Any],
    *,
    dex: str,
) -> int | None:
    normalized_dex = dex.strip().lower()
    for idx, item in enumerate(perp_dexs_payload):
        name: str | None = None
        if isinstance(item, str):
            name = item
        elif isinstance(item, dict):
            value = item.get("name")
            if isinstance(value, str):
                name = value
        if name is not None and name.strip().lower() == normalized_dex:
            return idx
    return None


def _extract_universe_index(meta_payload: dict[str, Any]) -> dict[str, int]:
    universe: list[Any] = []
    for key in ("universe", "assets", "coins"):
        value = meta_payload.get(key)
        if isinstance(value, list):
            universe = value
            break
    index: dict[str, int] = {}
    for idx, item in enumerate(universe):
        symbol: str | None = None
        if isinstance(item, str):
            symbol = item
        elif isinstance(item, dict):
            for key in ("name", "symbol", "coin"):
                value = item.get(key)
                if isinstance(value, str) and value:
                    symbol = value
                    break
        if symbol is None:
            continue
        normalized = symbol.removeprefix("xyz:").strip().upper()
        if normalized and normalized not in index:
            index[normalized] = idx
    return index


def _normalize_mid_keys(all_mids: dict[str, str]) -> set[str]:
    keys: set[str] = set()
    for key in all_mids:
        normalized = key.removeprefix("xyz:").strip().upper()
        if normalized:
            keys.add(normalized)
    return keys


def mid_candidates(canonical_symbol: str, coin: str) -> set[str]:
    symbol = canonical_symbol.strip().upper()
    coin_u = coin.strip().upper()
    return {symbol, coin_u, coin_u.removeprefix("XYZ:"), f"XYZ:{symbol}", f"xyz:{symbol}"}


def build_trade_xyz_registry(
    seed_path: Path,
    *,
    client: TradeXyzClient | None = None,
    all_mids_payload: dict[str, str] | None = None,
    meta_payload: dict[str, Any] | None = None,
    perp_dexs_payload: list[Any] | None = None,
) -> TradeXyzRegistryBuildResult:
    seed_specs = load_trade_xyz_seed(seed_path)
    mids = (
        all_mids_payload if all_mids_payload is not None else (client.all_mids() if client else {})
    )
    meta = meta_payload if meta_payload is not None else (client.meta() if client else {})
    perp_dexs = (
        perp_dexs_payload
        if perp_dexs_payload is not None
        else (client.perp_dexs() if client else [])
    )

    perp_dex_index = _extract_perp_dex_index_from_perp_dexs(perp_dexs, dex="xyz")
    if perp_dex_index is None:
        perp_dex_index = _extract_perp_dex_index(meta)
    universe_index = _extract_universe_index(meta)
    mid_symbols = _normalize_mid_keys(mids)

    instruments: list[InstrumentSpec] = []
    resolutions: list[TradeXyzAssetResolution] = []

    for spec in seed_specs:
        symbol = spec.canonical_symbol.upper()
        coin = f"xyz:{symbol}"
        excluded = symbol in EXCLUDED_ACTIVE_SYMBOLS
        index_in_meta = universe_index.get(symbol)
        has_mid_price = (
            bool(mid_candidates(symbol, coin) & set(mids.keys())) or symbol in mid_symbols
        )
        asset_id = (
            resolve_asset_id(perp_dex_index, index_in_meta)
            if perp_dex_index is not None and index_in_meta is not None
            else None
        )
        api_orderable = asset_id is not None and has_mid_price and not excluded
        notes = list(spec.notes)
        if asset_id is None:
            notes.append("unresolved_asset_mapping")
        if not has_mid_price:
            notes.append("missing_all_mids_price")
        if excluded:
            notes.append("excluded_active_symbol")
        updated = spec.model_copy(
            update={
                "venue": Venue.TRADE_XYZ,
                "dex": "xyz",
                "coin": coin,
                "perp_dex_index": perp_dex_index,
                "index_in_meta": index_in_meta,
                "asset_id": asset_id,
                "api_orderable": api_orderable,
                "active": spec.active and not excluded,
                "notes": list(dict.fromkeys(notes)),
            }
        )
        instruments.append(updated)
        resolutions.append(
            TradeXyzAssetResolution(
                symbol=symbol,
                coin=coin,
                perp_dex_index=perp_dex_index,
                index_in_meta=index_in_meta,
                asset_id=asset_id,
                has_mid_price=has_mid_price,
                excluded=excluded,
                api_orderable=api_orderable,
            )
        )

    return TradeXyzRegistryBuildResult(instruments=instruments, resolutions=resolutions)


def write_trade_xyz_registry(
    out_path: Path,
    build_result: TradeXyzRegistryBuildResult,
) -> None:
    write_json(out_path, [item.model_dump(mode="json") for item in build_result.instruments])
