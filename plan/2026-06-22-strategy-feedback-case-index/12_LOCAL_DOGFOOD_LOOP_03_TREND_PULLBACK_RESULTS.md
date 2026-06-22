<!--
作成日: 2026-06-22_20:16 JST
更新日: 2026-06-22_20:20 JST
-->

# Local Dogfood Loop 03 Trend Pullback Results

## 結論

Loop 03 では、`trend_pullback_user_v1` を今回の Strategy Input Feedback / Case Index surface に接続できるか調査し、承認不要でできる範囲を実行した。

結果:

- `trend_pullback_user_v1` は backtest / review artifact が豊富。
- ただし `strategy_runtime_observation_manifest.v1` と `strategy_learning_event.v1` は存在しない。
- `strategy-drift-review` は backtest result と runtime observation の両方を要求する。
- `strategy-learning-ledger-update` は drift review を要求する。
- `strategy-input-feedback-proposal-build` は runtime observation または learning event の少なくとも一方を要求する。
- `strategy-case-lite-update` は stage decision / runtime / drift / learning / revision / handoff / live 系 artifact を受け取るが、backtest artifact を直接 Case Lite 化する入力はない。
- したがって、`trend_pullback_user_v1` は今回の surface に runtime / learning route ではまだ接続できない。
- 承認不要でできる実装として、backtest-only の local dogfood input contract を作成し、validation `PASS` を確認した。
- さらに backtest / review artifact を Static Workbench Viewer にまとめ、viewer artifact count `8`、boundary violation `0` を確認した。

この Loop 03 の正しい読み方は「backtest-only の証拠台帳と読み取り viewer は作れたが、runtime / drift / learning / case index には進めない」である。これは失敗ではなく、現物に基づく停止である。

## 用語の言い換え

- `backtest-only`: 実売買や paper order の観測ではなく、研究用の過去データ検証だけを根拠にする状態。
- `runtime observation`: paper 実行観測の記録。ここでは `trend_pullback_user_v1` 用のものがない。
- `drift review`: backtest と runtime observation の差を比較するレビュー。runtime observation がないと作れない。
- `learning event`: drift review から得た学びの記録。drift review がないと作れない。
- `Case Lite`: 戦略の進行履歴を薄く束ねる artifact。現行CLIでは backtest artifact を直接入力にしない。
- `Workbench Viewer`: JSON / Markdown / Text artifact を静的HTMLで並べる読み取り用 viewer。

## 1. 計画

目的:

1. `trend_pullback_user_v1` の既存 artifact を、現行コードとCLI仕様を正として再棚卸しする。
2. runtime observation / learning event / case lite / case index に接続できるか判定する。
3. 無理に `ndx_open_gap_residual_v1` の paper evidence を流用しない。
4. 承認不要でできる backtest-only dogfood artifact を作る。
5. 判断結果を tracked plan doc に残す。

対象 strategy:

- `trend_pullback_user_v1`

対象外:

- paper order 実行
- live order 実行
- wallet
- signing
- exchange write
- credentialed network
- `ndx_open_gap_residual_v1` の paper session を trend 用に付け替えること

## 2. 現実チェック

### 2.1 CLI の現実

確認した CLI:

```bash
uv run sis strategy-runtime-observation-ingest --help
uv run sis strategy-drift-review --help
uv run sis strategy-learning-ledger-update --help
uv run sis strategy-input-feedback-proposal-build --help
uv run sis strategy-case-lite-update --help
uv run sis strategy-workbench-viewer-build --help
uv run sis strategy-backtest-artifact-summary --help
```

分かったこと:

- `strategy-runtime-observation-ingest` は `paper_observation_session_manifest.v1` を要求する。
- `strategy-drift-review` は `strategy_authoring_backtest_result.v1` と `strategy_runtime_observation_manifest.v1` を要求する。
- `strategy-learning-ledger-update` は `paper_vs_backtest_drift_review.json` を要求する。
- `strategy-input-feedback-proposal-build` は少なくとも `--runtime-observation` または `--learning-event` を要求する。
- `strategy-case-lite-update` は backtest artifact を直接入力にできない。
- `strategy-workbench-viewer-build` は JSON / Markdown / Text を扱えるが、YAML は直接 artifact として扱えない。
- `strategy-backtest-artifact-summary` は stdout に要約を出すだけで、artifact 出力先を持たない。

### 2.2 既存 artifact の現実

`trend_pullback_user_v1` として確認できた主な artifact:

