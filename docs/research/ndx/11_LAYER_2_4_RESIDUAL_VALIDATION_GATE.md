<!--
作成日: 2026-06-09_06:36 JST
更新日: 2026-06-09_06:36 JST
-->

# Layer 2.4 NDX Residual Validation Gate

Layer 2.4 validates whether the Layer 2.3 open-gap residual can proceed to a future
Strategy Lab research-only export. It does not write `strategy_signals.parquet`, run a
backtest, create a paper candidate, create `PaperIntentPreview`, or submit live orders.

## Command

```bash
uv run sis research-ndx-residual-validate \
  --root configs/research_layer_2_2/ndx \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --out data/research/ndx
```

## Outputs

- `data/research/ndx/residual_validation_summary.json`
- `data/research/ndx/residual_validation_decision.json`
- `data/reports/ndx_residual_validation_report.md`
- `data/reports/ndx_counter_dag_refutation_report.md`

## Decisions

- `APPROVE_STRATEGY_LAB_EXPORT`: future Layer 2.5 may build research-only Strategy Lab export.
- `REVISE_2_3`: Layer 2.3 feature/residual artifacts need correction or more validation sample.
- `REVISE_2_2`: Layer 2.2 DAG/freeze lineage needs correction.
- `REJECT_RESIDUAL`: residual survives lineage checks but is explained away by known-factor neutralization.

## Practical Boundary

Current Layer 2.3 preserves aggregate `source_ts_max`, but not per-source timestamp columns for
VIX and DGS10. Layer 2.4 therefore fails closed with `SOURCE_TIMESTAMP_AUDIT_MISSING` until
Layer 2.3 records per-source availability timestamps or an equivalent audit artifact.
