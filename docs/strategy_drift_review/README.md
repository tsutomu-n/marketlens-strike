<!--
作成日: 2026-06-19_00:00 JST
更新日: 2026-06-19_01:02 JST
-->

# Strategy Drift Review

## 結論

`strategy-drift-review` は、`strategy_authoring_backtest_result.v1` と `strategy_runtime_observation_manifest.v1` を読み、paper runtime が backtest 仮説とどこでズレたかを人間が確認するための `paper_vs_backtest_drift_review.v1` JSON と Markdown report を作る。

これは paper / live の許可ではない。PnL drift は runtime observation 側に実現 paper PnL がある場合だけ計算し、ない場合は fill / block / no-fill / spread / quote age だけの限定 review として明記する。

## Command

```bash
uv run sis strategy-drift-review \
  --backtest-result data/research/strategy_authoring/backtest_result.json \
  --runtime-observation data/runtime_observations/<strategy-id>/<session-id>/strategy_runtime_observation_manifest.json \
  --out data/strategy_drift_reviews/<strategy-id>/<session-id>
```

出力:

```text
data/strategy_drift_reviews/<strategy-id>/<session-id>/
  paper_vs_backtest_drift_review.json
  paper_vs_backtest_drift_review.md
```

## 読む入力

- `strategy_authoring_backtest_result.v1`
- `strategy_runtime_observation_manifest.v1`

読む主な値:

- backtest: `strategy_id`, `backtest_passed`, `signals_considered`, `executed_count`, `blocked_count`, `trade_count`, `total_return`, `max_drawdown`, `win_rate`
- runtime: `session_id`, `source_stage`, `ingest_status`, `ledger_entry_count`, `paper_fill_count`, `blocked_count`, `no_fill_count`, `max_observed_spread_bps`, `max_observed_quote_age_ms`, `pnl_available`, `realized_pnl_usd_total`, `fee_usd_total`, `slippage_usd_total`, `avg_slippage_bps`, `fill_price_drift_bps`, `order_lifecycle_counts`

## 出力の読み方

`review_status`:

- `READY_FOR_HUMAN_DRIFT_REVIEW`: backtest result と runtime observation が読めた。
- `NEEDS_RUNTIME_OBSERVATION`: runtime observation が空または不足している。
- `NEEDS_BACKTEST_RESULT`: backtest result が不足している。
- `BLOCKED_BOUNDARY_VIOLATION`: live / wallet / signing / exchange write 系 true flag が混入した。

`recommended_action`:

- `HUMAN_REVIEW_REQUIRED`: 機械的な閾値だけでは revise とは言えない。人間が読む。
- `EXTEND_OBSERVATION`: 観測が足りない。
- `REVISE_STRATEGY`: no-fill、blocked、spread、または PnL drift のいずれかが指定閾値を超えた。
- `REPAIR_ARTIFACTS`: 境界違反がある。

## 閾値

CLI で次を指定できる。

- `--max-no-fill-rate`
- `--max-blocked-rate`
- `--max-spread-bps`
- `--max-return-drift`

これらは drift review の警告・推奨 action を決めるための review threshold であり、paper / live permission ではない。

`--max-return-drift` は、runtime の `realized_pnl_usd_total / filled_notional_usd_total` と backtest の `total_return` の絶対差を見ます。runtime observation に PnL または filled notional がない場合、この条件は満たせず、review は PnL drift なしの限定 review になります。

## 境界

- paper order は実行しない。
- live order は実行しない。
- wallet、signing、exchange write は使わない。
- `HUMAN_REVIEW_REQUIRED` は micro live plan の許可ではない。
- PnL drift が使える場合も、人間レビュー用の材料であり、自動 micro live permission ではない。

次工程:

- `strategy-learning-ledger-update` で、この Drift Review を `strategy_learning_event.v1` と learning ledger に戻す。
- `strategy-revision-request-build` で、人間レビュー前提の `strategy_revision_request.v1` を作る。

## Verification

```bash
uv run pytest tests/strategy_drift_review -q
uv run python scripts/check_current_docs.py
```
