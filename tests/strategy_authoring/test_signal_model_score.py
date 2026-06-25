from __future__ import annotations

import math

import pytest

from sis.research.strategy_lab.authoring.compiler.signal_model_score import _model_score_value
from sis.research.strategy_lab.authoring.contracts.core import ModelScore, ScoreTerm


def test_model_score_value_uses_identity_activation_by_default() -> None:
    value = _model_score_value(
        {"alpha": 0.5},
        ModelScore(
            intercept=0.25,
            coefficients=[ScoreTerm(column="alpha", weight=2.0)],
        ),
    )

    assert value == pytest.approx(1.25)


def test_model_score_value_uses_stable_sigmoid_branches() -> None:
    positive = _model_score_value(
        {"alpha": 1.0},
        ModelScore(
            coefficients=[ScoreTerm(column="alpha", weight=20.0)],
            activation="sigmoid",
        ),
    )
    negative = _model_score_value(
        {"alpha": -1.0},
        ModelScore(
            coefficients=[ScoreTerm(column="alpha", weight=20.0)],
            activation="sigmoid",
        ),
    )

    assert positive == pytest.approx(1.0 / (1.0 + math.exp(-20.0)))
    assert negative == pytest.approx(math.exp(-20.0) / (1.0 + math.exp(-20.0)))


def test_model_score_value_applies_tanh_with_missing_value() -> None:
    value = _model_score_value(
        {},
        ModelScore(
            coefficients=[ScoreTerm(column="missing", weight=3.0)],
            activation="tanh",
            missing_value=0.5,
        ),
    )

    assert value == pytest.approx(math.tanh(1.5))


def test_model_score_value_clamps_to_unit_interval() -> None:
    assert (
        _model_score_value(
            {"raw": 2.0},
            ModelScore(
                coefficients=[ScoreTerm(column="raw", weight=1.0)],
                activation="clamp_0_1",
            ),
        )
        == 1.0
    )
    assert (
        _model_score_value(
            {"raw": -1.0},
            ModelScore(
                coefficients=[ScoreTerm(column="raw", weight=1.0)],
                activation="clamp_0_1",
            ),
        )
        == 0.0
    )


def test_model_score_value_returns_none_when_no_coefficient_is_usable() -> None:
    value = _model_score_value(
        {"missing": "not numeric"},
        ModelScore(coefficients=[ScoreTerm(column="missing", weight=3.0)]),
    )

    assert value is None
