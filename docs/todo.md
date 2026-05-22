# MarketLens Strike Live Evidence Fix Plan

## 追加タスク: refresh_live_evidence runner hardening

### 目的

`refresh_live_evidence.sh` / `.ps1` を単なる直列実行から、誤実行と空データ通過を防ぐ preflight 付きランナーへ強化する。

### 対象ファイル

- `scripts/refresh_live_evidence.sh`
- `scripts/refresh_live_evidence.ps1`
- `docs/LIVE_EVIDENCE_RUNBOOK.md`
- `tests/test_cli_smoke.py`
- `tests/` 配下の必要な追加テスト

### タスク

1. `refresh_live_evidence.sh` に `--dry-run` と `--force` を追加し、数値引数と option を安全に parse できるようにする。
2. 実行開始時に `uv` / `bun` の存在確認、`next-live-window` の表示、実行モード表示を追加する。
3. `--dry-run` 時は収集や artifact 更新を行わず、preflight 結果だけ表示して終了する。
4. 通常実行では `next-live-window` の推奨枠を使って window 外を検知し、`--force` なしでは停止する。
5. `bun run gtrade:collect-window` 実行後に sidecar pricing / trading variables / raw quotes の最低行数を検査し、不足時は normalize 以降へ進ませない。
6. `uv run sis diagnose-quotes` は venue 全体一括ではなく、`QQQ` / `SPY` / `XAU` を symbol 別に実行する。
7. 実行順を `collect -> row checks -> log-quotes -> normalize -> cost matrix -> diagnose -> backtest -> go/no-go -> evidence -> validate` に整理する。
8. 最後に主要 artifact path、decision、diagnostics 要約をまとめた summary を表示する。
9. PowerShell 版 `refresh_live_evidence.ps1` も同じ CLI 契約と stop condition に揃える。
10. shell / PowerShell の新しい挙動に合わせて runbook を更新し、dry-run と force の使い分けを明記する。

### 完了条件

- `bash scripts/refresh_live_evidence.sh --dry-run` が data 更新なしで preflight のみ表示する。
- 推奨 window 外の通常実行は非0終了し、`--force` 指定時のみ収集へ進む。
- raw 行数不足時は normalize 以降へ進まず、原因が標準出力で分かる。
- diagnostics が `QQQ` / `SPY` / `XAU` ごとに分かれて表示される。
- shell / PowerShell の使い方が [docs/LIVE_EVIDENCE_RUNBOOK.md](/home/tn/projects/marketlens-strike/docs/LIVE_EVIDENCE_RUNBOOK.md) と一致する。

## 目的

開場後の `refresh_live_evidence` 実行前に、live evidence 収集が止まらないリスク、XAU session 計算バグ、stale 判定の不一致、venue横断の Go/No-Go 判定混線を修正し、実測結果を信頼できる状態にする。

## 制約

- 実装は小さな Red -> Green で進める。
- 既存の `uv` / `bun` / `Justfile` / Typer CLI 構成を維持する。
- live取引や外部発注は行わない。対象は read-only data collection と local report generation の安全化のみ。
- `data/` 配下の実測生成物はテスト入力として新規作成しない。テストは `tmp_path`、fixture、mock WebSocket を使う。
- `GoNoGoReport` の model を拡張する場合は、`schemas/go_no_go_report.schema.json` と evidence card の出力も同時に揃える。
- 古い handoff spec は実装と矛盾する最小箇所だけ更新し、過去設計文書の全面改稿はしない。

## 対象ファイル

- `sidecars/gtrade/src/pricing_ws.ts`
- `sidecars/gtrade/src/pricing_ws.test.ts`
- `src/sis/market_calendar.py`
- `tests/test_market_calendar.py`
- `src/sis/reports/cost_matrix.py`
- `tests/test_cost_matrix.py`
- `src/sis/reports/quote_diagnostics.py`
- `src/sis/cli.py`
- `tests/test_quote_diagnostics.py`
- `src/sis/models.py`
- `src/sis/reports/go_no_go.py`
- `src/sis/reports/evidence.py`
- `src/sis/validation/artifacts.py`
- `schemas/go_no_go_report.schema.json`
- `tests/test_artifact_validation.py`
- `tests/test_go_no_go.py`
- `tests/test_evidence_card.py`
- `package.json`
- `.github/workflows/ci.yml`
- `docs/sis_venue_probe_handoff/docs/09_storage_reporting_spec.md`
- `docs/sis_venue_probe_handoff/docs/12_go_no_go_spec.md`

