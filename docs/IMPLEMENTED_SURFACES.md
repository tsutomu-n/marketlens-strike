<!--
作成日: 2026-06-17_06:32 JST
更新日: 2026-06-17_09:18 JST
-->

# Implemented Surfaces

この文書は現行コードで使える主要 surface を読むための入口です。詳細な capability catalog は [REPO_CAPABILITIES_CURRENT_2026-06-16.md](REPO_CAPABILITIES_CURRENT_2026-06-16.md) を読む。

## 結論

現在の主軸は backtest-first / venue-neutral。実装済み surface は、Strategy Lab / Strategy Authoring / backtest pack / Strategy Review / NDX local research gates / read-only Trade[XYZ] / paper operation / operations audit である。

production live trading、wallet、signing、exchange write は現行 operator path では許可しない。

## Core Runtime

| Surface | Status | Primary Evidence |
|---|---|---|
| Python 3.13 CLI workspace | implemented | `pyproject.toml`, `.python-version`, `uv.lock`, `src/sis/cli.py` |
| aggregate local gate | implemented | `scripts/check`, `uv run python scripts/check_current_docs.py` |
| command registration split | implemented | `src/sis/cli.py`, `src/sis/commands/` |
| current-doc checker | implemented | `scripts/check_current_docs.py` |

## Strategy And Backtest

| Surface | Status | Primary Evidence |
|---|---|---|
| Strategy Research Lab artifact chain | implemented | `src/sis/research/strategy_lab/`, Strategy Lab schemas, `tests/` |
| Strategy Authoring YAML flow | implemented | `strategy-author-*`, `src/sis/research/strategy_lab/authoring/`, `tests/strategy_authoring/` |
| Strategy backtest suite / comparison / robustness artifacts | implemented | `strategy-backtest-suite`, `strategy-backtest-compare`, `strategy-backtest-stress`, `strategy-backtest-regime-split`, `strategy-backtest-rolling-stability`, `strategy-backtest-benchmark-relative` |
| Strategy backtest pack and validation | implemented | `strategy-backtest-pack`, `strategy-backtest-pack-validate`, `schemas/strategy_backtest_pack*.json`, `docs/backtest/` |
| optional framework surfaces | implemented as optional / no-live | `strategy-backtest-framework-run`, `vectorbt`, `bt`, `metrics`, `reports` optional extras |
| Strategy Lifecycle review | implemented as local artifact review | `strategy-backtest-acceptance`, `strategy-paper-observation-cycle`, `strategy-lifecycle-review`, `docs/strategy_lifecycle/` |
| Strategy Review packet / operator decision record | implemented as read-only human-review packet plus non-permission decision artifact | `strategy-review-build`, `strategy-review-record`, `src/sis/strategy_review/`, `schemas/strategy_review_manifest.v1.schema.json`, `schemas/operator_strategy_review.v1.schema.json`, `tests/strategy_review/`, `docs/strategy_review/` |

## NDX Research Gates

| Surface | Status | Primary Evidence |
|---|---|---|
| Layer 2.2 DAG foundation | implemented local-only | `research-layer22-validate`, `research-layer22-export`, `configs/research_layer_2_2/ndx/` |
| Layer 2.2 review harness | implemented manual/local | `research-layer22-review-pack`, `research-layer22-review-import`, `research-layer22-exit-gate` |
| Layer 2.3 preflight / feature panel / residual | implemented fixture-first/local | `research-ndx-source-resolve`, `research-ndx-feature-panel`, `research-ndx-residual`, `research-ndx-diagnostics` |
| Layer 2.4 residual validation | implemented local gate | `research-ndx-residual-validate`, `schemas/ndx_residual_validation*.json` |
| Layer 2.5-2.8 paper-observation path | implemented local artifact gates | `research-ndx-strategy-lab-export`, `research-ndx-paper-observation-gate`, `research-ndx-operator-promotion`, `research-ndx-paper-observation-review` |

NDX approvals do not prove alpha, backtest readiness, paper readiness, live readiness, account readiness, wallet readiness, or exchange-write readiness.

## Venue / Execution / Operations

| Surface | Status | Primary Evidence |
|---|---|---|
| Trade[XYZ] registry / quote collection / normalization | implemented read-only | `collect-trade-xyz-*`, `src/sis/venues/trade_xyz/`, `tests/test_trade_xyz_*` |
| Trade[XYZ] data readiness / phase gate | implemented read-only | `validate-artifacts`, `phase-gate-review`, `trade-xyz-collection-status` |
| Trade[XYZ] pure backtest v0.1 | implemented Python API, no public CLI | `src/sis/backtest/engine/`, `src/sis/backtest/trade_xyz/`, `tests/backtest/` |
| Bitget demo smoke | implemented local/mock-first | `bitget-demo-smoke`, `src/sis/execution/bitget_demo_adapter.py` |
| paper operations | implemented paper/read-only | `paper-step`, `paper-from-intents`, `paper-report`, `paper-operations-cycle` |
| operations / audit / remediation surfaces | implemented | `operations-dashboard`, `operations-bundle`, `audit-*`, `remediation-*`, `current-state-index`, `readiness-snapshot` |

## Known Boundaries

- `VenueId` currently allows `trade_xyz` and `bitget_demo`.
- `bitget_futures` and `hyperliquid_perp` are catalog-only / disabled for current Strategy Lab schemas.
- `bitget_demo` is a demo execution surface, not production Bitget readiness.
- `PaperIntentPreview` is paper-only and requires revalidation before paper flow use.
- `strategy-review-build` creates review artifacts only. `strategy-review-record` records human decisions against those artifacts. Neither authorizes paper execution or live trading.
- `READ_ONLY_GO` is not live trading ready.
- `data/` is git-ignored runtime state and may be absent in a fresh checkout.

## Verification

```bash
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```
