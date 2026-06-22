<!--
作成日: 2026-06-22_20:06 JST
更新日: 2026-06-22_20:16 JST
-->

# Local Dogfood Loop 02 Source Contract Results

## 結論

Loop 02 では、Loop 01 で止まった `NEEDS_SOURCE_CONTRACT_CONTEXT` を現実的に検証した。

結果:

- `ndx_open_gap_residual_v1` 用の local dogfood 専用 `strategy_input_contract.v1` を作成した。
- `strategy-input-contract-validate` は最初 `NEEDS_FIX` になった。
- 原因は `paper_observation_ledger` の `created_at` が秒以下を持つのに、`max_allowed_timestamp` を `2026-06-17T11:13:45Z` ぴったりに置いたことだった。
- 実データの最終行は `2026-06-17T11:13:45.220224+00:00` なので、上限を `2026-06-17T11:13:46Z` に直した。
- 再検証後、contract validation は `PASS` になった。
- その contract を渡すと、Input Feedback proposal は `READY_FOR_HUMAN_REVIEW` になった。
- ただし review は `HOLD` のまま止めた。理由は、まだ人間が承認した contract 更新先と更新方針がなく、PnL evidence もなく、quote age も大きいからである。
- Viewer は8 artifact 版に更新し、boundary violation は `0` だった。

この Loop 02 は「contract があれば仕組みは前に進む」ことを確認したが、「contract を更新してよい」「paper / live に進んでよい」ことは確認していない。

## 用語の言い換え

- `strategy_input_contract.v1`: 戦略が何を根拠データとして使ってよいかを列挙する入力証拠台帳。
- `source contract`: 上の入力証拠台帳のこと。この文書では同じ意味で使う。
- `validation`: 入力証拠台帳に書いたファイルが存在し、ハッシュ、列、時刻、境界条件に矛盾がないかを確認すること。
- `proposal`: 観測結果を見て「入力証拠台帳のこの部分を人間が見直したほうがよい」と提案する成果物。
- `review`: proposal に対する人間または作業者の判断記録。
- `HOLD`: 進められる材料はあるが、承認や入力が足りないため止める判断。
- `READY_FOR_HUMAN_REVIEW`: 人間レビューに出せる状態。自動適用や実運用許可ではない。
- `boundary`: 禁止境界。ここでは live order、wallet、signing、exchange write などを使っていないこと。

## 1. 計画

目的:

1. Loop 01 の `NEEDS_SOURCE_CONTRACT_CONTEXT` が本当に source contract 不足だけで起きているか確認する。
2. 既存 active data から、dogfood 用の最小 `strategy_input_contract.v1` を作る。
3. contract validation を通す。
4. 同じ runtime observation に contract を添えて proposal を再生成する。
5. proposal が `READY_FOR_HUMAN_REVIEW` になるか確認する。
6. ただし direct apply、manual contract update 承認、paper execution、live execution には進めない。

対象 strategy:

- `ndx_open_gap_residual_v1`

理由:

- Loop 01 で使った paper observation session と整合する strategy が `ndx_open_gap_residual_v1` だった。
- `trend_pullback_user_v1` は backtest / review artifact は多いが、この runtime observation source とは直接つながらない。

## 2. 現実チェック

### 2.1 CLI の現実

確認した CLI:

```bash
uv run sis strategy-input-contract-validate --help
uv run sis strategy-input-feedback-proposal-build --help
uv run sis strategy-input-feedback-proposal-review --help
uv run sis strategy-workbench-viewer-build --help
```

分かったこと:

- `strategy-input-contract-validate` は contract を生成しない。既存の YAML / JSON を検証するだけ。
- `strategy-input-feedback-proposal-build` は `--source-contract` を任意で受け取る。
- `--source-contract` がない場合、proposal は `NEEDS_SOURCE_CONTRACT_CONTEXT` になり得る。
- `strategy-workbench-viewer-build` は JSON / Markdown / Text を受け付けるが、YAML は直接受け付けない。

このため、contract YAML は viewer に直接入れず、contract validation JSON と proposal の `source_artifacts` から辿る形にした。

### 2.2 入力データの現実

dogfood contract に含めた source:

| source_id | path | 役割 |
|---|---|---|
| `paper_observation_session_manifest` | `data/paper/observations/local-paper-20260617-200702/paper_observation_session_manifest.json` | paper observation session の目次 |
| `paper_observation_ledger` | `data/paper/observations/local-paper-20260617-200702/paper_observation_ledger.jsonl` | paper fill 観測の明細 |
| `paper_observation_review_decision` | `data/research/ndx/paper_observation_review_decision.json` | paper observation review の判断 |
| `operator_promotion_decision` | `data/research/ndx/operator_promotion_decision.json` | paper observation へ進めた判断 |
| `paper_candidate_pack` | `data/research/paper_candidate_pack.json` | paper candidate の候補パック |
| `paper_intent_preview` | `data/bot/paper_intent_preview.json` | paper intent preview |

