# Documentation Audit 2026-05-31 Backtest Update

コード、tests、CLI help、current docs lint を正として、Trade[XYZ] pure backtest v0.1 の main merge 後に必要な docs 更新を整理した。

## 結論

Trade[XYZ] pure backtest v0.1 は main に実装済み。既存 current docs は Strategy Authoring 完了時点の内容が中心で、新しい pure backtest surface を説明していなかったため、backtest専用docsと current docs の導線を追加した。

## Code Truth

対象コード:

- `src/sis/backtest/engine/`
- `src/sis/backtest/trade_xyz/`
- `tests/backtest/`

現行入口:

- `sis.backtest.engine.runner.run_backtest()`

公開されていないもの:

- `sis backtest-trade-xyz ...` のような public CLI
- live order
- wallet / signing / exchange write
- MT5 / IC Markets / CFD

## Updated Docs

- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/backtest/README.md`
- `docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md`
- `scripts/check_current_docs.py`

## Historical Docs

以下は current truth ではなく背景資料として読む。

- `資料/TRADE_XYZ_BACKTEST_ENGINE_V0_1_IMPLEMENTATION_PLAN_REV3 (1).md`
- `資料/TRADE_XYZ_BACKTEST_ENGINE_V0_1_IMPLEMENTATION_PLAN_REV2 (1).md`
- `資料/0531-repo/TRADE_XYZ_BACKTEST_REPO_BRIEF.md`
- `資料/0531-repo/TRADE_XYZ_BACKTEST_INTAKE_ADDENDUM.md`
- `資料/0531-backtest-oss.md`

## Verification

2026-05-31 main:

- `uv run pytest -q tests/backtest`: 54 passed
- `./scripts/check`: 650 passed
- `uv run python scripts/check_current_docs.py`: checked 81 current docs

## Current Read Rules

- `docs/backtest/README.md` を backtest surface の入口にする。
- `uv run sis build-backtest` は既存 bridge 系 command として扱う。
- `strategy-author-run --through backtest` は Strategy Authoring fixed-horizon paper-only 評価として扱う。
- Trade[XYZ] pure backtest v0.1 は Python API の `run_backtest()` を入口にする。
- `READ_ONLY_GO` を production live ready と読まない。
- pure backtest artifact を live order artifact と読まない。
