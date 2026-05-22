from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl

from sis.models import QuoteLog
from sis.storage.jsonl_store import read_jsonl


def collect_quote_logs(raw_root: Path) -> list[QuoteLog]:
    logs: list[QuoteLog] = []
    for path in sorted(raw_root.glob("*/*.jsonl")):
        for row in read_jsonl(path):
            logs.append(QuoteLog.model_validate(row))
    return logs


def normalize_quotes(raw_root: Path, parquet_path: Path, duckdb_path: Path) -> int:
    logs = collect_quote_logs(raw_root)
    if not logs:
        raise FileNotFoundError(f"No raw quote JSONL files found under {raw_root}")

    rows = [item.model_dump(mode="json") for item in logs]
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    frame = pl.DataFrame(rows)
    frame.write_parquet(parquet_path)

    duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(duckdb_path)) as conn:
        conn.execute("CREATE OR REPLACE TABLE quotes AS SELECT * FROM read_parquet(?)", [str(parquet_path)])
    return len(rows)

