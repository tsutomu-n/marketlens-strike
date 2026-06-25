from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from sis.research.ndx.artifacts import DAG_ID
from sis.research.ndx.artifacts import sha256_file
from sis.research.ndx.artifacts import sha256_json
from sis.research.ndx.artifacts import write_json
from sis.research.ndx.feature_panel import MODEL_FACTOR_COLUMNS
from sis.research.ndx.feature_panel import SOURCE_TIMESTAMP_COLUMNS
from sis.research.ndx.residual_validation_artifacts import artifact_reason_codes
from sis.research.ndx.residual_validation_artifacts import artifact_paths
from sis.research.ndx.residual_validation_artifacts import factor_column_status
from sis.research.ndx.residual_validation_artifacts import frame_lineage_status
from sis.research.ndx.residual_validation_artifacts import load_and_check_artifacts
from sis.research.ndx.residual_validation_artifacts import REQUIRED_ARTIFACTS
from sis.research.ndx.residual_validation_artifacts import residual_neutralized_alignment_status
from sis.research.ndx.residual_validation_artifacts import source_timestamp_audit_status


def test_frame_lineage_status_reports_missing_and_mismatch() -> None:
    missing = frame_lineage_status(
        pl.DataFrame({"date": ["2026-01-01"]}),
        dag_hash="hash-a",
        feature_manifest_hash="feature-hash",
        reason_code="LINEAGE_MISMATCH",
    )
    assert missing == {
        "status": "fail",
        "reason_code": "LINEAGE_MISMATCH",
        "missing_columns": ["dag_artifact_hash", "dag_id", "feature_manifest_hash"],
        "mismatch_count": 1,
    }

    mismatch = frame_lineage_status(
        pl.DataFrame(
            {
                "dag_id": ["HYP-NDX-001"],
                "dag_artifact_hash": ["hash-b"],
                "feature_manifest_hash": ["feature-hash"],
            }
        ),
        dag_hash="hash-a",
        feature_manifest_hash="feature-hash",
        reason_code="LINEAGE_MISMATCH",
    )
    assert mismatch["status"] == "fail"
    assert mismatch["reason_code"] == "LINEAGE_MISMATCH"
    assert mismatch["mismatch_count"] == 1


def test_residual_neutralized_alignment_status_compares_sorted_dates() -> None:
    status = residual_neutralized_alignment_status(
        pl.DataFrame({"date": ["2026-01-02", "2026-01-01"]}),
        pl.DataFrame({"date": ["2026-01-01", "2026-01-02"]}),
    )
    assert status["status"] == "pass"
    assert status["reason_code"] == "ok"

    missing = residual_neutralized_alignment_status(
        pl.DataFrame({"date": ["2026-01-01"]}),
        pl.DataFrame({"value": [1.0]}),
    )
    assert missing["status"] == "fail"
    assert missing["reason_code"] == "RESIDUAL_NEUTRALIZED_ALIGNMENT_MISSING_DATE"


def test_source_timestamp_audit_status_detects_late_source_timestamps() -> None:
    frame = pl.DataFrame(
        {
            "feature_ts": ["2026-01-02T00:00:00Z"],
            "source_ts_max": ["2026-01-02T00:00:00Z"],
        }
        | {column: ["2026-01-02T00:00:00Z"] for column in SOURCE_TIMESTAMP_COLUMNS}
        | {SOURCE_TIMESTAMP_COLUMNS[0]: ["2026-01-02T00:00:01Z"]}
    )

    status = source_timestamp_audit_status(frame)

    assert status["status"] == "fail"
    assert status["reason_code"] == "SOURCE_TIMESTAMP_EXCEEDS_FEATURE_TS"
    assert status["per_source_late_counts"][SOURCE_TIMESTAMP_COLUMNS[0]] == 1


def test_factor_column_status_and_artifact_reason_codes() -> None:
    status = factor_column_status(
        {
            "factor_columns": [
                "qqq_close",
                "future_return",
            ]
        }
    )
    assert status["status"] == "fail"
    assert status["reason_code"] == "MODEL_FACTOR_COLUMNS_INVALID"
    assert "qqq_close" in status["suspicious_columns"]
    assert "future_return" in status["suspicious_columns"]

    assert artifact_reason_codes(
        {
            "lineage": {"status": "fail", "reason_code": "LINEAGE_MISMATCH"},
            "metrics": {"status": "pass", "reason_code": "ok"},
            "plain": "pass",
        }
    ) == ["LINEAGE_MISMATCH"]


def test_required_artifact_paths_preserve_artifact_and_report_roots(tmp_path) -> None:
    artifact_dir = tmp_path / "artifacts"
    reports_dir = tmp_path / "reports"

    assert REQUIRED_ARTIFACTS == {
        "source_resolution": "source_resolution/data_source_resolution.json",
        "feature_panel": "ndx_feature_panel.parquet",
        "feature_manifest": "ndx_feature_manifest.json",
        "residuals": "open_gap_residuals.parquet",
        "residual_manifest": "open_gap_residual_manifest.json",
        "diagnostics": "../reports/ndx_residual_diagnostics.json",
        "neutralized_residuals": "../reports/neutralized_residuals.parquet",
        "neutralization_pre_report": "../reports/ndx_neutralization_pre_report.md",
        "counter_dag_skeleton": "../reports/ndx_counter_dag_refutation_skeleton.md",
    }

    assert artifact_paths(artifact_dir=artifact_dir, reports_dir=reports_dir) == {
        "source_resolution": artifact_dir / "source_resolution/data_source_resolution.json",
        "feature_panel": artifact_dir / "ndx_feature_panel.parquet",
        "feature_manifest": artifact_dir / "ndx_feature_manifest.json",
        "residuals": artifact_dir / "open_gap_residuals.parquet",
        "residual_manifest": artifact_dir / "open_gap_residual_manifest.json",
        "diagnostics": reports_dir / "ndx_residual_diagnostics.json",
        "neutralized_residuals": reports_dir / "neutralized_residuals.parquet",
        "neutralization_pre_report": reports_dir / "ndx_neutralization_pre_report.md",
        "counter_dag_skeleton": reports_dir / "ndx_counter_dag_refutation_skeleton.md",
    }


