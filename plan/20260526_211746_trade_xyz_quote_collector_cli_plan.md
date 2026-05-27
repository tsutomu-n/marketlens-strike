# Trade[XYZ] Quote Collector CLI Consumed Plan

Timestamp: 2026-05-26 21:17:46 JST  
Updated: 2026-05-27 JST

> Current status: historical consumed plan plus status note. PR12 read-only smoke and Trade[XYZ] phase gate cutover are complete. Check `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md`, and `uv run sis collect-trade-xyz-quotes --help` before using this as an implementation source.

## 結論

`trade_xyz` quote collector の public CLI 化と、PR12 read-only smoke までの phase gate 接続は完了済み。

現行 command:

```bash
uv run sis collect-trade-xyz-quotes --write-summary --write-report
```

この文書は current implementation plan ではなく、PR9a-PR12 で消化された historical plan として読む。

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
- `phase-gate-review` は Trade[XYZ] artifacts を使って `READ_ONLY_GO` を出せる。

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

## PR12 result

2026-05-27 の latest artifact:

- `data/ops/trade_xyz_quote_collection_summary.json`: 310 rows, 3673.995702 observed seconds
- `data/ops/pr12_fresh_read_only_smoke_summary.json`: `final_decision=READ_ONLY_GO`
- `data/reports/pr12_fresh_read_only_smoke_report.md`
- `data/ops/phase_gate_review_summary.json`: `phase_gate_decision=READ_ONLY_GO`, `next_actions=[]`

## 現在の残課題

`collect-trade-xyz-quotes` と Trade[XYZ] read-only phase gate は実装済みだが、Bot 化前にはまだ不足がある。

現状では live order はまだ出さない。残る主題は、paper / preview / no-trade reason を正式な bot artifact として切り出す作業である。

既知の不足:

- tracking report を Bot 判断へ接続する decision artifact
- `bot_decision.json` / orders preview の生成
- live order はまだ出さない

## 次に作るべきもの

次候補:

```text
Trade[XYZ] bot decision preview
```

目的:

- Trade[XYZ] + real market + tracking の品質を Bot 前段の Go/No-Go artifact に落とす。
- 実発注はしない。まず paper / preview / no-trade reason を生成する。

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

PR12 verification included:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --symbols SP500,XYZ100,NVDA,AAPL,MSFT --duration-minutes 60 --interval-seconds 60 --normalize --replace --write-summary --write-report
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis paper-operations-cycle
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

## Docs status

The active docs have been updated to treat `collect-trade-xyz-quotes` as implemented:

- `docs/DOCUMENT_AUDIT_2026-05-27.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/CODE_STATUS.md`

Do not update historical generated artifacts in `docs/archive/` or `docs/live_evidence_reports/`.
