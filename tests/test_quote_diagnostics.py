from sis.reports.quote_diagnostics import build_quote_diagnostics


def test_build_quote_diagnostics_reports_rates(tmp_path) -> None:
    quotes_dir = tmp_path / "raw/quotes/gtrade"
    quotes_dir.mkdir(parents=True)
    (quotes_dir / "2026-05-22.jsonl").write_text(
        "\n".join(
            [
                '{"ts_client":"2026-05-22T00:00:02.000Z","venue":"gtrade","canonical_symbol":"QQQ","oracle_ts_ms":1779408000000,'
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


def test_build_quote_diagnostics_uses_venue_stale_thresholds(tmp_path) -> None:
    quotes_dir = tmp_path / "raw/quotes/ostium"
    quotes_dir.mkdir(parents=True)
    (quotes_dir / "2026-05-22.jsonl").write_text(
        '{"ts_client":"2026-05-22T00:00:05.000Z","venue":"ostium","canonical_symbol":"XAU",'
        '"oracle_ts_ms":1779408000000,"mark_price":100.0,"index_price":100.0,'
        '"spread_bps":1.2,"market_status":"open","is_tradable":true}\n',
        encoding="utf-8",
    )

    [diag] = build_quote_diagnostics(
        tmp_path / "raw/quotes",
        venue="ostium",
        symbol="XAU",
        stale_thresholds_ms={"ostium": 5_000},
    )

    assert diag.stale_threshold_ms == 5_000
    assert diag.stale_rate == 0.0


def test_build_quote_diagnostics_counts_missing_oracle_ts_as_stale(tmp_path) -> None:
    quotes_dir = tmp_path / "raw/quotes/gtrade"
    quotes_dir.mkdir(parents=True)
    (quotes_dir / "2026-05-22.jsonl").write_text(
        '{"ts_client":"2026-05-22T00:00:05.000Z","venue":"gtrade","canonical_symbol":"SPY",'
        '"oracle_ts_ms":null,"mark_price":100.0,"index_price":100.0,'
        '"spread_bps":1.2,"market_status":"open","is_tradable":true}\n',
        encoding="utf-8",
    )

    [diag] = build_quote_diagnostics(tmp_path / "raw/quotes", venue="gtrade", symbol="SPY")

    assert diag.stale_rate == 1.0
    assert diag.stale_missing_oracle_ts_rate == 1.0


def test_build_quote_diagnostics_can_use_latest_venue_file_only(tmp_path) -> None:
    quotes_dir = tmp_path / "raw/quotes/trade_xyz"
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

    [diag] = build_quote_diagnostics(
        tmp_path / "raw/quotes",
        venue="trade_xyz",
        symbol="SP500",
        latest_only=True,
    )

    assert diag.rows == 1
    assert diag.fee_mode_unknown_rate == 0.0