重要な制限:

- ledger には `realized_pnl_usd`、`paper_pnl_usd`、`pnl_usd` がない。
- runtime observation の `max_observed_quote_age_ms` は `1048982067` と大きい。
- この contract は local dogfood 専用で、production / paper order / live order の readiness 証明ではない。

## 3. 実装

### 3.1 Local Dogfood Contract 作成

作成したファイル:

```text
data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml
```

主な内容:

- `schema_version: strategy_input_contract.v1`
- `contract_id: ndx-open-gap-residual-v1-local-dogfood-inputs`
- `strategy_family: ndx_open_gap_residual`
- `instruments: QQQ, XYZ100`
- `timeframe: 1d`
- `intended_use: paper_observation_research_only`

明示した禁止境界:

- `permits_live_order=false`
- `live_conversion_allowed=false`
- `wallet_used=false`
- `signing_used=false`
- `exchange_write_used=false`

### 3.2 初回 validation と失敗

実行:

```bash
uv run sis strategy-input-contract-validate \
  --contract data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation \
  --replace-existing
```

初回結果:

- CLI process status: `pass`
- validation_status: `NEEDS_FIX`
- missing_required_count: `0`
- boundary_violation_count: `0`
- invalid_required_count: `1`
- timestamp_violation_count: `1`

原因:

- `paper_observation_ledger` の最終 `created_at` は `2026-06-17T11:13:45.220224+00:00`。
- contract 側の `max_allowed_timestamp` は `2026-06-17T11:13:45Z`。
- 秒以下 `0.220224` のぶんだけ source timestamp が上限を超えた。

ここで避けた誤読:

- CLI の `status=pass` は「検証コマンドが実行できた」という意味で、contract が有効という意味ではない。
- contract の有効性は JSON の `validation_status` を見る必要がある。

### 3.3 timestamp 上限修正

修正:

```yaml
max_allowed_timestamp: "2026-06-17T11:13:46Z"
```

理由:

- 実データの最大 timestamp は `2026-06-17T11:13:45.220224+00:00`。
- 次の秒である `2026-06-17T11:13:46Z` を上限にすれば、未来データ違反ではなくなる。
- データ範囲を広げる修正ではなく、実在する最終行の秒以下を正しく含める修正である。

### 3.4 再 validation

実行:

```bash
uv run sis strategy-input-contract-validate \
  --contract data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation \
  --replace-existing
```

結果:

- status: `pass`
- validation_status: `PASS`
- contract_id: `ndx-open-gap-residual-v1-local-dogfood-inputs`
- missing_required_count: `0`
- boundary_violation_count: `0`
- column_check_failure_count: `0`
- invalid_required_count: `0`
- timestamp_violation_count: `0`
- warning_count: `0`

生成物:

```text
data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.json
data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.md
```

### 3.5 Contract あり proposal

実行:

```bash
uv run sis strategy-input-feedback-proposal-build \
  --strategy-id ndx_open_gap_residual_v1 \
  --runtime-observation data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json \
  --source-contract data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract \
  --replace-existing
```

結果:

- status: `pass`
- proposal_id: `ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63`
- proposal_status: `READY_FOR_HUMAN_REVIEW`
- proposed_change_count: `1`
- auto_applied: `false`
- direct_contract_edit_allowed: `false`
- paper_execution_allowed: `false`
- live_allowed: `false`

生成物:

```text
data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json
data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.md
```

提案された変更:

| change_id | target_section | 内容 |
|---|---|---|
| `runtime-001` | `execution_reality` | Runtime observation evidence を見て、execution reality または source validation expectations を人間が見直す |

読み方:

- `NEEDS_SOURCE_CONTRACT_CONTEXT` は source contract を渡すことで解消した。
- ただし proposal は「人間レビューの入力」であり、contract への自動反映ではない。

### 3.6 Contract あり proposal review

実行:

```bash
uv run sis strategy-input-feedback-proposal-review \
  --proposal data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json \
  --decision HOLD \
  --reviewer codex-local-dogfood \
  --rationale 'Local dogfood confirmed that a validated strategy_input_contract.v1 lets the feedback proposal advance to READY_FOR_HUMAN_REVIEW. Hold before any manual contract update because this run has no user-approved target contract update, no PnL evidence, and stale quote-age evidence.' \
  --required-action 'Choose a human-approved manual contract update target before applying runtime-001 to any Strategy Input Contract.' \
  --required-action 'If a manual contract update is later made, keep it review-only and rerun strategy-input-contract-validate before using it as authoring input.' \
  --required-action 'Do not treat this dogfood proposal as paper execution, live readiness, wallet, signing, exchange write, or credentialed network permission.' \
  --replace-existing
```

結果:

