<!--
作成日: 2026-06-08_21:44 JST
更新日: 2026-06-09_10:06 JST
-->

# Layer 2.3 NDX Preflight / Feature Panel / Open Gap Residual

This document describes the implemented local-only Layer 2.3 NDX preflight path.

## Boundary

- Starts only after Layer 2.2 Exit Gate is `APPROVE_2_3`.
- Requires `layer_2_2_freeze_manifest.json`.
- Requires `second_review_required=false`.
- Requires `unresolved_human_decisions=[]`.
- Uses fixture-first sources only.
- Does not export Strategy Lab artifacts.
- Does not generate `strategy_signals.parquet`.
- Does not run backtests, paper candidates, live orders, external APIs, credentials, or dependency additions.
- Does not add NQ, VXN, SOX direct, options, or gamma inputs.

## Commands

```bash
uv run sis research-ndx-source-resolve --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-ndx-feature-panel --root configs/research_layer_2_2/ndx --input-root tests/fixtures/ndx --out data/research/ndx
uv run sis research-ndx-residual --feature-panel data/research/ndx/ndx_feature_panel.parquet --out data/research/ndx
uv run sis research-ndx-diagnostics --residuals data/research/ndx/open_gap_residuals.parquet --out data/reports
```

## Artifacts

- `data/research/ndx/source_resolution/data_source_resolution.json`
- `data/research/ndx/ndx_feature_panel.parquet`
- `data/research/ndx/ndx_feature_manifest.json`
- `data/research/ndx/open_gap_residuals.parquet`
- `data/research/ndx/open_gap_residual_manifest.json`
- `data/reports/ndx_residual_diagnostics.json`
- `data/reports/neutralized_residuals.parquet`
- `data/reports/ndx_neutralization_pre_report.md`
- `data/reports/ndx_counter_dag_refutation_skeleton.md`

## Leakage Guard

The model input factors are `spy_gap`, `smh_gap`, `vix_change`, `dgs10_delta`, and
`mega_cap_basket_gap`. Same-day close-derived outcome columns are carried only for diagnostics,
not as residual model inputs. The feature builder preserves `qqq_source_ts`, `spy_source_ts`,
`smh_source_ts`, `mega_cap_basket_source_ts`, `vix_source_ts`, and `dgs10_source_ts`, then requires
each source timestamp and `source_ts_max` to be no later than `feature_ts`. `source_tier` must be
non-null on every row.
