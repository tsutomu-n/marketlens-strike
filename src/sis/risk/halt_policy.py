from __future__ import annotations

from pathlib import Path

import yaml


def load_halt_policy(path: Path = Path("configs/halt_policy.yaml")) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def summarize_halt_policy(policy: dict) -> list[str]:
    halt = policy.get("halt_policy", policy)
    stale = halt.get("stale_price", {})
    session = halt.get("session", {})
    spread = halt.get("spread", {}).get("max_spread_p90_bps", {})
    return [
        f"gtrade_max_age_ms={stale.get('gtrade_max_age_ms')}",
        f"ostium_max_age_ms={stale.get('ostium_max_age_ms')}",
        f"block_before_close_minutes={session.get('block_before_close_minutes')}",
        f"block_after_open_minutes={session.get('block_after_open_minutes')}",
        f"spread_limits={spread}",
    ]

