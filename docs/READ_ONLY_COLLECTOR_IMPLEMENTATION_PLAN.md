# Legacy Read-Only Collector Implementation Plan

この文書は legacy `gtrade` / `ostium` read-only collector の実装・検証・再開用メモである。repo 全体の migration plan 正本は `plan/PR-00_to_PR-08_implementation_plan.md` を使う。
運用手順と artifact contract の正本は `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md` を読む。
残リスクと hardening backlog は `docs/READ_ONLY_COLLECTOR_RISK_REVIEW.md` を読む。

## 結論

本番発注システムではなく、監査可能な legacy read-only collector を先に固める。

現在の実装は次を満たす。

- gTrade REST snapshot と backend WS event stream を保存する
- gTrade pricing WS v4 の mark price / index price を分けて保存する
- Ostium Builder API、legacy metadata REST、Python SDK read-only probe を別証跡として保存する
- raw response に `recv_ts_ms`、digest、schema digest、source endpoint を残す
- Phase gate が read-only collector artifact 不足を Phase 2 blocker にする

未完了なのは live smoke であり、外部 API / SDK の現時点の実応答を artifact として確定する作業である。

## Architecture

### Common artifact contract

各 collector は raw response を正規化前に保存する。

必須 field:

- `recv_ts_ms`
- `source_ts` または `oracle_ts_ms` が取得できる場合は別 field として保存
- `source`
- `source_endpoint`
- `body_digest`
- `schema_digest`
- `collector_version`
- `raw`

正規化済み quote / manifest は raw artifact の path と digest を参照する。

### gTrade collector

gTrade は TypeScript sidecar が担当する。

取得対象:

- `GET https://backend-arbitrum.gains.trade/trading-variables`
- `GET https://backend-arbitrum.gains.trade/open-trades`
- `wss://backend-arbitrum.gains.trade` backend event stream
- `wss://backend-pricing.eu.gains.trade/v4` pricing stream

重要な扱い:

- `deepReorg` を受信したら REST snapshot を full refresh する
- pricing v4 の `m` は mark price、`i` は index price として保存する
- flat array payload など 1 price しかない場合は `mark_index_inferred_equal=true` を保存し、同値補完を明示する
- unknown pair index は通常 quote に混ぜず quarantine に保存する

### Ostium collector

Ostium は Python collector が担当する。

取得対象:

- Builder API `https://builder.ostium.io/v1/prices`
- legacy metadata REST `https://metadata-backend.ostium.io/PricePublish/latest-prices`
- legacy metadata REST `https://metadata-backend.ostium.io/PricePublish/latest-price?asset=...`
- legacy metadata REST `https://metadata-backend.ostium.io/trading-hours/asset-schedule?asset=...`
- `ostium-python-sdk` の秘密鍵なし read-only probe

重要な扱い:

- dependency が存在するだけでは SDK read-only 成功にしない
- SDK probe が実データ取得できた時だけ `python_sdk.status=read_only_probe_passed` にする
- market close は missing data ではない
- asset は `canonical_symbol`、`venue_pair`、`legacy_asset_param`、`from`、`to` を分けて保存する
- per-asset legacy endpoint failure は raw error artifact として保存し、collector 全体は fail-closed summary を出す

## Task Chain

### T1. Ostium endpoint と asset mapping を修正する

Status: implemented

Goal:

- `api.ostium.io` 固定を廃止し、default endpoint を `metadata-backend.ostium.io` にする
- `SPX` / `NDX` / `XAU` を legacy REST param に直接投げず、`SPXUSD` / `NDXUSD` / `XAUUSD` などの `legacy_asset_param` に変換する

Target files:

- `src/sis/venues/ostium/constraints.py`
- `tests/test_ostium_constraints.py`

Acceptance:

- artifact の asset row に `canonical_symbol`、`venue_pair`、`legacy_asset_param`、`from`、`to` が入る
- `latest_price` と `trading_hours` は `legacy_asset_param` を query param に使う

