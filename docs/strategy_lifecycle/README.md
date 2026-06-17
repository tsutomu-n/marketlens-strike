<!--
作成日: 2026-06-11_21:34 JST
更新日: 2026-06-17_23:19 JST
-->

# Strategy Lifecycle

## 結論

Strategy Lifecycle は、Strategy Authoring backtest、paper observation、phase gate を local artifact でつなぎ、次の実務判断を出すための control plane です。

これは live trading 実装ではありません。`ELIGIBLE_FOR_LIVE_CANARY_PLAN` は、別計画として live canary plan を書いてよい候補という意味だけで、live order、wallet、signing、exchange write を許可しません。

## Commands

```bash
uv run sis strategy-backtest-acceptance --metrics-path data/research/strategy_backtest_metrics.json --out data/research/strategy_lifecycle --reports-dir data/reports
uv run sis strategy-paper-observation-cycle --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports
uv run sis strategy-paper-observation-append --data-dir data --artifact-dir data/research/ndx --reports-dir data/reports --session-manifest data/paper/observations/<session_id>/paper_observation_session_manifest.json
uv run sis strategy-lifecycle-review --data-dir data --out data/research/strategy_lifecycle --reports-dir data/reports
uv run sis strategy-paper-observation-status --data-dir data --out data/research/strategy_lifecycle --reports-dir data/reports
```

## Artifacts

- `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- `data/reports/strategy_backtest_acceptance_report.md`
- `data/research/ndx/paper_observation_review_decision.json`
- `data/paper/observations/<session_id>/paper_observation_session_manifest.json`
- `data/paper/observations/<session_id>/source_artifacts/paper_intent_preview.json`
- `data/paper/observations/<session_id>/paper_observation_ledger.jsonl`
- `data/paper/observations/<session_id>/paper_observation_append_summary.json`
- `data/research/strategy_lifecycle/strategy_lifecycle_review.json`
- `data/reports/strategy_lifecycle_review.md`
- `data/research/strategy_lifecycle/paper_observation_status.json`
- `data/reports/paper_observation_status.md`

## Read Order

1. `TARGET_OPERATING_MODEL.md`
2. `PAPER_OBSERVATION_CYCLE.md`
3. `docs/REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md`
4. `docs/NEXT_DIRECTION_CURRENT.md`
5. `docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_BRIDGE_PLAN_2026-06-15.md`
6. `docs/backtest/BACKTEST_TO_PAPER_OBSERVATION_EVIDENCE_MAP_2026-06-15.md`
7. `LIVE_CANARY_PLAN_GATE.md`
8. `docs/backtest/README.md`
9. `docs/research/ndx/README.md`
10. `docs/OPERATIONS_RUNBOOK.md`

## NDX Paper Observation Handoff

NDX Layer 2.6 / 2.7 / 2.8 は Strategy Lifecycle の上流にある paper-only gate です。Layer 2.8 の canonical artifact は `data/research/ndx/paper_observation_review_decision.json` で、Strategy Lifecycle はこの artifact を paper observation 側の入力として読む。

明示的に読み戻す場合:

```bash
uv run sis strategy-lifecycle-review \
  --data-dir data \
  --paper-review-path data/research/ndx/paper_observation_review_decision.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports

uv run sis strategy-paper-observation-status \
  --data-dir data \
  --canonical-review-path data/research/ndx/paper_observation_review_decision.json \
  --lifecycle-review-path data/research/strategy_lifecycle/strategy_lifecycle_review.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

Layer 2.8 の `PASS_PAPER_OBSERVATION_REVIEW` は paper observation 入力の通過だけを意味する。Strategy Authoring backtest acceptance と phase gate も揃って初めて `ELIGIBLE_FOR_LIVE_CANARY_PLAN` になり得るが、その場合でも live order、wallet、signing、exchange write は許可しない。

Layer 2.8 が `NEEDS_MORE_PAPER_OBSERVATION` の場合は、同じ日の rerun ではなく新しい通常 paper observation session を集める。smoke pass は通常 paper observation の代替にしない。NDX 側の詳細は [docs/research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md](../research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md) を読む。

## External Input

新しい通常 paper observation evidence が来た場合は、`docs/NEXT_DIRECTION_CURRENT.md` の `External Input Restart Checklist` を読む。ここでいう evidence は新しい trading day を含む通常観察の証拠です。同じ trading day の artifact rerun や fill 水増しは `10 trading days` の代替にしません。

再確認は次を使う:

```bash
uv run sis strategy-paper-observation-status \
  --data-dir data \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

確認する値:

- `latest_normal_requirement_gaps.trading_days`
- `normal_thresholds_met`
- `smoke_pass_counts_as_normal_pass=false`
- `live_conversion_allowed=false`

## Boundary

`strategy-lifecycle-review` は既存の `lifecycle-report` とは別物です。`lifecycle-report` は operations / recovery report で、Strategy Lifecycle の promotion 判定ではありません。

`strategy-paper-observation-append` は既存 session manifest を固定して、manifest に記録済みの session-local intent preview snapshot から同じ ledger に1回分追記します。fresh intent preview は作りません。

`strategy-paper-observation-status` は既存の paper observation review / session manifest / lifecycle review を読む status artifact です。paper intent 生成、paper order 実行、ledger 再集計はしません。smoke pass は通常threshold pass として数えません。通常thresholdの不足量は `latest_normal_requirement_gaps` に出ます。

どの decision でも `permits_live_order=false`, `live_conversion_allowed=false`, `wallet_used=false`, `venue_write_used=false`, `exchange_write_used=false` を維持します。
