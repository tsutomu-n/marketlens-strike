from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from sis.storage.jsonl_store import read_jsonl


@dataclass
class QuoteDiagnostic:
    venue: str
    symbol: str
    rows: int
    market_open_rows: int
    tradable_rate: float
    stale_rate: float
    missing_mark_price_rate: float
    missing_index_price_rate: float
    missing_spread_rate: float
    stale_missing_oracle_ts_rate: float
    stale_old_oracle_ts_rate: float
    market_status_unknown_rate: float
    market_closed_rate: float
    oracle_age_p50_ms: int | None
    oracle_age_p90_ms: int | None
    spread_p50_bps: float | None
    spread_p90_bps: float | None


def _pct(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return numerator / denominator


def _quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    idx = int((len(sorted_values) - 1) * q)
    return sorted_values[idx]


def _quantile_int(values: list[int], q: float) -> int | None:
    result = _quantile([float(item) for item in values], q)
    if result is None:
        return None
    return int(result)


def build_quote_diagnostics(
    raw_quotes_root: Path,
    venue: str | None = None,
    symbol: str | None = None,
) -> list[QuoteDiagnostic]:
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for path in sorted(raw_quotes_root.glob("*/*.jsonl")):
        for row in read_jsonl(path):
            key = (row.get("venue"), row.get("canonical_symbol"))
            if key[0] is None or key[1] is None:
                continue
            grouped[(str(key[0]), str(key[1]))].append(row)

    diagnostics: list[QuoteDiagnostic] = []
    for (row_venue, row_symbol), rows in sorted(grouped.items()):
        if venue and row_venue != venue:
            continue
        if symbol and row_symbol != symbol:
            continue

        market_open_rows = sum(1 for row in rows if row.get("market_status") == "open")
        tradable_rows = sum(1 for row in rows if row.get("is_tradable") is True)
        stale_rows = 0
        stale_missing_oracle = 0
        stale_old_oracle = 0
        missing_mark = 0
        missing_index = 0
        missing_spread = 0
        market_unknown = 0
        market_closed = 0
        oracle_ages: list[int] = []
        spreads: list[float] = []

        for row in rows:
            ts_client = row.get("ts_client")
            oracle_ts_ms = row.get("oracle_ts_ms")
            market_status = row.get("market_status")
            if market_status == "unknown":
                market_unknown += 1
            elif market_status == "closed":
                market_closed += 1

            if isinstance(ts_client, str) and isinstance(oracle_ts_ms, int):
                # Keep parsing lightweight: rely on ISO lexical layout and unix milliseconds conversion only.
                try:
                    from datetime import datetime

                    ts_ms = int(datetime.fromisoformat(ts_client.replace("Z", "+00:00")).timestamp() * 1000)
                    age = max(0, ts_ms - oracle_ts_ms)
                    oracle_ages.append(age)
                    if age > 10_000:
                        stale_rows += 1
                        stale_old_oracle += 1
                except ValueError:
                    stale_rows += 1
                    stale_missing_oracle += 1
            else:
                stale_rows += 1
                stale_missing_oracle += 1

            if row.get("mark_price") is None:
                missing_mark += 1
            if row.get("index_price") is None:
                missing_index += 1
            spread = row.get("spread_bps")
            if spread is None:
                missing_spread += 1
            elif isinstance(spread, (int, float)):
                spreads.append(float(spread))

        diagnostics.append(
            QuoteDiagnostic(
                venue=row_venue,
                symbol=row_symbol,
                rows=len(rows),
                market_open_rows=market_open_rows,
                tradable_rate=_pct(tradable_rows, len(rows)),
                stale_rate=_pct(stale_rows, len(rows)),
                missing_mark_price_rate=_pct(missing_mark, len(rows)),
                missing_index_price_rate=_pct(missing_index, len(rows)),
                missing_spread_rate=_pct(missing_spread, len(rows)),
                stale_missing_oracle_ts_rate=_pct(stale_missing_oracle, len(rows)),
                stale_old_oracle_ts_rate=_pct(stale_old_oracle, len(rows)),
                market_status_unknown_rate=_pct(market_unknown, len(rows)),
                market_closed_rate=_pct(market_closed, len(rows)),
                oracle_age_p50_ms=_quantile_int(oracle_ages, 0.5),
                oracle_age_p90_ms=_quantile_int(oracle_ages, 0.9),
                spread_p50_bps=_quantile(spreads, 0.5),
                spread_p90_bps=_quantile(spreads, 0.9),
            )
        )
    return diagnostics
