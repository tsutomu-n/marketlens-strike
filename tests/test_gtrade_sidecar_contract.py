import json
from pathlib import Path

from sis.models import MarketStatus
from sis.venues.gtrade.quotes import sidecar_market_status, sidecar_oracle_ts_ms


def test_gtrade_trading_variables_fixture_yields_market_status_and_timestamp() -> None:
    raw = json.loads(Path("tests/fixtures/gtrade_trading_variables.sample.json").read_text(encoding="utf-8"))
    snapshot = {
        "market_status": {
            "isIndicesOpen": raw["isIndicesOpen"],
            "isCommoditiesOpen": raw["isCommoditiesOpen"],
        },
        "raw": {"lastRefreshed": raw["lastRefreshed"]},
    }

    status_index, tradable_index = sidecar_market_status(snapshot, "index")
    status_commodity, tradable_commodity = sidecar_market_status(snapshot, "commodity")

    assert status_index == MarketStatus.OPEN
    assert tradable_index is True
    assert status_commodity == MarketStatus.CLOSED
    assert tradable_commodity is False

    assert sidecar_oracle_ts_ms(snapshot) == 1779408000000
