from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.paper_preview_order_fields import (
    _paper_preview_order_fields,
)


def test_paper_preview_order_fields_use_selected_row_values() -> None:
    fields = _paper_preview_order_fields(
        row={
            "entry_order_type": "limit",
            "entry_limit_offset_bps": 5.0,
            "entry_stop_offset_bps": 12.0,
            "entry_timeout_minutes": 30,
            "entry_time_in_force": "ioc",
            "entry_post_only": 1,
            "entry_reduce_only": True,
        },
        selected=True,
    )

    assert fields == {
        "entry_order_type": "limit",
        "entry_limit_offset_bps": 5.0,
        "entry_stop_offset_bps": 12.0,
        "entry_timeout_minutes": 30,
        "entry_time_in_force": "ioc",
        "entry_post_only": True,
        "entry_reduce_only": True,
    }


def test_paper_preview_order_fields_preserve_unselected_defaults() -> None:
    fields = _paper_preview_order_fields(
        row={
            "entry_order_type": "stop_market",
            "entry_limit_offset_bps": 5.0,
            "entry_time_in_force": "fok",
            "entry_post_only": True,
            "entry_reduce_only": True,
        },
        selected=False,
    )

    assert fields == {
        "entry_order_type": "market",
        "entry_limit_offset_bps": None,
        "entry_stop_offset_bps": None,
        "entry_timeout_minutes": None,
        "entry_time_in_force": "gtc",
        "entry_post_only": False,
        "entry_reduce_only": False,
    }
