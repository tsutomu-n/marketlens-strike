# Trade[XYZ] Quote Collector CLI Status And Next Plan

Timestamp: 2026-05-26 21:17:46 JST  
Updated: 2026-05-27 JST

> Current status: historical plan plus status note. The CLI described here has since grown additional options and artifacts. Check `uv run sis collect-trade-xyz-quotes --help` and `docs/DOCUMENT_AUDIT_2026-05-27.md` before using this as an implementation source.

## 結論

`trade_xyz` quote collector の public CLI 化は完了済み。

現行 command:

```bash
uv run sis collect-trade-xyz-quotes
```

この文書は、旧「CLI 化実装メモ」ではなく、次に必要な `Trade[XYZ] operations gate cutover` の前提資料として読む。

## 現行 status

Implemented:

- `uv run sis collect-trade-xyz-quotes` が public CLI として使える。
- `--registry-path` で registry JSON を指定できる。
- `--normalize/--no-normalize` で normalize 実行を切り替えられる。
- `--symbols`, `--max-symbols`, `--duration-minutes`, `--interval-seconds`, `--replace`, `--dry-run`, `--write-summary`, `--write-report`, `--output-dir` が使える。
- `--write-summary` は `data/ops/trade_xyz_quote_collection_summary.json`、`--write-report` は `data/reports/trade_xyz_quote_collection_report.md` を出す。
- default では raw quote JSONL 収集後に `data/normalized/quotes.parquet` と `data/normalized/sis.duckdb` を更新する。
- `probe trade-xyz` が生成する `data/registry/trade_xyz_instrument_registry.json` を標準入力 artifact とする。
- `log-quotes --venue gtrade` は current public CLI surface ではない。

Current command flow:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes
```

Raw only:

```bash
uv run sis collect-trade-xyz-quotes --no-normalize
```

## 実装済み surface

CLI:

- `src/sis/commands/quotes.py`
- command: `collect-trade-xyz-quotes`
- options:
  - `--registry-path`
  - `--normalize/--no-normalize`
  - `--symbols`
  - `--max-symbols`
  - `--duration-minutes`
  - `--interval-seconds`
  - `--replace/--append`
  - `--dry-run`
  - `--write-summary`
  - `--write-report`
  - `--output-dir`

Registry helper:

- `src/sis/venues/trade_xyz/registry.py`
- `load_trade_xyz_registry(path)`

Tests:

- `tests/test_cli_smoke.py`
- help 表示
- happy path
- `--no-normalize`
- registry missing
- no active instruments

Docs already updated:

- `README.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/CURRENT_STATE.md`

## 入出力 contract

Input:

- default registry: `data/registry/trade_xyz_instrument_registry.json`
- shape: `InstrumentSpec[]`
- active `trade_xyz` instruments only

Raw output:

- `data/raw/quotes/trade_xyz/<YYYY-MM-DD>.jsonl`

Normalized output:

- `data/normalized/quotes.parquet`
- `data/normalized/sis.duckdb`

Stdout:

- `quote_count=<n>`
- `raw_quotes_path=<path>`
- normalize 実行時:
  - `normalized_quotes_path=<path>`
  - `duckdb_path=<path>`
- summary/report 実行時:
  - `summary_path=<path>`
  - `report_path=<path>`
- `recommended_read_order_*`

## 現在の残課題

`collect-trade-xyz-quotes` は実装済みだが、Bot 化前にはまだ不足がある。

現状の operations/readiness artifact は一部 legacy `gtrade` / `ostium` 前提を見ている。
そのため、Trade[XYZ] quote が取得できても、`phase-gate-review` が Trade[XYZ] 主軸の readiness 判定になっているとは限らない。

既知の不足:

- `Trade[XYZ]` quote freshness / spread / depth / tradable rate を phase gate の主入力にする cutover
- real market quality と `trade_xyz` venue quality の combined gate
- tracking report を Bot 判断へ接続する decision artifact
- legacy `gtrade` / `ostium` blocker によらない readiness snapshot
- `bot_decision.json` / orders preview の生成
- live order はまだ出さない

## 次に作るべきもの

次PR候補:

```text
Trade[XYZ] operations gate cutover
```

目的:

- `collect-trade-xyz-quotes` で生成した fresh artifact を operations/readiness/phase gate に接続する。
- legacy live evidence gate ではなく、Trade[XYZ] + real market + tracking の品質で Bot 前段の Go/No-Go を判定する。
- 実発注はしない。まず paper / preview / no-trade reason を生成する。

## 推奨 command surface

第一候補:

```bash
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis validate-artifacts --strict
```

責務:

1. `probe trade-xyz`
2. `collect-trade-xyz-quotes --write-summary --write-report`
3. real market data ingest
4. feature panel build
5. signal build
6. real market vs Trade[XYZ] tracking report
7. Trade[XYZ] quality gate
8. readiness snapshot / phase gate refresh

この command は live order を出さない。

## Bot 前段 artifact

新規 artifact 候補:

- `data/ops/trade_xyz_data_quality.json`
- `data/reports/trade_xyz_data_quality.md`
- `data/ops/trade_xyz_readiness.json`
- `data/reports/trade_xyz_readiness.md`
- `data/bot/bot_decision.json`
- `data/reports/bot_orders_preview.md`

`bot_decision.json` の最低限の内容:

```text
symbol
side
decision: trade | no_trade
confidence
source_confidence
venue_quality_score
spread_bps
depth_10bps_usd
quote_age_ms
market_session_status
block_reasons
max_notional_usd
required_gates
```

## Gate inputs

Trade[XYZ] quote quality:

- quote row count
- quote age / freshness
- tradable rate
- spread p50 / p90
- depth 10bps / 25bps
- block reason rate
- `BLOCK_API_ERROR` rate
- missing bid / ask rate

Real market quality:

- provider availability
- source confidence
- stale/delayed data status
- market session status
- event blackout status

Tracking quality:

- real market vs venue price difference
- lead/lag confidence
- tracking status per symbol
- source confidence threshold

Paper readiness:

- fee model available
- paper fills use Trade[XYZ] quote and tracking quality
- no-trade reason is explicit

## Acceptance

Done when:

- `uv run sis collect-trade-xyz-quotes` remains public and tested.
- A single command can refresh Trade[XYZ] quote, real market, tracking, readiness artifacts without live order.
- `phase-gate-review` or a Trade[XYZ]-specific readiness command no longer requires legacy `gtrade` / `ostium` artifacts for the Trade[XYZ] Bot path.
- `bot_decision.json` can express both `trade` and `no_trade` decisions.
- no-trade reasons are explicit and test-covered.
- `./scripts/check` passes.

## Non-goals

- live order execution
- wallet / signing / secret handling
- production daemon deployment
- replacing paper execution with real execution
- removing historical legacy evidence docs

## Verification

Current CLI verification:

```bash
uv run sis collect-trade-xyz-quotes --help
uv run sis validate-artifacts --help
uv run pytest tests/test_cli_smoke.py -q
./scripts/check
```

Next PR verification should include:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --no-normalize
uv run sis collect-trade-xyz-quotes
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
uv run pytest tests/test_cli_smoke.py -q
uv run pytest -q
./scripts/check
```

## Docs status

The active docs have been updated to treat `collect-trade-xyz-quotes` as implemented:

- `docs/DOCUMENT_AUDIT_2026-05-26.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/CODE_STATUS.md`

Do not update historical generated artifacts in `docs/archive/` or `docs/live_evidence_reports/`.
