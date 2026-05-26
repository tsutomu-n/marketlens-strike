# marketlens-strike

`marketlens-strike` は、QQQ / SPY / XAU の venue 評価のための、ローカル research・paper operations・read-only execution evidence 用 workspace です。

現状の正本はコードです。手書きの docs は、コード起点の情報や生成 artifact の読み方を補足するものであり、実装そのものを上書きしません。

## まず読む

最初に次を読んでください。

1. [docs/CURRENT_STATE.md](/home/tn/projects/marketlens-strike/docs/CURRENT_STATE.md)
2. [docs/CODE_STATUS.md](/home/tn/projects/marketlens-strike/docs/CODE_STATUS.md)
3. [docs/OPERATIONS_RUNBOOK.md](/home/tn/projects/marketlens-strike/docs/OPERATIONS_RUNBOOK.md)
4. [docs/ARCHITECTURE_AND_PHASES.md](/home/tn/projects/marketlens-strike/docs/ARCHITECTURE_AND_PHASES.md)

その後、生成 runtime artifact を更新します。

```bash
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

更新後に最も重要なレポートは次です。

- `data/reports/current_state_index.md`
- `data/reports/readiness_snapshot.md`
- `data/reports/phase_gate_review.md`
- `data/reports/operations_dashboard.md`
- `data/reports/remediation_scoreboard.md`

`data/` は git 管理外です。生成ファイルは tracked source document ではなく、その時点の runtime evidence として扱ってください。

`docs/live_evidence_reports/` は live evidence runner が吐く markdown / HTML 出力の置き場です。既存ファイルは historical runtime output を含むため、現行判断はまず `data/reports/phase_gate_review.md` と `data/reports/readiness_snapshot.md` を優先してください。

## セットアップ

```bash
uv python install 3.14
uv sync --dev
uv run python -V
uv run sis --help
```

JavaScript sidecar は `bun` を使います。

```bash
bun install --frozen-lockfile
bun run gtrade:typecheck
bun run ostium:typecheck
```

ローカル検証を一通り流す場合:

```bash
./scripts/check
```

一部の archive 済み note には `rtk` が出てきますが、これは local wrapper にすぎません。利用できない場合は同じコマンドをそのまま実行してください。

## 主なワークフロー

operations / audit / phase gate / remediation / restart artifact を更新する:

```bash
uv run sis refresh-operations-artifacts
```

paper operations を 1 cycle 回し、下流 artifact まで再生成する:

```bash
uv run sis paper-operations-cycle
```

implementation status を再構築する:

```bash
uv run sis implementation-status --write
```

venue window が有効なときに live evidence を収集または再生する:

```bash
uv run python scripts/run_live_evidence.py --dry-run
uv run python scripts/run_live_evidence.py --duration-minutes 120 --metadata-interval-seconds 60
```

既存の gTrade sidecar data を quote pipeline に replay する:

```bash
bun run gtrade:probe
uv run sis log-quotes --venue gtrade --replace
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis check-go-no-go
uv run sis build-evidence-card
```

## よく使うコマンド

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

CLI 全体は `uv run sis --help` を見てください。

## 現在の制約

この repository には、research data、decision summary、paper trading、read-only execution surface、operations report、remediation dry-run まで、かなりの実装が入っています。

残っている運用上の blocker は docs 不足ではありません。2026-05-26 時点の `data/reports/phase_gate_review.md` では、判定は `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`、`Phase 2` 進入は `False` です。

- fresh live evidence の再収集と再評価がまだ必要
- 現在の evidence をもとに Go/No-Go を再確認する必要がある
- 実 live execution integration はまだ現在の safe surface の外にある
- external process supervision と provider delivery は未完了。`daemon-run` は local command-loop runner、`notification-outbox` は local notification queue を提供する

## 過去資料

古い handoff plan、stale な phase docs、過去の audit note は `docs/archive/` に残しています。これらは historical context 用です。現行の挙動判断は、コード、上で挙げた tracked docs、生成済み runtime artifact を基準にしてください。
