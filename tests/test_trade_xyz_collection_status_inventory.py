from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from sis.venues.trade_xyz.collection_status_inventory import raw_quote_inventory


def test_raw_quote_inventory_summarizes_traceability_and_bad_rows(tmp_path: Path) -> None:
    raw_quotes_root = tmp_path / "raw/quotes"
    quote_dir = raw_quotes_root / "trade_xyz"
    quote_dir.mkdir(parents=True)
    path = quote_dir / "sample.jsonl"
    path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "canonical_symbol": "nvda",
                        "source": "trade_xyz_l2Book",
                        "raw_payload_ref": "raw/1",
                    }
                ),
                json.dumps({"coin": "SP500", "source": "trade_xyz_l2Book"}),
                json.dumps({"source": "trade_xyz_l2Book", "raw_payload_ref": "raw/3"}),
                "{bad json",
                json.dumps(["not", "an", "object"]),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    mtime = datetime(2026, 1, 1, 12, 0, tzinfo=UTC).timestamp()
    os.utime(path, (mtime, mtime))

    inventory = raw_quote_inventory(
        raw_quotes_root,
        generated_at=datetime(2026, 1, 1, 12, 5, tzinfo=UTC),
    )

    assert inventory["file_count"] == 1
    assert inventory["row_count"] == 5
    assert inventory["traceable_row_count"] == 2
    assert inventory["untraceable_row_count"] == 3
    assert inventory["malformed_row_count"] == 2
    assert inventory["missing_symbol_row_count"] == 1
    assert inventory["symbol_counts"] == {"<missing>": 1, "NVDA": 1, "SP500": 1}
    assert inventory["source_counts"] == {"trade_xyz_l2Book": 3}
    assert inventory["latest_file"] == str(path)
    assert inventory["latest_file_age_seconds"] == 300.0
    assert inventory["files"][0]["malformed_row_count"] == 2
    assert inventory["files"][0]["missing_symbol_row_count"] == 1
