from sis.research.strategy_lab.authoring.compiler.multi_leg_order_overrides import (
    _multi_leg_order_overrides,
)
from sis.research.strategy_lab.authoring.contracts.multi_leg import MultiLegEntry


def test_multi_leg_order_overrides_resolve_fixed_values() -> None:
    leg = MultiLegEntry(
        real_market_symbol="BBB",
        side="opposite",
        entry_type="limit",
        limit_offset_bps=35,
        timeout_minutes=45,
        time_in_force="gtd",
        post_only=True,
        reduce_only=False,
    )

    assert _multi_leg_order_overrides(
        row={},
        leg=leg,
        default_entry_type="market",
        default_time_in_force="gtc",
    ) == {
        "entry_type": "limit",
        "limit_offset_bps": 35.0,
        "timeout_minutes": 45,
        "time_in_force": "gtd",
        "post_only": True,
        "reduce_only": False,
    }


def test_multi_leg_order_overrides_resolve_columns_and_default_fallbacks() -> None:
    row = {
        "entry_type": "limit",
        "limit_bps": "35",
        "stop_bps": "12",
        "timeout": 45,
        "tif": "gtd",
        "post_only": False,
        "reduce_only": True,
    }
    leg = MultiLegEntry(
        real_market_symbol="BBB",
        side="opposite",
        entry_type_column="entry_type",
        limit_offset_bps_column="limit_bps",
        stop_offset_bps_column="stop_bps",
        timeout_minutes_column="timeout",
        time_in_force_column="tif",
        post_only=True,
        post_only_column="post_only",
        reduce_only=False,
        reduce_only_column="reduce_only",
    )

    assert _multi_leg_order_overrides(
        row=row,
        leg=leg,
        default_entry_type="market",
        default_time_in_force="gtc",
    ) == {
        "entry_type": "limit",
        "limit_offset_bps": 35.0,
        "stop_offset_bps": 12.0,
        "timeout_minutes": 45,
        "time_in_force": "gtd",
        "post_only": False,
        "reduce_only": True,
    }


def test_multi_leg_order_overrides_omit_unset_inherited_defaults() -> None:
    leg = MultiLegEntry(
        real_market_symbol="BBB",
        side="opposite",
    )

    assert (
        _multi_leg_order_overrides(
            row={},
            leg=leg,
            default_entry_type="limit",
            default_time_in_force="gtd",
        )
        == {}
    )
