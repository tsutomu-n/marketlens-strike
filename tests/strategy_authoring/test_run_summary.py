from __future__ import annotations

import json

from sis.research.strategy_lab.authoring.compiler.run_summary import (
    write_authoring_run_summary,
)

from .helpers import _write_data, _write_spec, load_authoring_spec


def test_write_authoring_run_summary_records_explicit_counts_and_artifacts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)
    artifacts = {
        "signals_parquet": data_dir / "research/signals.parquet",
        "metrics": data_dir / "research/metrics.json",
    }

    out = write_authoring_run_summary(
        spec,
        data_dir=data_dir,
        through="paper-preview",
        artifacts=artifacts,
        signal_count=5,
        source_signal_count=8,
        evaluation_signal_count=3,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert out == data_dir / "research/strategy_authoring_run.json"
    assert payload == {
        "schema_version": "strategy_authoring_run.v1",
        "strategy_id": spec.experiment.strategy_id,
        "through": "paper-preview",
        "signal_count": 5,
        "source_signal_count": 8,
        "evaluation_signal_count": 3,
        "paper_only": True,
        "live_order_submitted": False,
        "artifacts": {
            "signals_parquet": str(artifacts["signals_parquet"]),
            "metrics": str(artifacts["metrics"]),
        },
    }


def test_write_authoring_run_summary_defaults_source_and_evaluation_counts(tmp_path) -> None:
    data_dir = tmp_path / "data"
    spec_path = tmp_path / "spec.yaml"
    _write_data(data_dir)
    _write_spec(spec_path)
    spec = load_authoring_spec(spec_path)

    out = write_authoring_run_summary(
        spec,
        data_dir=data_dir,
        through="signals",
        artifacts={},
        signal_count=2,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["source_signal_count"] == 2
    assert payload["evaluation_signal_count"] == 2
    assert payload["artifacts"] == {}
