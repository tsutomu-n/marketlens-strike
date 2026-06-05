<!--
作成日: 2026-05-26_19:07 JST
更新日: 2026-06-05_18:12 JST
-->

# marketlens-strike implementation planning docs

## 結論

この `plan/` は、historical planning record と implementation handoff を残す場所です。

現行コードでは PR-00〜PR-08 の migration code/test surface は完了済みです。Trade[XYZ] real data / backtest 関連の top-level plan も、実装順序、判断、acceptance、handoff を確認するための履歴資料です。current status は `docs/CURRENT_STATE.md`、`docs/CODE_STATUS.md`、`docs/OPERATIONS_RUNBOOK.md`、生成済み manifest を先に読んでください。

## Historical read order

1. `plan/archive/PR-00_to_PR-08_implementation_plan.md`
2. `plan/archive/PR-00_to_PR-08_TASK_CHAIN.yaml`
3. `plan/archive/PR-00_python_313_migration_plan.md`
4. `plan/archive/PR-00_TASK_CHAIN.yaml`
5. ZIP handoff の `00_READ_ME_FIRST.md`
6. ZIP handoff の `01_CURRENT_REPO_FACTS.md`
7. ZIP handoff の `02_GLOBAL_TARGET_ARCHITECTURE.md`
8. ZIP handoff の `03_DATA_CONTRACTS.md`
9. ZIP handoff の `04_ACCEPTANCE_MATRIX.md`
10. ZIP handoff の `06_FILE_BY_FILE_IMPLEMENTATION_MAP.md`
11. ZIP handoff の `pr_specs/PR-00_*.md` から順番に読む

## Trade[XYZ] historical plans

Top-level Trade[XYZ] plan docs are not current truth. Use them only for implementation history and handoff context.

- `plan/TRADE_XYZ_BACKTEST_V0_1_2_REAL_DATA_HARDENING_PLAN_REV5.md`
- `plan/TRADE_XYZ_DATA_COLLECTION_EXPANSION_IMPLEMENTATION_PLAN_2026-06-01.md`
- `plan/TRADE_XYZ_AFTER_WS_SMOKE_DATA_READY_PLAN_2026-06-01.md`
- `plan/TRADE_XYZ_BACKTEST_REAL_DATA_INGESTION_HANDOFF_2026-06-01.md`
- `plan/TRADE_XYZ_WS_TO_BACKTEST_INGESTION_FINAL_PLAN_2026-06-04.md`
- `plan/archive/TRADE_XYZ_BACKTEST_V0_1_1_REAL_DATA_STABILIZATION_PLAN_REV4.md`

## Source inputs

- ZIP: `/home/tn/projects/marketlens-strike/.tmp/marketlens_strike_pr0_pr8_implementation_handoff_v3.zip`
- 展開先: `/home/tn/projects/marketlens-strike/.tmp/marketlens_strike_pr0_pr8_implementation_handoff_v3/marketlens_strike_pr0_pr8_implementation_handoff_v2`
- 現行repo: `/home/tn/projects/marketlens-strike`

## Historical confirmed facts

- `src/sis/cli.py` は現行repoに存在するため、PR-00で CLI entrypoint 復旧は不要。
- `scripts/check` は `uv sync --dev --locked` を実行する。
- PR-00開始時点では `uv.lock` に Python 3.14 前提の metadata が残っていたため、PR-00の編集対象に含めた。
- この環境の `uv 0.10.6` は `uv lock --python <PYTHON>` に対応している。
- `/usr/bin/python3.13` が利用可能。

## Historical planning boundary

全体方針:

- PRは PR-00 から PR-08 まで順番に進める。
- PR-00〜PR-02を飛ばしてTrade[XYZ]実装へ入らない。
- PR-08より前にlive write pathを追加しない。
- `docs/live_evidence_reports/` などのhistorical artifactはPR-00のruntime migration対象外として扱う。

PR-00の対象:

- Python runtime version alignment
- lockfile regeneration
- CI setup Python version
- `scripts/check` runtime visibility
- active docs の Python version 表記

PR-00で扱わず、PR-01以降で扱うもの:

- Trade[XYZ] / HIP-3 collector 実装
- gTrade / Ostium archive
- schema v2 migration
- sidecar design changes
- live order / micro live canary
- historical generated artifact rewrite

上記のうち、PR-01以降で対象になるものは `plan/archive/PR-00_to_PR-08_implementation_plan.md` にPR別に定義する。
