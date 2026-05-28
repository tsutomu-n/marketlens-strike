# marketlens-strike

`marketlens-strike` は、`Trade[XYZ] / real market / tracking / paper / micro live safety` への migration を実装済みの workspace です。2026-05-28 時点では Trade[XYZ] read-only gate は `READ_ONLY_GO` で、fee mode blocker は解消済みです。

## Read First

1. [docs/CURRENT_STATE.md](/home/tn/projects/marketlens-strike/docs/CURRENT_STATE.md)
2. [docs/CODE_STATUS.md](/home/tn/projects/marketlens-strike/docs/CODE_STATUS.md)
3. [docs/OPERATIONS_RUNBOOK.md](/home/tn/projects/marketlens-strike/docs/OPERATIONS_RUNBOOK.md)
4. [docs/ARCHITECTURE_AND_PHASES.md](/home/tn/projects/marketlens-strike/docs/ARCHITECTURE_AND_PHASES.md)
5. [docs/trade_xyz_bot_beginner_guide.html](/home/tn/projects/marketlens-strike/docs/trade_xyz_bot_beginner_guide.html)
6. [plan/archive/PR-00_to_PR-08_implementation_plan.md](/home/tn/projects/marketlens-strike/plan/archive/PR-00_to_PR-08_implementation_plan.md) は historical migration contract として読む

## Setup

```bash
uv python install 3.13
uv sync --dev --locked
uv run python -V
uv run sis --help
```

依存を変更した時だけ:

```bash
uv lock --python /usr/bin/python3.13
```

全体確認:

```bash
./scripts/check
```

## Main Flows

implementation and ops artifacts:

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

Trade[XYZ] universe:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
```

Useful quote collection variants:

```bash
uv run sis collect-trade-xyz-quotes --symbols SP500,NVDA --duration-minutes 5 --interval-seconds 60
uv run sis collect-trade-xyz-quotes --no-normalize --write-summary --write-report
uv run sis collect-trade-xyz-quotes --dry-run --max-symbols 3
```

paper cycle:

```bash
uv run sis paper-operations-cycle
```

Trade[XYZ] quote refresh:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
uv run sis bot-preview
```

`check-go-no-go` and `build-evidence-card` remain supplemental artifact reports. They are not the primary Bot-readiness gate; use `phase-gate-review` for the current Trade[XYZ] decision.
`bot-preview` writes a read-only HOLD decision to `data/bot/bot_decision.json` and `data/reports/bot_orders_preview.md` when run; those files are runtime artifacts and may be absent in a fresh checkout. It does not use wallet secrets, signing, or exchange writes.

PR12 read-only smoke evidence:

- `data/ops/pr12_fresh_read_only_smoke_summary.json`
- `data/reports/pr12_fresh_read_only_smoke_report.md`
- latest observed window: 310 rows / 3673.995702 seconds / `SP500`, `XYZ100`, `NVDA`, `AAPL`, `MSFT`
- latest phase gate: `READ_ONLY_GO`, `individual_stock_decision=paper_only`, `next_actions=[]`
- current strict validation: `checked_files=12`, `issues=0`
- current execution drift classification: `P2_BLOCKER=0`, `LIVE_READINESS_BLOCKER=6`

## Current Boundaries

- `trade_xyz` / `real_market` / `tracking` / `paper` / `micro_live` の code surface はある
- `src/sis/cli.py` は root Typer app の組み立てと `main()` に寄せ、command 実装は `src/sis/commands/` に分割済み
- micro live は code/test surface であり、現時点では public CLI command を公開していない
- `collect-trade-xyz-quotes` は public CLI command として利用できる
- Trade[XYZ] read-only artifact は phase gate に接続済み
- Trade[XYZ] active symbols の `fee_mode`, `taker_fee_bps`, `maker_fee_bps` は `configs/fee_model.trade_xyz.yaml` から registry / quote row へ伝播する
- Alpaca provider は silent empty stub ではなく、credentials 未設定時は明示的に unavailable で失敗する
- `bot-preview` は実行時に read-only HOLD preview artifact を出力する
- wallet secrets, signing, production live trading は未完了
- `data/` は git 管理外

## Current Verification

2026-05-28 時点:

- `uv run ruff check .`: pass
- `uv run pyrefly check`: pass
- `uv run pytest -q`: 292 passed
- `./scripts/check`: pass, 292 passed
- `uv run sis validate-artifacts --strict`: `checked_files=12`, `issues=0`
- `uv run sis phase-gate-review`: `READ_ONLY_GO`, `phase2_entry_allowed=true`, `blockers=[]`

## Legacy Notes

gTrade / Ostium の legacy source, sidecar, raw data, registry, 専用テストは `archive/gtrade_ostium_legacy_archive_*.zip` に圧縮済みです。展開済みの file tree は active repo から削除済みで、新規実装の主軸は Trade[XYZ] です。
