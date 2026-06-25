from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from sis.models import InstrumentSpec
from sis.venues.trade_xyz.historical_archive_normalization import extract_l2_payload
from sis.venues.trade_xyz.historical_archive_normalization import source_ts_ms_from_payload
from sis.venues.trade_xyz.normalizer import payload_hash, quote_from_l2_book

HISTORICAL_QUOTE_SOURCE = "hyperliquid_archive.l2Book+asset_ctxs"
MISSING_ASSET_CTX_BLOCK_REASON = "BLOCK_HISTORICAL_ASSET_CTX_MISSING"

__all__ = [
    "HISTORICAL_QUOTE_SOURCE",
    "MISSING_ASSET_CTX_BLOCK_REASON",
    "HistoricalArchiveQuoteRowResult",
    "build_historical_archive_quote_row",
]


@dataclass(frozen=True)
class HistoricalArchiveQuoteRowResult:
    quote: dict[str, Any] | None
    skip_reason: str | None
    missing_asset_ctx: bool = False


def build_historical_archive_quote_row(
    *,
    row: object,
    instrument: InstrumentSpec,
    effective_coin: str,
    asset_ctx: dict[str, Any] | None,
    output_path: Path,
    row_index: int,
) -> HistoricalArchiveQuoteRowResult:
    if not isinstance(row, dict):
        return HistoricalArchiveQuoteRowResult(quote=None, skip_reason="invalid_json_object")
    archive_row = cast(dict[str, Any], row)
    payload = extract_l2_payload(archive_row)
    if payload is None:
        return HistoricalArchiveQuoteRowResult(quote=None, skip_reason="missing_levels")
    source_ts_ms = source_ts_ms_from_payload(payload) or source_ts_ms_from_payload(archive_row)
    if source_ts_ms is None:
        return HistoricalArchiveQuoteRowResult(quote=None, skip_reason="missing_source_ts_ms")
    if "time" not in payload:
        payload = {**payload, "time": source_ts_ms}
    quote_ts = datetime.fromtimestamp(source_ts_ms / 1000, tz=UTC)
    quote = quote_from_l2_book(
        canonical_symbol=instrument.canonical_symbol,
        coin=effective_coin,
        asset_id=instrument.asset_id,
        real_market_symbol=instrument.real_market_symbol,
        payload=payload,
        asset_ctx=asset_ctx,
        fee_mode=instrument.fee_mode,
        taker_fee_bps=instrument.taker_fee_bps,
        maker_fee_bps=instrument.maker_fee_bps,
        source=HISTORICAL_QUOTE_SOURCE,
        now=quote_ts,
    )
    combined_payload = {
        "l2Book": payload,
        "assetCtx": asset_ctx,
        "archive_row": archive_row,
    }
    block_reasons = list(quote.block_reasons)
    if asset_ctx is None:
        block_reasons.append(MISSING_ASSET_CTX_BLOCK_REASON)
    block_reasons = list(dict.fromkeys(block_reasons))
    quote = quote.model_copy(
        update={
            "source_ts_ms": source_ts_ms,
            "raw_payload_sha256": payload_hash(combined_payload),
            "raw_payload": combined_payload,
            "raw_payload_ref": f"{output_path}#row={row_index}",
            "is_tradable": quote.is_tradable and asset_ctx is not None,
            "block_reasons": block_reasons,
        }
    )
    return HistoricalArchiveQuoteRowResult(
        quote=quote.model_dump(mode="json"),
        skip_reason=None,
        missing_asset_ctx=asset_ctx is None,
    )
