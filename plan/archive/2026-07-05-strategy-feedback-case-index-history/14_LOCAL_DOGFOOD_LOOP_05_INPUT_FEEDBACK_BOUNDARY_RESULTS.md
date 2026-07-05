<!--
作成日: 2026-06-22_20:24 JST
更新日: 2026-06-22_20:24 JST
-->

# Local Dogfood Loop 05 Input Feedback Boundary Results

## 結論

Loop 05 では、Loop 04 で backtest-only artifact を Case Lite / Case Index に通せるようになった後の誤読リスクを潰した。

確認結果:

- `strategy-case-lite-update --artifact` は backtest / review artifact を Case Lite に入れられる。
- しかし `strategy-input-feedback-proposal-build` は backtest-only artifact を proposal 入力にしない。
- `strategy-input-feedback-proposal-build` の発火源は `--runtime-observation` または `--learning-event` である。
- `--source-contract` は文脈であり、発火源ではない。
- 実際に `--source-contract` だけで実行すると `status=fail` で止まる。

この境界を [docs/strategy_input_feedback/README.md](../../docs/strategy_input_feedback/README.md) に追記した。

## 1. 計画

目的:

1. backtest-only Case Lite / Case Index を見た利用者が、Input Feedback proposal も作れると誤読しないようにする。
2. 現行CLIの実際の error と help を確認する。
3. 必要なら docs だけを更新し、コード変更はしない。

対象外:

- Input Feedback の入力に backtest artifact を追加すること。
- backtest result から擬似 learning event を作ること。
- runtime observation を偽造すること。

## 2. 現実チェック

確認したCLI:

```bash
uv run sis strategy-input-feedback-proposal-build --help
```

help 上の入力:

- `--runtime-observation`
- `--learning-event`
- `--source-contract`

docs 既存記述:

- `--runtime-observation` と `--learning-event` は複数指定できる。
- 少なくとも一方が必要。

追加で実行した確認:

```bash
uv run sis strategy-input-feedback-proposal-build \
  --strategy-id trend_pullback_user_v1 \
  --source-contract data/local_dogfood/2026-06-22-trend-pullback/strategy_inputs/trend_pullback_user_v1_input_contract.yaml \
  --out data/local_dogfood/2026-06-22-trend-pullback/strategy_input_feedback_empty_check \
  --replace-existing
```

結果:

```text
status=fail
error=at least one --runtime-observation or --learning-event is required
```

判定:

- `trend_pullback_user_v1` は input contract validation と backtest-only Case Lite / Case Index までは進んだ。
- しかし runtime observation または learning event がないため、Input Feedback proposal は作れない。
- これは正しい停止であり、backtest result から無理に update proposal を作らない。

## 3. 実装

更新したファイル:

```text
docs/strategy_input_feedback/README.md
```

追加した内容:

- backtest-only artifact は Input Feedback proposal の入力ではない。
- `strategy-case-lite-update --artifact` で backtest result を Case Lite / Case Index に入れられても、それだけでは proposal は作れない。
- `--source-contract` だけでは proposal は作れない。
- 実際の failure text:

```text
status=fail
error=at least one --runtime-observation or --learning-event is required
```

## 4. 完了条件

Loop 05 は次を満たした。

- 現行CLI help を確認した。
- `--source-contract` だけの failure を実行確認した。
- docs に backtest-only / source-contract-only の境界を追記した。
- コード変更は不要と判断した。

## 5. 残った現実的な課題

1. `trend_pullback_user_v1` の Input Feedback proposal はまだ作れない。
   - 理由: runtime observation または learning event がない。
   - 進める絶対条件: trend と明確に紐づく runtime observation か learning event を用意すること。

2. backtest-only artifact から learning event を作る route はない。
   - 理由: 現行設計では learning event は drift review 由来。
   - 進める絶対条件: backtest-only learning を別概念として設計するか、runtime observation を用意して drift review を作ること。

3. Case Lite / Case Index の見た目だけでは operational readiness と誤読される可能性がある。
   - 理由: latest_status に `READY_FOR_HUMAN_REVIEW` が表示され得る。
   - 対策: boundary flags と docs の読み方を維持し、paper/live permission と切り離して説明する。

## 6. 次ループ案

### 推奨: Loop 06 は current implementation contract / TASK_CHAIN と実装済み差分の整合を監査する

状態:

- 実行済み。結果は [15_LOCAL_DOGFOOD_LOOP_06_PLAN_ALIGNMENT_RESULTS.md](15_LOCAL_DOGFOOD_LOOP_06_PLAN_ALIGNMENT_RESULTS.md) を読む。

理由:

- Local dogfood の結果、当初計画にはなかった `strategy-case-lite-update --artifact` が実装された。
- 既存 plan の `02_TASKS.md`、`03_FILE_MAP.md`、`04_TEST_AND_ACCEPTANCE.md`、`TASK_CHAIN.yaml` が、この追加実装を反映していない可能性がある。
- 次にコードを増やすより、active implementation plan と current implementation の差分を揃える方が実務的。

実行候補:

1. `02_TASKS.md`、`03_FILE_MAP.md`、`04_TEST_AND_ACCEPTANCE.md`、`TASK_CHAIN.yaml` を読む。
2. Case Lite `--artifact` と backtest-only Case Index dogfood を反映すべき箇所を特定する。
3. 反映が必要なら docs / task chain を更新する。
4. full `./scripts/check` を回す。
