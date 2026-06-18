<!--
作成日: 2026-06-18_23:49 JST
更新日: 2026-06-19_01:02 JST
-->

# Strategy Runtime Observation

## 結論

Strategy Runtime Observation は、paper smoke / normal paper observation の session manifest と observation ledger を読み、Drift Review と次回 Strategy Input Contract に戻すための runtime observation manifest を作る first slice です。

これは live observation ではありません。`strategy-runtime-observation-ingest` は paper runtime artifact を読むだけで、paper order、live order、wallet、signing、exchange write を実行しません。

## できること

- `paper_observation_session_manifest.v1` から session id と ledger path を読む。
- `paper_observation_ledger.jsonl` を正規化して `runtime_observation_ledger.jsonl` としてコピーする。
- filled / blocked / no-fill、unique intent、unique symbol、spread、quote age、block reason を集計する。
- ledger に PnL / cost / slippage / fill price drift / order lifecycle がある場合は集計する。
- PnL がない場合は `pnl_available=false` と `pnl_unavailable_reason` を manifest に残す。
- `strategy_runtime_observation_manifest.v1` と Markdown summary を出す。
- ledger や session manifest に live / wallet / signing / exchange write 系の true flag が混入した場合は `BLOCKED_BOUNDARY_VIOLATION` として止める。

## Command

```bash
uv run sis strategy-runtime-observation-ingest \
  --strategy-id <strategy-id> \
  --session-manifest data/paper/observations/<session-id>/paper_observation_session_manifest.json \
  --source-stage paper_smoke \
  --out data/runtime_observations/<strategy-id>/<session-id>
```

## Artifact

- `runtime_observation_ledger.jsonl`
- `strategy_runtime_observation_manifest.json`
- `strategy_runtime_observation_summary.md`

`strategy_runtime_observation_manifest.json` の `summary` には、次の実行品質項目を含みます。

- `pnl_available`
- `pnl_unavailable_reason`
- `realized_pnl_usd_total`
- `gross_pnl_usd_total`
- `fee_usd_total`
- `slippage_usd_total`
- `avg_slippage_bps`
- `max_abs_slippage_bps`
- `avg_fill_price_drift_bps`
- `max_abs_fill_price_drift_bps`
- `filled_notional_usd_total`
- `order_lifecycle_counts`

これらは Drift Review の材料です。PnL がない artifact は、PnL / cost drift を評価できない限定 observation として扱います。

`data/` 配下の artifact は runtime / generated state です。fresh checkout では再生成してください。

## Status

- `INGESTED`: ledger rows を読み、summary と manifest を作成済み。
- `EMPTY_LEDGER`: ledger は存在するが行がない。
- `BLOCKED_BOUNDARY_VIOLATION`: live / wallet / signing / exchange write 系の禁止境界に触れている。

## 境界

- live order、wallet、signing、exchange write は使わない。
- Micro Live Canary 後の actual live execution observation とは混ぜない。
- この artifact は Drift Review の入力であり、paper pass、live readiness、micro live permission ではない。
