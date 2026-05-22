import json
from pathlib import Path

from sis.venues.ostium.probe import write_ostium_live_probe_outputs


def test_ostium_probe_http_mock_returns_quotes_without_live_api(httpx_mock, tmp_path) -> None:
    payload = json.loads(Path("tests/fixtures/ostium_prices.sample.json").read_text(encoding="utf-8"))
    httpx_mock.add_response(url="https://builder.ostium.io/v1/prices", json=payload)

    specs, quotes = write_ostium_live_probe_outputs(data_dir=tmp_path)

    assert len(specs) == 3
    assert len(quotes) == 3
    by_symbol = {quote.canonical_symbol: quote for quote in quotes}
    assert by_symbol["SPX_EQUIV"].bid_price == 6000.1
    assert by_symbol["SPX_EQUIV"].ask_price == 6000.3
    assert by_symbol["SPX_EQUIV"].mid_price == 6000.2
    assert by_symbol["SPX_EQUIV"].spread_bps is not None
