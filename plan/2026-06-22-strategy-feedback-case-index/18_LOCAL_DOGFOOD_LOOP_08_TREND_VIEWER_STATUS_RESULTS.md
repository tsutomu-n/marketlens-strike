<!--
作成日: 2026-06-22_20:52 JST
更新日: 2026-06-22_20:52 JST
-->

# Local Dogfood Loop 08 Trend Viewer Status Results

## 結論

推奨 A の `trend_pullback_user_v1` で Local dogfood を進めた。

結果として、`Strategy Workbench Viewer` の summary table が `strategy_case_lite.v1` と `strategy_case_index.v1` を `n/a` status として表示していた問題を修正した。これらの artifact は root field に `status` を持たず、`summary.latest_status` または case index 内の latest case status に状態を持つため、viewer の badge では `READY_FOR_HUMAN_REVIEW` を出すべきだった。

修正後、trend pullback の再生成済み viewer では、Case Lite と Case Index がどちらも `READY_FOR_HUMAN_REVIEW` の warning badge で表示される。これは人間レビュー待ちの表示であり、paper / live / wallet / signing / exchange write の許可ではない。

## 1. 計画

対象:

- lane: `Local dogfood`
- strategy_id: `trend_pullback_user_v1`
- primary artifact:
  - `data/local_dogfood/2026-06-22-trend-pullback/strategy_cases/trend_pullback_user_v1/strategy_case_lite.json`
  - `data/local_dogfood/2026-06-22-trend-pullback/strategy_case_index/trend-pullback-local-dogfood-index.json`
  - `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html`

完了条件:

- Case Lite / Case Index / Viewer manifest を現物確認する。
- Viewer が `READY_FOR_HUMAN_REVIEW` を permission と誤読させず、状態として見えることを確認する。
- 見つかった問題は focused test を先に追加し、code を局所修正する。
- trend viewer を再生成し、generated artifact で修正を確認する。
- focused test と current docs check、full check を通す。

やらないこと:

- credential、network、paper order、live order、wallet、signing、exchange write。
- Strategy Input Contract の direct apply。
- DB registry、Svelte / server UI。

## 2. 追加調査と現実チェック

確認した事実:

- `strategy_case_lite.v1` の `summary.latest_status` は `READY_FOR_HUMAN_REVIEW`。
- `strategy_case_index.v1` の latest case status も `READY_FOR_HUMAN_REVIEW`。
- `paper_execution_allowed=false`、`live_allowed=false`、`permits_live_order=false`、`wallet_used=false`、`signing_used=false`、`exchange_write_used=false` は維持されている。
- 既存 viewer HTML の詳細 section には `latest_status=READY_FOR_HUMAN_REVIEW` が出ていた。
- しかし summary table と detail badge は、Case Lite / Case Index を `n/a` として表示していた。

原因:

- `src/sis/strategy_workbench_viewer/service.py` の `_compact_summary` は `latest_status` を抽出していた。
- 一方で badge 用の `status` は `_first_status` が root の `status` / `review_status` / `decision_status` などだけを読むため、Case Lite / Case Index の latest status を拾えていなかった。

判断:

- 全 artifact に対して `summary.latest_status` を status 扱いにするのは広すぎる。
- 今回は `strategy_case_lite.v1` と `strategy_case_index.v1` に限定して、`summary.latest_status` を artifact status badge に使う。
- `READY_FOR_HUMAN_REVIEW` は既存 rendering の badge class で warning 扱いなので、permission 誤読を強めない。

## 3. 実装

変更した code:

- `src/sis/strategy_workbench_viewer/service.py`
  - `strategy_case_lite.v1` と `strategy_case_index.v1` に限り、root status がない場合に compact summary の `latest_status` を artifact status として使うようにした。

変更した tests:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
  - Case Index の source artifact status が `READY_FOR_HUMAN_REVIEW` になることを追加。
  - Case Lite 単体でも `summary.latest_status` が status badge になる test を追加。

更新した docs:

- `docs/strategy_workbench_viewer/README.md`
  - Case Lite / Case Index の `latest_status` が status badge に使われることを明記。

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
html_path=data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html
manifest_path=data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json
```

## 修正後の現物確認

manifest の status 抜粋:

```text
strategy_review_manifest.v1  READY_FOR_HUMAN_REVIEW
strategy_case_lite.v1        READY_FOR_HUMAN_REVIEW
strategy_case_index.v1       READY_FOR_HUMAN_REVIEW
```

HTML の summary table でも次を確認した。

- `strategy_case_lite.v1 / trend_pullback_user_v1` は `<span class="badge warn">READY_FOR_HUMAN_REVIEW</span>`。
- `strategy_case_index.v1` は `<span class="badge warn">READY_FOR_HUMAN_REVIEW</span>`。
- `boundary_violation_count=0`。

## 検証

Focused RED:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py -q
```

実装前の期待失敗:

```text
2 failed, 5 passed
KeyError: 'status'
```

Focused GREEN:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py -q
```

結果:

```text
7 passed in 0.21s
```

## 残リスク

- `READY_FOR_HUMAN_REVIEW` は人間レビュー待ちであり、実行許可ではない。
- `trend_pullback_user_v1` はまだ Runtime Observation / Learning Event がないため、Input Feedback proposal dogfood には進めない。
- `n/a` のまま残る backtest pack / suite / comparison artifact は root status を持たないため、今回の修正では広げない。
- generated `data/local_dogfood/...` は local dogfood artifact であり、tracked source of truth ではない。

## 次の実務的な選択肢

1. A を継続し、Viewer で次に読みにくい点を探す。
2. A の範囲で、Runtime Observation / Learning Event が本当に必要かを判断する。
3. B に移り、NDX の Input Feedback proposal / review の表示を同じ観点で dogfood する。
