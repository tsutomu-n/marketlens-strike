from __future__ import annotations

from pathlib import Path

from sis.reports.quote_diagnostics import build_quote_diagnostics


def phase_gate_quote_diagnostics(
    data_dir: Path,
    *,
    diagnostics_symbols: tuple[str, ...],
    stale_thresholds_ms: dict[str, int],
) -> list[dict[str, object]]:
    diagnostics: list[dict[str, object]] = []
    for symbol in diagnostics_symbols:
        items = build_quote_diagnostics(
            data_dir / "raw/quotes",
            venue="trade_xyz",
            symbol=symbol,
            stale_thresholds_ms=stale_thresholds_ms,
            latest_only=True,
        )
        diagnostics.append(
            {
                "symbol": symbol,
                "available": bool(items),
                "items": [item.__dict__.copy() for item in items],
            }
        )
    return diagnostics
