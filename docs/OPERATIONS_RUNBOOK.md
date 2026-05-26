# Operations Runbook

この runbook は、現行コードから運用状態を再生成して読むための手順です。`data/` は git 管理外なので、再開時はまず artifact を作り直します。

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
7. `data/reports/remediation_scoreboard.md`

## Paper Operations

paper state を 1 cycle 進め、下流 artifact まで更新する。

```bash
uv run sis paper-operations-cycle
```

主要 artifact:

- `data/reports/paper_operations_runbook.md`
- `data/reports/paper_cycle_history.md`
- `data/reports/operations_dashboard.md`
- `data/reports/audit_dashboard.md`

local daemon loop を bounded smoke として実行する場合:

```bash
uv run sis daemon-run --mode paper --command "uv run sis paper-step" --max-cycles 1
```

常駐させる場合は、外部 supervisor なしであることを理解したうえで明示的に `--forever` を付けます。停止は kill switch または command failure です。

主要 artifact:

- `data/ops/daemon_loop.json`
- `data/ops/daemon_loop_summary.json`
- `data/ops/daemon_loop_events.jsonl`
- `data/reports/daemon_loop.md`

notification を provider 送信せず local queue に積む場合:

```bash
uv run sis notification-outbox --level warn --title "Stale" --body "recollect live evidence"
```

主要 artifact:

- `data/notifications/outbox.jsonl`
- `data/notifications/latest_notification.json`
- `data/ops/notification_outbox_summary.json`
- `data/reports/notification_outbox.md`

## Read-Only Execution Surfaces

target 不要の read-only observation は refresh / daemon dry-run / paper cycle で再集約されます。

```bash
uv run sis execution-snapshot --venue gtrade --fills-limit 5 --order-limit 5
uv run sis execution-venue-comparison
uv run sis execution-venue-diagnostics
uv run sis execution-read-only-surfaces
uv run sis refresh-operations-artifacts
```

single command surface:

```bash
uv run sis balance-status --venue gtrade
uv run sis fill-status --venue gtrade --limit 20
uv run sis order-status --venue gtrade --order-id ord-1
uv run sis reconcile-positions --venue ostium
```

`cancel-order` と `close-position` は target 依存です。自動 refresh の対象にしません。

## Live Evidence

実行前に dry-run で推奨 window と preflight を確認する。

```bash
uv run python scripts/run_live_evidence.py --dry-run
```

取得する場合:

```bash
uv run python scripts/run_live_evidence.py --duration-minutes 120 --metadata-interval-seconds 60 --backend-event-duration-minutes 30
```

sidecar を replay して Go/No-Go まで更新する場合:

```bash
bun run gtrade:probe
uv run sis log-quotes --venue gtrade --replace
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis check-go-no-go
uv run sis build-evidence-card
uv run sis phase-gate-review
```

live evidence report は `docs/live_evidence_reports/` に出ます。最新運用判断は `data/reports/phase_gate_review.md` と `data/reports/readiness_snapshot.md` で確認します。

`XNYS` や `QQQ` / `SPY` / `XAU` の市場カレンダー差分は `docs/XNYS_MARKET_CALENDAR.md` を読む。

read-only collector の raw artifact / manifest / phase gate 連携は `docs/LIVE_EVIDENCE_READ_ONLY_COLLECTORS.md` を読む。実装計画とタスク一覧は `docs/READ_ONLY_COLLECTOR_IMPLEMENTATION_PLAN.md` を読む。Ostium は Builder API artifact、legacy metadata REST、Python SDK read-only probe が揃って初めて constraint pass と扱う。

## Remediation

remediation chain は dry-run の運用支援です。実 command の自動実行ではありません。

```bash
uv run sis remediation-planner
uv run sis remediation-execution-plan
uv run sis remediation-session
uv run sis remediation-session-checkpoint
uv run sis remediation-scoreboard
uv run sis remediation-evaluator
uv run sis remediation-evidence
uv run sis remediation-command-results
```

operator が実行結果を取り込む場合:

```bash
uv run sis remediation-evidence-ingest --action-key <key> --result pass --exit-code 0
```

## Stop Conditions

- `phase_gate_review` が Phase 2 entry を許可しない場合、Phase 2 完了扱いにしない。
- generated artifact が欠けている場合、推測で判断せず `refresh-operations-artifacts` を再実行する。
- live evidence が古い場合、Go/No-Go の改善を実装完了と扱わない。
- read-only execution surface を live trading integration と混同しない。