Verification:

```bash
uv run pytest tests/test_ostium_constraints.py -q
```

### T2. Ostium Builder API artifact を constraint summary に統合する

Status: implemented

Goal:

- Builder API `GET /v1/prices` の raw artifact を保存する
- constraint summary に Builder artifact path / digest / schema digest を残す

Target files:

- `src/sis/venues/ostium/constraints.py`
- `src/sis/cli.py`
- `tests/test_ostium_constraints.py`

Acceptance:

- summary に `builder_prices_artifact` が入る
- CLI に `--builder-prices-endpoint` がある

Verification:

```bash
uv run sis ostium-constraint-artifact --help
uv run pytest tests/test_ostium_constraints.py -q
```

### T3. Ostium Python SDK read-only probe を実取得化する

Status: implemented

Goal:

- SDK version check だけを合格にしない
- 秘密鍵なし SDK client で price または pair detail を実取得する

Target files:

- `src/sis/venues/ostium/constraints.py`
- `tests/test_ostium_constraints.py`

Acceptance:

- 成功時のみ `python_sdk.status=read_only_probe_passed`
- missing dependency / SDK call failure は `constraint_status=failed`
- `private_key_used=false` を保存する

Verification:

```bash
uv run pytest tests/test_ostium_constraints.py -q
```

### T4. gTrade pricing v4 semantics を固定する

Status: implemented

Goal:

- mark price と index price を別 field として扱う
- 1 price payload の同値補完を明示する

Target files:

- `sidecars/gtrade/src/pricing_parser.ts`
- `sidecars/gtrade/src/pricing_collector.ts`
- `sidecars/gtrade/src/pricing_collector.test.ts`

Acceptance:

- v4 object payload は `mark_index_inferred_equal=false`
- flat array fallback は `mark_index_inferred_equal=true`
- pricing output row に `mark_index_inferred_equal` が残る

Verification:

```bash
bun run gtrade:test
bun run gtrade:typecheck
```

### T5. Phase gate を read-only collector contract に合わせる

Status: implemented

Goal:

- Phase 2 判定前に collector artifact の証跡不足を止める

Target files:

- `src/sis/reports/phase_gate_review.py`
- `tests/test_phase_gate_review.py`

Acceptance:

- missing Builder artifact は blocker
- missing legacy latest prices artifact は blocker
- SDK status が `read_only_probe_passed` でなければ blocker
- asset-level trading-hours artifact がなければ blocker

Verification:

```bash
uv run pytest tests/test_phase_gate_review.py -q
```

### T6. Runner と docs を同期する

Status: implemented

Goal:

- live evidence runner の manifest に collector の新しい成功指標を残す
- runbook と collector doc を更新する

Target files:

- `src/sis/live_evidence_runner.py`
- `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md`

Acceptance:

- manifest row_counts に `ostium_builder_prices_artifacts` が入る
- manifest row_counts に `ostium_sdk_read_only_probe_passed` が入る
- docs に Builder API、metadata REST、SDK read-only probe の成功条件が書かれている

Verification:

```bash
uv run pytest tests/test_live_evidence_runner.py tests/test_cli_smoke.py -q
```

### T7. Live smoke を実行する

Status: pending

Goal:

- 実ネットワークで Ostium / gTrade artifact が生成されることを確認する

Commands:

```bash
uv run sis ostium-constraint-artifact --run-id manual_smoke
bun run gtrade:backend-collect -- --duration-minutes 1 --run-id manual_smoke
```

Acceptance:

- `data/ops/ostium_constraints_manual_smoke.json` が生成される
- `constraint_status` が `pass` または fail-closed reason 付きの `failed`
- `data/raw/sidecar/gtrade-backend/manifests/**/manual_smoke.json` が生成される
- gTrade manifest が `status=completed`

Verification:

