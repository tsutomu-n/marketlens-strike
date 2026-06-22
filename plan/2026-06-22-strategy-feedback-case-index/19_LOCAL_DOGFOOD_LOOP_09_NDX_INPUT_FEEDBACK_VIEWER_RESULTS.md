<!--
作成日: 2026-06-22_20:58 JST
更新日: 2026-06-22_20:58 JST
-->

# Local Dogfood Loop 09 NDX Input Feedback Viewer Results

## 結論

B の `ndx_open_gap_residual_v1` で Local dogfood を進めた。

結果として、`Strategy Workbench Viewer` が `strategy_input_contract_update_review.v1` の `decision=HOLD` を status badge に出せず、`n/a` と表示していた問題を修正した。Input Feedback review は root `status` ではなく root `decision` を持つため、Viewer では `decision` を status-like field として扱う必要があった。

修正後、NDX viewer では source contract なし review と source contract あり review の両方が `HOLD` の warning badge で表示される。さらに `manual_contract_update_input_allowed=false`、`direct_contract_edit_allowed=false`、`auto_applied=false`、`paper_execution_allowed=false`、`live_allowed=false`、`source_proposal_status` が compact summary に出る。

これは manual contract update の入力としても未承認であることを見えるようにする修正であり、paper / live / wallet / signing / exchange write の許可ではない。

## 1. 計画

対象:

- lane: `Local dogfood`
- strategy_id: `ndx_open_gap_residual_v1`
- primary artifacts:
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html`

完了条件:

- Proposal / review / viewer manifest を現物確認する。
- `HOLD` review が Viewer summary table と detail badge で見えることを確認する。
- manual update 禁止、自動適用禁止、paper/live 不許可が compact summary で見えることを確認する。
- 見つかった問題は focused test を先に追加し、code を局所修正する。
- NDX viewer を再生成し、generated artifact で修正を確認する。
- focused test と current docs check、full check を通す。

やらないこと:

- manual contract update。
- credential、network、paper order、live order、wallet、signing、exchange write。
- source contract の direct apply。

## 2. 追加調査と現実チェック

確認した事実:

- source contract なし proposal:
  - `schema_version=strategy_input_contract_update_proposal.v1`
  - `status=NEEDS_SOURCE_CONTRACT_CONTEXT`
- source contract なし review:
  - `schema_version=strategy_input_contract_update_review.v1`
  - `decision=HOLD`
  - `manual_contract_update_input_allowed=false`
- source contract あり proposal:
  - `schema_version=strategy_input_contract_update_proposal.v1`
  - `status=READY_FOR_HUMAN_REVIEW`
- source contract あり review:
  - `schema_version=strategy_input_contract_update_review.v1`
  - `decision=HOLD`
  - `manual_contract_update_input_allowed=false`
  - rationale は、user-approved target contract update がないこと、PnL evidence がないこと、stale quote-age evidence があることを理由にしている。

既存 viewer の問題:

- Proposal は `NEEDS_SOURCE_CONTRACT_CONTEXT` / `READY_FOR_HUMAN_REVIEW` の badge が出ていた。
- Review は `decision=HOLD` を持つのに、summary table と detail badge では `n/a` だった。
- Preview JSON を開けば `manual_contract_update_input_allowed=false` は見えたが、compact summary では弱かった。

判断:

- `decision` は repo 内で多くの decision artifact が持つ状態・判断 field なので、Viewer の status 抽出対象に追加してよい。
- Input Feedback proposal / review の id、decision、source proposal status、manual update / direct edit / auto apply / paper / live の boolean は compact summary として見せる価値がある。
- `HOLD` は permission ではない。既存 badge class では warning 扱いであり、実務上の誤読を減らす。

## 3. 実装

変更した code:

- `src/sis/strategy_workbench_viewer/service.py`
  - `STATUS_KEYS` に `decision` を追加。
  - compact summary に `proposal_id`、`decision`、`source_proposal_status`、`proposed_change_count`、`approved_change_count`、`required_action_count`、`manual_contract_update_input_allowed`、`requires_human_contract_update`、`direct_contract_edit_allowed`、`auto_applied`、`paper_execution_allowed`、`live_allowed` を追加。
  - `strategy_input_contract_update_proposal.v1` では `proposed_change_count` を集計。
  - `strategy_input_contract_update_review.v1` では approved / required action count と source proposal status を集計。

変更した tests:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
  - `strategy_input_contract_update_review.v1` の `decision=HOLD` が status badge になること。
  - manual update 禁止、direct edit 禁止、自動適用禁止、paper/live 不許可が compact summary に残ること。

更新した docs:

- `docs/strategy_workbench_viewer/README.md`
  - `decision` を status 抽出対象として明記。
  - Strategy Input Feedback proposal / review の compact summary 表示項目を明記。

再生成した local artifact:

- `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html`
- `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json`

再生成コマンド:

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

再生成結果:

```text
status=pass
artifact_count=8
boundary_violation_count=0
html_path=data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html
manifest_path=data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json
```

## 修正後の現物確認

manifest の status 抜粋:

```text
strategy_input_contract_update_proposal.v1  NEEDS_SOURCE_CONTRACT_CONTEXT
strategy_input_contract_update_review.v1    HOLD
strategy_input_contract_update_proposal.v1  READY_FOR_HUMAN_REVIEW
strategy_input_contract_update_review.v1    HOLD
strategy_case_lite.v1                       INGESTED
strategy_case_index.v1                      INGESTED
```

HTML で確認した表示:

- source contract なし review は `<span class="badge warn">HOLD</span>`。
- source contract あり review は `<span class="badge warn">HOLD</span>`。
- `manual_contract_update_input_allowed: False` が detail summary に出る。
- `direct_contract_edit_allowed: False` が detail summary に出る。
- `auto_applied: False` が detail summary に出る。
- `paper_execution_allowed: False` と `live_allowed: False` が detail summary に出る。
- `source_proposal_status` が `NEEDS_SOURCE_CONTRACT_CONTEXT` または `READY_FOR_HUMAN_REVIEW` として出る。
- `boundary_violation_count=0`。

## 検証

Focused RED:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py -q
```

実装前の期待失敗:

```text
1 failed, 7 passed
KeyError: 'status'
```

Focused GREEN:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py -q
```

結果:

```text
8 passed in 0.21s
```

## 残リスク

- `HOLD` は manual update 承認ではない。むしろ止める判断である。
- `READY_FOR_HUMAN_REVIEW` は人間レビュー待ちであり、paper / live / wallet / signing / exchange write の許可ではない。
- NDX runtime observation は PnL evidence を持たず、quote age stale evidence が残る。
- source contract あり proposal が `READY_FOR_HUMAN_REVIEW` でも、review が `HOLD` なので direct apply に進まない。
- generated `data/local_dogfood/...` は local dogfood artifact であり、tracked source of truth ではない。

## 次の実務的な選択肢

1. B を継続し、NDX viewer で stale quote age / PnL 不足が summary で十分に見えるかを確認する。
2. A に戻り、trend の Runtime Observation / Learning Event が必要か判断する。
3. C に移り、Crypto Perp Viewer / Daily Brief の permission flag 表示を同じ観点で dogfood する。
