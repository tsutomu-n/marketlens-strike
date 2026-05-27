# marketlens-strike

`marketlens-strike` は、`Trade[XYZ] / real market / tracking / paper / micro live safety` への migration を実装済みの workspace です。現行の operator-facing artifact chain には legacy read-only collector も一部残ります。

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
uv run sis collect-trade-xyz-quotes
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
uv run sis collect-trade-xyz-quotes
uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis build-backtest
uv run sis check-go-no-go
uv run sis build-evidence-card
```

## Current Boundaries

- `trade_xyz` / `real_market` / `tracking` / `paper` / `micro_live` の code surface はある
- `src/sis/cli.py` は root Typer app の組み立てと `main()` に寄せ、command 実装は `src/sis/commands/` に分割済み
- micro live は code/test surface であり、現時点では public CLI command を公開していない
- `collect-trade-xyz-quotes` は public CLI command として利用できる
- wallet secrets, signing, production live trading は未完了
- `data/` は git 管理外

## Current Verification

2026-05-27 時点:

- `uv run ruff check .`: pass
- `uv run pyrefly check`: pass
- `uv run pytest -q`: 270 passed
- `./scripts/check`: pass

## Legacy Notes

gTrade / Ostium の legacy source, sidecar, raw data, registry, 専用テストは `archive/gtrade_ostium_legacy_archive_*.zip` に圧縮済みです。展開済みの file tree は active repo から削除済みで、新規実装の主軸は Trade[XYZ] です。
