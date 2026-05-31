from __future__ import annotations

from pathlib import Path


FORBIDDEN_SCOPE_TERMS = [
    "sis.execution",
    "src/sis/execution",
    "nonce",
    "cloid",
    "place_limit_order",
    "schedule_cancel",
    "cancel_by_cloid",
]

ALLOWED_METADATA_TERMS = {
    "wallet_used",
    "exchange_write_used",
    "no live order, wallet, signing, or exchange write",
}


def test_pure_backtest_scope_has_no_live_execution_coupling() -> None:
    roots = [Path("src/sis/backtest/engine"), Path("src/sis/backtest/trade_xyz")]
    violations: list[str] = []
    for root in roots:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            for term in FORBIDDEN_SCOPE_TERMS:
                if term in text:
                    violations.append(f"{path}:{term}")
            for term in ("wallet", "signing", "exchange write"):
                if term in text and not any(allowed in text for allowed in ALLOWED_METADATA_TERMS):
                    violations.append(f"{path}:{term}")

    assert violations == []
