<!--
作成日: 2026-06-22_21:17 JST
更新日: 2026-06-22_21:17 JST
-->

# Local Dogfood Loop 12 NDX Proposal Viewer Evidence Results

## 結論

B の `ndx_open_gap_residual_v1` で Local dogfood を継続した。

Loop 11 で Input Feedback proposal の `evidence_summary` に quote age と PnL 不足を入れたが、追加調査で Viewer summary table はまだ `proposal_id`、`proposed_change_count`、permission flag だけを表示していた。つまり critical evidence は JSON preview を開かないと見えなかった。

これを修正し、`strategy_input_contract_update_proposal.v1` の first proposed change から `target_section`、`source_reason`、`evidence_summary` を compact summary に出すようにした。NDX viewer では、source contract なし / あり proposal の両方で `max_observed_quote_age_ms=1048982067` と `pnl_available=False` が summary table から見える。

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

- 現行 Viewer manifest で proposal critical evidence が compact summary にないことを確認する。
- focused RED test を追加する。
- Viewer summary extraction を局所修正する。
- NDX viewer を再生成し、summary table と manifest に critical evidence が出ることを確認する。
- focused test、strategy_workbench_viewer tests、current docs check、full check を通す。

やらないこと:

- proposal schema の変更。
- source contract の手動更新。
- generated proposal の direct apply。
- paper / live order、wallet、signing、exchange write。

## 2. 追加調査と現実チェック

修正前の Viewer manifest では、Input Feedback proposal summary は次の粒度だった。

```json
{
  "auto_applied": false,
  "direct_contract_edit_allowed": false,
  "live_allowed": false,
  "paper_execution_allowed": false,
  "proposal_id": "ndx_open_gap_residual_v1-input-feedback-f3cb881ae7447e63",
  "proposed_change_count": 1,
  "strategy_id": "ndx_open_gap_residual_v1"
}
```

問題:

- `READY_FOR_HUMAN_REVIEW` proposal でも、なぜ review すべきかが summary table で見えない。
- `max_observed_quote_age_ms=1048982067` と `pnl_available=False` は preview にしか出ない。
- operator が summary table だけを見ると、`READY_FOR_HUMAN_REVIEW` を楽観的に読める余地が残る。

判断:

- proposal schema 変更は不要。`proposed_changes[0]` の既存 field を Viewer summary に出せば足りる。
- すべての proposed change を展開すると summary が過剰になるため、first change の索引だけを出す。
- first change の evidence は長いが、今回の用途では「見落とさない」ことを優先する。

## 3. 実装

変更した code:

- `src/sis/strategy_workbench_viewer/service.py`
  - `strategy_input_contract_update_proposal.v1` で `proposed_changes` の先頭 item から次を compact summary に追加。
    - `first_proposed_change_target_section`
    - `first_proposed_change_source_reason`
    - `first_proposed_change_evidence_summary`

変更した tests:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
  - Input Feedback proposal fixture を追加。
  - first proposed change の target / source reason / evidence summary が manifest と HTML に出ることを assert。

更新した docs:

- `docs/strategy_workbench_viewer/README.md`
  - Input Feedback proposal / review の compact summary に first proposed change evidence が出ることを明記。

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

source contract なし / あり proposal の Viewer summary に次が出る。

```text
first_proposed_change_target_section=execution_reality
first_proposed_change_source_reason=runtime_observation:INGESTED
first_proposed_change_evidence_summary=runtime ingest_status=INGESTED; no_fill_count=0; blocked_count=0; max_observed_quote_age_ms=1048982067; max_observed_spread_bps=0.332474441027346; pnl_available=False; pnl_unavailable_reason=ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd
```

HTML summary table でも同じ内容を確認した。

## 検証

Focused RED:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_summarizes_input_feedback_proposal_evidence -q
```

実装前の期待失敗:

```text
1 failed
KeyError: 'first_proposed_change_target_section'
```

Focused GREEN:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_summarizes_input_feedback_proposal_evidence -q
```

結果:

```text
1 passed in 0.22s
```

## 残リスク

- `READY_FOR_HUMAN_REVIEW` は manual review 待ちであり、manual contract update 承認ではない。
- first change だけを compact summary に出すため、複数 proposed change の全量確認には preview JSON が必要。
- `max_observed_quote_age_ms=1048982067` は stale evidence であり、freshness の証明ではない。
- `pnl_available=False` のため、収益性や改善効果はこの artifact からは判断できない。
- generated `data/local_dogfood/...` は local dogfood artifact であり、tracked source of truth ではない。

## 次の実務的な選択肢

1. B をさらに継続し、Case Lite / Case Index が Input Feedback の HOLD と critical evidence を open action / blocked reason として十分に持っているか確認する。
2. A に戻り、trend の Runtime Observation / Learning Event を作る価値を判断する。
3. C に移り、Crypto Perp Viewer / Daily Brief の permission flag 表示を同じ観点で dogfood する。
