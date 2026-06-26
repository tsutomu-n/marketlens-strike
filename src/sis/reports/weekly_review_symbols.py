from __future__ import annotations

LEGACY_BACKTEST_SYMBOLS = frozenset({"QQQ", "SPY", "XAU", "NDX_EQUIV", "SPX_EQUIV"})


def canonical_symbols(metrics_rows: list[dict[str, object]]) -> list[str]:
    return sorted(
        {
            str(symbol)
            for row in metrics_rows
            for symbol in [row.get("canonical_symbol")]
            if isinstance(symbol, str) and symbol
        }
    )


def backtest_symbol_scope(symbols: list[str]) -> str:
    if set(symbols) & LEGACY_BACKTEST_SYMBOLS:
        return "historical_or_legacy_symbols"
    return "current_or_non_legacy_symbols"
