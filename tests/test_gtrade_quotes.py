from sis.storage.jsonl_store import read_jsonl
from sis.venues.gtrade.quotes import convert_sidecar_to_quote_logs


def test_convert_sidecar_to_quote_logs_embeds_pair_raw_payload(tmp_path) -> None:
    sidecar_path = tmp_path / "sidecar.jsonl"
    out_path = tmp_path / "quotes.jsonl"
    sidecar_path.write_text(
        '{"ts_client":"2026-05-22T00:00:00.000Z","venue":"gtrade",'
        '"network":"arbitrum","backend":"https://backend-arbitrum.gains.trade",'
        '"raw_payload_sha256":"abc123",'
        '"market_status":{"isIndicesOpen":true},'
        '"pairs":[{"canonical_symbol":"SPY","venue_symbol":"SPY/USD",'
        '"pair_index":86,"asset_class":"index","spread_bps":2}]}\n',
        encoding="utf-8",
    )

    count = convert_sidecar_to_quote_logs(sidecar_path, out_path)

    [quote] = list(read_jsonl(out_path))
    assert count == 1
    assert quote["raw_payload"]["pair"]["pair_index"] == 86
    assert quote["raw_payload"]["market_status"]["isIndicesOpen"] is True
