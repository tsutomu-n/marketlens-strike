from __future__ import annotations

from pathlib import Path

from sis.storage.jsonl_store import read_json


def latest_positions_sidecar(raw_sidecar_dir: Path) -> Path | None:
    files = sorted(raw_sidecar_dir.glob("positions_*.json"))
    return files[-1] if files else None


def positions_have_liquidation_reference(path: Path | None) -> bool:
    if path is None or not path.exists():
        return False
    data = read_json(path)
    if not isinstance(data, dict):
        return False
    positions = data.get("positions")
    if not isinstance(positions, list) or not positions:
        return False
    return all(
        isinstance(item, dict)
        and item.get("liquidation_px") not in {None, ""}
        and item.get("entry_px") not in {None, ""}
        and item.get("side") in {"long", "short"}
        for item in positions
    )
