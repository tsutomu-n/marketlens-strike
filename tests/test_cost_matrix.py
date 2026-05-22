from datetime import datetime, timezone

import polars as pl
import pytest

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


def test_build_cost_matrix_overlays_sidecar_and_registry_cost_metadata(tmp_path) -> None:
    quotes_path = tmp_path / "quotes.parquet"
    out_path = tmp_path / "venue_cost_matrix.csv"
    gtrade_sidecar_root = tmp_path / "raw/sidecar/gtrade"
    ostium_registry_path = tmp_path / "registry/ostium_instrument_registry.json"
    gtrade_sidecar_root.mkdir(parents=True)
    ostium_registry_path.parent.mkdir(parents=True)

    (gtrade_sidecar_root / "2026-05-22.jsonl").write_text(
        '{"pairs":[{"canonical_symbol":"XAU","spread_bps":0,'
        '"pair_index":90,"fee_index":"13","total_position_size_fee_p":"350000000"}],'
        '"raw":{"collaterals":[{"isActive":true,'
        '"borrowingFees":{"v2":{"pairParams":{"90":{"borrowingRatePerSecondP":"100"}}}},'
        '"fundingFees":{"pairParams":{"90":{"fundingFeesEnabled":true}},'
        '"pairData":{"90":{"lastFundingRatePerSecondP":"200000000"}}}}]}}\n',
        encoding="utf-8",
    )
    ostium_registry_path.write_text(
        '[{"venue":"ostium","canonical_symbol":"XAU","opening_fee_bps":3,'
        '"rollover_fee_per_block":"1.2e-10","rollover_rate_long":"-0.01",'
        '"rollover_rate_short":"0.02"}]',
        encoding="utf-8",
    )
    pl.DataFrame(
        [
            {
                "ts_client": datetime.now(timezone.utc).isoformat(),
                "venue": "gtrade",
                "canonical_symbol": "XAU",
                "venue_symbol": "XAU/USD",
                "spread_bps": 0.0,
                "oracle_ts_ms": None,
                "is_tradable": True,
            },
            {
                "ts_client": datetime.now(timezone.utc).isoformat(),
                "venue": "ostium",
                "canonical_symbol": "XAU",
                "venue_symbol": "XAU-USD",
                "spread_bps": 2.0,
                "oracle_ts_ms": None,
                "is_tradable": True,
            },
        ]
    ).write_parquet(quotes_path)

    build_cost_matrix_from_quotes(
        quotes_path,
        out_path,
        gtrade_sidecar_root=gtrade_sidecar_root,
        ostium_registry_path=ostium_registry_path,
    )

    matrix = pl.read_csv(out_path)
    gtrade_xau = matrix.filter((pl.col("venue") == "gtrade") & (pl.col("symbol") == "XAU")).row(
        0, named=True
    )
    ostium_xau = matrix.filter((pl.col("venue") == "ostium") & (pl.col("symbol") == "XAU")).row(
        0, named=True
    )
    assert gtrade_xau["open_fee_bps"] == 3.5
    assert gtrade_xau["close_fee_bps"] == 3.5
    assert gtrade_xau["holding_cost_4h_bps"] == 0.0432
    assert gtrade_xau["holding_cost_24h_bps"] == 0.2592
    assert gtrade_xau["holding_cost_72h_bps"] == pytest.approx(0.7776)
    assert "fee_index=13" in gtrade_xau["notes"]
    assert ostium_xau["open_fee_bps"] == 3.0
    assert ostium_xau["holding_cost_4h_bps"] == 1.0
    assert ostium_xau["holding_cost_24h_bps"] == 6.0
    assert ostium_xau["holding_cost_72h_bps"] == 18.0
    assert "rollover_rate_long=-0.01" in ostium_xau["notes"]
