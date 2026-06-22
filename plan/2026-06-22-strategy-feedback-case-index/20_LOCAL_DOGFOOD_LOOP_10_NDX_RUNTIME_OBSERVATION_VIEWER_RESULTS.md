<!--
作成日: 2026-06-22_21:05 JST
更新日: 2026-06-22_21:05 JST
-->

# Local Dogfood Loop 10 NDX Runtime Observation Viewer Results

## 結論

B の `ndx_open_gap_residual_v1` で Local dogfood を継続した。

結果として、`Strategy Workbench Viewer` が `strategy_runtime_observation_manifest.v1` の実務上重要な観測値を compact summary に出していない問題を修正した。具体的には `max_observed_quote_age_ms=1048982067`、`pnl_available=false`、`pnl_unavailable_reason`、ledger / paper order / fill / no-fill / blocked count、filled notional、spread、first / last observed timestamp が、Viewer の summary と HTML で見えるようになった。

これは「PnL evidence がある」「quote が新鮮」「paper 実行に進める」という証明ではない。逆に、PnL がなく、stale quote-age evidence があることを見落としにくくする修正である。

## 1. 計画

対象:

- lane: `Local dogfood`
- strategy_id: `ndx_open_gap_residual_v1`
- primary artifact:
  - `data/local_dogfood/2026-06-22-ndx-open-gap/strategy_runtime_observation/strategy_runtime_observation_manifest.json`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer.html`
  - `data/local_dogfood/2026-06-22-ndx-open-gap/viewer/strategy_workbench_viewer_manifest.json`

完了条件:

- Runtime Observation manifest の現物を読み、summary に含まれる実務判断値を列挙する。
- 既存 Viewer manifest / HTML で、その値が compact summary に出ているか確認する。
- 欠落がある場合は focused RED test を追加する。
- Viewer summary extraction を局所修正する。
- NDX viewer を再生成し、generated artifact で値が出ることを確認する。
- focused test、strategy workbench viewer test、current docs check、full check を通す。

やらないこと:

- credential、network、paper order、live order、wallet、signing、exchange write。
- PnL の推定生成。
- quote freshness の修復。
- runtime observation artifact の書き換え。
- source contract の manual update / direct apply。

## 2. 追加調査と現実チェック

Runtime Observation manifest の現物:

- `schema_version=strategy_runtime_observation_manifest.v1`
- `strategy_id=ndx_open_gap_residual_v1`
- `ingest_status=INGESTED`
- `ledger_entry_count=20`
- `paper_order_count=20`
- `paper_fill_count=20`
- `no_fill_count=0`
- `blocked_count=0`
- `filled_notional_usd_total=20000.0`
- `unique_intent_count=1`
- `unique_symbol_count=1`
- `max_observed_quote_age_ms=1048982067`
- `max_observed_spread_bps=0.332474441027346`
- `pnl_available=false`
- `pnl_unavailable_reason=ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd`
- `first_observed_at=2026-06-17T11:07:10.330218+00:00`
- `last_observed_at=2026-06-17T11:13:45.220224+00:00`
- `live_allowed=false`

既存 Viewer の問題:

- `status=INGESTED` と `strategy_id`、`live_allowed=false` だけが compact summary に出ていた。
- `max_observed_quote_age_ms` が出ていなかった。
- `pnl_available=false` と `pnl_unavailable_reason` が出ていなかった。
- paper fill が 20 件ある一方で PnL がない、という読み取り上重要な組み合わせが summary table で見えなかった。

判断:

- Runtime Observation の count、quote age、spread、PnL availability は、operator が paper / live readiness を誤読しないために必要な最低限の summary である。
- `order_lifecycle_counts` や `status_counts` は object 型なので compact summary には入れない。Viewer の preview JSON では確認できるため、今回は scalar 値に絞る。
- `pnl_available=false` は安全側に倒す情報であり、permission ではない。表示対象に入れてよい。
- `max_observed_quote_age_ms=1048982067` は「新鮮な quote がある」証明ではなく、むしろ stale evidence として読むべき値である。

## 3. 実装

変更した code:

- `src/sis/strategy_workbench_viewer/service.py`
  - compact summary 対象に Runtime Observation 用の scalar 値を追加。
  - string:
    - `first_observed_at`
    - `last_observed_at`
    - `pnl_unavailable_reason`
  - integer:
    - `ledger_entry_count`
    - `paper_order_count`
    - `paper_fill_count`
    - `no_fill_count`
    - `blocked_count`
    - `unique_intent_count`
    - `unique_symbol_count`
    - `max_observed_quote_age_ms`
  - number:
    - `filled_notional_usd_total`
    - `max_observed_spread_bps`
  - boolean:
    - `pnl_available`

変更した tests:

- `tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py`
  - `strategy_runtime_observation_manifest.v1` の summary から、paper order / fill / no-fill / blocked count、quote age、spread、filled notional、PnL 利用可否、PnL 不足理由、first / last observed timestamp が compact summary と HTML に出ることを追加。

更新した docs:

- `docs/strategy_workbench_viewer/README.md`
  - Runtime Observation の compact summary 表示対象を明記。
  - この表示が permission ではなく、stale quote / PnL 不足を見落とさないためのものだと明記。

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

Viewer manifest の Runtime Observation summary:

```text
status=INGESTED
strategy_id=ndx_open_gap_residual_v1
ledger_entry_count=20
paper_order_count=20
paper_fill_count=20
no_fill_count=0
blocked_count=0
unique_intent_count=1
unique_symbol_count=1
filled_notional_usd_total=20000.0
max_observed_quote_age_ms=1048982067
max_observed_spread_bps=0.332474441027346
pnl_available=false
pnl_unavailable_reason=ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd
first_observed_at=2026-06-17T11:07:10.330218+00:00
last_observed_at=2026-06-17T11:13:45.220224+00:00
live_allowed=false
```

HTML で確認した表示:

- `max_observed_quote_age_ms: 1048982067`
- `pnl_available: False`
- `pnl_unavailable_reason: ledger rows do not include realized_pnl_usd, paper_pnl_usd, or pnl_usd`
- `filled_notional_usd_total: 20000.0`
- `paper_order_count: 20`
- `paper_fill_count: 20`
- `no_fill_count: 0`
- `blocked_count: 0`
- `boundary_violation_count=0`

## 検証

Focused RED:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_summarizes_runtime_observation_execution_reality -q
```

