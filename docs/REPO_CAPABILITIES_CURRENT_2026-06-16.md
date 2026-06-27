<!--
作成日: 2026-06-16_06:46 JST
更新日: 2026-06-27_23:14 JST
-->

# Repo Capabilities Current

## 結論

この文書は、`marketlens-strike` で現在使える主要 capability の短い入口です。実装の正本は `src/`、`tests/`、`schemas/`、`configs/`、`scripts/`、CLI help、CI、lockfile です。固定の pass count、古い artifact snapshot、過去の plan 文言は current proof として扱いません。

旧 1387 行版は historical detail として [archive/2026-06-23-doc-triage/REPO_CAPABILITIES_CURRENT_2026-06-16_FULL.md](archive/2026-06-23-doc-triage/REPO_CAPABILITIES_CURRENT_2026-06-16_FULL.md) に移動済みです。

## 現在できること

| 領域 | 現行入口 | 実装正本 |
|---|---|---|
| 全体現在地 | [CURRENT_STATE.md](CURRENT_STATE.md) | `src/`, `tests/`, `schemas/`, `uv run sis --help` |
| 実装済み surface | [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) | `src/sis/commands/`, `src/sis/cli.py`, `tests/` |
| CLI catalog | [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) | `uv run sis --help`, `uv run python scripts/check_cli_catalog.py` |
| Strategy Lab / Authoring | [strategy_research_lab/README.md](strategy_research_lab/README.md) | `src/sis/research/strategy_lab/`, `tests/strategy_authoring/` |
| Backtest | [backtest/README.md](backtest/README.md), `strategy-backtest-html-report` | `src/sis/backtest/`, `tests/backtest/`, `tests/strategy_authoring/` |
| Strategy Review | [strategy_review/README.md](strategy_review/README.md) | `src/sis/strategy_review/`, `schemas/strategy_review_manifest.v1.schema.json` |
| Strategy Operations first slices | [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md) | `src/sis/strategy_*`, `schemas/strategy_*.json`, `tests/strategy_*` |
| Crypto Perp Truth-Cycle | [runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md) | `src/sis/crypto_perp/`, `tests/crypto_perp/`, `schemas/crypto_perp_*.json` |
| NDX research gates | [research/ndx/README.md](research/ndx/README.md) | `configs/research_layer_2_2/ndx/`, `src/sis/research/`, `tests/` |
| Trade[XYZ] read-only / backtest | [runbooks/TRADE_XYZ_RUNBOOK.md](runbooks/TRADE_XYZ_RUNBOOK.md), [backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md](backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md) | `src/sis/venues/trade_xyz/`, `src/sis/backtest/trade_xyz/`, `tests/` |
| Operations / audit / remediation | [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md), [runbooks/README.md](runbooks/README.md) | `src/sis/commands/`, `src/sis/tracking/`, `tests/` |

## 誤読してはいけない境界

- `PASS`、`READY_FOR_HUMAN_REVIEW`、`READ_ONLY_GO`、`PAPER_OBSERVATION_CANDIDATE` は、alpha proof、paper execution permission、live readiness、account readiness、wallet readiness、exchange-write readiness ではない。
- Strategy Review、Strategy Case、Daily Brief、Workbench Viewer は existing artifact を読んで human review を助ける仕組みであり、注文許可ではない。
- Crypto Perp の tiny live measurement、credentialed account probe、order preview は別の明示承認と安全条件なしに実行しない。
- Trade[XYZ] は実装済み venue surface だが、標準の開発主軸は backtest-first / venue-neutral。
- `data/` は runtime / generated state であり、fresh checkout では存在や鮮度を再確認する。

## 確認コマンド

```bash
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

## 関連資料

- 非技術者向け: [APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md](APP_USER_GUIDE_NON_TECHNICAL_2026-06-20.md)
- 詳細な現状説明: [APP_CURRENT_STATE_DETAILED_2026-06-20.md](APP_CURRENT_STATE_DETAILED_2026-06-20.md)
- 実務的な次方向: [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md)
- docs triage: [CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md](CURRENT_DOCS_AND_STRUCTURE_TRIAGE_2026-06-27.md)
