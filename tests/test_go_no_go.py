from sis.models import Decision
from sis.reports.go_no_go import _decision_for_state, _threshold_result


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


def test_decision_for_state_names_live_window_condition() -> None:
    assert _decision_for_state(
        core_ready=True,
        blockers=[
            "stale_rate at or below threshold",
            "tradable_rate at or above threshold",
        ],
        signals_exists=False,
    ) == Decision.CONDITIONAL_GO_NEEDS_LIVE_WINDOW


def test_decision_for_state_names_cost_failure() -> None:
    assert _decision_for_state(
        core_ready=True,
        blockers=["Holding/rollover cost reproduced for target horizons"],
        signals_exists=True,
    ) == Decision.NO_GO_COST


def test_decision_for_state_names_missing_signal_backtest_when_otherwise_ready() -> None:
    assert _decision_for_state(
        core_ready=True,
        blockers=[],
        signals_exists=False,
    ) == Decision.CONDITIONAL_GO_NEEDS_SIGNAL_BACKTEST


def test_decision_for_state_go_when_ready_and_signal_backtest_present() -> None:
    assert _decision_for_state(
        core_ready=True,
        blockers=[],
        signals_exists=True,
    ) == Decision.GO
