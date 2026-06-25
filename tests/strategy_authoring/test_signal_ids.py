from __future__ import annotations

from sis.research.strategy_lab.authoring.compiler.signal_ids import (
    _compiled_signal_id,
    _multi_leg_group_id,
    _signal_id,
)

from .helpers import _feature_rows, _write_data, _write_spec, load_authoring_spec


def test_signal_id_is_stable_and_side_sensitive(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    binding = spec.experiment.symbol_bindings[0]
    row = _feature_rows()[0]

    first = _signal_id(spec, row, binding, side="long")
    second = _signal_id(spec, row, binding, side="long")
    short = _signal_id(spec, row, binding, side="short")

    assert first == second
    assert first != short


def test_compiled_signal_id_uses_compiled_row_identity(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    row = {
        "ts_signal": "2026-01-01T00:00:00+00:00",
        "execution_symbol": "QQQ100",
    }

    first = _compiled_signal_id(spec, row, side="none")
    second = _compiled_signal_id(spec, row, side="none")
    close = _compiled_signal_id(spec, row, side="close")

    assert first == second
    assert first != close


def test_multi_leg_group_id_is_stable_and_base_side_sensitive(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    row = _feature_rows()[0]

    long_group = _multi_leg_group_id(spec, row, base_side="long")
    repeated_long_group = _multi_leg_group_id(spec, row, base_side="long")
    short_group = _multi_leg_group_id(spec, row, base_side="short")

    assert long_group == repeated_long_group
    assert long_group != short_group
