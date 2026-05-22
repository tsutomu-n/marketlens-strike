from sis.reports.go_no_go import _threshold_result


def test_threshold_result_requires_values_for_every_row() -> None:
    rows = [
        {"venue": "gtrade", "symbol": "SPY", "stale_rate": ""},
        {"venue": "ostium", "symbol": "XAU", "stale_rate": "0.0"},
    ]

    assert _threshold_result(rows, "stale_rate", maximum=0.05) == "MISSING"


def test_threshold_result_blocks_values_outside_threshold() -> None:
    rows = [
        {"venue": "gtrade", "symbol": "SPY", "tradable_rate": "0.90"},
        {"venue": "ostium", "symbol": "XAU", "tradable_rate": "1.0"},
    ]

    assert _threshold_result(rows, "tradable_rate", minimum=0.95) == "NO_GO"
