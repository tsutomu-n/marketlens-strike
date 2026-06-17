<!--
作成日: 2026-06-12_01:16 JST
更新日: 2026-06-17_16:57 JST
-->

# Paper Observation Cycle

## 結論

`strategy-paper-observation-cycle` は、fresh `PaperIntentPreview` を生成し、session ごとの paper observation ledger に記録し、その session を NDX paper observation review と Strategy Lifecycle review へ渡すための paper-only command です。

これは live trading command ではありません。出力は常に `permits_live_order=false`, `wallet_used=false`, `venue_write_used=false`, `exchange_write_used=false` を維持します。

## Command

```bash
uv run sis strategy-paper-observation-cycle \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports
```

Local fixture smoke:

```bash
uv run sis strategy-paper-observation-cycle \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --session-id local-smoke \
  --smoke
```

`--smoke` は `min_fills_for_pass=1` と `min_trading_days_for_pass=1` を使う local verification 用です。smoke pass は production paper pass ではありません。

`--session-id` を指定する場合は、`local-smoke` のような単一 path segment だけを使います。`/`、`..`、absolute path は拒否されます。

## Inputs

- `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- `data/research/paper_candidate_pack.json`
- `data/research/promotion_decision.json`
- `data/research/ndx/operator_promotion_decision.json`
- `data/normalized/quotes.parquet`

Backtest acceptance は `PASS_BACKTEST_ACCEPTANCE` が必須です。fail / missing の場合、cycle は session artifact を作らず fail closed します。

## Outputs

- `data/bot/paper_intent_preview.json`
- `data/reports/paper_intent_preview.md`
- `data/paper/observations/<session_id>/paper_observation_session_manifest.json`
- `data/paper/observations/<session_id>/paper_observation_ledger.jsonl`
- `data/paper/observations/<session_id>/paper_observation_review_decision.json`
- `data/paper/observations/<session_id>/paper_observation_cycle_summary.json`
- `data/research/ndx/paper_observation_review_decision.json`
- `data/research/strategy_lifecycle/strategy_lifecycle_review.json`
- `data/reports/paper_observation_session_report.md`

## Artifact Roles

The session ledger is the observation-window source of truth. It is the artifact used to compute fills, trading days, blocked rate, timestamp completeness, and boundary violations.

`data/paper/orders.parquet`, `data/paper/fills.parquet`, and `data/paper/positions.parquet` are current paper state snapshots. They are checked for existence and hashes, but they are not the cumulative observation-window truth.

The session manifest records source artifact paths, source hashes, thresholds, `smoke`, and paper-only boundary flags. The recorded sources include backtest acceptance, operator promotion, fresh intent preview, `PaperCandidatePack`, and `PromotionDecision`. Use it when rerunning review:

```bash
uv run sis research-ndx-paper-observation-review \
  --data-dir data \
  --artifact-dir data/research/ndx \
  --reports-dir data/reports \
  --session-manifest data/paper/observations/<session_id>/paper_observation_session_manifest.json
```

Use `strategy-paper-observation-status` after review when the question is whether current evidence is normal-threshold paper observation, smoke-only pass, stale/mismatched artifact, or incomplete artifact:

```bash
uv run sis strategy-paper-observation-status \
  --data-dir data \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

This status command reads existing review/session/lifecycle artifacts. It does not create paper intents, submit paper orders, or recompute the ledger.

## Stop Conditions

- backtest acceptance is missing or not `PASS_BACKTEST_ACCEPTANCE`
- source candidate pack or promotion decision is missing
- fresh paper intent preview has no intents
- session manifest source hash does not match current source artifact
- paper ledger has live / wallet / venue-write / exchange-write boundary violation
- review thresholds are not met, in which case lifecycle should remain `CONTINUE_PAPER_OBSERVATION`
