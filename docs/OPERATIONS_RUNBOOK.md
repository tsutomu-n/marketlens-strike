# Operations Runbook

この runbook は current repo を再開・再検証・再生成するための最短手順です。`data/` は git 管理外なので、artifact は必要に応じて作り直します。

## Restart

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

読む順番:

1. `docs/CURRENT_STATE.md`
2. `docs/CODE_STATUS.md`
3. `data/reports/current_state_index.md`
4. `data/reports/readiness_snapshot.md`
5. `data/reports/phase_gate_review.md`
6. `data/reports/operations_dashboard.md`

## Trade[XYZ] Migration Surfaces

registry / universe:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
```

quote ingest:

- `collect-trade-xyz-quotes` は `probe trade-xyz` が生成した registry を読んで raw quote JSONL を収集する。
- default では normalize まで実行する。raw JSONL だけ欲しい時は `--no-normalize` を使う。
- `--symbols`, `--max-symbols`, `--duration-minutes`, `--interval-seconds`, `--replace`, `--dry-run`, `--write-summary`, `--write-report`, `--output-dir` で収集対象と artifact 出力を絞れる。
- `--write-summary` は `data/ops/trade_xyz_quote_collection_summary.json`、`--write-report` は `data/reports/trade_xyz_quote_collection_report.md` を出す。
- legacy `gtrade` / `ostium` replay command は active CLI から削除済み。

real market and tracking:

```bash
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
```

## Paper Operations

paper state を 1 cycle 進める:

```bash
uv run sis paper-operations-cycle
```

関連 artifact:

- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`
- `data/reports/daily_paper_report.md`
- `data/reports/paper_operations_runbook.md`

## Execution And Ops Artifacts

read-only execution surface:

```bash
uv run sis execution-snapshot
uv run sis execution-venue-comparison
uv run sis execution-venue-diagnostics
uv run sis execution-read-only-surfaces
```

single-command surface:

```bash
uv run sis healthcheck
uv run sis notification-outbox --level warn --title "Stale" --body "recollect live evidence"
```

## Live Evidence

gTrade / Ostium の legacy collector は `archive/gtrade_ostium_legacy_archive_*.zip` に圧縮済みで、展開済み file tree は active repo から削除済み。legacy sidecar command を直接呼ぶ手順は current CLI として扱わない。

dry-run:

```bash
uv run python scripts/run_live_evidence.py --dry-run
```

run:

```bash
uv run python scripts/run_live_evidence.py --duration-minutes 120 --metadata-interval-seconds 60
```

この non-dry-run path は現在停止する。legacy gTrade/Ostium collector はZIP化済みなので、現行の収集は次のTrade[XYZ] refresh pathを使う。

Trade[XYZ] refresh path:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

`check-go-no-go` と `build-evidence-card` は補助reportとして残る。Bot前の現行判定は `phase-gate-review` を正本にする。

PR12 fresh read-only smoke path:

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

2026-05-27 の既知良好 artifact:

- `data/ops/trade_xyz_quote_collection_summary.json`: 310 rows, 3673.995702 observed seconds
- `data/ops/pr12_fresh_read_only_smoke_summary.json`: `final_decision=READ_ONLY_GO`
- `data/ops/phase_gate_review_summary.json`: `phase_gate_decision=READ_ONLY_GO`, `next_actions=[]`

`docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md` 以降の 3 文書は、この legacy read-only collector chain の補助資料です。`Trade[XYZ]` migration 完了そのものの説明ではありません。

## Daemon And Notifications

bounded local loop:

```bash
uv run sis daemon-run --mode paper --command "uv run sis paper-step" --max-cycles 1
```

dry-run:

```bash
uv run sis daemon-dry-run --mode paper --command "uv run sis paper-step" --every-minutes 30
```

`daemon-run` は local command-loop runner です。external supervisor や remote orchestration は未完了です。

## Micro Live Boundary

`Trade[XYZ]` micro live canary は code/test surface としては存在するが、現時点では public CLI command を公開していない。

標準確認:

```bash
uv run pytest tests/test_trade_xyz_live_order_policy.py tests/test_trade_xyz_adapter_safety.py tests/test_micro_live_canary.py -q
```

manual live smoke は標準運用手順に含めない。wallet / signing / exchange write integration は別途レビュー前提。

## Stop Conditions

- `phase-gate-review` が `phase2_entry_allowed=false` の間は、運用上の昇格完了と扱わない。ただし legacy artifact blocker が出ている場合は current Trade[XYZ] path と legacy path を分けて読む。
- generated artifact が欠けている場合、推測で判断せず再生成する。
- micro live code path があることをもって live trading ready と解釈しない。
- migration docs と legacy live evidence docs を混同しない。
