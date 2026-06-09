from __future__ import annotations

from datetime import date, timedelta
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import polars as pl

from research.helpers import CONFIG_DIR
from sis.research.ndx.artifacts import (
    DAG_ID,
    dag_artifact_hash,
    sha256_file,
    sha256_json,
    write_json,
)
from sis.research.ndx.residual_validation import run_residual_validation_gate
from support.cli import invoke_cli
from support.cli import normalized_stdout


FIXTURE_DIR = Path("tests/fixtures/ndx")
REVIEW_FIXTURE_DIR = Path("tests/fixtures/research_layer_2_2/reviews")


def _write_approve_review_result(review_dir: Path) -> Path:
    pack = json.loads((review_dir / "llm_review_input.json").read_text(encoding="utf-8"))
    text = (REVIEW_FIXTURE_DIR / "valid_approve.json").read_text(encoding="utf-8")
    payload = json.loads(text.replace("sha256:PACK_HASH_PLACEHOLDER", pack["pack_hash"]))
    result_path = review_dir / "llm_review_result.json"
    result_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return result_path


def _prepare_layer22_approval(tmp_path: Path) -> Path:
    artifact_dir = tmp_path / "data/research/ndx"
    review_dir = artifact_dir / "review"
    assert (
        invoke_cli(
            ["research-layer22-export", "--root", str(CONFIG_DIR), "--out", str(artifact_dir)]
        ).exit_code
        == 0
    )
    assert (
        invoke_cli(
            ["research-layer22-review-pack", "--root", str(CONFIG_DIR), "--out", str(review_dir)]
        ).exit_code
        == 0
    )
    review_result = _write_approve_review_result(review_dir)
    assert (
        invoke_cli(
            [
                "research-layer22-review-import",
                "--pack",
                str(review_dir / "llm_review_input.json"),
                "--result",
                str(review_result),
            ]
        ).exit_code
        == 0
    )
    result = invoke_cli(
        [
            "research-layer22-exit-gate",
            "--root",
            str(CONFIG_DIR),
            "--pack",
            str(review_dir / "llm_review_input.json"),
            "--review",
            str(review_dir / "normalized_review.json"),
            "--out",
            str(review_dir),
        ]
    )
    assert result.exit_code == 0, result.stdout
    return artifact_dir


def _build_layer23_artifacts(artifact_dir: Path, reports_dir: Path) -> None:
    assert (
        invoke_cli(
            [
                "research-ndx-source-resolve",
                "--root",
                str(CONFIG_DIR),
                "--artifact-dir",
                str(artifact_dir),
                "--out",
                str(artifact_dir),
            ]
        ).exit_code
        == 0
    )
    assert (
        invoke_cli(
            [
                "research-ndx-feature-panel",
                "--root",
                str(CONFIG_DIR),
                "--artifact-dir",
                str(artifact_dir),
                "--input-root",
                str(FIXTURE_DIR),
                "--out",
                str(artifact_dir),
            ]
        ).exit_code
        == 0
    )
    assert (
        invoke_cli(
            [
                "research-ndx-residual",
                "--feature-panel",
                str(artifact_dir / "ndx_feature_panel.parquet"),
                "--feature-manifest",
                str(artifact_dir / "ndx_feature_manifest.json"),
                "--out",
                str(artifact_dir),
            ]
        ).exit_code
        == 0
    )
    assert (
        invoke_cli(
            [
                "research-ndx-diagnostics",
                "--residuals",
                str(artifact_dir / "open_gap_residuals.parquet"),
                "--residual-manifest",
                str(artifact_dir / "open_gap_residual_manifest.json"),
                "--out",
                str(reports_dir),
            ]
        ).exit_code
        == 0
    )


