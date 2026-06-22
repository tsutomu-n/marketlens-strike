<!--
作成日: 2026-06-22_19:59 JST
更新日: 2026-06-22_20:06 JST
-->

# Local Dogfood Loop 01 Plan Review Results

## 結論

1セット目の `1=計画`、`2=現実チェック`、`3=実装` を実行した。

当初の棚卸しでは `trend_pullback_user_v1` を第一候補にしたが、追加調査で補正した。`trend_pullback_user_v1` は backtest / review artifact が多い一方、今回の新 surface を通しで dogfood する直接入力、つまり `strategy_runtime_observation_manifest.v1`、`strategy_learning_event.v1`、`strategy_case_lite.v1` が active `data/` にない。

既存 paper session と整合する対象は `ndx_open_gap_residual_v1` だったため、Loop 01 の実行対象は `ndx_open_gap_residual_v1` に変更した。これは「理想的な流れ」ではなく、現物 artifact に合わせた補正である。

結果として、local/offline だけで次を生成できた。

- `strategy_runtime_observation_manifest.v1`
- `strategy_input_contract_update_proposal.v1`
- `strategy_input_contract_update_review.v1`
- `strategy_case_lite.v1`
- `strategy_case_index.v1`
- `strategy_workbench_viewer.v1`

ただし、source contract はないため、proposal は `NEEDS_SOURCE_CONTRACT_CONTEXT`、review は `HOLD` で止めた。これは正しい停止であり、direct apply や contract 更新へ進めない。

## 1. 計画

目的:

- `Local dogfood` として、今回追加した local/offline surface を実 artifact で通す。
- credential、network、paper order、live order、wallet、signing、exchange write は使わない。
- `data/` の runtime artifact は git-ignored なので、判断結果を tracked plan doc に残す。

当初計画:

1. `trend_pullback_user_v1` を第一候補にする。
2. `data/strategy_reviews/dogfood-operator-current/review_manifest.json` と backtest artifacts を読む。
3. Runtime Observation を作れるなら Input Feedback proposal を作る。
4. Case Lite、Case Index、Workbench Viewer へ進む。

期待していた成果:

- `Strategy Input Feedback` が source contract 不足を正しく示す。
- `Strategy Case Index` と `Workbench Viewer` が実 artifact を読める。
- 進めない境界を report と JSON に残す。

## 2. 現実チェック

追加調査で分かったこと:

- active `data/` に `strategy_input_contract.v1` は見つからない。
- active `data/` に `strategy_runtime_observation_manifest.v1` は見つからない。
- active `data/` に `strategy_learning_event.v1` は見つからない。
- active `data/` に `strategy_case_lite.v1` と `strategy_case_index.v1` は見つからない。
- `trend_pullback_user_v1` は backtest / review の材料は多いが、paper session と直結する runtime observation source がない。
- `data/paper/observations/local-paper-20260617-200702/` は `ndx_open_gap_residual_v1` 寄りの paper evidence である。

補正判断:

- `trend_pullback_user_v1` に paper session を無理に結びつけると、strategy と paper source が混線する。
- Loop 01 では、既存 paper session と整合する `ndx_open_gap_residual_v1` を使う。
- `trend_pullback_user_v1` は次以降の review / backtest dogfood 候補として保留する。

この判断で避けた誤り:

- strategy_id だけを差し替えて別戦略の paper evidence を使うこと。
- source contract がない proposal を update-ready と読むこと。
- `status=pass` を paper / live permission と読むこと。

## 3. 実装

### 3.1 Runtime Observation Ingest

実行:

```bash
uv run sis strategy-runtime-observation-ingest \
  --strategy-id ndx_open_gap_residual_v1 \
  --session-manifest data/paper/observations/local-paper-20260617-200702/paper_observation_session_manifest.json \
  --source-stage normal_paper_observation \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation \
  --replace-existing
```

結果:

- status: `pass`
- ingest_status: `INGESTED`
- strategy_id: `ndx_open_gap_residual_v1`
- session_id: `local-paper-20260617-200702`
- ledger_entry_count: `20`
- generated artifact: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json`
- report: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_summary.md`

確認した boundary:

- `permits_live_order=false`
- `live_conversion_allowed=false`
- `wallet_used=false`
- `signing_used=false`
- `exchange_write_used=false`

