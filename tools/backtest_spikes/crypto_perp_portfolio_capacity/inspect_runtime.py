from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from crypto_perp_portfolio_capacity.pack_reader import (  # type: ignore[import-not-found]
        build_runtime_inventory,
        load_candidate_pack,
    )
else:
    from .pack_reader import build_runtime_inventory, load_candidate_pack


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-pack-dir", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    pack = load_candidate_pack(args.candidate_pack_dir)
    inventory = build_runtime_inventory(pack)
    args.out.mkdir(parents=True, exist_ok=True)
    output = args.out / "runtime_inventory.json"
    output.write_text(
        json.dumps(inventory.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("status=pass")
    print(f"pack_id={inventory.pack_id}")
    print(f"event_count={inventory.event_count}")
    print(f"peak_overlap={inventory.execution_window_peak_overlap}")
    print(f"runtime_inventory_path={output.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
