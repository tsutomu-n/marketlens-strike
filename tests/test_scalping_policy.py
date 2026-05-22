from sis.risk.scalping_policy import check_timeframe


def test_scalping_timeframes_are_blocked() -> None:
    assert not check_timeframe("1m").allowed
    assert check_timeframe("1m").reason == "BLOCK_SCALPING_TIMEFRAME"
    assert not check_timeframe("5m").allowed


def test_swing_timeframes_are_allowed() -> None:
    assert check_timeframe("4h").allowed
    assert check_timeframe("1d").allowed
    assert check_timeframe("3d").allowed


def test_unknown_timeframe_is_flagged() -> None:
    decision = check_timeframe("2h")
    assert not decision.allowed
    assert decision.reason == "BLOCK_UNKNOWN_TIMEFRAME"

