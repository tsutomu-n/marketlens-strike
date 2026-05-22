from datetime import datetime, timezone

import polars as pl

from sis.reports.cost_matrix import build_cost_matrix_from_quotes


def test_build_cost_matrix_uses_normalized_quote_aggregates(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    out_path = tmp_path / "venue_cost_matrix.csv"
    pl.DataFrame(
        [
            {
                "ts_client": datetime.now(timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "spread_bps": 2.0,
                "oracle_ts_ms": None,
                "is_tradable": True,
            },
            {
                "ts_client": datetime.now(timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "SPY",
                "venue_symbol": "SPY/USD",
                "spread_bps": 4.0,
                "oracle_ts_ms": None,
                "is_tradable": False,
            },
        ]
    ).write_parquet(quotes_path)

    build_cost_matrix_from_quotes(quotes_path, out_path)

    matrix = pl.read_csv(out_path)
    spy = matrix.filter((pl.col("venue") == "gtrade") & (pl.col("symbol") == "SPY")).row(
        0, named=True
    )
    assert spy["spread_p50_bps"] is not None
    assert spy["tradable_rate"] == 0.5