重要な観測:

- `paper_fill_count=20`
- `paper_order_count=20`
- `max_observed_quote_age_ms=1048982067`
- `pnl_available=false`
- `pnl_unavailable_reason=ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd`

読み方:

- paper runtime は読めた。
- ただし PnL はない。
- quote age が大きいので、freshness や live readiness の証拠ではない。

### 3.2 Strategy Input Feedback Proposal

実行:

```bash
uv run sis strategy-input-feedback-proposal-build \
  --strategy-id ndx_open_gap_residual_v1 \
  --runtime-observation data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback \
  --replace-existing
```

結果:

- status: `pass`
- proposal_id: `ndx_open_gap_residual_v1-input-feedback-e7447e63`
- proposal_status: `NEEDS_SOURCE_CONTRACT_CONTEXT`
- proposed_change_count: `1`
- artifact: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json`
- report: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.md`

確認した boundary:

- `auto_applied=false`
- `direct_contract_edit_allowed=false`
- `permits_live_order=false`
- `exchange_write_used=false`

読み方:

- Runtime Observation から proposal は作れた。
- source contract がないので、manual contract update の入力としてはまだ不足。
- これは失敗ではなく、正しい停止。

### 3.3 Strategy Input Feedback Review

実行:

```bash
uv run sis strategy-input-feedback-proposal-review \
  --proposal data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json \
  --decision HOLD \
  --reviewer codex-local-dogfood \
  --rationale 'Local dogfood confirmed runtime observation can produce an update proposal, but active data has no strategy_input_contract.v1 for this strategy. Hold before any manual contract update.' \
  --required-action 'Provide or generate strategy_input_contract.v1 for ndx_open_gap_residual_v1 before manual contract update review.' \
  --required-action 'Keep auto_applied=false and direct_contract_edit_allowed=false; do not patch any contract in this run.' \
  --replace-existing
```

結果:

- status: `pass`
- review_id: `ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36`
- decision: `HOLD`
- manual_contract_update_input_allowed: `false`
- auto_applied: `false`
- direct_contract_edit_allowed: `false`
- artifact: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json`
- report: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.md`

読み方:

- proposal を承認せず、HOLD として止めた。
- source contract が用意されるまで manual update に進めない。

### 3.4 Strategy Case Lite

実行:

```bash
uv run sis strategy-case-lite-update \
  --strategy-id ndx_open_gap_residual_v1 \
  --runtime-observation data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases \
  --case-id ndx_open_gap_residual_v1-local-dogfood \
  --replace-existing
```

結果:

- status: `pass`
- case_id: `ndx_open_gap_residual_v1-local-dogfood`
- strategy_id: `ndx_open_gap_residual_v1`
- latest_status: `INGESTED`
- artifact_count: `1`
- artifact: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json`
- report: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.md`

読み方:

- Case Lite は runtime observation 1件を束ねられた。
- review/proposal は Case Lite の入力対象ではないため、Case Lite には入っていない。

### 3.5 Strategy Case Index

実行:

```bash
uv run sis strategy-case-index-build \
  --case data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index \
  --index-id ndx-open-gap-local-dogfood-index \
  --replace-existing
```

結果:

- status: `pass`
- index_id: `ndx-open-gap-local-dogfood-index`
- case_count: `1`
- strategy_count: `1`
- paper_execution_allowed: `false`
- live_allowed: `false`
- db_persistence_allowed: `false`
- artifact: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.json`
- report: `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.md`

読み方:

- Case Index は read-only index として機能した。
- DB registry ではない。
- paper / live permission ではない。

### 3.6 Strategy Workbench Viewer

実行:

```bash
uv run sis strategy-workbench-viewer-build \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.json \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/viewer \
  --viewer-id ndx-open-gap-local-dogfood-viewer \
  --replace-existing
