from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.portfolio_net_exposure_selection import (
    _first_over_limit_group_net_weight,
    _lowest_rank_overweight_candidate,
    _net_position_weight,
    _overweight_side,
)


def _row(symbol: str, side: str, weight: float, *, rank=None, group: str | None = None):
    row = {
        "execution_symbol": symbol,
        "side": side,
        "position_weight": weight,
        "rank_score": rank,
    }
    if group is not None:
        row["_portfolio_group"] = group
    return row


def test_net_position_weight_uses_long_minus_short_abs_weights() -> None:
    rows = [
        _row("LONG100", "long", -0.6),
        _row("SHORT100", "short", 0.2),
        _row("HOLD100", "none", 1.0),
    ]

    assert _net_position_weight(rows) == 0.39999999999999997
    assert _overweight_side(0.4) == "long"
    assert _overweight_side(-0.4) == "short"


def test_lowest_rank_overweight_candidate_uses_rank_then_index() -> None:
    rows = [
        _row("HIGH100", "long", 0.6, rank=0.9),
        _row("MISSING100", "long", 0.5, rank=None),
        _row("LOW100", "long", 0.4, rank=0.1),
        _row("SHORT100", "short", 0.3, rank=0.0),
    ]

    candidate = _lowest_rank_overweight_candidate(rows, side="long")

    assert candidate == (1, rows[1])


def test_lowest_rank_overweight_candidate_can_filter_group_and_return_none() -> None:
    rows = [
        _row("TECH100", "long", 0.6, rank=0.9, group="tech"),
        _row("ENERGY100", "long", 0.5, rank=0.1, group="energy"),
    ]

    assert _lowest_rank_overweight_candidate(rows, side="short") is None
    assert _lowest_rank_overweight_candidate(rows, side="long", group="tech") == (0, rows[0])


def test_first_over_limit_group_net_weight_preserves_group_insertion_order() -> None:
    rows = [
        _row("ENERGY-LONG", "long", 0.8, group="energy"),
        _row("TECH-LONG", "long", 0.7, group="tech"),
        _row("TECH-SHORT", "short", 0.1, group="tech"),
        _row("ENERGY-SHORT", "short", 0.2, group="energy"),
    ]

    assert _first_over_limit_group_net_weight(rows, 0.5) == ("energy", 0.6000000000000001)


def test_first_over_limit_group_net_weight_returns_none_when_balanced() -> None:
    rows = [
        _row("TECH-LONG", "long", 0.3, group="tech"),
        _row("TECH-SHORT", "short", 0.2, group="tech"),
        _row("MISSING-GROUP", "long", 1.0, group=" "),
    ]

    assert _first_over_limit_group_net_weight(rows, 0.5) is None
