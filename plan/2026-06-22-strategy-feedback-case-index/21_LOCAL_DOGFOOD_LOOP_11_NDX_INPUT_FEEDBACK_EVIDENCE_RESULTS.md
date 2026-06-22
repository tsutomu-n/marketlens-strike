<!--
作成日: 2026-06-22_21:12 JST
更新日: 2026-06-22_21:12 JST
-->

# Local Dogfood Loop 11 NDX Input Feedback Evidence Results

## 結論

B の `ndx_open_gap_residual_v1` で Local dogfood を継続した。

Loop 10 では Viewer に Runtime Observation の `max_observed_quote_age_ms=1048982067` と `pnl_available=false` を表示できるようにした。追加調査した結果、肝心の Input Feedback proposal の `evidence_summary` は `no_fill_count`、`blocked_count`、`max_observed_spread_bps` だけを持ち、quote age と PnL 不足を落としていた。

これを修正し、Runtime Observation 由来の proposal は `max_observed_quote_age_ms`、`pnl_available`、`pnl_unavailable_reason` も evidence summary に含めるようにした。これは「paper / live に進める」ための修正ではない。むしろ、manual contract update のレビュー時に stale quote と PnL 不足を見落とさないための修正である。

## 1. 計画

対象:

- lane: `Local dogfood`
- strategy_id: `ndx_open_gap_residual_v1`
- code:
  - `src/sis/strategy_input_feedback/service.py`
  - `tests/strategy_input_feedback/test_strategy_input_feedback.py`
- docs:
  - `docs/strategy_input_feedback/README.md`
- regenerated local artifacts:
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-e7447e63-review-e54d8e36.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract/ndx_open_gap_residual_v1/ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63-review-20b18c2a.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json`

完了条件:

- Runtime Observation の quote age / PnL 不足が proposal evidence に出ているか現物確認する。
- 欠落がある場合は focused RED test を追加する。
- proposal generation を局所修正する。
- source contract なし / あり proposal と review を再生成する。
- Viewer を再生成し、preview に更新後 evidence が出ることを確認する。
- focused test、strategy_input_feedback tests、current docs check、full check を通す。

やらないこと:

- source contract の手動更新。
- generated proposal の direct apply。
- PnL の推定生成。
- quote freshness の修復。
- credential、network、paper order、live order、wallet、signing、exchange write。

## 2. 追加調査と現実チェック

Runtime Observation の現物には次があった。

- `max_observed_quote_age_ms=1048982067`
- `max_observed_spread_bps=0.332474441027346`
- `pnl_available=false`
- `pnl_unavailable_reason=ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd`
- `paper_fill_count=20`
- `no_fill_count=0`
- `blocked_count=0`

既存 proposal の `evidence_summary`:

```text
runtime ingest_status=INGESTED; no_fill_count=0; blocked_count=0; max_observed_spread_bps=0.332474441027346
```

問題:

- `max_observed_quote_age_ms` がない。
- `pnl_available=false` がない。
- `pnl_unavailable_reason` がない。
- review rationale には「no PnL evidence」「stale quote-age evidence」と書いているが、proposal 自体の evidence summary からは確認しづらい。

判断:

- schema 変更は不要。`evidence_summary` は既に文字列であり、今回の目的は evidence の具体化で足りる。
- proposal artifact は review の前段で読む artifact なので、review rationale だけに重要情報を置くのは弱い。
- `paper_fill_count=20` は今回は proposal evidence に入れない。Runtime evidence の最小指標として no-fill / blocked / quote age / spread / PnL に絞る。paper fill count は Viewer と source Runtime Observation preview で確認できる。

## 3. 実装

変更した code:

- `src/sis/strategy_input_feedback/service.py`
  - `_runtime_change(...)` の `evidence_summary` に次を追加。
    - `max_observed_quote_age_ms`
    - `pnl_available`
    - `pnl_unavailable_reason`

変更した tests:

- `tests/strategy_input_feedback/test_strategy_input_feedback.py`
  - Runtime Observation fixture に `max_observed_quote_age_ms`、`max_observed_spread_bps`、`pnl_available=false`、`pnl_unavailable_reason` を追加。
  - proposal の `evidence_summary` に quote age、PnL 利用可否、PnL 不足理由が出ることを assert。

更新した docs:

- `docs/strategy_input_feedback/README.md`
  - Runtime Observation 由来 proposal の `evidence_summary` が quote age / PnL 不足を含むことを明記。
  - これは実行許可ではなく、manual review で欠陥を見落とさないための要約だと明記。

## 再生成した local artifacts

source contract なし proposal:

```bash
uv run sis strategy-input-feedback-proposal-build \
  --strategy-id ndx_open_gap_residual_v1 \
  --runtime-observation data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback \
  --replace-existing