| path | schema / 種類 | 読み方 |
|---|---|---|
| `docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml` | authoring spec | 戦略仕様 |
| `data/research/backtest_pack/source_artifacts/research/strategy_signal_manifest.json` | `strategy_signal_manifest.v1` | trend 用に固定コピーされた signal manifest |
| `data/research/backtest_pack/source_artifacts/research/strategy_signals.jsonl` | `strategy_signal.v1` rows | 7 signals, all `trend_pullback_user_v1` |
| `data/research/strategy_backtest_metrics.json` | `strategy_authoring_backtest_result.v1` | backtest result |
| `data/research/backtest_pack/strategy_backtest_pack.json` | `strategy_backtest_pack.v1` | backtest pack |
| `data/research/backtest_pack/strategy_backtest_pack_validation.json` | `strategy_backtest_pack_validation.v1` | validation `PASS` |
| `data/research/backtest_suite/strategy_backtest_suite_result.json` | `strategy_backtest_suite_result.v1` | 5 runs, 5 passed |
| `data/research/backtest_compare/strategy_backtest_comparison.json` | `strategy_backtest_comparison.v1` | comparison summary |
| `data/strategy_reviews/dogfood-operator-current/review_manifest.json` | `strategy_review_manifest.v1` | review status `READY_FOR_HUMAN_REVIEW` |

重要な補正:

- active root の `data/research/strategy_signal_manifest.json` は `ndx_open_gap_residual_v1` を指している。
- そのため `trend_pullback_user_v1` の contract には使わない。
- `trend_pullback_user_v1` には、backtest pack 内の固定コピー `data/research/backtest_pack/source_artifacts/research/strategy_signal_manifest.json` を使う。

### 2.3 Paper / runtime の現実

確認:

```bash
find data/paper/observations -name 'paper_observation_session_manifest.json' -print
rg -n "trend_pullback_user_v1" data/paper data/local_dogfood
```

結果:

- paper observation session manifest は複数ある。
- ただし manifest 自体に `strategy_id` は入っていない。
- `data/paper/observations` には `trend_pullback_user_v1` 文字列が見つからない。
- 既存 local dogfood runtime observation は `ndx_open_gap_residual_v1` 用である。

判定:

- paper session を `trend_pullback_user_v1` 用として読み替える根拠がない。
- ここで `--strategy-id trend_pullback_user_v1` を付けて runtime ingest すると、別戦略の paper evidence を誤結合するリスクが高い。
- よって runtime / drift / learning route は止める。

## 3. 実装

### 3.1 Trend Pullback Local Dogfood Contract

作成したファイル:

```text
data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/trend_pullback_user_v1_input_contract.yaml
```

主な内容:

- `schema_version: strategy_input_contract.v1`
- `contract_id: trend-pullback-user-v1-local-dogfood-inputs`
- `strategy_family: trend_pullback`
- `instruments: QQQ, XYZ100`
- `timeframe: 4h`
- `intended_use: research_backtest_only`

明示した禁止境界:

- `permits_live_order=false`
- `live_conversion_allowed=false`
- `wallet_used=false`
- `signing_used=false`
- `exchange_write_used=false`

known gaps:

- local dogfood 専用であり、production / paper execution / live readiness の入力契約ではない。
- `strategy_runtime_observation_manifest.v1` がない。
- `strategy_learning_event.v1` がない。
- paper observation session は `trend_pullback_user_v1` を識別していない。
- backtest metrics は研究シミュレーションであり、paper fill や live execution の観測ではない。

### 3.2 Contract Validation

実行:

```bash
uv run sis strategy-input-contract-validate \
  --contract data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/trend_pullback_user_v1_input_contract.yaml \
  --out data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation \
  --replace-existing
```

結果:

- status: `pass`
- validation_status: `PASS`
- contract_id: `trend-pullback-user-v1-local-dogfood-inputs`
- missing_required_count: `0`
- boundary_violation_count: `0`
- invalid_required_count: `0`
- timestamp_violation_count: `0`
- warning_count: `0`

特に確認したこと:

- `packed_strategy_signals_jsonl` は required columns present。
- `packed_strategy_signals_jsonl` の timestamp check は `true`。
- max observed timestamp は `2026-06-17T10:35:56Z`。
- すべての declared sha256 は現物と一致。

生成物:

```text
data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json
data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.md
```

### 3.3 Trend Pullback Workbench Viewer

実行:

```bash
uv run sis strategy-workbench-viewer-build \
  --artifact data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json \
  --artifact data/research/strategy_backtest_metrics.json \
  --artifact data/research/backtest_pack/strategy_backtest_pack.json \
  --artifact data/research/backtest_pack/strategy_backtest_pack_validation.json \
  --artifact data/research/backtest_suite/strategy_backtest_suite_result.json \
  --artifact data/research/backtest_compare/strategy_backtest_comparison.json \
  --artifact data/strategy_reviews/dogfood-operator-current/review_manifest.json \
  --artifact data/strategy_reviews/dogfood-operator-current/review.md \
  --out data/local_dogfood/2026-06-22-trend-pullback/viewer \
  --viewer-id trend-pullback-local-dogfood-viewer \
  --replace-existing
```