```bash
uv run python -m json.tool data/ops/ostium_constraints_manual_smoke.json
find data/raw/sidecar/gtrade-backend/manifests -name manual_smoke.json -print
```

### T8. Full live evidence run で Phase gate を確認する

Status: pending

Goal:

- 実収集 window 後、Phase 2 可否を artifact ベースで判断する

Commands:

```bash
uv run python scripts/run_live_evidence.py \
  --duration-minutes 120 \
  --metadata-interval-seconds 60 \
  --backend-event-duration-minutes 30
uv run sis phase-gate-review
```

Acceptance:

- live evidence manifest に read-only collector row_counts が入る
- `data/ops/phase_gate_review_summary.json` の `read_only_collector_gate_passed` が true または具体 blocker を返す
- `phase2_entry_allowed` は log ではなく artifact と phase gate summary で判断する

Verification:

```bash
uv run python -m json.tool data/ops/phase_gate_review_summary.json
```

### T9. Risk hardening implementation

Status: pending

Goal:

- `docs/READ_ONLY_COLLECTOR_RISK_REVIEW.md` の Better Backlog を実装し、Phase gate の過信リスクを下げる

Target files:

- `src/sis/venues/ostium/constraints.py`
- `src/sis/reports/phase_gate_review.py`
- `tests/test_ostium_constraints.py`
- `tests/test_phase_gate_review.py`
- `tests/test_cli_smoke.py`

Acceptance:

- SDK empty payload は `read_only_probe_passed` にならない
- top-level fetch failure でも summary が生成される
- artifact ref の path / digest / schema digest / file existence を gate が検査する
- asset-level `trading_hours_observed=true` を gate が検査する

Verification:

```bash
uv run pytest tests/test_ostium_constraints.py tests/test_phase_gate_review.py tests/test_cli_smoke.py -q
uv run pytest -q
```

## Current Verification

実装後に確認済み:

```bash
uv run pytest tests/test_ostium_constraints.py tests/test_ostium_probe.py tests/test_phase_gate_review.py tests/test_live_evidence_runner.py tests/test_cli_smoke.py -q
uv run pytest -q
uv run ruff check .
uv run pyrefly check
bun run gtrade:test
bun run gtrade:typecheck
uv run sis ostium-constraint-artifact --help
```

結果:

- Python targeted tests: 89 passed
- Full pytest: 256 passed
- Ruff: pass
- Pyrefly: pass, 0 errors
- gTrade sidecar tests: 12 passed
- gTrade typecheck: pass
- CLI help: new `--builder-prices-endpoint` と metadata endpoint default を確認済み

## Known Gaps / Risk Review

現行実装の残リスクは `docs/READ_ONLY_COLLECTOR_RISK_REVIEW.md` に分離して管理する。

特に次は未実装の hardening backlog である。

- SDK empty payload を `read_only_probe_passed` にしない payload quality validation
- Builder API / legacy latest-prices の top-level fetch failure を raw error artifact と summary に残す処理
- Phase gate による artifact ref の path / digest / schema digest / file existence 検査
- asset-level `trading_hours_observed=true` の gate 側再確認
- old fixture の new contract 化
- live smoke artifact 由来の regression fixture 追加

## Stop Conditions

次の場合は Phase 2 に進めない。

- gTrade backend manifest が無い
- gTrade backend manifest が `completed` でない
- gTrade `deepReorg` 受信時に full refresh path が無い
- Ostium constraint artifact が無い
- Ostium constraint artifact が `constraint_status=pass` でない
- Ostium Builder API raw artifact が無い
- Ostium legacy latest prices artifact が無い
- Ostium SDK が `read_only_probe_passed` でない
- Ostium asset-level trading-hours artifact が無い

## Out Of Scope

- 本番発注
- 秘密鍵利用
- allowance 付与
- contract write
- paper trading への自動昇格
- live smoke 失敗時の upstream workaround の自動採用
