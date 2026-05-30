# marketlens-strike

`marketlens-strike` は、`Trade[XYZ] / real market / tracking / paper / micro live safety` への migration を実装済みの workspace です。2026-05-28 時点では Trade[XYZ] read-only gate は `READ_ONLY_GO` で、fee mode blocker は解消済みです。

## Read First

1. [docs/CURRENT_STATE.md](/home/tn/projects/marketlens-strike/docs/CURRENT_STATE.md)
2. [docs/CODE_STATUS.md](/home/tn/projects/marketlens-strike/docs/CODE_STATUS.md)
3. [docs/DOCUMENT_AUDIT_2026-05-30.md](/home/tn/projects/marketlens-strike/docs/DOCUMENT_AUDIT_2026-05-30.md)
4. [docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md](/home/tn/projects/marketlens-strike/docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md)
5. [docs/strategy_research_lab/README.md](/home/tn/projects/marketlens-strike/docs/strategy_research_lab/README.md)
6. [docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md](/home/tn/projects/marketlens-strike/docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md)
7. [docs/OPERATIONS_RUNBOOK.md](/home/tn/projects/marketlens-strike/docs/OPERATIONS_RUNBOOK.md)
8. [docs/ARCHITECTURE_AND_PHASES.md](/home/tn/projects/marketlens-strike/docs/ARCHITECTURE_AND_PHASES.md)
9. [docs/trade_xyz_bot_beginner_guide.html](/home/tn/projects/marketlens-strike/docs/trade_xyz_bot_beginner_guide.html)
10. [plan/archive/PR-00_to_PR-08_implementation_plan.md](/home/tn/projects/marketlens-strike/plan/archive/PR-00_to_PR-08_implementation_plan.md) は historical migration contract として読む

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

Strategy Research Lab to paper-only preview:

```bash
uv run sis strategy-preview
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
uv run sis strategy-author-bundle-run --bundle docs/strategy_research_lab/examples/multi_strategy_authoring_bundle.yaml
```

Strategy Lab の schema / artifact flow / paper-only boundary は [docs/strategy_research_lab/README.md](/home/tn/projects/marketlens-strike/docs/strategy_research_lab/README.md) を読む。作戦を作る入口は [docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html](/home/tn/projects/marketlens-strike/docs/algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.html)。今できることの一覧は [docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md](/home/tn/projects/marketlens-strike/docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md)、わかりやすい HTML 版は [docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html](/home/tn/projects/marketlens-strike/docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html)。authoring YAML は entry / hold / close / reduce / add / rebalance / long / short / derived features / column-to-column condition / exclusion-none condition / regime membership filter / regime-specific overrides / paper-only dynamic multi-leg / pair-trade signal / cross-sectional top-bottom / paper-only linear model score / train-model adapter / temporal-cadence control / event-window calendar filters / bracket-OCO lifecycle / opposite-signal exit / explicit close-signal exit / reduce-signal partial exit / add-signal scale-in / rebalance-signal exposure resize / order-style entry / slippage / partial-fill / spread gate / depth-based fill / stop-loss / take-profit / close-signal exit / partial exit / trailing stop / sizing / portfolio exposure limits / risk throttle / volatility targeting / target-weight / inverse-vol allocation / position-state pyramiding controls / parameter sweep / era metrics / multi-strategy bundle / risk-parity allocation の paper backtest に対応する。`data/research/strategy_signals.parquet` が canonical signal artifact で、`data/research/signals.csv` は legacy export。

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
- Strategy Research Lab は `StrategyExperimentSpec` から `PaperIntentPreview` までの研究 / 候補生成 / paper昇格判断 surface を持つ
- `PaperIntentPreview` は paper-only で、live order への変換は禁止
- Strategy Lab の詳細 runtime validation は Pydantic model が正本で、tracked JSON Schema は thin guard として扱う
- wallet secrets, signing, production live trading は未完了
- `data/` は git 管理外

## Current Verification

2026-05-30 code/docs check:

- `./scripts/check`: pass, 426 passed
- `uv run pyrefly check`: pass, 0 errors
- `uv run python scripts/check_current_docs.py`: pass, `checked 74 current docs`

2026-05-28 runtime artifact snapshot:

- `uv run sis validate-artifacts --strict`: `checked_files=12`, `issues=0`
- `uv run sis phase-gate-review`: `READ_ONLY_GO`, `phase2_entry_allowed=true`, `blockers=[]`

## Legacy Notes

gTrade / Ostium の legacy source, sidecar, raw data, registry, 専用テストは `archive/gtrade_ostium_legacy_archive_*.zip` に圧縮済みです。展開済みの file tree は active repo から削除済みで、新規実装の主軸は Trade[XYZ] です。
