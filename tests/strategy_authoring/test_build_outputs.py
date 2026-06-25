from __future__ import annotations

from datetime import datetime, timezone

from sis.research.strategy_lab.authoring.compiler.build_outputs import (
    _build_signal_frame_and_manifest,
)
from sis.research.strategy_lab.authoring.compiler.trade_rows import _trade_signal_row
from sis.research.strategy_lab.signal_artifact import (
    empty_signal_artifact_run_id,
    file_sha256,
    signal_artifact_run_id,
)

from .helpers import _feature_rows, _write_data, _write_spec, load_authoring_spec


def test_build_signal_frame_and_manifest_uses_empty_run_id_for_empty_rows(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    feature_path = data_dir / "research/feature_panel.parquet"

    frame, manifest = _build_signal_frame_and_manifest(
        rows=[],
        spec=spec,
        feature_path=feature_path,
        generated_at=generated_at,
    )

    feature_hash = file_sha256(feature_path)
    assert frame.is_empty()
    assert manifest.generated_at == generated_at
    assert manifest.feature_panel_sha256 == feature_hash
    assert manifest.signal_count == 0
    assert manifest.signal_artifact_run_id == empty_signal_artifact_run_id(
        generator_id="strategy_authoring",
        strategy_id=spec.experiment.strategy_id,
        strategy_family=spec.experiment.strategy_family,
        strategy_version=spec.experiment.strategy_version,
        symbol_bindings=spec.experiment.symbol_bindings,
        feature_panel_sha256=feature_hash,
    )


def test_build_signal_frame_and_manifest_validates_non_empty_rows(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    generated_at = datetime(2026, 1, 2, tzinfo=timezone.utc)
    feature_path = data_dir / "research/feature_panel.parquet"
    signal_row = _trade_signal_row(
        spec=spec,
        row=_feature_rows()[0],
        binding=spec.experiment.symbol_bindings[0],
        side="long",
        generated_at=generated_at,
        raw_score=0.8,
        rank=0.8,
    )

    frame, manifest = _build_signal_frame_and_manifest(
        rows=[signal_row],
        spec=spec,
        feature_path=feature_path,
        generated_at=generated_at,
    )

    assert frame.height == 1
    assert manifest.generated_at == generated_at
    assert manifest.signal_count == 1
    assert manifest.signal_artifact_run_id == signal_artifact_run_id(frame)
    assert manifest.generator_parameters == {
        "authoring_schema_version": spec.schema_version,
        "reason_code": spec.rules.reason_code,
    }
