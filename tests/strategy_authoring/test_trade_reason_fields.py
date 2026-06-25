from types import SimpleNamespace

from sis.research.strategy_lab.authoring.compiler.trade_reason_fields import (
    _trade_reason_fields,
)


def _spec(*, reason_code: str = "base_reason"):
    return SimpleNamespace(rules=SimpleNamespace(reason_code=reason_code))


def test_trade_reason_fields_use_default_reason_code() -> None:
    assert _trade_reason_fields(
        spec=_spec(reason_code="entry_reason"),
        regime=None,
        reason_codes=None,
    ) == {
        "reason_codes": ["entry_reason"],
        "block_reasons": [],
    }


def test_trade_reason_fields_preserve_custom_reason_codes() -> None:
    assert _trade_reason_fields(
        spec=_spec(),
        regime=None,
        reason_codes=["pair_trade_v1", "multi_leg", "hedge_leg"],
    ) == {
        "reason_codes": ["pair_trade_v1", "multi_leg", "hedge_leg"],
        "block_reasons": [],
    }


def test_trade_reason_fields_append_regime_marker() -> None:
    assert _trade_reason_fields(
        spec=_spec(),
        regime=SimpleNamespace(name="high_vol"),
        reason_codes=["entry"],
    ) == {
        "reason_codes": ["entry", "regime:high_vol"],
        "block_reasons": [],
    }


def test_trade_reason_fields_empty_reason_codes_fall_back_to_default() -> None:
    assert _trade_reason_fields(
        spec=_spec(reason_code="fallback_reason"),
        regime=SimpleNamespace(name="low_vol"),
        reason_codes=[],
    ) == {
        "reason_codes": ["fallback_reason", "regime:low_vol"],
        "block_reasons": [],
    }


def test_trade_reason_fields_return_fresh_block_reason_lists() -> None:
    first = _trade_reason_fields(spec=_spec(), regime=None, reason_codes=None)
    second = _trade_reason_fields(spec=_spec(), regime=None, reason_codes=None)

    first["block_reasons"].append("mutated")

    assert second["block_reasons"] == []
