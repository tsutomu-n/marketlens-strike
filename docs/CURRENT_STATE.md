# Current State

この文書は `marketlens-strike` の現在位置を読むための入口です。現状の正本はコードと生成 artifact です。古い handoff や phase 文書は archive に移しました。

## 結論

- この repo は初期の venue probe だけではなく、research data、decision summary、paper trading、read-only execution surface、operations/audit report、remediation dry-run まで実装を持つ。
- 運用上はまだ Phase 1 gate が閉じていない。理由は fresh live evidence の再収集と Go/No-Go 再判定が未完了だから。
- 実 live order execution と外部 provider 配信は未完了。`daemon-run` は local command-loop runner、`notification-outbox` は local notification queue を持つが、外部 supervisor / provider 連携とは分けて扱う。
- 最新の運用状態は `data/ops/*.json` と `data/reports/*.md` を読む。これらは `uv run sis refresh-operations-artifacts` で再生成する。

## Source Of Truth

優先順位は次の通りです。

1. `src/`, `schemas/`, `sidecars/`, `scripts/`, `tests/`
2. generated runtime artifacts under `data/ops/` and `data/reports/`
3. tracked docs: `docs/CURRENT_STATE.md`, `docs/CODE_STATUS.md`, `docs/OPERATIONS_RUNBOOK.md`, `docs/ARCHITECTURE_AND_PHASES.md`
4. archive under `docs/archive/`

archive は historical context です。現行判断の正本にはしません。

## What Exists In Code

現行コードは少なくとも次の surface を持ちます。

- venue quote collection and normalization for gTrade / Ostium
- cost matrix, quote diagnostics, Go/No-Go report, EvidenceCard
- research data ingest, event calendar, feature panel, signal builder, research quality report
- backtest bridge and decision summary
- local paper trading state, fills, positions, daily PnL, reports
- read-only execution adapters, balance/fill/order/position/reconciliation artifacts
- operations dashboard, timelines, audit bundle, current-state index, readiness snapshot
- remediation planner, execution plan, session, checkpoint, scoreboard, evaluator, evidence, command-results
- live evidence runner, scheduler, manifest summary, markdown/HTML reports
- bounded or explicit persistent local daemon command loop with kill-switch blocking
- local notification outbox with latest notification JSON, report, summary, and operation-chain entry

詳細な実装表は `docs/CODE_STATUS.md` を読む。再生成は次で行う。

```bash
uv run sis implementation-status --write
```

## What Is Still Not Proven

次は未完了または再確認が必要です。

- fresh live evidence window の再収集
- `stale_rate` / `tradable_rate` を含む Go/No-Go 再判定
- live execution API による発注・約定・残高の本統合
- target 依存の cancel/close/order status の自動再観測
- external supervisor / provider delivery 連携

## Verification Status

2026-05-26 時点で確認済み:

- `./scripts/check`: pass
- `uv run ruff check .`: pass
- `uv run pytest -q`: 256 passed
- `uv run pyrefly check`: pass, 0 errors
- `bun run --cwd archive/legacy_sidecars/gtrade typecheck`: pass
- `bun run --cwd archive/legacy_sidecars/ostium typecheck`: pass
- `bun run --cwd archive/legacy_sidecars/gtrade test`: 12 passed
- `bun run --cwd archive/legacy_sidecars/ostium test`: 5 passed
- `uv run sis refresh-operations-artifacts`: pass

## Recommended Read Order

まず tracked docs を読む。

1. `docs/CURRENT_STATE.md`
2. `docs/CODE_STATUS.md`
3. `docs/OPERATIONS_RUNBOOK.md`
4. `docs/ARCHITECTURE_AND_PHASES.md`

次に generated runtime artifact を読む。

1. `data/reports/current_state_index.md`
2. `data/reports/readiness_snapshot.md`
3. `data/reports/phase_gate_review.md`
4. `data/reports/operations_dashboard.md`
5. `data/reports/remediation_scoreboard.md`

artifact が古い場合は次を実行する。

```bash
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```