実装前の期待失敗:

```text
1 failed
KeyError: 'ledger_entry_count'
```

Focused GREEN:

```bash
uv run pytest tests/strategy_workbench_viewer/test_strategy_workbench_viewer.py::test_strategy_workbench_viewer_summarizes_runtime_observation_execution_reality -q
```

結果:

```text
1 passed in 0.21s
```

## 残リスク

- `INGESTED` は観測 artifact を取り込んだ状態であり、paper / live 実行許可ではない。
- `paper_fill_count=20` は paper fill の記録であり、PnL evidence ではない。
- `pnl_available=false` のため、収益性や損益改善はこの artifact からは判断できない。
- `max_observed_quote_age_ms=1048982067` は非常に古い quote を含む evidence であり、freshness の証明ではない。
- Viewer は artifact を読みやすくするだけで、runtime observation の品質を修復しない。
- generated `data/local_dogfood/...` は local dogfood artifact であり、tracked source of truth ではない。

## 次の実務的な選択肢

1. B をさらに継続し、NDX の Input Feedback proposal / review がこの Runtime Observation 欠陥を十分に反映しているか確認する。
2. A に戻り、trend の Runtime Observation / Learning Event を用意する価値があるか判断する。
3. C に移り、Crypto Perp Viewer / Daily Brief の permission flag 表示を同じ観点で dogfood する。
