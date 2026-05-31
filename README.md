# marketlens-strike

`marketlens-strike` is a Python 3.13 CLI workspace for Trade[XYZ] research,
read-only evidence collection, Strategy Research Lab workflows, paper operations,
and safety gates.

The code is the source of truth. Current docs summarize the implemented surfaces
and the latest verified snapshots; generated files under `data/` may be absent
in a fresh checkout until commands are run.

## Read First

1. [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md)
2. [docs/CODE_STATUS.md](docs/CODE_STATUS.md)
3. [docs/DOCUMENT_AUDIT_2026-05-31.md](docs/DOCUMENT_AUDIT_2026-05-31.md)
4. [docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md](docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md)
5. [docs/strategy_research_lab/README.md](docs/strategy_research_lab/README.md)
6. [docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md](docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md)
7. [docs/OPERATIONS_RUNBOOK.md](docs/OPERATIONS_RUNBOOK.md)
8. [docs/ARCHITECTURE_AND_PHASES.md](docs/ARCHITECTURE_AND_PHASES.md)
9. [docs/trade_xyz_bot_beginner_guide.html](docs/trade_xyz_bot_beginner_guide.html)
10. [plan/archive/PR-00_to_PR-08_implementation_plan.md](plan/archive/PR-00_to_PR-08_implementation_plan.md) is a historical migration contract.

## Setup

```bash
uv python install 3.13
uv sync --dev --locked
uv run python -V
uv run sis --help
```

Only update the lockfile when dependencies change:

```bash
uv lock --python /usr/bin/python3.13
```

Run the aggregate local gate:

```bash
./scripts/check
```

`./scripts/check` runs locked sync, Python version check, Ruff lint and format
check, current-docs lint, Pyrefly, and Pytest.

## Main Flows

Operations and status artifacts:

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

Trade[XYZ] read-only refresh:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
uv run sis bot-preview
```

Useful quote collection variants:

```bash
uv run sis collect-trade-xyz-quotes --symbols SP500,NVDA --duration-minutes 5 --interval-seconds 60
uv run sis collect-trade-xyz-quotes --no-normalize --write-summary --write-report
uv run sis collect-trade-xyz-quotes --dry-run --max-symbols 3
```

Paper operations:

```bash
uv run sis paper-operations-cycle
```

Strategy Research Lab to paper-only preview:

```bash
uv run sis strategy-preview
uv run sis strategy-experiment-run --spec path/to/strategy_experiment.yaml
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

Strategy authoring YAML to paper-only preview:

```bash
uv run sis strategy-author-init --out docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-explain --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-author-train-model --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --target-column research_return_1d --feature-column research_return_4h --feature-column vix_level
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
```

Strategy Lab details live in [docs/strategy_research_lab/README.md](docs/strategy_research_lab/README.md).
The author-facing capability list is
[docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md](docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md),
with an HTML explanation at
[docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html](docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html).
Strategy idea preparation starts at
[docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html](docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html).

## Current Boundaries

- `trade_xyz`, `real_market`, `tracking`, `paper`, and `micro_live` code surfaces exist.
- `src/sis/cli.py` builds the root Typer app; command implementations live under `src/sis/commands/`.
- `collect-trade-xyz-quotes` is a public CLI command.
- micro live is a code/test safety surface, not a public operator command.
- `bot-preview` writes read-only HOLD preview artifacts when run; it does not use wallet secrets, signing, or exchange writes.
- `check-go-no-go` and `build-evidence-card` are supplemental reports. Use `phase-gate-review` for the current Trade[XYZ] decision.
- `data/research/strategy_signals.parquet` is the canonical Strategy Lab signal artifact. `data/research/signals.csv` is a legacy export.
- `PaperIntentPreview` is paper-only. Do not convert it to live orders.
- Strategy Lab runtime validation lives in Pydantic models; tracked JSON Schema files are thin guards for interoperability.
- wallet secrets, signing, exchange writes, and production live trading remain out of scope.
- `data/` is git-ignored runtime state.

## Current Verification

2026-05-31 code/docs check:

- `./scripts/check`: pass, 596 passed
- `uv run pyrefly check`: pass, 0 errors
- `uv run python scripts/check_current_docs.py`: pass, `checked 78 current docs`

2026-05-28 runtime artifact snapshot:

- `uv run sis validate-artifacts --strict`: `checked_files=12`, `issues=0`
- `uv run sis phase-gate-review`: `READ_ONLY_GO`, `phase2_entry_allowed=true`, `blockers=[]`
- current execution drift classification: `P2_BLOCKER=0`, `LIVE_READINESS_BLOCKER=5`

`READ_ONLY_GO` means the read-only / paper gate is clear. It does not mean
production live trading is ready.

## Legacy Notes

gTrade / Ostium source, sidecars, raw data, registry files, and dedicated tests
were compressed into `archive/gtrade_ostium_legacy_archive_*.zip`. The active
repo tree now uses Trade[XYZ] as the main venue path.
