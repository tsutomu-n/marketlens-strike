from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from sis.storage.jsonl_store import write_json


def sha256_file(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def build_evidence_card(data_dir: Path, out_dir: Path) -> Path:
    now = datetime.now(timezone.utc)
    run_id = now.strftime("%Y%m%d_%H%M%S")
    card = {
        "run_id": run_id,
        "created_at": now.isoformat(),
        "scope": {
            "venues": ["gtrade", "ostium"],
            "symbols": ["SPY", "QQQ", "XAU"],
            "timeframes": ["4h", "1d", "3d"],
            "scalping_policy": "prohibited_by_default",
        },
        "data": {
            "normalized_quote_digest": sha256_file(data_dir / "normalized/quotes.parquet"),
            "cost_matrix_digest": sha256_file(data_dir / "research/venue_cost_matrix.csv"),
            "go_no_go_report_digest": sha256_file(data_dir / "research/go_no_go_report.md"),
        },
        "decision": "CONDITIONAL_GO",
        "blockers": [
            "Ostium symbol/price/session probe not implemented",
            "Venue quote collection period not complete",
        ],
        "next_actions": [
            "Collect gTrade quote logs",
            "Normalize quote logs",
            "Implement read-only Ostium probe",
        ],
    }
    out_path = out_dir / f"evidence_card_{run_id}.json"
    write_json(out_path, card)
    return out_path

