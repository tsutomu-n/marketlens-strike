from __future__ import annotations

from dataclasses import dataclass

from sis.research.strategy_lab.authoring.compiler.regime_overrides import (
    _exit_override,
    _exit_override_column,
    _matching_regime_override,
    _override_column,
    _override_value,
    _regime_value,
)
from sis.research.strategy_lab.authoring.io import template_yaml

from .helpers import _write_data, load_authoring_spec


def _spec(tmp_path):
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "regime-overrides.yaml"
    _write_data(data_dir)
    spec_path.write_text(
        template_yaml().replace(
            "  exit:\n    stop_loss_bps: 150",
            "  regime_overrides:\n"
            "    - name: high_vol\n"
            "      when:\n"
            "        all:\n"
            "          - column: vix_level\n"
            "            op: gte\n"
            "            value: 25\n"
            "      stop_loss_bps: 90\n"
            "      position_weight: 0.25\n"
            "  exit:\n    stop_loss_bps: 150",
        ),
        encoding="utf-8",
    )
    return load_authoring_spec(spec_path)


@dataclass
class _Overrides:
    stop_loss_bps: float | None = None
    position_weight: float | None = None


def test_matching_regime_override_returns_first_matching_override(tmp_path) -> None:
    spec = _spec(tmp_path)

    matched = _matching_regime_override({"vix_level": 30.0}, spec)
    missing = _matching_regime_override({"vix_level": 20.0}, spec)

    assert matched is not None
    assert matched.name == "high_vol"
    assert missing is None


def test_regime_value_prefers_override_then_default() -> None:
    override = _Overrides(stop_loss_bps=90.0)

    assert _regime_value(override, "stop_loss_bps", 150.0) == 90.0
    assert _regime_value(override, "position_weight", 1.0) == 1.0
    assert _regime_value(None, "stop_loss_bps", 150.0) == 150.0


def test_exit_override_value_and_column_semantics() -> None:
    overrides = {"stop_loss_bps": 80.0}

    assert _exit_override(overrides, "stop_loss_bps", 150.0) == 80.0
    assert _exit_override({}, "stop_loss_bps", 150.0) == 150.0
    assert _exit_override(None, "stop_loss_bps", 150.0) == 150.0
    assert _exit_override_column(overrides, "stop_loss_bps", "stop_column") is None
    assert _exit_override_column({}, "stop_loss_bps", "stop_column") == "stop_column"


def test_generic_override_value_and_column_semantics() -> None:
    overrides = {"timeout_minutes": 15}

    assert _override_value(overrides, "timeout_minutes", 5) == 15
    assert _override_value({}, "timeout_minutes", 5) == 5
    assert _override_value(None, "timeout_minutes", 5) == 5
    assert _override_column(overrides, "timeout_minutes", "timeout_column") is None
    assert _override_column({}, "timeout_minutes", "timeout_column") == "timeout_column"