結果:

- status: `pass`
- artifact_count: `8`
- boundary_violation_count: `0`
- paper_execution_allowed: `false`
- live_allowed: `false`
- wallet_used: `false`
- signing_used: `false`
- exchange_write_used: `false`

生成物:

```text
data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html
data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json
```

## 4. 現在ある成果物一覧

| 種類 | path | 状態 |
|---|---|---|
| Trend input contract | `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/trend_pullback_user_v1_input_contract.yaml` | dogfood only |
| Contract validation JSON | `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.json` | `PASS` |
| Contract validation report | `data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/validation/strategy_input_contract_validation.md` | `PASS` |
| Viewer HTML | `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer.html` | 8 artifact |
| Viewer manifest | `data/local_dogfood/2026-06-22-trend-pullback/viewer/strategy_workbench_viewer_manifest.json` | 8 artifact / boundary violation 0 |

## 5. 完了条件

Loop 03 は次を満たした。

- `trend_pullback_user_v1` の existing artifacts を再棚卸しした。
- active root の signal manifest と backtest pack 内の trend manifest の違いを見つけ、contract では後者を使った。
- runtime observation / drift / learning / case lite / case index へ進めない理由を CLI仕様と artifact 現物で確認した。
- local dogfood contract を作成し、validation `PASS` を確認した。
- backtest / review artifacts を Workbench Viewer にまとめた。
- live order、wallet、signing、exchange write、credentialed network は使っていない。

## 6. 残った現実的な課題

1. `trend_pullback_user_v1` の runtime observation がない。
   - 影響: drift review、learning event、input feedback proposal、case lite へ進めない。
   - 進める絶対条件: `trend_pullback_user_v1` と明確に紐づく paper observation session または runtime observation を用意すること。

2. backtest-only contract は paper/live readiness ではない。
   - 影響: backtest result が `PASS` でも paper execution や live execution の根拠にならない。
   - 進める絶対条件: paper observation または live observation の別 artifact を作ること。

3. active root の signal manifest が NDX を指している。
   - 影響: `data/research/strategy_signal_manifest.json` を安易に trend の証拠として使うと strategy_id が混線する。
   - 進める絶対条件: trend 用には backtest pack 内の fixed snapshot を使うか、root manifest の current owner を明示すること。

4. Case Index はまだ trend に対して未生成。
   - 理由: Case Lite の入力対象がない。
   - Loop 04 後の状態: Case Lite に `--artifact` を追加し、backtest-only artifact を Case Lite / Case Index へ通した。現在値は [13_LOCAL_DOGFOOD_LOOP_04_CASE_LITE_BACKTEST_ARTIFACT_RESULTS.md](13_LOCAL_DOGFOOD_LOOP_04_CASE_LITE_BACKTEST_ARTIFACT_RESULTS.md) を読む。

5. Workbench Viewer は YAML contract を直接表示しない。
   - 理由: 現行CLIは YAML artifact を unsupported format として扱う。
   - 進める絶対条件: Viewer の YAML support を別実装するか、validation JSON / proposal source_artifacts 経由で辿る運用にすること。

## 7. 次ループ案

### 推奨: Loop 04 は「runtime observation を作るべきか、Case Lite の backtest-only support を作るべきか」を計画レビューする

状態:

- 実行済み。結果は [13_LOCAL_DOGFOOD_LOOP_04_CASE_LITE_BACKTEST_ARTIFACT_RESULTS.md](13_LOCAL_DOGFOOD_LOOP_04_CASE_LITE_BACKTEST_ARTIFACT_RESULTS.md) を読む。

現実的な選択肢:

1. `trend_pullback_user_v1` の paper observation source を新規に用意する。
   - 長所: 現行設計に沿って drift / learning / input feedback / case lite へ進める。
   - 短所: paper observation 実行や evidence 用意が必要。承認や実行条件が増える。

2. Case Lite に backtest-only artifact support を追加する。
   - 長所: 既存 backtest artifact を Case Index に接続できる。
   - 短所: Case Lite の責務が広がる。Strategy Operations の時系列と backtest report の境界が曖昧になる。

3. Workbench Viewer の YAML support を追加する。
   - 長所: input contract 自体を viewer で読める。
   - 短所: Case Index / Input Feedback の本質的な欠落は解消しない。

推奨順位:

1. まず選択肢 2 の実装妥当性を review する。
2. ただし、Case Lite の責務が広がりすぎるなら実装しない。
3. その場合は、選択肢 1 を「ユーザーが用意するもの」または別 plan に戻す。
