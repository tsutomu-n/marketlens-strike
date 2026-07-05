<!--
作成日: 2026-06-22_21:23 JST
更新日: 2026-06-22_21:23 JST
-->

# Local Dogfood Loop 13 NDX Case HOLD Results

## 結論

B の `ndx_open_gap_residual_v1` で Local dogfood を継続した。

追加調査で、NDX Case Lite / Case Index が Runtime Observation 1件だけを取り込んでおり、`latest_status=INGESTED`、`open_actions=[]`、`blocked_reasons=[]` になっていた。これは、すでに Input Feedback review が `HOLD` で、PnL 不足と stale quote を理由に manual contract update を止めている現状を case summary に反映していない。

これを修正し、Case Lite が `strategy_input_contract_update_proposal.v1` と `strategy_input_contract_update_review.v1` を既知 artifact として扱えるようにした。Input Feedback review の `HOLD` / `REJECT` / `NEEDS_FIX` は blocked reason になり、review の最初の `required_actions` と proposal の最初の recommendation は open action になる。

NDX Case Lite / Case Index / Viewer を再生成した結果、Case Lite と Case Index は `HOLD` の warning badge になり、Case Index summary には first open action と first blocked reason が出るようになった。

## 1. 計画

対象:

- lane: `Local dogfood`
- strategy_id: `ndx_open_gap_residual_v1`
- code:
  - `src/sis/strategy_case_lite/models.py`
  - `src/sis/strategy_case_lite/service.py`
  - `schemas/strategy_case_lite.v1.schema.json`
  - `tests/strategy_case_lite/test_strategy_case_lite.py`
- docs:
  - `docs/strategy_case_lite/README.md`
- regenerated local artifacts:
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.md`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index/ndx-open-gap-local-dogfood-index.md`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json`

完了条件:

- 現行 Case Lite / Index が Input Feedback HOLD を反映していないことを現物確認する。
- focused RED test を追加する。
- Case Lite が Input Feedback proposal/review を既知 artifact として扱う。
- HOLD review と context-missing proposal を blocked reason に出す。
- required action / recommendation を open action に出す。
- NDX Case Lite / Index / Viewer を再生成し、`HOLD` と action / blocker を確認する。
- focused test、strategy_case_lite tests、current docs check、full check を通す。

やらないこと:

- source contract の手動更新。
- generated proposal の direct apply。
- Case registry / DB 化。
- paper / live order、wallet、signing、exchange write。

## 2. 追加調査と現実チェック

修正前の Case Lite:

```json
{
  "latest_status": "INGESTED",
  "open_actions": [],
  "blocked_reasons": [],
  "artifact_count": 1
}
```

修正前の Case Index:

```json
{
  "latest_status": "INGESTED",
  "open_actions": [],
  "blocked_reasons": []
}
```

問題:

- Input Feedback review は `HOLD` だが、case summary には出ていない。
- source contract なし proposal は `NEEDS_SOURCE_CONTRACT_CONTEXT` だが、case summary には出ていない。
- Case Index / Viewer から見ると `INGESTED` だけに見え、manual review が止まっていることが一覧で分からない。

判断:

- Case Lite は `--artifact` で追加 JSON を受けられるため、proposal/review を含める運用に寄せるのが現実的。
- ただし generic のままだと action / blocker 抽出が弱いので、typed artifact に昇格する。
- review の required action は list だが、既存 timeline model は `action: str | None` なので、まず最初の action だけを summary に出す。全量は preview JSON / Markdown report で確認する。

## 3. 実装

変更した code:

- `src/sis/strategy_case_lite/models.py`
  - `StrategyCaseArtifactType` に次を追加。
    - `strategy_input_contract_update_proposal`
    - `strategy_input_contract_update_review`
- `src/sis/strategy_case_lite/service.py`
  - schema version から上記 artifact type へ mapping。
  - proposal の最初の `proposed_changes[].recommendation` を action として抽出。
  - review の最初の `required_actions[]` を action として抽出。
  - proposal `NEEDS_SOURCE_CONTRACT_CONTEXT` / `BLOCKED_BOUNDARY_VIOLATION` を blocked reason に追加。
  - review `HOLD` / `REJECT` / `NEEDS_FIX` を blocked reason に追加。
- `schemas/strategy_case_lite.v1.schema.json`
  - artifact type enum に proposal / review を追加。

変更した tests:

- `tests/strategy_case_lite/test_strategy_case_lite.py`
  - Input Feedback proposal / HOLD review fixture を追加。
  - Case Lite summary が `latest_status=HOLD`、open action、blocked reason、typed artifact を持つことを assert。

更新した docs:

- `docs/strategy_case_lite/README.md`
  - Input Feedback proposal / review が typed additional artifact になること。
  - HOLD / context missing を open action / blocked reason に反映すること。
  - それが実行許可ではないこと。

## 再生成した local artifacts

Case Lite:

```bash
uv run sis strategy-case-lite-update \
  --strategy-id ndx_open_gap_residual_v1 \
  --runtime-observation data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/validation/strategy_input_contract_validation.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json \
  --artifact data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases \
  --case-id ndx_open_gap_residual_v1-local-dogfood \
  --replace-existing
