from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

import polars as pl

from sis.research.ndx.artifacts import (
    DAG_ID,
    dag_artifact_hash,
    sha256_file,
    sha256_json,
    utc_now_iso,
    write_json,
)
from sis.research.ndx.fixture_loader import load_bar_fixture, load_level_fixture
from sis.research.ndx.leakage import ISO_TS_FORMAT
from sis.research.ndx.leakage import validate_feature_panel
from sis.research.ndx.start_conditions import require_layer23_start_conditions


MODEL_FACTOR_COLUMNS = ["spy_gap", "smh_gap", "vix_change", "dgs10_delta", "mega_cap_basket_gap"]
SOURCE_TIMESTAMP_COLUMNS = [
    "qqq_source_ts",
    "spy_source_ts",
    "smh_source_ts",
    "mega_cap_basket_source_ts",
    "vix_source_ts",
    "dgs10_source_ts",
]
FEATURE_COLUMNS = [
    "date",
    "qqq_open",
    "qqq_close",
    "qqq_prev_close",
    "qqq_gap",
    "qqq_open_to_close_return",
    "spy_gap",
    "smh_gap",
    "vix_level",
    "vix_change",
    "dgs10_delta",
    "mega_cap_basket_gap",
    "feature_ts",
    *SOURCE_TIMESTAMP_COLUMNS,
    "source_ts_max",
    "source_tier",
    "dag_id",
    "dag_artifact_hash",
]


@dataclass(frozen=True)
class FeaturePanelResult:
    panel_path: Path
    manifest_path: Path
    report_path: Path
    row_count: int
    feature_manifest_hash: str


def build_ndx_feature_panel(
    *,
    root: Path,
    artifact_dir: Path,
    input_root: Path,
    out_dir: Path,
) -> FeaturePanelResult:
    start = require_layer23_start_conditions(root=root, artifact_dir=artifact_dir)
    dag_hash = dag_artifact_hash(artifact_dir)
    frame = build_feature_frame(input_root=input_root, dag_hash=dag_hash)
    validate_feature_panel(frame, model_input_columns=MODEL_FACTOR_COLUMNS)

    panel_path = out_dir / "ndx_feature_panel.parquet"
    panel_path.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(panel_path)
    manifest_payload = {
        "schema_version": "ndx_feature_manifest.v1",
        "dag_id": DAG_ID,
        "dag_artifact_hash": dag_hash,
        "layer_2_2_pack_hash": start.pack_hash,
        "created_at": utc_now_iso(),
        "feature_panel_path": panel_path.as_posix(),
        "feature_panel_hash": sha256_file(panel_path),
        "row_count": frame.height,
        "feature_columns": FEATURE_COLUMNS,
        "model_factor_columns": MODEL_FACTOR_COLUMNS,
        "source_timestamp_columns": SOURCE_TIMESTAMP_COLUMNS,
        "outcome_columns": ["qqq_open_to_close_return"],
        "leakage_checks": {
            "source_ts_max_lte_feature_ts": True,
            "per_source_ts_lte_feature_ts": True,
            "outcome_not_model_input": True,
            "same_day_close_not_model_input": True,
            "source_tier_required": True,
        },
    }
    manifest_payload["feature_manifest_hash"] = sha256_json(manifest_payload)
    manifest_path = write_json(out_dir / "ndx_feature_manifest.json", manifest_payload)
    report_path = _write_report(
        out_dir / "reports/ndx_feature_panel.md",
        row_count=frame.height,
        dag_hash=dag_hash,
        manifest_hash=str(manifest_payload["feature_manifest_hash"]),
    )
    return FeaturePanelResult(
        panel_path=panel_path,
        manifest_path=manifest_path,
        report_path=report_path,
        row_count=frame.height,
        feature_manifest_hash=str(manifest_payload["feature_manifest_hash"]),
    )


