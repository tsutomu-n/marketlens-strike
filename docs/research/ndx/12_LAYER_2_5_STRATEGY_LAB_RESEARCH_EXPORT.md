<!--
作成日: 2026-06-10_15:55 JST
更新日: 2026-06-10_15:55 JST
-->

# Layer 2.5 NDX Strategy Lab Research Export

Layer 2.5 converts an approved Layer 2.4 residual validation result into the existing Strategy Lab canonical signal artifact. It is research-only.

## Command

```bash
uv run sis research-ndx-strategy-lab-export \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports
```

Use `--replace-existing` only when intentionally replacing `data/research/strategy_signals.parquet` and `data/research/strategy_signal_manifest.json`. Without it, existing Strategy Lab signal artifacts cause a fail-closed exit.

## Inputs

- `data/research/ndx/residual_validation_decision.json`
- `data/research/ndx/residual_validation_summary.json`
- `data/research/ndx/ndx_feature_panel.parquet`
- `data/research/ndx/ndx_feature_manifest.json`
- `data/research/ndx/open_gap_residuals.parquet`
- `data/research/ndx/open_gap_residual_manifest.json`
- `data/reports/neutralized_residuals.parquet`
- `data/reports/ndx_residual_diagnostics.json`

## Outputs

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signal_manifest.json`
- `data/research/ndx/strategy_lab_research_export_manifest.json`
- `data/reports/ndx_strategy_lab_research_export_report.md`

## Boundary

Layer 2.5 requires `APPROVE_STRATEGY_LAB_EXPORT` and `permits_strategy_lab_research_only_export=true`. It keeps backtest, paper candidate, PaperIntentPreview, live order, external API, credentials, wallet, and venue-write permissions false.

Signal rows include `RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED` in `block_reasons`, and selected signal block reasons are propagated into paper candidate block reasons. NDX/QQQ remains blocked from paper intent generation under the current venue suitability gate.