def test_layer24_current_layer23_artifacts_fail_closed_for_sample_size(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = tmp_path / "data/reports"
    _build_layer23_artifacts(artifact_dir, reports_dir)

    result = run_residual_validation_gate(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        reports_dir=reports_dir,
        out_dir=artifact_dir,
    )

    decision = json.loads(result.decision_path.read_text(encoding="utf-8"))
    assert result.decision == "REVISE_2_3"
    assert "SOURCE_TIMESTAMP_AUDIT_MISSING" not in result.reason_codes
    assert "INSUFFICIENT_VALIDATION_SAMPLE" in result.reason_codes
    assert "INSUFFICIENT_VALIDATION_ERAS" in result.reason_codes
    assert decision["permits_strategy_lab_research_only_export"] is False
    assert decision["permits_backtest"] is False


def test_layer24_cli_writes_decision_and_reports_without_strategy_signals(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = tmp_path / "data/reports"
    _build_layer23_artifacts(artifact_dir, reports_dir)

    result = invoke_cli(
        [
            "research-ndx-residual-validate",
            "--root",
            str(CONFIG_DIR),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--out",
            str(artifact_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    assert "status=pass" in normalized_stdout(result)
    assert "decision=REVISE_2_3" in normalized_stdout(result)
    assert (artifact_dir / "residual_validation_summary.json").exists()
    assert (artifact_dir / "residual_validation_decision.json").exists()
    assert (reports_dir / "ndx_residual_validation_report.md").exists()
    assert (reports_dir / "ndx_counter_dag_refutation_report.md").exists()
    assert not (artifact_dir / "strategy_signals.parquet").exists()
    assert not (artifact_dir / "research/strategy_signals.parquet").exists()
    _validate_json_artifact(
        schema_path=Path("schemas/ndx_residual_validation_summary.v1.schema.json"),
        artifact_path=artifact_dir / "residual_validation_summary.json",
    )
    _validate_json_artifact(
        schema_path=Path("schemas/ndx_residual_validation_decision.v1.schema.json"),
        artifact_path=artifact_dir / "residual_validation_decision.json",
    )


def test_layer24_revises_2_2_for_dag_hash_mismatch(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = tmp_path / "data/reports"
    _write_synthetic_layer23_artifacts(artifact_dir, reports_dir, row_count=90, mode="approve")
    manifest_path = artifact_dir / "ndx_feature_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["dag_artifact_hash"] = "sha256:" + "0" * 64
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = run_residual_validation_gate(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        reports_dir=reports_dir,
        out_dir=artifact_dir,
    )

    assert result.decision == "REVISE_2_2"
    assert "REVISE_2_2_DAG_ARTIFACT_HASH_MISMATCH" in result.reason_codes


def test_layer24_revises_2_3_for_feature_manifest_self_hash_mismatch(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = tmp_path / "data/reports"
    _write_synthetic_layer23_artifacts(artifact_dir, reports_dir, row_count=90, mode="approve")
    manifest_path = artifact_dir / "ndx_feature_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["row_count"] = manifest["row_count"] + 1
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    result = run_residual_validation_gate(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        reports_dir=reports_dir,
        out_dir=artifact_dir,
    )

    assert result.decision == "REVISE_2_3"
    assert "REVISE_2_3_FEATURE_MANIFEST_HASH_MISMATCH" in result.reason_codes


def test_layer24_revises_2_3_for_late_per_source_timestamp(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = tmp_path / "data/reports"
    _write_synthetic_layer23_artifacts(artifact_dir, reports_dir, row_count=90, mode="approve")
    feature_panel_path = artifact_dir / "ndx_feature_panel.parquet"
    frame = pl.read_parquet(feature_panel_path)
    late_ts = "2026-01-01T14:32:00+00:00"
    frame.with_columns(
        [
            pl.when(pl.col("date") == date(2026, 1, 1))
            .then(pl.lit(late_ts))
            .otherwise(pl.col("vix_source_ts"))
            .alias("vix_source_ts"),
            pl.when(pl.col("date") == date(2026, 1, 1))
            .then(pl.lit(late_ts))
            .otherwise(pl.col("source_ts_max"))
            .alias("source_ts_max"),
        ]
    ).write_parquet(feature_panel_path)
    _refresh_feature_manifest_lineage(artifact_dir=artifact_dir, reports_dir=reports_dir)

    result = run_residual_validation_gate(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        reports_dir=reports_dir,
        out_dir=artifact_dir,
    )

    assert result.decision == "REVISE_2_3"
    assert "SOURCE_TIMESTAMP_EXCEEDS_FEATURE_TS" in result.reason_codes


def test_layer24_revises_2_3_for_invalid_residual_factor_columns(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = tmp_path / "data/reports"
    _write_synthetic_layer23_artifacts(artifact_dir, reports_dir, row_count=90, mode="approve")
    residual_manifest_path = artifact_dir / "open_gap_residual_manifest.json"
    residual_manifest = json.loads(residual_manifest_path.read_text(encoding="utf-8"))
    residual_manifest["factor_columns"] = [*residual_manifest["factor_columns"], "qqq_close"]
    residual_manifest_path.write_text(
        json.dumps(residual_manifest, indent=2) + "\n", encoding="utf-8"
    )

    result = run_residual_validation_gate(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        reports_dir=reports_dir,
        out_dir=artifact_dir,
    )

    assert result.decision == "REVISE_2_3"
    assert "MODEL_FACTOR_COLUMNS_INVALID" in result.reason_codes


def test_layer24_revises_2_3_for_residual_frame_lineage_mismatch(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = tmp_path / "data/reports"
    _write_synthetic_layer23_artifacts(artifact_dir, reports_dir, row_count=90, mode="approve")
    residuals_path = artifact_dir / "open_gap_residuals.parquet"
    pl.read_parquet(residuals_path).with_columns(
        pl.lit("HYP-NDX-OTHER").alias("dag_id")
    ).write_parquet(residuals_path)
    residual_manifest_path = artifact_dir / "open_gap_residual_manifest.json"
    residual_manifest = json.loads(residual_manifest_path.read_text(encoding="utf-8"))
    residual_manifest["residuals_hash"] = sha256_file(residuals_path)
    residual_manifest_path.write_text(
        json.dumps(residual_manifest, indent=2) + "\n", encoding="utf-8"
    )

    result = run_residual_validation_gate(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        reports_dir=reports_dir,
        out_dir=artifact_dir,
    )

    assert result.decision == "REVISE_2_3"
    assert "RESIDUAL_LINEAGE_MISMATCH" in result.reason_codes


def test_layer24_approves_sufficient_synthetic_residual_sample(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = tmp_path / "data/reports"
    _write_synthetic_layer23_artifacts(artifact_dir, reports_dir, row_count=90, mode="approve")

    result = run_residual_validation_gate(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        reports_dir=reports_dir,
        out_dir=artifact_dir,
    )

    decision = json.loads(result.decision_path.read_text(encoding="utf-8"))
    assert result.decision == "APPROVE_STRATEGY_LAB_EXPORT"
    assert result.reason_codes == []
    assert decision["permits_strategy_lab_research_only_export"] is True
    assert decision["permits_paper_intent_preview"] is False


def test_layer24_rejects_known_factor_mirage(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = tmp_path / "data/reports"
    _write_synthetic_layer23_artifacts(artifact_dir, reports_dir, row_count=90, mode="mirage")

    result = run_residual_validation_gate(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        reports_dir=reports_dir,
        out_dir=artifact_dir,
    )

    assert result.decision == "REJECT_RESIDUAL"
    assert "KNOWN_FACTOR_MIRAGE" in result.reason_codes


def test_ndx_layer24_schemas_are_valid() -> None:
    for path in sorted(Path("schemas").glob("ndx_residual_validation_*.schema.json")):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def _write_synthetic_layer23_artifacts(
    artifact_dir: Path,
    reports_dir: Path,
    *,
    row_count: int,
    mode: str,
) -> None:
    reports_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "source_resolution").mkdir(parents=True, exist_ok=True)
    dag_hash = dag_artifact_hash(artifact_dir)
    write_json(
        artifact_dir / "source_resolution/data_source_resolution.json",
        {
            "schema_version": "ndx_source_resolution.v1",
            "dag_id": DAG_ID,
            "dag_artifact_hash": dag_hash,
            "resolved_sources": [{"source_id": "QQQ"}],
            "deferred_sources": [],
        },
    )
    dates = [date(2026, 1, 1) + timedelta(days=index) for index in range(row_count)]
    feature_panel = _feature_panel_frame(dates=dates, dag_hash=dag_hash)
    feature_panel_path = artifact_dir / "ndx_feature_panel.parquet"
    feature_panel.write_parquet(feature_panel_path)
    feature_manifest = {
        "schema_version": "ndx_feature_manifest.v1",
        "dag_id": DAG_ID,
        "dag_artifact_hash": dag_hash,
        "feature_panel_path": feature_panel_path.as_posix(),
        "feature_panel_hash": sha256_file(feature_panel_path),
        "row_count": row_count,
        "feature_columns": feature_panel.columns,
        "model_factor_columns": [
            "spy_gap",
            "smh_gap",
            "vix_change",
            "dgs10_delta",
            "mega_cap_basket_gap",
        ],
        "outcome_columns": ["qqq_open_to_close_return"],
    }
    feature_manifest["feature_manifest_hash"] = sha256_json(feature_manifest)
    write_json(artifact_dir / "ndx_feature_manifest.json", feature_manifest)
    residuals = _residual_frame(
        dates=dates,
        dag_hash=dag_hash,
        feature_manifest_hash=str(feature_manifest["feature_manifest_hash"]),
    )
    residuals_path = artifact_dir / "open_gap_residuals.parquet"
    residuals.write_parquet(residuals_path)
    residual_manifest = {
        "schema_version": "ndx_open_gap_residual_manifest.v1",
        "dag_id": DAG_ID,
        "dag_artifact_hash": dag_hash,
        "feature_manifest_hash": feature_manifest["feature_manifest_hash"],
        "residuals_path": residuals_path.as_posix(),
        "residuals_hash": sha256_file(residuals_path),
        "row_count": residuals.height,
        "target_column": "qqq_gap",
        "factor_columns": [
            "spy_gap",
            "smh_gap",
            "vix_change",
            "dgs10_delta",
            "mega_cap_basket_gap",
        ],
        "training_policy": "strictly_before_prediction_date",
        "emits_strategy_signals": False,
    }
    write_json(artifact_dir / "open_gap_residual_manifest.json", residual_manifest)
    neutralized = _neutralized_frame(
        residuals=residuals,
        feature_manifest_hash=str(feature_manifest["feature_manifest_hash"]),
        mode=mode,
    )
    neutralized_path = reports_dir / "neutralized_residuals.parquet"
    neutralized.write_parquet(neutralized_path)
    write_json(
        reports_dir / "ndx_residual_diagnostics.json",
        {
            "schema_version": "ndx_residual_diagnostics.v1",
            "dag_id": DAG_ID,
            "dag_artifact_hash": dag_hash,
            "feature_manifest_hash": feature_manifest["feature_manifest_hash"],
            "row_count": residuals.height,
            "missing_rate": 0,
            "residual_mean": 0,
            "residual_std": 1,
            "neutralized_residuals_path": neutralized_path.as_posix(),
            "neutralized_residuals_hash": sha256_file(neutralized_path),
            "emits_strategy_signals": False,
        },
    )
    (reports_dir / "ndx_neutralization_pre_report.md").write_text("synthetic\n", encoding="utf-8")
    (reports_dir / "ndx_counter_dag_refutation_skeleton.md").write_text(
        "synthetic\n", encoding="utf-8"
    )


def _refresh_feature_manifest_lineage(*, artifact_dir: Path, reports_dir: Path) -> None:
    feature_manifest_path = artifact_dir / "ndx_feature_manifest.json"
    feature_manifest = json.loads(feature_manifest_path.read_text(encoding="utf-8"))
    feature_manifest["feature_panel_hash"] = sha256_file(artifact_dir / "ndx_feature_panel.parquet")
    feature_manifest_without_self = {
        key: value for key, value in feature_manifest.items() if key != "feature_manifest_hash"
    }
    feature_manifest["feature_manifest_hash"] = sha256_json(feature_manifest_without_self)
    feature_manifest_path.write_text(
        json.dumps(feature_manifest, indent=2) + "\n", encoding="utf-8"
    )
    new_feature_hash = str(feature_manifest["feature_manifest_hash"])

    residuals_path = artifact_dir / "open_gap_residuals.parquet"
    pl.read_parquet(residuals_path).with_columns(
        pl.lit(new_feature_hash).alias("feature_manifest_hash")
    ).write_parquet(residuals_path)
    residual_manifest_path = artifact_dir / "open_gap_residual_manifest.json"
    residual_manifest = json.loads(residual_manifest_path.read_text(encoding="utf-8"))
    residual_manifest["feature_manifest_hash"] = new_feature_hash
    residual_manifest["residuals_hash"] = sha256_file(residuals_path)
    residual_manifest_path.write_text(
        json.dumps(residual_manifest, indent=2) + "\n", encoding="utf-8"
    )

    neutralized_path = reports_dir / "neutralized_residuals.parquet"
    pl.read_parquet(neutralized_path).with_columns(
        pl.lit(new_feature_hash).alias("feature_manifest_hash")
    ).write_parquet(neutralized_path)
    diagnostics_path = reports_dir / "ndx_residual_diagnostics.json"
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    diagnostics["feature_manifest_hash"] = new_feature_hash
    diagnostics["neutralized_residuals_hash"] = sha256_file(neutralized_path)
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8")


def _feature_panel_frame(*, dates: list[date], dag_hash: str) -> pl.DataFrame:
    rows = []
    for index, current_date in enumerate(dates):
        date_text = current_date.isoformat()
        source_ts = f"{date_text}T14:29:00+00:00"
        rows.append(
            {
                "date": current_date,
                "qqq_open": 100.0 + index,
                "qqq_close": 100.5 + index,
                "qqq_prev_close": 99.5 + index,
                "qqq_gap": 0.001 + index * 0.0001,
                "qqq_open_to_close_return": 0.002 + index * 0.0002,
                "spy_gap": 0.001 + index * 0.00003,
                "smh_gap": 0.0015 + index * 0.00004,
                "vix_level": 15.0 + index % 7,
                "vix_change": (-1) ** index * 0.1,
                "dgs10_delta": (-1) ** (index + 1) * 0.01,
                "mega_cap_basket_gap": 0.0012 + index * 0.00005,
                "feature_ts": f"{date_text}T14:31:00+00:00",
                "source_ts_max": source_ts,
                "source_tier": "fixture_required",
                "qqq_source_ts": source_ts,
                "spy_source_ts": source_ts,
                "smh_source_ts": source_ts,
                "mega_cap_basket_source_ts": source_ts,
                "vix_source_ts": source_ts,
                "dgs10_source_ts": source_ts,
                "dag_id": DAG_ID,
                "dag_artifact_hash": dag_hash,
            }
        )
    return pl.DataFrame(rows)


def _residual_frame(
    *,
    dates: list[date],
    dag_hash: str,
    feature_manifest_hash: str,
) -> pl.DataFrame:
    rows = []
    for index, current_date in enumerate(dates):
        raw = math_like_residual(index)
        rows.append(
            {
                "date": current_date,
                "actual_qqq_gap": raw + 0.001,
                "expected_qqq_gap": 0.001,
                "open_gap_residual": raw,
                "qqq_open_to_close_return": raw * 2.0 + 0.01,
                "model_window_start": dates[0],
                "model_window_end": current_date - timedelta(days=1),
                "model_training_row_count": 6 + index,
                "factor_columns": json.dumps(
                    ["spy_gap", "smh_gap", "vix_change", "dgs10_delta", "mega_cap_basket_gap"]
                ),
                "model_config_hash": f"model-{index}",
                "dag_id": DAG_ID,
                "dag_artifact_hash": dag_hash,
                "feature_manifest_hash": feature_manifest_hash,
                "spy_gap": raw * 0.1,
                "smh_gap": raw * 0.2,
                "vix_change": raw * -0.3,
                "dgs10_delta": raw * 0.05,
                "mega_cap_basket_gap": raw * 0.15,
            }
        )
    return pl.DataFrame(rows).with_columns(
        [
            pl.col("date").cast(pl.Date),
            pl.col("model_window_start").cast(pl.Date),
            pl.col("model_window_end").cast(pl.Date),
        ]
    )


def _neutralized_frame(
    *,
    residuals: pl.DataFrame,
    feature_manifest_hash: str,
    mode: str,
) -> pl.DataFrame:
    rows = []
    for row in residuals.to_dicts():
        raw = float(row["open_gap_residual"])
        value = raw * 0.8 if mode == "approve" else 0.0
        rows.append(
            {
                "date": row["date"],
                "dag_id": DAG_ID,
                "dag_artifact_hash": row["dag_artifact_hash"],
                "feature_manifest_hash": feature_manifest_hash,
                "raw_open_gap_residual": raw,
                "spy_gap_neutralized_residual": value,
                "smh_gap_neutralized_residual": value,
                "vix_change_neutralized_residual": value,
                "dgs10_delta_neutralized_residual": value,
                "mega_cap_basket_gap_neutralized_residual": value,
                "combined_neutralized_residual": value,
            }
        )
    return pl.DataFrame(rows).with_columns(pl.col("date").cast(pl.Date))


def math_like_residual(index: int) -> float:
    cycle = [0.012, -0.008, 0.015, -0.011, 0.006, -0.004, 0.01]
    return cycle[index % len(cycle)] + index * 0.00003


def _validate_json_artifact(*, schema_path: Path, artifact_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
