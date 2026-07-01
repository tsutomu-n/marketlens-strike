<!--
作成日: 2026-06-17_06:32 JST
更新日: 2026-07-01_20:42 JST
-->

# Migration History

この文書は `marketlens-strike` の実装履歴を読むための一覧です。現在の機能面は [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) を読む。

## PR-00 To PR-08

| PR | Title | Status | Evidence |
|---|---|---|---|
| PR-00 | Python 3.13 migration | DONE | `pyproject.toml`, `.python-version`, `uv.lock`, `.github/workflows/ci.yml`, `scripts/check` |
| PR-01 | Archive legacy venues | DONE | active legacy file tree removed, root `/archive/` ignored for optional local packages, `package.json` legacy note, `pyproject.toml` without `ostium-python-sdk` |
| PR-02 | Generalize models and schemas | DONE | `src/sis/models.py`, `schemas/`, `configs/*.yaml`, `configs/instrument_registry.seed.json` |
| PR-03 | Build Trade[XYZ] universe mapping | DONE | `src/sis/venues/trade_xyz/registry.py`, `src/sis/venues/trade_xyz/report.py`, `tests/test_trade_xyz_registry.py`, `perpDexs` fallback |
| PR-04 | Add Trade[XYZ] read-only collector | DONE | `src/sis/venues/trade_xyz/collector.py`, `src/sis/venues/trade_xyz/normalizer.py`, `tests/test_trade_xyz_collector.py` |
| PR-05 | Add real market data layer | DONE | `src/sis/real_market/`, `tests/test_real_market_models.py`, `tests/test_real_market_quality.py`, `tests/test_real_market_features.py` |
| PR-06 | Add real vs venue tracking | DONE | `src/sis/tracking/`, `tests/test_tracking_models.py`, `tests/test_real_vs_venue_tracking.py`, `tests/test_lead_lag.py` |
| PR-07 | Gate paper execution by venue quality | DONE | `src/sis/paper/`, `src/sis/core/execution_plan.py`, `tests/test_paper_trading.py`, `tests/test_paper_runner.py` |
| PR-08 | Add Trade[XYZ] micro live safety canary | DONE | `src/sis/execution/trade_xyz_adapter.py`, `src/sis/execution/live_order_policy.py`, `src/sis/execution/micro_live_canary.py`, PR-08 tests |

## Post-PR08 / PR9a-PR12

| Slice | Status | Evidence |
|---|---|---|
| PR9a CLI import recovery | DONE | `uv run sis --help`, `uv run python -m sis.cli --help` |
| PR9b HIP-3 mapping and contexts | DONE | `perpDexs` asset-id fallback, `metaAndAssetCtxs` enrichment, `tests/test_trade_xyz_registry.py` |
| PR9c fresh quote window | DONE | `collect-trade-xyz-quotes --duration-minutes --interval-seconds --write-summary --write-report` |
| PR10 strict validation and diagnostics | DONE | `validate-artifacts --strict`, `diagnose-quotes --venue trade_xyz`, `tests/test_validate_artifacts_trade_xyz.py` |
| PR11 operations cutover | DONE | `phase-gate-review` consumes Trade[XYZ] artifacts and emits `READ_ONLY_GO` / `CONDITIONAL_INDEX_ONLY` / `NO_GO` |
| PR12 fresh read-only smoke | DONE | `data/ops/pr12_fresh_read_only_smoke_summary.json`, `data/reports/pr12_fresh_read_only_smoke_report.md` |
| P2 gate restore / fee mode resolution | DONE | `configs/fee_model.trade_xyz.yaml`, `tests/test_trade_xyz_registry.py`, `tests/test_trade_xyz_collector.py`, `tests/test_phase_gate_review.py` |
| P2 execution drift classification | DONE | `src/sis/reports/phase_gate_review.py`, `phase-gate-review` artifact summary |
| P2 Alpaca provider stub removal | DONE | `src/sis/real_market/providers/alpaca.py`, `tests/test_alpaca_provider.py` |

## Post-Pivot Implementation Groups

| Group | Status | Evidence |
|---|---|---|
| Strategy Research Lab schemas/models | DONE | `src/sis/research/strategy_lab/`, `src/sis/research_protocol/`, Strategy Lab schemas |
| Strategy Lab paper-only workflow | DONE | `strategy-preview`, `strategy-experiment-run`, `evaluate-strategy-lab`, `build-paper-candidate-pack`, `promotion-decision`, `build-paper-intent-preview`, `paper-from-intents` |
| Strategy Authoring YAML workflow | DONE | `strategy-author-init`, `strategy-author-validate`, `strategy-author-explain`, `strategy-author-run`, `strategy-author-train-model`, `strategy-author-bundle-run`, `tests/strategy_authoring/` |
| Trade[XYZ] pure backtest v0.1 | DONE / CLI not public | `src/sis/backtest/engine/`, `src/sis/backtest/trade_xyz/`, `tests/backtest/`, `docs/backtest/` |
| Strategy Lifecycle control plane | DONE / local artifact review and status only | `strategy-backtest-acceptance`, `strategy-paper-observation-cycle`, `strategy-lifecycle-review`, `strategy-paper-observation-status`, `docs/strategy_lifecycle/` |
| Strategy Backtest pack and optional framework surfaces | DONE | `strategy-backtest-pack`, `strategy-backtest-pack-validate`, `strategy-backtest-framework-run`, optional extras in `pyproject.toml` |
| NDX Layer 2.2-2.8 local gates | DONE | `research-layer22-*`, `research-ndx-*`, `docs/research/ndx/`, `tests/research/` |
| Strategy Review builder | DONE | `strategy-review-build`, `src/sis/strategy_review/`, `schemas/strategy_review_manifest.v1.schema.json`, `tests/strategy_review/`, `docs/strategy_review/` |

## Verification

この文書には古い pass count を固定しない。履歴の実装状態を疑う場合は、現在の code と tests を再確認する。

```bash
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```

## Boundaries

- migration `DONE` は live trading ready を意味しない。
- micro live は code / test safety surface であり、標準 operator CLI live execution ではない。
- Trade[XYZ] pure backtest v0.1 は Python API surface。public CLI は separate legacy / bridge command と混同しない。
- NDX Layer 2.2-2.8 は local artifact gates。external API、wallet、signing、exchange write、production live trading を許可しない。