## タスク

1. `collectPricingFrames()` に `createWebSocket` optional dependency を追加し、実運用では global `WebSocket`、テストでは fake WebSocket を使えるようにする。
2. `collectPricingFrames()` は正規化後の `maxMessages` と `durationMs` がどちらも無効なら error にする。env の `GTRADE_PRICING_MAX_MESSAGES` が有効なら guard は通す。
3. `durationMs > 0` の場合は接続中全体に timer を持たせ、無通信でも duration 到達で close / resolve する。
4. XAU の `_xau_close_for_open_time()` を修正し、月〜木の 18:00 ET 以降に始まる session は翌日 17:00 ET close にする。
5. `cost_matrix` の stale 集計で `oracle_ts_ms` 欠損を stale として数える。
6. `quote_diagnostics` の stale threshold を 10,000ms 固定から venue別 threshold mapping に変更し、既定値は `gtrade=3000ms`、`ostium=5000ms` にする。
7. CLI の `diagnose-quotes` は `load_halt_policy()` から venue別 stale threshold を読み、診断出力にも使用閾値を表示する。
8. `GoNoGoReport` に `venue_decisions` を追加する。gTrade と Ostium を別々に `GO` / `CONDITIONAL_*` / `NO_GO_*` で判定し、最重要 blocker を `main_blocker` として保持する。
9. `write_go_no_go_markdown()` に `## Venue Decisions` table を追加し、global decision と venue別 decision を分けて表示する。
10. `schemas/go_no_go_report.schema.json` と `build_evidence_card()` を拡張し、artifact validation と evidence card が新 model と矛盾しないようにする。
11. `validate-artifacts` は過去の古い evidence card ではなく最新 evidence card を検証対象にし、refresh 後の strict validation が古い生成物で失敗しないようにする。
12. root `package.json` に `gtrade:collect-window` を追加する。
13. CI の Python install を `3.13` に変更する。
14. 古い report spec docs の `go_no_go_report.md` format に `Venue Decisions` を最小追記する。

## テスト方針

- TypeScript targeted:
  - `cd sidecars/gtrade && bun test src/pricing_ws.test.ts`
  - `cd sidecars/gtrade && bun run typecheck`
- Python targeted:
  - `uv run pytest tests/test_market_calendar.py tests/test_cost_matrix.py tests/test_quote_diagnostics.py tests/test_go_no_go.py tests/test_evidence_card.py tests/test_cli_smoke.py`
- Full local check:
  - `just check`
- Smoke commands:
  - `uv run sis next-live-window --venue gtrade --symbol QQQ`
  - `uv run sis next-live-window --venue gtrade --symbol SPY`
  - `uv run sis next-live-window --venue gtrade --symbol XAU`
  - `uv run sis diagnose-quotes`
  - `uv run sis check-go-no-go`
  - `uv run sis validate-artifacts --strict`

## 完了条件

- `collect-gtrade-window` が無通信の pricing websocket でも duration 到達で終了する。
- `collectPricingFrames()` が無制限実行を暗黙に許さない。
- XAU の `next_close_jst` が `next_open_jst` より前にならない。
- missing `oracle_ts_ms` が `diagnose-quotes` と `cost_matrix` の両方で stale として扱われる。
- stale threshold が `configs/halt_policy.yaml` の venue別値と一致する。
- `go_no_go_report.md` に global decision とは別に `Venue Decisions` table が出る。
- evidence card と JSON schema が `venue_decisions` に対応している。
- root から `bun run gtrade:collect-window` を呼べる。
- CI の Python setup が `3.13` になっている。
- `validate-artifacts --strict` が古い evidence card に阻害されず、最新 evidence card を検証する。
- テスト方針に記載したコマンドが成功する。