```

結果:

```text
status=pass
proposal_id=ndx_open_gap_residual_v1-input-feedback-e7447e63
proposal_status=NEEDS_SOURCE_CONTRACT_CONTEXT
proposed_change_count=1
auto_applied=false
direct_contract_edit_allowed=false
```

source contract なし review:

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

source contract あり proposal:

```bash
uv run sis strategy-input-feedback-proposal-build \
  --strategy-id ndx_open_gap_residual_v1 \
  --runtime-observation data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json \
  --source-contract data/local_dogfood/2026-06-22-ndx-open-gap/strategy_inputs/ndx_open_gap_residual_v1_input_contract.yaml \
  --out data/local_dogfood/2026-06-22-ndx-open-gap/strategy_input_feedback_with_contract \
  --replace-existing
```

結果:

```text
status=pass
proposal_id=ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63
proposal_status=READY_FOR_HUMAN_REVIEW
proposed_change_count=1
auto_applied=false
direct_contract_edit_allowed=false
```

source contract あり review:

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

source contract なし / あり proposal の `evidence_summary` はどちらも次になった。

```text
runtime ingest_status=INGESTED; no_fill_count=0; blocked_count=0; max_observed_quote_age_ms=1048982067; max_observed_spread_bps=0.332474441027346; pnl_available=False; pnl_unavailable_reason=ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd
```

Viewer HTML preview でも次を確認した。

- `max_observed_quote_age_ms=1048982067`
- `pnl_available=False`
- `pnl_unavailable_reason=ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd`
- proposal status:
  - source contract なし: `NEEDS_SOURCE_CONTRACT_CONTEXT`
  - source contract あり: `READY_FOR_HUMAN_REVIEW`
- review decision:
  - source contract なし: `HOLD`
  - source contract あり: `HOLD`
- `manual_contract_update_input_allowed=false`
- `auto_applied=false`
- `direct_contract_edit_allowed=false`
- `boundary_violation_count=0`

## 検証

Focused RED:

```bash
uv run pytest tests/strategy_input_feedback/test_strategy_input_feedback.py::test_runtime_observation_without_contract_builds_context_limited_proposal -q
```

実装前の期待失敗:

```text
1 failed
AssertionError: assert 'max_observed_quote_age_ms=1048982067' in evidence_summary
```

Focused GREEN:

```bash
uv run pytest tests/strategy_input_feedback/test_strategy_input_feedback.py::test_runtime_observation_without_contract_builds_context_limited_proposal -q
```

結果:

```text
1 passed in 0.23s
```

## 残リスク

- proposal の `READY_FOR_HUMAN_REVIEW` は manual review 入力であり、manual contract update 承認ではない。
- review は `HOLD` のままなので、manual contract update input は許可されていない。
- `pnl_available=False` のため、収益性や改善効果はこの artifact からは判断できない。
- `max_observed_quote_age_ms=1048982067` は stale evidence であり、freshness の証明ではない。
- generated `data/local_dogfood/...` は local dogfood artifact であり、tracked source of truth ではない。

## 次の実務的な選択肢

1. B をさらに継続し、`READY_FOR_HUMAN_REVIEW` proposal が Viewer summary table で `proposed_change_count` だけでなく critical evidence を要約表示できるか確認する。
2. A に戻り、trend の Runtime Observation / Learning Event を作る価値を判断する。
3. C に移り、Crypto Perp Viewer / Daily Brief の permission flag 表示を同じ観点で dogfood する。
