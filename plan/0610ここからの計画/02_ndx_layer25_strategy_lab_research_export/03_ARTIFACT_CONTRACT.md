<!--
作成日: 2026-06-10_12:02 JST
更新日: 2026-06-10_12:02 JST
-->

# Artifact contract

## Command

```bash
uv run sis research-ndx-strategy-lab-export \
  --artifact-dir data/research/ndx \
  --reports-dir data/research/ndx/reports \
  --out data/research
```

Options:

- `--artifact-dir`: NDX Layer 2.3 / 2.4 artifact directory. Default `data/research/ndx`.
- `--reports-dir`: NDX residual reports directory. Default `data/research/ndx/reports`.
- `--out`: Strategy Lab research artifact directory. Default `data/research`.

## Required inputs

- `artifact-dir/residual_validation_decision.json`
- `artifact-dir/residual_validation_summary.json`
- `artifact-dir/ndx_feature_panel.parquet`
- `artifact-dir/ndx_feature_manifest.json`
- `artifact-dir/open_gap_residuals.parquet`
- `artifact-dir/open_gap_residual_manifest.json`
- `reports-dir/neutralized_residuals.parquet`
- `reports-dir/ndx_residual_diagnostics.json`

## Outputs on approval

- `out/strategy_signals.parquet`
- `out/strategy_signal_manifest.json`
- `artifact-dir/strategy_lab_research_export_manifest.json`
- `out/../reports/ndx_strategy_lab_research_export_report.md`

`out` is normally `data/research`, so the report resolves to `data/reports/ndx_strategy_lab_research_export_report.md`.

## Manifest schema

Add `schemas/ndx_strategy_lab_research_export_manifest.v1.schema.json`.

Required fields:

- `schema_version: "ndx_strategy_lab_research_export_manifest.v1"`
- `dag_id: "HYP-NDX-001"`
- `export_id: "sha256:<64 hex>"`
- `created_at`
- `source_decision_id`
- `source_decision_path`
- `source_summary_path`
- `feature_panel_path`
- `feature_panel_hash`
- `residuals_path`
- `residuals_hash`
- `neutralized_residuals_path`
- `neutralized_residuals_hash`
- `strategy_signals_path`
- `strategy_signals_hash`
- `strategy_signal_manifest_path`
- `strategy_signal_manifest_hash`
- `signal_count`
- `strategy_id`
- `strategy_family`
- `strategy_version`
- `generator_id`
- `research_only: true`
- `permits_backtest: false`
- `permits_paper_candidate: false`
- `permits_paper_intent_preview: false`
- `permits_live_order: false`
- `external_api_used: false`
- `credentials_used: false`
- `wallet_used: false`
- `venue_write_used: false`

## Signal row mapping

Use one Strategy Lab row per joined residual date.

- Join key: `date`.
- `ts_signal`: `ndx_feature_panel.feature_ts`.
- Score source: `neutralized_residuals.combined_neutralized_residual`.
- `raw_score`: combined neutralized residual.
- `percentile_rank`: deterministic percentile rank of `raw_score` within the export frame.
- `rank_score`: `abs(raw_score)` percentile rank within the export frame.
- `tail_bucket`: `top` for `percentile_rank >= 0.8`, `bottom` for `percentile_rank <= 0.2`, otherwise `middle`.
- `side`: `long` when `raw_score > 0`, `short` when `raw_score < 0`, `none` when exactly zero.
- `confidence`: bounded `abs(raw_score) / max(abs(raw_score))`, with zero frame producing `0.0`.
- `timeframe`: `1d`.
- `execution_venue`: `trade_xyz`.
- `execution_symbol`: `XYZ100`.
- `real_market_symbol`: `QQQ`.
- `strategy_id`: `ndx_open_gap_residual_v1`.
- `strategy_family`: `ndx_open_gap_residual`.
- `strategy_version`: `v1`.
- `generator_id`: `ndx_layer25_residual_research_export`.
- `feature_snapshot_ref`: `ndx_feature_manifest:<feature_manifest_hash>:<date>`.
- `reason_codes`: include `ndx_layer25_research_export` and `approved_residual_validation`.
- `block_reasons`: include `RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED`.

## Determinism

The same input artifacts must produce the same signal identity, `signal_artifact_run_id`, export manifest `export_id`, and hashes except for timestamp fields explicitly excluded by existing Strategy Lab run-id logic.
