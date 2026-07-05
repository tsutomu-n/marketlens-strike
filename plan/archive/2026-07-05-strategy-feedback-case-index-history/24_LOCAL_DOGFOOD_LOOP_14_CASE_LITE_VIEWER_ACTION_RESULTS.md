<!--
作成日: 2026-06-22_21:29 JST
更新日: 2026-06-22_21:29 JST
-->

# Local Dogfood Loop 14 Case Lite Viewer Action Results

## 結論

B の `ndx_open_gap_residual_v1` で Local dogfood を継続した。

Loop 13 で Case Lite / Case Index は `HOLD` と open action / blocked reason を持つようになった。しかし追加調査で、Viewer の Case Lite summary は `latest_status=HOLD` だけを表示し、Case Lite 自体の `open_actions` と `blocked_reasons` は preview JSON を開かないと見えなかった。Case Index には first open action / blocker が出ていたため、Case Lite と Case Index の見え方が不揃いだった。

これを修正し、`strategy_case_lite.v1` の `summary.open_actions[0]` と `summary.blocked_reasons[0]` を Viewer compact summary の `first_open_action` / `first_blocked_reason` として出すようにした。NDX viewer では Case Lite section にも `Choose a human-approved manual contract update target...` と `strategy_input_feedback_proposal:NEEDS_SOURCE_CONTRACT_CONTEXT` が表示される。

## 1. 計画

対象:

- lane: `Local dogfood`
- strategy_id: `ndx_open_gap_residual_v1`
- code:
  - `src/sis/strategy_workbench_viewer/service.py`
  - `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
- docs:
  - `docs/strategy_workbench_viewer/README.md`
- regenerated local artifacts:
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json`

完了条件:

- Case Lite の現物 summary と Viewer manifest の差を確認する。
- focused RED test を追加する。
- Case Lite summary extraction を局所修正する。
- NDX Viewer を再生成し、Case Lite section に first open action / blocked reason が出ることを確認する。
- focused test、strategy_workbench_viewer tests、current docs check、full check を通す。

やらないこと:

- Case Lite schema 変更。
- Case Index の再設計。
- source contract の manual update。
- generated proposal の direct apply。
- paper / live order、wallet、signing、exchange write。

## 2. 追加調査と現実チェック

Case Lite の現物 summary:

```json
{
  "latest_status": "HOLD",
  "open_actions": [
    "Choose a human-approved manual contract update target before applying runtime-001 to any Strategy Input Contract.",
    "Provide or generate strategy_input_contract.v1 for ndx_open_gap_residual_v1 before manual contract update review.",
    "Review runtime observation evidence before manually updating execution reality or source validation expectations in the Strategy Input Contract."
  ],
  "blocked_reasons": [
    "strategy_input_feedback_proposal:NEEDS_SOURCE_CONTRACT_CONTEXT",
    "strategy_input_feedback_review:HOLD"
  ]
}
```

修正前の Viewer manifest の Case Lite summary:

```json
{
  "latest_status": "HOLD",
  "live_allowed": false,
  "paper_execution_allowed": false,
  "strategy_id": "ndx_open_gap_residual_v1"
}
```

問題:

- Case Lite section だけを見ると、何をすべきか、何で止まっているかが分からない。
- Case Index には first open action / blocker が出ているため、同じ case 情報なのに表示粒度が不揃い。
- operator が Case Lite section だけを見ると、HOLD の理由確認が preview JSON 依存になる。

判断:

- schema 変更は不要。Viewer summary extraction の問題。
- Case Index と同じ `first_open_action` / `first_blocked_reason` を使えば、UI と docs の意味がぶれない。
- 全 action / blocker は preview JSON と Case Lite Markdown で読む。Viewer compact summary は先頭だけを出す。

## 3. 実装

変更した code:

- `src/sis/strategy_workbench_viewer/service.py`
  - `strategy_case_lite.v1` の `summary.open_actions[0]` を `first_open_action` に出す。
  - `summary.blocked_reasons[0]` を `first_blocked_reason` に出す。

変更した tests:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
  - Case Lite 単体の Viewer build で `first_open_action` と `first_blocked_reason` が manifest / HTML に出ることを assert。

更新した docs:

- `docs/strategy_workbench_viewer/README.md`
  - Case Lite でも first open action / first blocked reason を compact summary に出すことを明記。

## 再生成した local artifacts

Viewer:

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

```text
status=pass
artifact_count=8
boundary_violation_count=0
```

## 修正後の現物確認

Viewer manifest の Case Lite summary:

```text
latest_status=HOLD
first_open_action=Choose a human-approved manual contract update target before applying runtime-001 to any Strategy Input Contract.
first_blocked_reason=strategy_input_feedback_proposal:NEEDS_SOURCE_CONTRACT_CONTEXT
paper_execution_allowed=false
live_allowed=false
```

HTML の Case Lite section でも同じ内容を確認した。

## 検証

Focused RED:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_uses_case_lite_latest_status_as_status_badge -q
```

実装前の期待失敗:

```text
1 failed
KeyError: 'first_open_action'
```

Focused GREEN:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_uses_case_lite_latest_status_as_status_badge -q
```

結果:

```text
1 passed in 0.21s
```

## 残リスク

- `first_open_action` / `first_blocked_reason` は先頭だけを出す。全量確認には Case Lite JSON / Markdown が必要。
- `HOLD` は停止・レビュー待ちであり、manual contract update 承認ではない。
- generated `data/local_dogfood/...` は local dogfood artifact であり、tracked source of truth ではない。

## 次の実務的な選択肢

1. B dogfood の code/docs diff を整理し、どこまでを今回の完成範囲とするか completion audit する。
2. A に戻り、trend の Runtime Observation / Learning Event を作る価値を判断する。
3. C に移り、Crypto Perp Viewer / Daily Brief の permission flag 表示を同じ観点で dogfood する。