- status: `pass`
- review_id: `ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a`
- decision: `HOLD`
- manual_contract_update_input_allowed: `false`
- auto_applied: `false`
- direct_contract_edit_allowed: `false`
- paper_execution_allowed: `false`
- live_allowed: `false`

生成物:

```text
data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json
data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.md
```

HOLD にした理由:

1. この run は local dogfood であり、ユーザー承認済みの manual contract update ではない。
2. proposal の `runtime-001` は「見直し提案」であり、具体的な差分パッチではない。
3. PnL evidence がない。
4. quote age が大きく、freshness 証明ではない。
5. paper execution / live execution / wallet / signing / exchange write の許可がない。

### 3.7 Viewer 更新

初回試行:

```bash
uv run sis strategy-workbench-viewer-build \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml \
  ...
```

結果:

- status: `fail`
- error: `unsupported artifact format: data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml`

対応:

- YAML contract を viewer artifact から外した。
- contract 自体は proposal の `source_artifacts` と validation JSON から辿れる。

再実行:

```bash
uv run sis strategy-workbench-viewer-build \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.json \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/viewer \
  --viewer-id ndx-open-gap-local-dogfood-viewer \
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
data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html
data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json
```

## 4. 現在ある成果物一覧

| 種類 | path | 状態 |
|---|---|---|
| Local dogfood input contract | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml` | dogfood only |
| Contract validation JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.json` | `PASS` |
| Contract validation report | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.md` | `PASS` |
| No-contract proposal JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json` | `NEEDS_SOURCE_CONTRACT_CONTEXT` |
| No-contract review JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json` | `HOLD` |
| Contract proposal JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json` | `READY_FOR_HUMAN_REVIEW` |
| Contract review JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json` | `HOLD` |
| Viewer HTML | `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html` | 8 artifact |
| Viewer manifest | `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json` | 8 artifact / boundary violation 0 |

## 5. 完了条件

Loop 02 は次を満たした。

- `NEEDS_SOURCE_CONTRACT_CONTEXT` の原因が source contract 不足であることを、contract あり proposal で確認した。
- local dogfood contract を作った。
- contract validation を `PASS` まで持っていった。
- proposal が `READY_FOR_HUMAN_REVIEW` になることを確認した。
- review を `HOLD` にして、manual contract update へ進ませなかった。
- Viewer を8 artifact 版に更新した。
- live order、wallet、signing、exchange write、credentialed network は使っていない。

## 6. 残った現実的な課題

1. Manual contract update は未実施。
   - 理由: ユーザー承認済みの更新先と更新方針がない。
   - 進める絶対条件: どの contract に `runtime-001` をどう反映するかを人間が決めること。

2. PnL evidence はまだない。
   - 理由: paper ledger に PnL 系列がない。
   - 進める絶対条件: `realized_pnl_usd`、`paper_pnl_usd`、`pnl_usd` のいずれかを含む paper/runtime evidence を用意すること。

3. Freshness evidence はまだない。
   - 理由: quote age が大きい。
   - 進める絶対条件: fresh quote / market data を扱う別 gate か、freshness を評価できる artifact を用意すること。

4. `trend_pullback_user_v1` はまだこの surface で dogfood していない。
   - 理由: 既存 paper observation source と strategy_id が直結しない。
   - 進める絶対条件: `trend_pullback_user_v1` に対応する runtime observation、learning event、または strategy 入力 contract を用意すること。

5. Viewer は YAML contract を直接表示できない。
   - 理由: CLI が YAML artifact を unsupported format として拒否した。
   - 進める絶対条件: Viewer の対象 artifact format を拡張する実装計画を別途立てること。

## 7. 次ループ案

### 推奨: Loop 03 は `trend_pullback_user_v1` の接続可能性を調査する

状態:

- 実行済み。結果は [12_LOCAL_DOGFOOD_LOOP_03_TREND_PULLBACK_RESULTS.md](12_LOCAL_DOGFOOD_LOOP_03_TREND_PULLBACK_RESULTS.md) を読む。

理由:

- `ndx_open_gap_residual_v1` は source contract あり proposal まで確認できた。
- ここで手動 contract update に進むには、人間の承認が必要になる。
- いま承認なしでできる価値が高い次手は、棚卸し上の第一候補だった `trend_pullback_user_v1` を同じ surface に接続できるか確認すること。

実行方針:

1. `trend_pullback_user_v1` の backtest / review / strategy artifacts を再棚卸しする。
2. runtime observation または learning event を作れる source があるか確認する。
3. なければ、backtest-only dogfood として扱える最小 route を計画する。
4. 無理に `ndx_open_gap_residual_v1` の paper evidence を流用しない。

### 代替: Manual contract update 計画へ進む

必要条件:

- ユーザーが `runtime-001` をどの contract に反映するかを指定する。
- 反映後の contract validation を必須にする。
- direct apply ではなく、人間が差分を読む前提にする。

この選択は、必須の承認事項が増えるため、現時点では推奨順位を下げる。