```

結果:

```text
status=pass
case_id=ndx_open_gap_residual_v1-local-dogfood
latest_status=HOLD
artifact_count=6
```

Case Index:

```bash
uv run sis strategy-case-index-build \
  --case data/local_dogfood/2026-06-22-ndx-open-gap/strategy_cases/ndx_open_gap_residual_v1/strategy_case_lite.json \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_case_index \
  --index-id ndx-open-gap-local-dogfood-index \
  --replace-existing
```

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

## 修正後の現物確認

Case Lite:

```text
latest_status=HOLD
artifact_count=6
blocked_reasons=[
  strategy_input_feedback_proposal:NEEDS_SOURCE_CONTRACT_CONTEXT,
  strategy_input_feedback_review:HOLD
]
open_actions=[
  Choose a human-approved manual contract update target before applying runtime-001 to any Strategy Input Contract.,
  Provide or generate strategy_input_contract.v1 for ndx_open_gap_residual_v1 before manual contract update review.,
  Review runtime observation evidence before manually updating execution reality or source validation expectations in the Strategy Input Contract.
]
```

Case Index:

```text
latest_status=HOLD
first_open_action=Choose a human-approved manual contract update target before applying runtime-001 to any Strategy Input Contract.
first_blocked_reason=strategy_input_feedback_proposal:NEEDS_SOURCE_CONTRACT_CONTEXT
```

Viewer:

- `strategy_case_lite.v1` は `HOLD` warning badge。
- `strategy_case_index.v1` は `HOLD` warning badge。
- `first_open_action` と `first_blocked_reason` が summary に出る。
- `boundary_violation_count=0`。

## 検証

Focused RED:

```bash
uv run pytest tests/strategy_case_lite/test_strategy_case_lite.py::test_strategy_case_lite_summarizes_input_feedback_hold_review -q
```

実装前の期待失敗:

```text
1 failed
AssertionError: assert [] == [...]
```

Focused GREEN:

```bash
uv run pytest tests/strategy_case_lite/test_strategy_case_lite.py::test_strategy_case_lite_summarizes_input_feedback_hold_review -q
```

結果:

```text
1 passed in 0.21s
```

## 残リスク

- Case Lite / Index の `HOLD` は停止・レビュー待ちの表示であり、manual contract update 承認ではない。
- timeline の action は artifact ごとに1件なので、複数 required action の全量確認には review JSON / Markdown が必要。
- source contract なし proposal と source contract あり proposal の両方を同じ case に入れているため、case summary は保守的に blocker を残す。
- `pnl_available=False` と stale quote evidence は Case Lite summary そのものには出ない。Viewer の proposal / runtime section で確認する。
- generated `data/local_dogfood/...` は local dogfood artifact であり、tracked source of truth ではない。

## 次の実務的な選択肢

1. B は一旦、Runtime Observation、Input Feedback、Viewer、Case Lite、Case Index の主要な楽観表示リスクを潰した状態として、verification diff を整理する。
2. A に戻り、trend の Runtime Observation / Learning Event を作る価値を判断する。
3. C に移り、Crypto Perp Viewer / Daily Brief の permission flag 表示を同じ観点で dogfood する。
