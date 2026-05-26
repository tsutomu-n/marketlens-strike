from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sis.models import InstrumentSpec
from sis.storage.jsonl_store import append_jsonl
from sis.storage.normalize import normalize_quotes
from sis.venues.trade_xyz.client import TradeXyzClient
from sis.venues.trade_xyz.normalizer import quote_from_l2_book


def collect_trade_xyz_quotes(
    *,
    instruments: list[InstrumentSpec],
    out_path: Path,
    client: TradeXyzClient | None = None,
    all_mids_payload: dict[str, str] | None = None,
    book_payloads: dict[str, dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> int:
    own_client = client is None
    created_client = client or TradeXyzClient()
    ts = now or datetime.now(timezone.utc)
    mids = all_mids_payload if all_mids_payload is not None else created_client.all_mids()

    try:
        count = 0
        for instrument in instruments:
            if not instrument.active:
                continue
            coin = instrument.coin or f"xyz:{instrument.canonical_symbol}"
            try:
                payload = (
                    book_payloads[coin]
                    if book_payloads is not None and coin in book_payloads
                    else created_client.l2_book(coin)
                )
            except Exception:
                payload = {"levels": [[], []], "error": "BLOCK_API_ERROR"}

            quote = quote_from_l2_book(
                canonical_symbol=instrument.canonical_symbol,
                coin=coin,
                asset_id=instrument.asset_id,
                real_market_symbol=instrument.real_market_symbol,
                payload=payload,
                now=ts,
            )
            if coin not in mids:
                quote = quote.model_copy(
                    update={"is_tradable": False, "block_reasons": ["BLOCK_API_ERROR"]}
                )
            append_jsonl(out_path, quote.model_dump(mode="json"))
            count += 1
        return count
    finally:
        if own_client:
            created_client.close()


def collect_and_normalize_trade_xyz_quotes(
    *,
    data_dir: Path,
    instruments: list[InstrumentSpec],
    client: TradeXyzClient | None = None,
    all_mids_payload: dict[str, str] | None = None,
    book_payloads: dict[str, dict[str, Any]] | None = None,
    now: datetime | None = None,
) -> int:
    ts = now or datetime.now(timezone.utc)
    day = ts.date().isoformat()
    out_path = data_dir / f"raw/quotes/trade_xyz/{day}.jsonl"
    count = collect_trade_xyz_quotes(
        instruments=instruments,
        out_path=out_path,
        client=client,
        all_mids_payload=all_mids_payload,
        book_payloads=book_payloads,
        now=ts,
    )
    normalize_quotes(
        data_dir / "raw/quotes",
        data_dir / "normalized/quotes.parquet",
        data_dir / "normalized/sis.duckdb",
    )
    return count
