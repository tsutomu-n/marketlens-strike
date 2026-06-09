from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
import polars as pl
import pytest

from research.helpers import CONFIG_DIR
from sis.research.ndx.feature_panel import MODEL_FACTOR_COLUMNS, build_ndx_feature_panel
from sis.research.ndx.leakage import NdxLeakageError, validate_feature_panel
from sis.research.ndx.residual_model import build_open_gap_residuals
from sis.research.ndx.source_resolution import build_source_resolution
from sis.research.ndx.start_conditions import Layer23StartConditionError
from sis.research.ndx.start_conditions import require_layer23_start_conditions
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
    exit_result = invoke_cli(
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
    assert exit_result.exit_code == 0, exit_result.stdout
    return artifact_dir


def test_layer23_start_conditions_accept_clean_layer22_approval(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)

    result = require_layer23_start_conditions(root=CONFIG_DIR, artifact_dir=artifact_dir)

    assert result.dag_id == "HYP-NDX-001"
    assert result.freeze_manifest_path.exists()


def test_layer23_start_conditions_reject_missing_freeze_manifest(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    (artifact_dir / "review/layer_2_2_freeze_manifest.json").unlink()

    with pytest.raises(Layer23StartConditionError):
        require_layer23_start_conditions(root=CONFIG_DIR, artifact_dir=artifact_dir)


def test_source_resolution_marks_required_and_deferred_sources(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)

    result = build_source_resolution(
        root=CONFIG_DIR, artifact_dir=artifact_dir, out_dir=artifact_dir
    )

    payload = json.loads(result.artifact_path.read_text(encoding="utf-8"))
    assert payload["dag_id"] == "HYP-NDX-001"
    assert {item["source_id"] for item in payload["resolved_sources"]} == {
        "QQQ",
        "SPY",
        "SMH",
        "VIX",
        "DGS10",
        "MEGA_CAP_BASKET",
    }
    assert "NQ_FUTURES" in {item["source_id"] for item in payload["deferred_sources"]}
    assert payload["policy"]["external_api_allowed"] is False


def test_feature_panel_uses_fixture_sources_and_blocks_leaky_model_inputs(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)

    result = build_ndx_feature_panel(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        input_root=FIXTURE_DIR,
        out_dir=artifact_dir,
    )

    frame = pl.read_parquet(result.panel_path)
    assert result.row_count == 12
    assert "qqq_open_to_close_return" in frame.columns
    assert all(frame["source_ts_max"] <= frame["feature_ts"])
    assert set(MODEL_FACTOR_COLUMNS).issubset(frame.columns)
    with pytest.raises(NdxLeakageError):
        validate_feature_panel(frame, model_input_columns=[*MODEL_FACTOR_COLUMNS, "qqq_close"])


def test_open_gap_residual_trains_only_on_strict_prior_rows(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    feature = build_ndx_feature_panel(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        input_root=FIXTURE_DIR,
        out_dir=artifact_dir,
    )

    result = build_open_gap_residuals(
        feature_panel_path=feature.panel_path,
        feature_manifest_path=feature.manifest_path,
        out_dir=artifact_dir,
        min_window=6,
    )

    frame = pl.read_parquet(result.residuals_path)
    assert frame.height == 6
    for row in frame.to_dicts():
        assert row["model_window_end"] < row["date"]
        assert row["model_training_row_count"] >= 6
        assert row["factor_columns"] == json.dumps(MODEL_FACTOR_COLUMNS)
        assert row["dag_id"] == "HYP-NDX-001"
    assert "signal" not in result.residuals_path.name


def test_ndx_layer23_cli_writes_acceptance_artifacts_without_strategy_signals(tmp_path) -> None:
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = tmp_path / "data/reports"

    source_result = invoke_cli(
        [
            "research-ndx-source-resolve",
            "--root",
            str(CONFIG_DIR),
            "--artifact-dir",
            str(artifact_dir),
            "--out",
            str(artifact_dir),
        ]
    )
    assert source_result.exit_code == 0, source_result.stdout
    assert "status=pass" in normalized_stdout(source_result)

    panel_result = invoke_cli(
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
    )
    assert panel_result.exit_code == 0, panel_result.stdout

    residual_result = invoke_cli(
        [
            "research-ndx-residual",
            "--feature-panel",
            str(artifact_dir / "ndx_feature_panel.parquet"),
            "--feature-manifest",
            str(artifact_dir / "ndx_feature_manifest.json"),
            "--out",
            str(artifact_dir),
        ]
    )
    assert residual_result.exit_code == 0, residual_result.stdout

    diagnostics_result = invoke_cli(
        [
            "research-ndx-diagnostics",
            "--residuals",
            str(artifact_dir / "open_gap_residuals.parquet"),
            "--residual-manifest",
            str(artifact_dir / "open_gap_residual_manifest.json"),
            "--out",
            str(reports_dir),
        ]
    )
    assert diagnostics_result.exit_code == 0, diagnostics_result.stdout
    assert (artifact_dir / "source_resolution/data_source_resolution.json").exists()
    assert (artifact_dir / "ndx_feature_panel.parquet").exists()
    assert (artifact_dir / "open_gap_residuals.parquet").exists()
    assert (reports_dir / "neutralized_residuals.parquet").exists()
    assert (reports_dir / "ndx_counter_dag_refutation_skeleton.md").exists()
    assert not (artifact_dir / "research/strategy_signals.parquet").exists()
    assert not (artifact_dir / "strategy_signals.parquet").exists()
    _validate_json_artifact(
        schema_path=Path("schemas/ndx_source_resolution.v1.schema.json"),
        artifact_path=artifact_dir / "source_resolution/data_source_resolution.json",
    )
    _validate_json_artifact(
        schema_path=Path("schemas/ndx_feature_manifest.v1.schema.json"),
        artifact_path=artifact_dir / "ndx_feature_manifest.json",
    )
    _validate_json_artifact(
        schema_path=Path("schemas/ndx_open_gap_residual_manifest.v1.schema.json"),
        artifact_path=artifact_dir / "open_gap_residual_manifest.json",
    )
    _validate_json_artifact(
        schema_path=Path("schemas/ndx_residual_diagnostics.v1.schema.json"),
        artifact_path=reports_dir / "ndx_residual_diagnostics.json",
    )


def test_ndx_layer23_schemas_are_valid() -> None:
    for path in sorted(Path("schemas").glob("ndx_*.schema.json")):
        Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))


def _validate_json_artifact(*, schema_path: Path, artifact_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
