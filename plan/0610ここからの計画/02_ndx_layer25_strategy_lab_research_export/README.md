<!--
作成日: 2026-06-10_12:02 JST
更新日: 2026-06-10_12:02 JST
-->

# NDX Layer 2.5 Strategy Lab research-only export implementation plan

## 結論

Layer 2.5 は、Layer 2.4 の `APPROVE_STRATEGY_LAB_EXPORT` だけを入口にして、NDX residual validation の結果を Strategy Lab の canonical signal artifact へ変換する最小実装にする。

実装対象は research-only export まで。backtest、paper candidate、PaperIntentPreview、live order、外部API、credential、wallet、venue write は対象外。

## Read order

1. `01_GOAL_AND_SCOPE.md`
2. `02_CODE_TRUTH_AND_RISK_AUDIT.md`
3. `03_ARTIFACT_CONTRACT.md`
4. `04_IMPLEMENTATION_TASKS.md`
5. `05_ACCEPTANCE_AND_VERIFICATION.md`
6. `06_CODER_HANDOFF_PROMPT.md`

## Implementation target

Add one explicit CLI path:

```bash
uv run sis research-ndx-strategy-lab-export \
  --artifact-dir data/research/ndx \
  --reports-dir data/research/ndx/reports \
  --out data/research
```

Expected write surface on approval:

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signal_manifest.json`
- `data/research/ndx/strategy_lab_research_export_manifest.json`
- `data/reports/ndx_strategy_lab_research_export_report.md`

Expected fail-closed surface when Layer 2.4 is not approved:

- non-zero CLI exit
- no `strategy_signals.parquet`
- no `strategy_signal_manifest.json`
- no paper/live artifacts

## Boundary

This plan authorizes code and schema work only for research export. It does not authorize a claim that the NDX residual is alpha, production-ready, venue-ready, account-ready, or safe for paper/live execution.
