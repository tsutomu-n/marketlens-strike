<!--
作成日: 2026-06-17_21:52 JST
更新日: 2026-06-17_21:52 JST
-->

# NDX Research Runbook

NDX Layer 2.2 / 2.3 / 2.4 の local research gate を再生成・確認する domain runbook です。ここにある approve は research / Strategy Lab export までの gate であり、paper / live 実行許可ではありません。

## NDX Layer 2.2 Review Gate

Layer 2.2 DAG foundation と manual review gate を再生成・再確認する手順:

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
```

手動 review JSON を `data/research/ndx/review/llm_review_result.json` に置いた後:

```bash
uv run sis research-layer22-review-import \
  --pack data/research/ndx/review/llm_review_input.json \
  --result data/research/ndx/review/llm_review_result.json

uv run sis research-layer22-exit-gate \
  --root configs/research_layer_2_2/ndx \
  --pack data/research/ndx/review/llm_review_input.json \
  --review data/research/ndx/review/normalized_review.json \
  --out data/research/ndx/review
```

生成物は `data/research/ndx/` と `data/reports/` 以下の git-ignored runtime artifact。fresh checkout では再生成する。

stop conditions:

- external API、credentials、provider SDK、dependency追加が必要になった
- Strategy Lab export、backtest、PaperIntentPreview、paper/live/order path が必要になった
- Trade[XYZ] integration や live readiness claim へ話が広がった

## NDX Layer 2.3 / 2.4 Local Research Gates

Layer 2.3/2.4 は Layer 2.2 の `APPROVE_2_3` と freeze manifest を前提に、fixture-first artifact を再生成・検証する local-only research gate です。fresh checkout では `data/` の artifact は無い前提で作り直します。

開始条件:

```bash
jq -r '[.decision, (.second_review_required|tostring), ((.unresolved_human_decisions|length)|tostring), (.blocker_count|tostring), .pack_hash] | @tsv' data/research/ndx/review/layer_2_2_exit_decision.json
jq -r '[.dag_id, .exit_decision, .pack_hash] | @tsv' data/research/ndx/review/layer_2_2_freeze_manifest.json
```

期待値は `APPROVE_2_3`、`second_review_required=false`、未解決 human decision count `0`、blocker count `0`、freeze manifestあり。満たさない場合は 2.3/2.4 へ進まない。

Layer 2.3:

```bash
uv run sis research-ndx-source-resolve --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-ndx-feature-panel --root configs/research_layer_2_2/ndx --input-root tests/fixtures/ndx --out data/research/ndx
uv run sis research-ndx-residual --feature-panel data/research/ndx/ndx_feature_panel.parquet --out data/research/ndx
uv run sis research-ndx-diagnostics --residuals data/research/ndx/open_gap_residuals.parquet --out data/reports
```

Layer 2.4:

```bash
uv run sis research-ndx-residual-validate \
  --root configs/research_layer_2_2/ndx \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --out data/research/ndx
```

確認する artifact:

- `data/research/ndx/source_resolution/data_source_resolution.json`
- `data/research/ndx/ndx_feature_panel.parquet`
- `data/research/ndx/ndx_feature_manifest.json`
- `data/research/ndx/open_gap_residuals.parquet`
- `data/research/ndx/open_gap_residual_manifest.json`
- `data/research/ndx/residual_validation_summary.json`
- `data/research/ndx/residual_validation_decision.json`
- `data/reports/ndx_neutralization_pre_report.md`
- `data/reports/ndx_residual_validation_report.md`
- `data/reports/ndx_counter_dag_refutation_report.md`

現在の default fixture artifact は 90 feature rows / 84 residual rows で `APPROVE_STRATEGY_LAB_EXPORT` になる。これは Layer 2.5 research-only export bridge の許可であり、alpha、backtest、paper candidate、`PaperIntentPreview`、paper/live readiness の証明ではない。

stop conditions:

- `APPROVE_2_3`、freeze manifest、`second_review_required=false`、未解決 human decision なしを確認できない
- `source_ts_max <= feature_ts` または per-source timestamp checks が壊れた
- same-day close-derived outcome が residual model input に混入した
- QQQ / NDX / NQ の責務が混ざった
- DGS10 / VIX の timestamp availability が曖昧になった
- `dag_id` / `dag_artifact_hash` / manifest hash lineage が欠けた
- Strategy Lab export、`strategy_signals.parquet`、backtest、paper candidate、`PaperIntentPreview`、paper/live/order path、external API、credentials、dependency追加、NQ / VXN / SOX direct / options / gamma input が必要になった
