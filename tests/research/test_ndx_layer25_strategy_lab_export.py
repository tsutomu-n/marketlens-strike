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
from sis.research.strategy_lab.signal_artifact import (
    read_strategy_signal_manifest,
    signal_artifact_run_id,
)
from sis.research.strategy_lab.signal_frame import validate_strategy_signal_frame
from sis.research.strategy_lab.specs import SymbolBinding
from support.cli import invoke_cli


RESEARCH_ONLY_BLOCK = "RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED"
REVIEW_FIXTURE_DIR = Path("tests/fixtures/research_layer_2_2/reviews")


def test_layer25_exports_approved_residuals_to_strategy_lab_artifacts(tmp_path) -> None:
    data_dir, artifact_dir, reports_dir = _approved_layer24_artifacts(tmp_path)

    result = invoke_cli(
        [
            "research-ndx-strategy-lab-export",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 0, result.stdout
    signals_path = data_dir / "research/strategy_signals.parquet"
    signal_manifest_path = data_dir / "research/strategy_signal_manifest.json"
    export_manifest_path = artifact_dir / "strategy_lab_research_export_manifest.json"
    report_path = data_dir / "reports/ndx_strategy_lab_research_export_report.md"
    assert signals_path.exists()
    assert signal_manifest_path.exists()
    assert export_manifest_path.exists()
    assert report_path.exists()

    signals = pl.read_parquet(signals_path)
    manifest = read_strategy_signal_manifest(signal_manifest_path)
    export_manifest = json.loads(export_manifest_path.read_text(encoding="utf-8"))
    assert signals.height == 90
    assert manifest.generator_id == "ndx_layer25_residual_research_export"
    assert manifest.strategy_id == "ndx_open_gap_residual_v1"
    assert manifest.signal_count == signals.height
    assert export_manifest["research_only"] is True
    assert export_manifest["permits_backtest"] is False
    assert export_manifest["permits_paper_candidate"] is False
    assert export_manifest["permits_paper_intent_preview"] is False
    assert export_manifest["permits_live_order"] is False
    assert export_manifest["replace_existing"] is False
    assert export_manifest["replaced_existing_artifact"] is False
    assert export_manifest["previous_strategy_signals_hash"] is None
    assert export_manifest["signal_count"] == signals.height
    assert export_manifest["strategy_signals_hash"] == sha256_file(signals_path)
    assert export_manifest["strategy_signal_manifest_hash"] == sha256_file(signal_manifest_path)
    assert export_manifest["side_policy"] == "residual_sign_directional_research_only"
    assert export_manifest["tested_variant_count"] == 1
    assert "created_at" in export_manifest["hash_excludes"]

    binding = SymbolBinding(
        execution_venue="trade_xyz",
        execution_symbol="XYZ100",
        real_market_symbol="QQQ",
        asset_class="equity_index_proxy",
        country="US",
    )
    validated = validate_strategy_signal_frame(signals, symbol_bindings=[binding])
    assert validated.height == signals.height
    assert set(signals.get_column("execution_symbol").to_list()) == {"XYZ100"}
    assert set(signals.get_column("real_market_symbol").to_list()) == {"QQQ"}
    assert set(signals.get_column("timeframe").to_list()) == {"1d"}
    assert RESEARCH_ONLY_BLOCK in signals.get_column("block_reasons").to_list()[0]
    assert (
        signals.sort("ts_signal").get_column("ts_signal").to_list()[0].isoformat()
        == "2026-01-01T14:31:00+00:00"
    )
    assert (
        signals.get_column("feature_snapshot_ref")
        .to_list()[0]
        .startswith("ndx_feature_manifest:sha256:")
    )
    assert manifest.signal_artifact_run_id == signal_artifact_run_id(signals)
    _validate_json_artifact(
        schema_path=Path("schemas/ndx_strategy_lab_research_export_manifest.v1.schema.json"),
        artifact_path=export_manifest_path,
    )


def test_layer25_fails_closed_for_non_approved_decision(tmp_path) -> None:
    data_dir, artifact_dir, reports_dir = _layer24_artifacts(tmp_path, mode="mirage")

    result = invoke_cli(
        [
            "research-ndx-strategy-lab-export",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 2
    assert not (data_dir / "research/strategy_signals.parquet").exists()
    assert not (data_dir / "research/strategy_signal_manifest.json").exists()


def test_layer25_fails_closed_for_missing_and_hash_mismatch_inputs(tmp_path) -> None:
    data_dir, artifact_dir, reports_dir = _approved_layer24_artifacts(tmp_path)
    (reports_dir / "neutralized_residuals.parquet").unlink()

    result = invoke_cli(
        [
            "research-ndx-strategy-lab-export",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 2
    assert not (data_dir / "research/strategy_signals.parquet").exists()

    data_dir, artifact_dir, reports_dir = _approved_layer24_artifacts(tmp_path / "hash")
    diagnostics_path = reports_dir / "ndx_residual_diagnostics.json"
    diagnostics = json.loads(diagnostics_path.read_text(encoding="utf-8"))
    diagnostics["neutralized_residuals_hash"] = "sha256:" + "0" * 64
    diagnostics_path.write_text(json.dumps(diagnostics, indent=2) + "\n", encoding="utf-8")

    result = invoke_cli(
        [
            "research-ndx-strategy-lab-export",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 2
    assert not (data_dir / "research/strategy_signals.parquet").exists()


def test_layer25_requires_replace_existing_before_overwriting_strategy_artifact(
    tmp_path,
) -> None:
    data_dir, artifact_dir, reports_dir = _approved_layer24_artifacts(tmp_path)
    existing_path = data_dir / "research/strategy_signals.parquet"
    existing_manifest_path = data_dir / "research/strategy_signal_manifest.json"
    existing_path.parent.mkdir(parents=True, exist_ok=True)
    pl.DataFrame({"sentinel": [1]}).write_parquet(existing_path)
    existing_manifest_path.write_text('{"sentinel": true}\n', encoding="utf-8")
    previous_signals_hash = sha256_file(existing_path)
    previous_manifest_hash = sha256_file(existing_manifest_path)

    result = invoke_cli(
        [
            "research-ndx-strategy-lab-export",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )

    assert result.exit_code == 2
    assert sha256_file(existing_path) == previous_signals_hash
    assert sha256_file(existing_manifest_path) == previous_manifest_hash

    result = invoke_cli(
        [
            "research-ndx-strategy-lab-export",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--replace-existing",
        ]
    )

    assert result.exit_code == 0, result.stdout
    export_manifest = json.loads(
        (artifact_dir / "strategy_lab_research_export_manifest.json").read_text(encoding="utf-8")
    )
    assert export_manifest["replace_existing"] is True
    assert export_manifest["replaced_existing_artifact"] is True
    assert export_manifest["previous_strategy_signals_hash"] == previous_signals_hash
    assert export_manifest["previous_strategy_signal_manifest_hash"] == previous_manifest_hash


def test_layer25_export_id_is_stable_for_identical_source_artifacts(tmp_path) -> None:
    data_dir, artifact_dir, reports_dir = _approved_layer24_artifacts(tmp_path)

    result = invoke_cli(
        [
            "research-ndx-strategy-lab-export",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )
    assert result.exit_code == 0, result.stdout
    first = json.loads(
        (artifact_dir / "strategy_lab_research_export_manifest.json").read_text(encoding="utf-8")
    )

    result = invoke_cli(
        [
            "research-ndx-strategy-lab-export",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
            "--replace-existing",
        ]
    )
    assert result.exit_code == 0, result.stdout
    second = json.loads(
        (artifact_dir / "strategy_lab_research_export_manifest.json").read_text(encoding="utf-8")
    )
    assert second["export_id"] == first["export_id"]


def test_layer25_downstream_strategy_lab_stays_paper_intent_closed(
    tmp_path,
    monkeypatch,
) -> None:
    data_dir, artifact_dir, reports_dir = _approved_layer24_artifacts(tmp_path)
    monkeypatch.setenv("SIS_DATA_DIR", str(data_dir))

    result = invoke_cli(
        [
            "research-ndx-strategy-lab-export",
            "--data-dir",
            str(data_dir),
            "--artifact-dir",
            str(artifact_dir),
            "--reports-dir",
            str(reports_dir),
        ]
    )
    assert result.exit_code == 0, result.stdout
    assert invoke_cli(["evaluate-strategy-lab"]).exit_code == 0
    assert invoke_cli(["build-paper-candidate-pack"]).exit_code == 0
    pack = json.loads((data_dir / "research/paper_candidate_pack.json").read_text())
    assert pack["selected_candidate_ids"] == []
    assert pack["candidates"][0]["status"] == "blocked"
    assert RESEARCH_ONLY_BLOCK in pack["candidates"][0]["block_reasons"]
    assert (
        "VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION"
        in pack["candidates"][0]["block_reasons"]
    )

    assert invoke_cli(["promotion-decision", "--decision", "promote"]).exit_code == 0
    assert invoke_cli(["build-paper-intent-preview"]).exit_code == 0
    intents = json.loads((data_dir / "bot/paper_intent_preview.json").read_text())
    assert intents == []


def test_ndx_layer25_schema_is_valid() -> None:
    Draft202012Validator.check_schema(
        json.loads(
            Path("schemas/ndx_strategy_lab_research_export_manifest.v1.schema.json").read_text(
                encoding="utf-8"
            )
        )
    )


def _approved_layer24_artifacts(tmp_path: Path) -> tuple[Path, Path, Path]:
    return _layer24_artifacts(tmp_path, mode="approve")


def _layer24_artifacts(tmp_path: Path, *, mode: str) -> tuple[Path, Path, Path]:
    data_dir = tmp_path / "data"
    artifact_dir = _prepare_layer22_approval(tmp_path)
    reports_dir = data_dir / "reports"
    _write_synthetic_layer23_artifacts(artifact_dir, reports_dir, row_count=90, mode=mode)
    result = run_residual_validation_gate(
        root=CONFIG_DIR,
        artifact_dir=artifact_dir,
        reports_dir=reports_dir,
        out_dir=artifact_dir,
    )
    assert result.decision in {"APPROVE_STRATEGY_LAB_EXPORT", "REJECT_RESIDUAL"}
    return data_dir, artifact_dir, reports_dir


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
        raw = _math_like_residual(index)
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


def _math_like_residual(index: int) -> float:
    cycle = [0.012, -0.008, 0.015, -0.011, 0.006, -0.004, 0.01]
    return cycle[index % len(cycle)] + index * 0.00003


def _validate_json_artifact(*, schema_path: Path, artifact_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)