```

結果:

Loop 01 時点の初回 viewer 出力:

- status: `pass`
- artifact_count: `5`
- boundary_violation_count: `0`
- HTML: `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html`
- manifest: `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json`

補足:

- 同じ viewer path は Loop 02 で source contract validation と契約あり proposal / review を含む `artifact_count=8` の版に更新した。
- 現在の viewer manifest を読む場合は [11_LOCAL_DOGFOOD_LOOP_02_SOURCE_CONTRACT_RESULTS.md](11_LOCAL_DOGFOOD_LOOP_02_SOURCE_CONTRACT_RESULTS.md) を正とする。

読み方:

- Loop 01 時点では Viewer は5 artifact をまとめられた。
- Case Index compact summary も出た。
- boundary violation は 0。

## 生成物一覧

| 種類 | path |
|---|---|
| Runtime Observation JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json` |
| Runtime Observation report | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_summary.md` |
| Runtime Observation ledger | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/runtime_observation_ledger.jsonl` |
| Input Feedback proposal JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json` |
| Input Feedback proposal report | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.md` |
| Input Feedback review JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json` |
| Input Feedback review report | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.md` |
| Case Lite JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json` |
| Case Lite report | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.md` |
| Case Index JSON | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.json` |
| Case Index report | `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.md` |
| Viewer HTML | `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html` |
| Viewer manifest | `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json` |

## Loop 01 時点で残った現実的な課題

補足:

- このセクションは Loop 01 完了時点の記録である。
- `strategy_input_contract.v1` 不足は Loop 02 で local dogfood contract を作成し、validation `PASS` まで確認した。
- Loop 02 後の現在値は [11_LOCAL_DOGFOOD_LOOP_02_SOURCE_CONTRACT_RESULTS.md](11_LOCAL_DOGFOOD_LOOP_02_SOURCE_CONTRACT_RESULTS.md) を読む。

1. `strategy_input_contract.v1` がない。
   - 影響: proposal は `NEEDS_SOURCE_CONTRACT_CONTEXT` で止まる。
   - Loop 02 後の状態: `ndx_open_gap_residual_v1` 用の local dogfood contract は作成済みで、contract validation は `PASS`。

2. Runtime observation の PnL がない。
   - 影響: drift / learning で PnL 差分を扱えない。
   - 次手: paper ledger に realized PnL / paper PnL がある evidence を使うか、PnL なし前提の learning に限定する。

3. quote age が大きい。
   - 影響: freshness / live readiness の証拠にならない。
   - 次手: D19 data freshness gate の別計画まで扱わない。

4. Case Lite は proposal / review を直接束ねない。
   - 影響: Case Lite / Case Index だけでは Input Feedback review の状態が見えない。
   - 次手: Case Lite の入力対象拡張を考える前に、Viewer で proposal / review / case index を並べる運用で足りるか dogfood する。

5. `trend_pullback_user_v1` は未実行。
   - 影響: backtest / review artifact が豊富な第一候補をまだ通していない。
   - 次手: `trend_pullback_user_v1` に紐づく runtime observation または learning event を作れるか確認する。

## Loop 01 完了時点の次ループ案

次の `1=計画`、`2=現実チェック`、`3=実装` では、次のどちらかを選ぶ想定だった。

補足:

- 次ループ案 A は Loop 02 として実行済み。
- 現在の推奨次手は [11_LOCAL_DOGFOOD_LOOP_02_SOURCE_CONTRACT_RESULTS.md](11_LOCAL_DOGFOOD_LOOP_02_SOURCE_CONTRACT_RESULTS.md) の「次ループ案」を読む。

### 次ループ案 A: `ndx_open_gap_residual_v1` の source contract を用意する

状態:

- Loop 02 で実行済み。

目的:

- `NEEDS_SOURCE_CONTRACT_CONTEXT` を解消し、proposal / review が manual contract update input として評価できるか確認する。

必要:

- `strategy_input_contract.v1` の作成または既存 path。
- ただし direct apply はまだしない。

### 次ループ案 B: `trend_pullback_user_v1` の runtime observation / learning event を作れるか調査する

目的:

- 棚卸し上の第一候補を、今回の new surface に接続できるか確認する。

必要:

- `trend_pullback_user_v1` に対応する paper session、runtime observation、drift review、learning event のどれか。
- ない場合は、backtest-only dogfood として別扱いにする。

## 完了条件

Loop 01 は次を満たした。

- 計画を立てた。
- 現実チェックで当初推奨を補正した。
- local/offline のみで実 artifact を生成した。
- generated artifacts の boundary が no live / no wallet / no signing / no exchange write を維持している。
- tracked summary としてこの文書に結果を残した。
