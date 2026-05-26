# marketlens-strike

`marketlens-strike` is a local research, paper-ops, and read-only execution
evidence workspace for QQQ / SPY / XAU venue evaluation.

The current code is the source of truth. Hand-written docs explain how to read
the code-owned and generated artifacts; they do not override the implementation.

## Start Here

Read these files first:

1. [docs/CURRENT_STATE.md](/home/tn/projects/marketlens-strike/docs/CURRENT_STATE.md)
2. [docs/CODE_STATUS.md](/home/tn/projects/marketlens-strike/docs/CODE_STATUS.md)
3. [docs/OPERATIONS_RUNBOOK.md](/home/tn/projects/marketlens-strike/docs/OPERATIONS_RUNBOOK.md)
4. [docs/ARCHITECTURE_AND_PHASES.md](/home/tn/projects/marketlens-strike/docs/ARCHITECTURE_AND_PHASES.md)

Then refresh the generated runtime view:

```bash
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

The most useful generated reports after refresh are:

- `data/reports/current_state_index.md`
- `data/reports/readiness_snapshot.md`
- `data/reports/phase_gate_review.md`
- `data/reports/operations_dashboard.md`
- `data/reports/remediation_scoreboard.md`

`data/` is ignored by git. Treat generated files as current runtime evidence,
not as tracked source documents.

## Setup

```bash
uv python install 3.14
uv sync --dev
uv run python -V
uv run sis --help
```

JavaScript sidecars use `bun`:

```bash
bun install --frozen-lockfile
bun run gtrade:typecheck
bun run ostium:typecheck
```

Run the full local verification gate:

```bash
./scripts/check
```

Some archived notes mention `rtk`. It is only a local wrapper. If it is not
available, run the same command without it.

## Main Workflows

Refresh operations, audit, phase-gate, remediation, and restart artifacts:

```bash
uv run sis refresh-operations-artifacts
```

Run one paper operations cycle and regenerate downstream artifacts:

```bash
uv run sis paper-operations-cycle
```

Rebuild the generated implementation status:

```bash
uv run sis implementation-status --write
```

Collect or replay live evidence when the venue window is valid:

```bash
uv run python scripts/run_live_evidence.py --dry-run
uv run python scripts/run_live_evidence.py --duration-minutes 120 --metadata-interval-seconds 60
```

Replay existing gTrade sidecar data into the quote pipeline:

```bash
bun run gtrade:probe
uv run sis log-quotes --venue gtrade --replace
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis check-go-no-go
uv run sis build-evidence-card
```

## Common Commands

```bash
uv run sis probe gtrade
uv run sis probe ostium
uv run sis probe ostium --read-only-live
uv run sis diagnose-quotes
uv run sis build-cost-matrix
uv run sis check-go-no-go
uv run sis build-evidence-card
uv run sis execution-snapshot --venue gtrade --fills-limit 5 --order-limit 5
uv run sis execution-venue-comparison
uv run sis execution-venue-diagnostics
uv run sis execution-read-only-surfaces
uv run sis balance-status --venue gtrade
uv run sis fill-status --venue gtrade --limit 20
uv run sis order-status --venue gtrade --order-id ord-1
uv run sis reconcile-positions --venue ostium
uv run sis healthcheck
uv run sis notification-outbox --level warn --title "Stale" --body "recollect"
uv run sis daemon-dry-run --mode paper --command "uv run sis paper-step" --every-minutes 30
uv run sis daemon-run --mode paper --command "uv run sis paper-step" --max-cycles 1
uv run sis current-state-index
uv run sis readiness-snapshot
uv run sis operations-dashboard
uv run sis paper-operations-runbook
uv run sis remediation-scoreboard
```

Use `uv run sis --help` for the full CLI surface.

## Current Limits

The repository contains substantial implementation for research data, decision
summaries, paper trading, read-only execution surfaces, operations reports, and
remediation dry runs.

The remaining operational blockers are not documentation blockers:

- fresh live evidence still needs to be recollected and re-evaluated
- Go/No-Go must be rechecked from current evidence
- real live execution integration is still outside the current safe surface
- external process supervision and provider delivery are not complete; `daemon-run`
  provides the local command-loop runner and `notification-outbox` provides the local notification queue

## Historical Material

Older handoff plans, stale phase docs, and previous audit notes are preserved
under `docs/archive/`. They are historical context only. Current behavior comes
from the code, tracked docs listed above, and generated runtime artifacts.