def build_feature_frame(*, input_root: Path, dag_hash: str) -> pl.DataFrame:
    qqq = load_bar_fixture(input_root, "qqq_daily.csv", prefix="qqq")
    spy = load_bar_fixture(input_root, "spy_daily.csv", prefix="spy")
    smh = load_bar_fixture(input_root, "smh_daily.csv", prefix="smh")
    mega = load_bar_fixture(input_root, "mega_cap_basket_daily.csv", prefix="mega_cap_basket")
    vix = load_level_fixture(input_root, "vix_daily.csv", prefix="vix")
    dgs10 = load_level_fixture(input_root, "dgs10_daily.csv", prefix="dgs10")

    frame = qqq.join(spy, on="date", how="inner")
    for other in (smh, mega, vix, dgs10):
        frame = frame.join(other, on="date", how="inner")
    missing_source_columns = [
        column for column in SOURCE_TIMESTAMP_COLUMNS if column not in frame.columns
    ]
    if missing_source_columns:
        raise ValueError(
            "NDX feature panel missing source timestamp columns: "
            + ", ".join(missing_source_columns)
        )
    if frame.height == 0:
        raise ValueError("NDX feature panel has no joined fixture rows.")
    required_count = min(source.height for source in (qqq, spy, smh, mega, vix, dgs10))
    if frame.height != required_count:
        raise ValueError("NDX feature panel lost rows during required fixture joins.")
    return (
        frame.with_columns(
            [
                ((pl.col("qqq_open") - pl.col("qqq_prev_close")) / pl.col("qqq_prev_close")).alias(
                    "qqq_gap"
                ),
                ((pl.col("qqq_close") - pl.col("qqq_open")) / pl.col("qqq_open")).alias(
                    "qqq_open_to_close_return"
                ),
                ((pl.col("spy_open") - pl.col("spy_prev_close")) / pl.col("spy_prev_close")).alias(
                    "spy_gap"
                ),
                ((pl.col("smh_open") - pl.col("smh_prev_close")) / pl.col("smh_prev_close")).alias(
                    "smh_gap"
                ),
                (pl.col("vix_value")).alias("vix_level"),
                (pl.col("vix_value") - pl.col("vix_prev_value")).alias("vix_change"),
                (pl.col("dgs10_value") - pl.col("dgs10_prev_value")).alias("dgs10_delta"),
                (
                    (pl.col("mega_cap_basket_open") - pl.col("mega_cap_basket_prev_close"))
                    / pl.col("mega_cap_basket_prev_close")
                ).alias("mega_cap_basket_gap"),
                (pl.col("date").cast(pl.Utf8) + pl.lit("T14:31:00+00:00")).alias("feature_ts"),
                pl.max_horizontal(
                    [
                        pl.col(column).str.to_datetime(ISO_TS_FORMAT)
                        for column in SOURCE_TIMESTAMP_COLUMNS
                    ]
                )
                .dt.to_string("%Y-%m-%dT%H:%M:%S%:z")
                .alias("source_ts_max"),
                pl.lit("fixture_required").alias("source_tier"),
                pl.lit(DAG_ID).alias("dag_id"),
                pl.lit(dag_hash).alias("dag_artifact_hash"),
            ]
        )
        .select(FEATURE_COLUMNS)
        .sort("date")
    )


def _write_report(path: Path, *, row_count: int, dag_hash: str, manifest_hash: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# NDX Layer 2.3 Feature Panel\n\n"
        f"- dag_id: {DAG_ID}\n"
        f"- dag_artifact_hash: {dag_hash}\n"
        f"- row_count: {row_count}\n"
        f"- feature_manifest_hash: {manifest_hash}\n"
        f"- model_factor_columns: {json.dumps(MODEL_FACTOR_COLUMNS)}\n"
        f"- source_timestamp_columns: {json.dumps(SOURCE_TIMESTAMP_COLUMNS)}\n"
        "- leakage_checks: pass\n",
        encoding="utf-8",
    )
    return path
