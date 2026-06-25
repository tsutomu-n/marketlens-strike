from __future__ import annotations

from typing import Any


def _trade_reason_fields(
    *,
    spec: Any,
    regime: Any | None,
    reason_codes: list[str] | None,
) -> dict[str, list[str]]:
    effective_reason_codes = reason_codes or [spec.rules.reason_code]
    if regime is not None:
        effective_reason_codes = [*effective_reason_codes, f"regime:{regime.name}"]
    return {
        "reason_codes": effective_reason_codes,
        "block_reasons": [],
    }
