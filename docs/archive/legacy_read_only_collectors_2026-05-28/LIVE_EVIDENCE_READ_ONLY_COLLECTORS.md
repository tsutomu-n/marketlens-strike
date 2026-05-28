# Legacy Live Evidence Read-Only Collectors

> Current status: historical / legacy. Commands such as `bun run gtrade:backend-collect` and `uv run sis ostium-constraint-artifact` are not current public CLI surfaces in this checkout. Treat this file as evidence history unless the legacy archive is intentionally restored. For current Trade[XYZ] read-only gate status, read `docs/CURRENT_STATE.md` and `docs/OPERATIONS_RUNBOOK.md`.

この文書は legacy `gtrade` / `ostium` read-only collector chain の運用メモです。`Trade[XYZ]` migration 全体の正本ではありません。
実装計画とタスク一覧は `READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md` を読む。
残リスクと hardening backlog は `READ_ONLY_COLLECTOR_RISK_REVIEW.md` を読む。

## 結論

本番発注、署名、allowance、private key は扱わない。

Phase gate の材料として必要なのは、raw response、受信時刻、digest、schema digest、collector manifest、market close / deepReorg の扱いを残すことである。

current repo context:

- migration code の主軸は `trade_xyz`
- それとは別に、current operations chain の一部はこの legacy collector evidence をまだ参照する

## gTrade

既存の collector は `/trading-variables` REST snapshot と pricing WS を保存する。

追加した collector は次を保存する。

- `/trading-variables` REST snapshot
- `/open-trades` REST snapshot
- backend WS raw event stream
- `deepReorg` 受信時の full REST refresh
- REST / WS の read-only reconciliation manifest

実行:

```bash
bun run gtrade:backend-collect -- --duration-minutes 30 --run-id manual_001
```

主な artifact:

```text
data/raw/sidecar/gtrade-backend/rest/YYYY-MM-DD/<run_id>_*.json
data/raw/sidecar/gtrade-backend/backend-ws/YYYY-MM-DD/<run_id>.jsonl
data/raw/sidecar/gtrade-backend/manifests/YYYY-MM-DD/<run_id>.json
data/ops/gtrade_state_reconciliation_<run_id>.json
```

pricing WS v4 は mark price と index price を分けて保存する。flat array payload のように 1 price しか無い場合は、`mark_index_inferred_equal=true` として同値補完を明示する。unknown pairId は通常 quotes に混ぜず、quarantine に分離する。

```text
data/raw/sidecar/gtrade-pricing-quarantine/YYYY-MM-DD.jsonl
```

## Ostium

追加した constraint collector は次を保存する。

- Builder API `https://builder.ostium.io/v1/prices` の latest prices
- legacy metadata REST `https://metadata-backend.ostium.io/PricePublish/latest-prices`
- legacy metadata REST の asset 別 latest price
- legacy metadata REST の asset 別 trading-hours schedule
- Python SDK の秘密鍵なし read-only 実取得 status
- market close を missing data と区別する constraint summary
- 2026-02 以降の非成行 `openTrade` slippage constraint

実行:

```bash
uv run sis ostium-constraint-artifact --run-id manual_001
```

主な artifact:

```text
data/raw/sidecar/ostium-constraints/YYYY-MM-DD/<run_id>.json
data/ops/ostium_constraints_<run_id>.json
```

Python SDK が環境に無い、または秘密鍵なし read-only 実取得に失敗した場合、artifact は `constraint_status=failed` になる。これは意図的な fail-closed であり、dependency が存在するだけでは Python SDK read-only を確認したとは扱わない。

## Live Evidence Runner

`scripts/run_live_evidence.py` 経由の runner は、gTrade price / metadata collection 後に read-only collector evidence step を実行する。

```bash
uv run python scripts/run_live_evidence.py \
  --duration-minutes 120 \
  --metadata-interval-seconds 60 \
  --backend-event-duration-minutes 30
```

manifest の `row_counts` に次が追加される。

- `gtrade_backend_event_rows`
- `gtrade_backend_reconnect_count`
- `gtrade_backend_deep_reorg_count`
- `ostium_constraint_assets`
- `ostium_constraint_failures`
- `ostium_builder_prices_artifacts`
- `ostium_sdk_read_only_probe_passed`

## Phase Gate

legacy collector path では、`uv run sis phase-gate-review` は次が欠ける場合に Phase 2 を許可しない。

Trade[XYZ] artifacts が存在する current path では、phase gate は Trade[XYZ] registry / quote / collection summary / diagnostics / strict validation を主入力にする。

- latest gTrade backend collector manifest
- latest Ostium constraint artifact
- gTrade backend collector manifest が `completed`
- Ostium constraint artifact が `constraint_status=pass`
- Ostium constraint artifact が Builder API raw artifact を持つ
- Ostium constraint artifact が legacy latest prices artifact を持つ
- Ostium constraint artifact が Python SDK `read_only_probe_passed` を持つ
- Ostium asset-level trading-hours artifact を持つ
- `deepReorg` 検出時に full refresh path が記録されている

market close は missing data ではない。Ostium constraint artifact で closed と分類されていれば、価格欠損とは別に扱う。

現在の gate は summary field の存在検査が中心であり、artifact file existence / digest validation は future hardening として `READ_ONLY_COLLECTOR_RISK_REVIEW.md` に残している。
