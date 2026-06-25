from __future__ import annotations

import math

import pytest

from sis.research.strategy_lab.authoring.compiler.signal_selection import (
    _entry_passes,
    _rank_score,
    _score,
    _score_value,
    _selected_side,
    _side_from_column,
    _tail_bucket,
)
from sis.research.strategy_lab.authoring.contracts.base import StrategyAuthoringValidationError
from sis.research.strategy_lab.authoring.contracts.core import (
    Condition,
    EntryRules,
    ModelScore,
    ScoreRules,
    ScoreTerm,
)
from sis.research.strategy_lab.authoring.contracts.risk_controls import CrossSectionalRules
from sis.research.strategy_lab.authoring.contracts.spec import AuthoringRules


def test_entry_passes_honors_all_any_and_none_conditions() -> None:
    entry = EntryRules(
        all=[Condition(column="trade_allowed", op="is_true")],
        any=[
            Condition(column="research_return_1d", op="gt", value=0.01),
            Condition(column="source_confidence", op="gte", value=0.9),
        ],
        none=[Condition(column="halted", op="is_true")],
    )

    assert _entry_passes(
        {
            "trade_allowed": True,
            "research_return_1d": 0.02,
            "source_confidence": 0.5,
            "halted": False,
        },
        entry,
    )
    assert not _entry_passes(
        {
            "trade_allowed": True,
            "research_return_1d": 0.0,
            "source_confidence": 0.5,
            "halted": False,
        },
        entry,
    )
    assert not _entry_passes(
        {
            "trade_allowed": True,
            "research_return_1d": 0.02,
            "source_confidence": 0.5,
            "halted": True,
        },
        entry,
    )


def test_score_combines_weighted_terms_and_model_score_activations() -> None:
    row = {
        "research_return_1d": 0.03,
        "source_confidence": 0.8,
    }

    assert _score(
        row,
        ScoreRules(weighted_sum=[ScoreTerm(column="research_return_1d", weight=10.0)]),
    ) == pytest.approx(0.3)
    assert _score(
        row,
        ScoreRules(
            model_score=ModelScore(
                intercept=0.0,
                coefficients=[ScoreTerm(column="source_confidence", weight=2.0)],
                activation="sigmoid",
            )
        ),
    ) == pytest.approx(1.0 / (1.0 + math.exp(-1.6)))
    assert _score(
        {},
        ScoreRules(
            model_score=ModelScore(
                coefficients=[ScoreTerm(column="missing", weight=3.0)],
                activation="tanh",
                missing_value=0.5,
            )
        ),
    ) == pytest.approx(math.tanh(1.5))
    assert (
        _score(
            {"raw": 2.0},
            ScoreRules(
                model_score=ModelScore(
                    coefficients=[ScoreTerm(column="raw", weight=1.0)],
                    activation="clamp_0_1",
                )
            ),
        )
        == 1.0
    )
    assert _score({}, ScoreRules()) is None


def test_rank_tail_and_score_value_helpers_preserve_existing_buckets() -> None:
    assert _rank_score(None) is None
    assert _rank_score(-1.0) == 0.0
    assert _rank_score(2.0) == 1.0

    assert _tail_bucket(None) == "none"
    assert _tail_bucket(0.8) == "top"
    assert _tail_bucket(0.2) == "bottom"
    assert _tail_bucket(0.5) == "middle"

    assert _score_value({"raw_score": 0.25}) == 0.25
    assert _score_value({"raw_score": "0.25"}) is None


def test_side_column_maps_supported_values_and_rejects_unknown_values() -> None:
    assert _side_from_column({"direction": "BUY"}, "direction") == "long"
    assert _side_from_column({"direction": "bear"}, "direction") == "short"
    assert _side_from_column({"direction": "flat"}, "direction") == "none"
    with pytest.raises(StrategyAuthoringValidationError, match="Unsupported side value"):
        _side_from_column({"direction": "sideways"}, "direction")


def test_selected_side_uses_side_column_only_after_entry_passes() -> None:
    rules = AuthoringRules(
        side="auto",
        side_column="direction",
        entry=EntryRules(all=[Condition(column="trade_allowed", op="is_true")]),
    )

    assert _selected_side({"trade_allowed": False, "direction": "long"}, rules) == (None, None)
    assert _selected_side({"trade_allowed": True, "direction": "short"}, rules) == ("short", None)
    assert _selected_side({"trade_allowed": True, "direction": "flat"}, rules) == (
        "none",
        "side_column_hold",
    )


def test_selected_side_flags_ambiguous_long_and_short_entries() -> None:
    rules = AuthoringRules(
        side="auto",
        entry=EntryRules(all=[Condition(column="trade_allowed", op="is_true")]),
        long_entry=EntryRules(all=[Condition(column="long_flag", op="is_true")]),
        short_entry=EntryRules(all=[Condition(column="short_flag", op="is_true")]),
    )

    assert _selected_side(
        {"trade_allowed": True, "long_flag": True, "short_flag": True},
        rules,
    ) == ("none", "ambiguous_side")
    assert _selected_side(
        {"trade_allowed": True, "long_flag": True, "short_flag": False},
        rules,
    ) == ("long", None)
    assert _selected_side(
        {"trade_allowed": True, "long_flag": False, "short_flag": True},
        rules,
    ) == ("short", None)


def test_selected_side_auto_cross_sectional_defaults_to_long() -> None:
    rules = AuthoringRules(
        side="auto",
        entry=EntryRules(all=[Condition(column="trade_allowed", op="is_true")]),
        cross_sectional=CrossSectionalRules(long_top_n=1),
        score=ScoreRules(weighted_sum=[ScoreTerm(column="research_return_1d", weight=1.0)]),
    )

    assert _selected_side({"trade_allowed": True, "research_return_1d": 0.1}, rules) == (
        "long",
        None,
    )
