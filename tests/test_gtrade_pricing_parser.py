import json
from pathlib import Path

from sis.storage.jsonl_store import read_jsonl
from sis.venues.archive.gtrade.quotes import convert_sidecar_to_quote_logs


def test_gtrade_pricing_fixture_is_ingested_into_quote_log(tmp_path) -> None:
    pricing_payload = json.loads(
        Path("tests/fixtures/archive/gtrade_pricing_v4.sample.json").read_text(encoding="utf-8")
    )

    sidecar_path = tmp_path / "sidecar.jsonl"
    pricing_path = tmp_path / "pricing.jsonl"
    out_path = tmp_path / "quotes.jsonl"

    sidecar_path.write_text(
        '{"ts_client":"2026-05-22T00:00:00.000Z","venue":"gtrade","network":"arbitrum",'
        '"backend":"https://backend-arbitrum.gains.trade","raw_payload_sha256":"abc123",'
        '"raw":{"lastRefreshed":"2026-05-22T00:00:00.000Z"},"market_status":{"isIndicesOpen":true},'
        '"pairs":[{"canonical_symbol":"SPY","venue_symbol":"SPY/USD","pair_index":86,"asset_class":"index","spread_bps":2}]}'
        "\n",
        encoding="utf-8",
    )

    pricing_path.write_text(
        json.dumps(
            {
                "ts_client": "2026-05-22T00:00:01.000Z",
                "venue": "gtrade",
                "source": "gtrade_pricing_v4",
                "network": "arbitrum",
                "prices": [
                    {
                        "canonical_symbol": "SPY",
                        "venue_symbol": "SPY/USD",
                        "pair_index": 86,
                        "mark_price": float(pricing_payload["prices"]["86"]["m"]),
                        "index_price": float(pricing_payload["prices"]["86"]["i"]),
                    }
                ],
                "oracle_ts_ms": 1779408000000,
                "raw_payload_sha256": "p1",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    count = convert_sidecar_to_quote_logs(sidecar_path, out_path, pricing_path=pricing_path)

    [row] = list(read_jsonl(out_path))
    assert count == 1
    assert row["mark_price"] == 512.34
    assert row["index_price"] == 512.31
    assert row["oracle_ts_ms"] == 1779408000000
