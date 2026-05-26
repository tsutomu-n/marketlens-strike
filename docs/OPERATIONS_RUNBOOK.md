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
```

quote ingest:

- `trade_xyz` quote collector は code surface と tests では存在するが、現時点では public CLI command を公開していない。
- `uv run sis log-quotes` は legacy `gtrade` replay 専用。

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
uv run sis execution-snapshot --venue gtrade --fills-limit 5 --order-limit 5
uv run sis execution-venue-comparison
uv run sis execution-venue-diagnostics
uv run sis execution-read-only-surfaces
```

single-command surface:

```bash
uv run sis balance-status --venue gtrade
uv run sis fill-status --venue gtrade --limit 20
uv run sis order-status --venue gtrade --order-id ord-1
uv run sis reconcile-positions --venue ostium
uv run sis healthcheck
uv run sis notification-outbox --level warn --title "Stale" --body "recollect live evidence"
```

## Live Evidence

現在の operational live evidence chain は legacy archive collector を含む。

dry-run:

```bash
uv run python scripts/run_live_evidence.py --dry-run
```

run:

```bash
uv run python scripts/run_live_evidence.py --duration-minutes 120 --metadata-interval-seconds 60 --backend-event-duration-minutes 30
```

legacy replay path:

```bash
bun run --cwd archive/legacy_sidecars/gtrade probe
uv run sis log-quotes --venue gtrade --replace
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis check-go-no-go
uv run sis build-evidence-card
uv run sis phase-gate-review
```

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

- `phase-gate-review` が `phase2_entry_allowed=false` の間は、運用上の昇格完了と扱わない。
- generated artifact が欠けている場合、推測で判断せず再生成する。
- micro live code path があることをもって live trading ready と解釈しない。
- migration docs と legacy live evidence docs を混同しない。
