from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl

from sis.models import QuoteLog
from sis.storage.jsonl_store import read_jsonl


def quote_log_identity(log: QuoteLog) -> tuple[str, str, str, str]:
    return (
        log.ts_client.isoformat(),
        log.venue.value,
        log.canonical_symbol,
        log.raw_payload_sha256,
    )


def collect_quote_logs(raw_root: Path) -> list[QuoteLog]:
    logs: list[QuoteLog] = []
    seen: set[tuple[str, str, str, str]] = set()
    for path in sorted(raw_root.glob("*/*.jsonl")):
        for row in read_jsonl(path):
            log = QuoteLog.model_validate(row)
            key = quote_log_identity(log)
            if key in seen:
                continue
            seen.add(key)
            logs.append(log)
    return logs


def normalize_quotes(raw_root: Path, parquet_path: Path, duckdb_path: Path) -> int:
    logs = collect_quote_logs(raw_root)
    if not logs:
        raise FileNotFoundError(f"No raw quote JSONL files found under {raw_root}")

    rows = []
    for item in logs:
        row = item.model_dump(mode="json")
        row.pop("raw_payload", None)
        rows.append(row)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.DataFrame(rows)
    frame.write_parquet(parquet_path)

    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(duckdb_path)) as conn:
        conn.execute("CREATE OR REPLACE TABLE quotes AS SELECT * FROM read_parquet(?)", [str(parquet_path)])
    return len(rows)
