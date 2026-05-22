from sis.reports.quote_diagnostics import build_quote_diagnostics


def test_build_quote_diagnostics_reports_rates(tmp_path) -> None:
    quotes_dir = tmp_path / "raw/quotes/gtrade"
    quotes_dir.mkdir(parents=True)
    (quotes_dir / "2026-05-22.jsonl").write_text(
        "\n".join(
            [
                '{"ts_client":"2026-05-22T00:00:10.000Z","venue":"gtrade","canonical_symbol":"QQQ","oracle_ts_ms":1779408000000,'
                '"mark_price":100.0,"index_price":100.0,"spread_bps":1.2,"market_status":"open","is_tradable":true}',
                '{"ts_client":"2026-05-22T00:00:30.000Z","venue":"gtrade","canonical_symbol":"QQQ","oracle_ts_ms":1779407980000,'
                '"mark_price":null,"index_price":100.1,"spread_bps":null,"market_status":"unknown","is_tradable":false}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    [diag] = build_quote_diagnostics(tmp_path / "raw/quotes", venue="gtrade", symbol="QQQ")

    assert diag.rows == 2
    assert diag.market_open_rows == 1
    assert diag.tradable_rate == 0.5
    assert diag.stale_rate == 0.5
    assert diag.missing_mark_price_rate == 0.5
    assert diag.missing_index_price_rate == 0.0
    assert diag.missing_spread_rate == 0.5
    assert diag.stale_missing_oracle_ts_rate == 0.0
    assert diag.stale_old_oracle_ts_rate == 0.5
    assert diag.market_status_unknown_rate == 0.5
    assert diag.market_closed_rate == 0.0
