<!--
作成日: 2026-06-22_21:58 JST
更新日: 2026-06-22_21:58 JST
-->

# Local Dogfood Loop 17 Trend Pack Suite Comparison Viewer Summary Results

## 結論

A: `trend_pullback_user_v1` の Local dogfood を継続した。

Loop 16 では backtest result / pack validation の summary を追加したが、Trend Viewer にはまだ `strategy_backtest_pack.v1`、`strategy_backtest_suite_result.v1`、`strategy_backtest_comparison.v1` がほぼ空 summary のまま残っていた。これでは、5手法 suite が何を通したのか、optional framework が実行されたのか skipped なのか、comparison の weakest era がどこかを一覧で見落としやすい。

修正後は、Trend Viewer で pack artifact count、suite method / run / pass count、best run、comparison の native result、suite best run、weakest era、optional framework の skipped status が見える。

これは readable evidence の改善であり、paper / live 実行許可、profit claim、外部 framework 採用判断ではない。

## 1. 計画

対象:

- lane: `Local dogfood`
- selection: `A`
- strategy_id: `trend_pullback_user_v1`
- primary viewer:
  - `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json`
  - `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html`

完了条件:

- `strategy_backtest_pack.v1`、`strategy_backtest_suite_result.v1`、`strategy_backtest_comparison.v1` の現物構造を確認する。
- Viewer compact summary に、実務判断に使う key だけを追加する。
- focused RED / GREEN を残す。
- Trend Viewer を再生成し、現物 HTML / manifest に summary が出ることを確認する。
- docs を更新し、full check を通す。

やらないこと:

- Runtime Observation / Learning Event の捏造。
- Input Feedback proposal の無理な生成。
- optional framework の新規採用。
- dependency 追加。
- credential、network、paper order、live order、wallet、signing、exchange write。

## 2. 追加調査と現実チェック

修正前の Viewer 現物:

```text
strategy_backtest_pack.v1:
- summary: paper_only=true, live_order_submitted=false のみ

strategy_backtest_suite_result.v1:
- summary: paper_only=true, live_order_submitted=false のみ

strategy_backtest_comparison.v1:
- summary: empty
```

現物 artifact で確認した key:

```text
strategy_backtest_pack.v1:
- artifact_count=45
- suite_method_count=5
- suite_run_count=5
- suite_passed_count=5
- external_result_count=9
- external_engine_run=false
- external_framework_policy_decision=complete_without_locked_external_dependency
- standard_engine=strategy_authoring_native
- locked_dependency_added=false

strategy_backtest_suite_result.v1:
- suite_id=trend_pullback_backtest_suite_v1
- method_count=5
- run_count=5
- passed_count=5
- failed_count=0
- trade_count=35
- total_return=0.023312048843726618
- cost_drag_bps=35.0
- best_run_method_id=single_window
- best_run_total_return=0.004662409768745324

strategy_backtest_comparison.v1:
- method_result_count=2
- external_result_count=9
- framework_adapter_count=9
- native_trade_count=7
- native_total_return=0.004662409768745324
- suite_failed_run_count=0
- threshold_failure_count=0
- suite_best_run_method_id=single_window
- weakest_era=2026-01-05
- weakest_era_total_return=0.0019993404303773055
- portfolio_run_status=skipped
- metric_status=skipped
- report_status=skipped
```

判断:

- これらは JSON の深い preview に存在していたが、一覧 summary に出ていなかった。
- optional framework の `skipped` は重要である。外部 framework が実行されたように誤読しないため。
- `suite_passed_count=5` や `failed_count=0` は evidence の一部だが、alpha 証明ではない。
- `trade_count=35` は suite 全体の合算であり、独立した35日分の live / paper evidence ではない。

## 3. 実装

変更した code:

- `src/sis/strategy_workbench_viewer/service.py`
  - `strategy_backtest_pack.v1`
    - `pack_artifact_count`
    - `suite_method_count`
    - `suite_run_count`
    - `suite_passed_count`
    - `external_result_count`
    - `external_engine_run`
    - `external_framework_policy_decision`
    - `standard_engine`
    - `locked_dependency_added`
    - `external_adapters_required_for_completion`
  - `strategy_backtest_suite_result.v1`
    - `suite_id`
    - `method_count`
    - `run_count`
    - `passed_count`
    - `failed_count`
    - `trade_count`
    - `total_return`
    - `cost_drag_bps`
    - best run summary
  - `strategy_backtest_comparison.v1`
    - method / external / adapter counts
    - native result summary
    - suite best run summary
    - weakest era summary
    - optional framework skipped statuses

変更した tests:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
  - `test_strategy_workbench_viewer_summarizes_backtest_pack_suite_and_comparison` を追加。

更新した docs:

- `docs/strategy_workbench_viewer/README.md`
  - pack / suite / comparison の compact summary を明記。

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

Viewer manifest:

```text
strategy_backtest_pack.v1:
- pack_artifact_count=45
- suite_method_count=5
- suite_run_count=5
- suite_passed_count=5
- external_result_count=9
- external_engine_run=false
- standard_engine=strategy_authoring_native
- locked_dependency_added=false

strategy_backtest_suite_result.v1:
- suite_id=trend_pullback_backtest_suite_v1
- method_count=5
- run_count=5
- passed_count=5
- failed_count=0
- trade_count=35
- total_return=0.023312048843726618
- best_run_method_id=single_window

strategy_backtest_comparison.v1:
- method_result_count=2
- external_result_count=9
- framework_adapter_count=9
- native_trade_count=7
- native_total_return=0.004662409768745324
- suite_failed_run_count=0
- threshold_failure_count=0
- weakest_era=2026-01-05
- portfolio_run_status=skipped
- metric_status=skipped
- report_status=skipped
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

- `pack_artifact_count`
- `suite_method_count`
- `best_run_method_id`
- `weakest_era_total_return`
- `portfolio_run_status`
- `metric_status`
- `report_status`

## 検証

Focused RED:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_summarizes_backtest_pack_suite_and_comparison -q
```

実装前の期待失敗:

```text
KeyError: 'pack_artifact_count'
```

Focused GREEN:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_summarizes_backtest_pack_suite_and_comparison -q
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
14 passed
```

## 残リスク

- suite の `trade_count=35` は5手法の合算であり、独立した35日分の paper / live evidence ではない。
- optional framework は skipped であり、外部 framework で検証済みという意味ではない。
- `suite_passed_count=5`、`failed_count=0` は local backtest artifact の範囲の話であり、profit claim ではない。
- A には Runtime Observation / Learning Event がまだない。Input Feedback proposal はまだ自然には作れない。

## 次の実務的な選択肢

1. A の dogfood をまとめ、Runtime Observation / Learning Event が必要かを別計画に切る。
2. C に移り、Crypto Perp viewer-only の permission flag / Daily Brief 誤読リスクを確認する。
3. D の negative sample を使って、失敗・欠損・境界違反の Viewer 表示を dogfood する。