def test_load_and_check_artifacts_reads_files_and_builds_statuses(tmp_path) -> None:
    paths = _write_valid_artifact_bundle(tmp_path)

    loaded = load_and_check_artifacts(paths)

    assert loaded["feature_panel"].height == 1
    assert loaded["residuals"].height == 1
    assert loaded["neutralized"].height == 1
    assert loaded["feature_manifest"]["feature_panel_hash"] == sha256_file(paths["feature_panel"])
    checks = loaded["artifact_checks"]
    assert checks["dag_id"] == DAG_ID
    assert checks["feature_panel_lineage"]["status"] == "pass"
    assert checks["residual_lineage"]["status"] == "pass"
    assert checks["neutralized_lineage"]["status"] == "pass"
    assert checks["source_timestamp_audit"]["status"] == "pass"
    assert checks["model_factor_columns"]["status"] == "pass"


def test_load_and_check_artifacts_rejects_feature_panel_hash_mismatch(tmp_path) -> None:
    paths = _write_valid_artifact_bundle(tmp_path)
    pl.read_parquet(paths["feature_panel"]).with_columns(pl.lit(1).alias("extra")).write_parquet(
        paths["feature_panel"]
    )

    with pytest.raises(ValueError, match="REVISE_2_3_FEATURE_PANEL_HASH_MISMATCH"):
        load_and_check_artifacts(paths)


def _write_valid_artifact_bundle(tmp_path: Path) -> dict[str, Path]:
    artifact_dir = tmp_path / "artifacts"
    reports_dir = tmp_path / "reports"
    artifact_dir.mkdir(parents=True)
    reports_dir.mkdir(parents=True)
    (artifact_dir / "source_resolution").mkdir()
    paths = artifact_paths(artifact_dir=artifact_dir, reports_dir=reports_dir)
    dag_hash = "sha256:" + "1" * 64
    feature_manifest_hash = ""
    source_timestamp_values = {
        column: ["2026-01-01T14:30:00+00:00"] for column in SOURCE_TIMESTAMP_COLUMNS
    }
    feature_panel = pl.DataFrame(
        {
            "date": ["2026-01-01"],
            "dag_id": [DAG_ID],
            "dag_artifact_hash": [dag_hash],
            "feature_ts": ["2026-01-01T14:31:00+00:00"],
            "source_ts_max": ["2026-01-01T14:30:00+00:00"],
            **source_timestamp_values,
        }
    )
    feature_panel.write_parquet(paths["feature_panel"])
    feature_manifest = {
        "schema_version": "ndx_feature_manifest.v1",
        "dag_id": DAG_ID,
        "dag_artifact_hash": dag_hash,
        "feature_panel_hash": sha256_file(paths["feature_panel"]),
        "row_count": feature_panel.height,
    }
    feature_manifest["feature_manifest_hash"] = sha256_json(feature_manifest)
    feature_manifest_hash = str(feature_manifest["feature_manifest_hash"])
    residuals = pl.DataFrame(
        {
            "date": ["2026-01-01"],
            "dag_id": [DAG_ID],
            "dag_artifact_hash": [dag_hash],
            "feature_manifest_hash": [feature_manifest_hash],
            "model_window_end": ["2025-12-31"],
            "model_training_row_count": [20],
            "open_gap_residual": [0.01],
            "qqq_open_to_close_return": [0.02],
        }
    )
    residuals.write_parquet(paths["residuals"])
    neutralized = pl.DataFrame(
        {
            "date": ["2026-01-01"],
            "dag_id": [DAG_ID],
            "dag_artifact_hash": [dag_hash],
            "feature_manifest_hash": [feature_manifest_hash],
            "combined_neutralized_residual": [0.01],
        }
    )
    neutralized.write_parquet(paths["neutralized_residuals"])
    write_json(
        paths["source_resolution"],
        {
            "dag_id": DAG_ID,
            "dag_artifact_hash": dag_hash,
        },
    )
    write_json(paths["feature_manifest"], feature_manifest)
    write_json(
        paths["residual_manifest"],
        {
            "dag_id": DAG_ID,
            "dag_artifact_hash": dag_hash,
            "feature_manifest_hash": feature_manifest_hash,
            "residuals_hash": sha256_file(paths["residuals"]),
            "factor_columns": list(MODEL_FACTOR_COLUMNS),
        },
    )
    write_json(
        paths["diagnostics"],
        {
            "dag_id": DAG_ID,
            "dag_artifact_hash": dag_hash,
            "feature_manifest_hash": feature_manifest_hash,
            "neutralized_residuals_hash": sha256_file(paths["neutralized_residuals"]),
        },
    )
    return paths
