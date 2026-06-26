from __future__ import annotations

from pathlib import Path

from sis.reports.phase_gate_review_diagnostics import phase_gate_quote_diagnostics


def test_phase_gate_quote_diagnostics_marks_available_and_missing_symbols(
    tmp_path: Path,
) -> None:
    quotes_dir = tmp_path / "data/raw/quotes/trade_xyz"
    quotes_dir.mkdir(parents=True)
    (quotes_dir / "2026-05-27.jsonl").write_text(
        '{"ts_client":"2026-05-27T00:00:00Z","venue":"trade_xyz","canonical_symbol":"SP500",'
        '"source_ts_ms":1779840000000,"mark_price":100.0,"index_price":100.0,'
        '"oracle_price":100.0,"funding_rate":0.0,"open_interest_usd":1.0,'
        '"spread_bps":1.0,"fee_mode":"standard","market_status":"open","is_tradable":true}\n',
        encoding="utf-8",
    )

    diagnostics = phase_gate_quote_diagnostics(
        tmp_path / "data",
        diagnostics_symbols=("SP500", "XYZ100"),
        stale_thresholds_ms={"trade_xyz": 5_000},
    )

    assert diagnostics[0]["symbol"] == "SP500"
    assert diagnostics[0]["available"] is True
    assert diagnostics[0]["items"][0]["rows"] == 1
    assert diagnostics[0]["items"][0]["fee_mode_unknown_rate"] == 0.0
    assert diagnostics[1] == {"symbol": "XYZ100", "available": False, "items": []}


def test_phase_gate_quote_diagnostics_uses_latest_trade_xyz_file_only(
    tmp_path: Path,
) -> None:
    quotes_dir = tmp_path / "data/raw/quotes/trade_xyz"
    quotes_dir.mkdir(parents=True)
    (quotes_dir / "2026-05-27.jsonl").write_text(
        '{"ts_client":"2026-05-27T00:00:00Z","venue":"trade_xyz","canonical_symbol":"SP500",'
        '"source_ts_ms":1779840000000,"mark_price":100.0,"index_price":100.0,'
        '"oracle_price":100.0,"funding_rate":0.0,"open_interest_usd":1.0,'
        '"spread_bps":1.0,"fee_mode":"unknown","market_status":"open","is_tradable":true}\n',
        encoding="utf-8",
    )
    (quotes_dir / "2026-05-28.jsonl").write_text(
        '{"ts_client":"2026-05-28T00:00:00Z","venue":"trade_xyz","canonical_symbol":"SP500",'
        '"source_ts_ms":1779926400000,"mark_price":100.0,"index_price":100.0,'
        '"oracle_price":100.0,"funding_rate":0.0,"open_interest_usd":1.0,'
        '"spread_bps":1.0,"fee_mode":"standard","market_status":"open","is_tradable":true}\n',
        encoding="utf-8",
    )

    [diagnostic] = phase_gate_quote_diagnostics(
        tmp_path / "data",
        diagnostics_symbols=("SP500",),
        stale_thresholds_ms={"trade_xyz": 5_000},
    )

    assert diagnostic["available"] is True
    assert diagnostic["items"][0]["rows"] == 1
    assert diagnostic["items"][0]["fee_mode_unknown_rate"] == 0.0
