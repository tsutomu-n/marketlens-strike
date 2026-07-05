<!--
作成日: 2026-06-22_21:49 JST
更新日: 2026-06-22_21:49 JST
-->

# Local Dogfood Loop 16 Trend Backtest Viewer Summary Results

## 結論

A: `trend_pullback_user_v1` の Local dogfood を継続した。

結果として、Trend Viewer で一番重要な backtest / pack validation evidence が compact summary に出ていなかった問題を修正した。以前の Viewer は `strategy_authoring_backtest_result.v1` で `strategy_id` しか表示せず、`strategy_backtest_pack_validation.v1` も実務上ほぼ空 summary だった。これでは `READY_FOR_HUMAN_REVIEW` の理由を人間が一覧で確認しにくい。

修正後は、Trend Viewer で `backtest_passed`、`trade_count`、`total_return`、`net_pnl_usd`、`paper_only`、`live_order_submitted=false`、pack validation の `decision=PASS`、`check_count`、`failed_count=0`、`locked_dependency_added=false` が見える。

これは backtest evidence を読みやすくするだけであり、paper / live 実行許可、profit claim、alpha proof ではない。

## 1. 計画

対象:

- lane: `Local dogfood`
- selection: `A`
- strategy_id: `trend_pullback_user_v1`
- primary viewer:
  - `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json`
  - `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html`

完了条件:

- A の Viewer manifest を現物確認し、backtest / validation artifact の summary 欠落を特定する。
- `strategy_authoring_backtest_result.v1` と `strategy_backtest_pack_validation.v1` の compact summary を追加する。
- focused RED / GREEN を残す。
- Trend Viewer を再生成し、現物 HTML / manifest に summary が出ることを確認する。
- docs を更新し、full check を通す。

やらないこと:

- Runtime Observation / Learning Event の捏造。
- Input Feedback proposal の無理な生成。
- Strategy Input Contract の direct apply。
- credential、network、paper order、live order、wallet、signing、exchange write。

## 2. 追加調査と現実チェック

現物確認:

```bash
jq '.source_artifacts[] | {title,path,schema_version,status,summary}' \
  data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json
```

修正前の問題:

- `strategy_authoring_backtest_result.v1 / trend_pullback_user_v1`
  - summary は `strategy_id` だけ。
  - `backtest_passed`、`trade_count`、`total_return`、`net_pnl_usd`、`paper_only`、`live_order_submitted` が一覧で見えない。
- `strategy_backtest_pack_validation.v1`
  - status / summary が実務的に弱い。
  - `decision=PASS`、`failed_count=0`、`locked_dependency_added=false` が一覧で見えない。

現物 artifact の重要値:

```text
strategy_backtest_metrics.json:
- strategy_id=trend_pullback_user_v1
- backtest_passed=true
- trade_count=7
- total_return=0.004662409768745324
- net_pnl_usd=46.62409768745324
- max_drawdown=0.0
- paper_only=true
- live_order_submitted=false

strategy_backtest_pack_validation.json:
- decision=PASS
- check_count=206
- passed_count=206
- failed_count=0
- locked_dependency_added=false
- external_framework_policy_decision=complete_without_locked_external_dependency
- paper_only=true
- live_order_submitted=false
```

判断:

- A で Runtime Observation を作るのは根拠がないためやらない。
- Case / Viewer dogfood としては、既存 backtest evidence の可読性を改善するのが最小で現実的。
- `PASS` や `backtest_passed=true` は permission ではないため、docs に境界を明記する。

## 3. 実装

変更した code:

- `src/sis/strategy_workbench_viewer/service.py`
  - compact summary 対象 key に backtest / pack validation 系の key を追加。
  - `strategy_authoring_backtest_result.v1` では `summary.aggregate_metrics` と `summary.capital` から `trade_count`、`total_return`、`max_drawdown`、`net_pnl_usd`、`ending_equity_usd`、`max_drawdown_loss_usd` を抽出。
  - `paper_only` と `live_order_submitted` も summary に出す。

変更した tests:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
  - `test_strategy_workbench_viewer_summarizes_backtest_result_and_pack_validation` を追加。
  - backtest result と pack validation の compact summary が manifest / HTML に出ることを検証。

更新した docs:

- `docs/strategy_workbench_viewer/README.md`
  - Strategy Backtest result / pack validation の compact summary を明記。
  - これが paper / live 実行許可や alpha 証明ではないことを明記。

再生成した local artifact:

- `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html`
- `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json`

再生成コマンド:

```bash
uv run sis strategy-workbench-viewer-build \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json \
  --artifact data/research/strategy_backtest_metrics.json \
  --artifact data/research/backtest_pack/strategy_backtest_pack.json \
  --artifact data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --artifact data/research/backtest_suite/strategy_backtest_suite_result.json \
  --artifact data/research/backtest_compare/strategy_backtest_comparison.json \
  --artifact data/strategy_reviews/dogfood-operator-current/review_manifest.json \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json \
  --out data/local_dogfood/2026-06-22-trend-pullback/viewer \
  --viewer-id trend-pullback-local-dogfood-viewer \
  --replace-existing
```

再生成結果:

```text
status=pass
artifact_count=9
boundary_violation_count=0
```

## 修正後の現物確認

Manifest:

```text
strategy_authoring_backtest_result.v1:
- backtest_passed=true
- trade_count=7
- total_return=0.004662409768745324
- max_drawdown=0.0
- net_pnl_usd=46.62409768745324
- ending_equity_usd=10046.624097687452
- paper_only=true
- live_order_submitted=false

strategy_backtest_pack_validation.v1:
- status=PASS
- decision=PASS
- check_count=206
- passed_count=206
- failed_count=0
- locked_dependency_added=false
- external_framework_policy_decision=complete_without_locked_external_dependency
```

Viewer boundary:

```text
artifact_count=9
boundary_violation_count=0
live_allowed=false
paper_execution_allowed=false
wallet_used=false
signing_used=false
exchange_write_used=false
```

HTML では次を確認した。

- `backtest_passed`
- `trade_count`
- `net_pnl_usd`
- `locked_dependency_added`
- `complete_without_locked_external_dependency`

## 検証

Focused RED:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_summarizes_backtest_result_and_pack_validation -q
```

実装前の期待失敗:

```text
KeyError: 'backtest_passed'
```

Focused GREEN:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_summarizes_backtest_result_and_pack_validation -q
```

結果:

```text
1 passed
```

Viewer test:

```bash
uv run pytest tests/strategy_workbench_viewer -q
```

結果:

```text
13 passed
```

## 残リスク

- `backtest_passed=true` と `decision=PASS` は、paper / live / profit の許可ではない。
- `trade_count=7` は少ない。これを強い alpha evidence と読むのは危険。
- A には Runtime Observation / Learning Event がまだない。Input Feedback proposal はまだ自然には作れない。
- Viewer は正本ではない。正本は JSON artifact、schema、CLI、tests。

## 次の実務的な選択肢

1. A を継続し、backtest suite / comparison / pack の空 summary をさらに実用化する。
2. A の不足をまとめ、Runtime Observation / Learning Event が必要かどうかを別計画で判断する。
3. C に移り、Crypto Perp viewer-only の permission flag 表示を確認する。
