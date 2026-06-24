from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def raw_quote_inventory(raw_quotes_root: Path, *, generated_at: datetime) -> dict[str, Any]:
    quote_dir = raw_quotes_root / "trade_xyz"
    files = sorted(quote_dir.glob("*.jsonl"))
    total_rows = 0
    traceable_rows = 0
    untraceable_rows = 0
    malformed_rows = 0
    missing_symbol_rows = 0
    symbol_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    latest_path: Path | None = None
    latest_mtime: float | None = None
    per_file: list[dict[str, Any]] = []
    for path in files:
        row_count = 0
        traceable_count = 0
        file_malformed_rows = 0
        file_missing_symbol_rows = 0
        file_symbol_counts: dict[str, int] = {}
        file_source_counts: dict[str, int] = {}
        with path.open("r", encoding="utf-8") as handle:
            lines = [line for line in handle if line.strip()]
        for line in lines:
            row_count += 1
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                malformed_rows += 1
                file_malformed_rows += 1
                continue
            if not isinstance(row, dict):
                malformed_rows += 1
                file_malformed_rows += 1
                continue
            if row.get("raw_payload_ref") is None:
                untraceable_rows += 1
            else:
                traceable_count += 1
            symbol = (
                row.get("canonical_symbol")
                or row.get("symbol")
                or row.get("asset_symbol")
                or row.get("coin")
            )
            if isinstance(symbol, str) and symbol.strip():
                symbol_key = symbol.strip().upper()
            else:
                symbol_key = "<missing>"
                missing_symbol_rows += 1
                file_missing_symbol_rows += 1
            source = row.get("source")
            source_key = (
                source.strip() if isinstance(source, str) and source.strip() else "<missing>"
            )
            symbol_counts[symbol_key] = symbol_counts.get(symbol_key, 0) + 1
            file_symbol_counts[symbol_key] = file_symbol_counts.get(symbol_key, 0) + 1
            source_counts[source_key] = source_counts.get(source_key, 0) + 1
            file_source_counts[source_key] = file_source_counts.get(source_key, 0) + 1
        total_rows += row_count
        traceable_rows += traceable_count
        stat = path.stat()
        if latest_mtime is None or stat.st_mtime > latest_mtime:
            latest_mtime = stat.st_mtime
            latest_path = path
        per_file.append(
            {
                "path": str(path),
                "row_count": row_count,
                "traceable_row_count": traceable_count,
                "untraceable_row_count": row_count - traceable_count,
                "malformed_row_count": file_malformed_rows,
                "missing_symbol_row_count": file_missing_symbol_rows,
                "symbol_counts": dict(sorted(file_symbol_counts.items())),
                "source_counts": dict(sorted(file_source_counts.items())),
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC).isoformat(),
            }
        )
    latest_file_modified_at = (
        datetime.fromtimestamp(latest_mtime, tz=UTC) if latest_mtime is not None else None
    )
    latest_file_age_seconds = (
        max(0.0, (generated_at - latest_file_modified_at).total_seconds())
        if latest_file_modified_at is not None
        else None
    )
    untraceable_rows = total_rows - traceable_rows
    return {
        "raw_quotes_root": str(raw_quotes_root),
        "file_count": len(files),
        "row_count": total_rows,
        "traceable_row_count": traceable_rows,
        "untraceable_row_count": untraceable_rows,
        "malformed_row_count": malformed_rows,
        "missing_symbol_row_count": missing_symbol_rows,
        "symbol_counts": dict(sorted(symbol_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "latest_file": str(latest_path) if latest_path is not None else None,
        "latest_file_modified_at": latest_file_modified_at.isoformat()
        if latest_file_modified_at is not None
        else None,
        "latest_file_age_seconds": latest_file_age_seconds,
        "files": per_file,
    }
