from __future__ import annotations

from sis.reports.weekly_review_symbols import backtest_symbol_scope, canonical_symbols


def test_canonical_symbols_filters_and_sorts_symbol_values() -> None:
    rows: list[dict[str, object]] = [
        {"canonical_symbol": "MSFT"},
        {"canonical_symbol": ""},
        {"canonical_symbol": "QQQ"},
        {"canonical_symbol": None},
        {"canonical_symbol": 42},
        {"canonical_symbol": "AAPL"},
        {"canonical_symbol": "QQQ"},
    ]

    assert canonical_symbols(rows) == ["AAPL", "MSFT", "QQQ"]


def test_backtest_symbol_scope_marks_legacy_symbol_sets() -> None:
    assert backtest_symbol_scope(["QQQ", "AAPL"]) == "historical_or_legacy_symbols"
    assert backtest_symbol_scope(["AAPL", "MSFT"]) == "current_or_non_legacy_symbols"
    assert backtest_symbol_scope([]) == "current_or_non_legacy_symbols"
