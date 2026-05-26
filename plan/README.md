# marketlens-strike implementation planning docs

## 結論

この `plan/` は、PR-00〜PR-08 migration の historical planning record です。

現行コードでは PR-00〜PR-08 の migration code/test surface は完了済みです。この directory は、当時の実装順序、判断、acceptance を確認するために残します。current status は `docs/CURRENT_STATE.md` と `docs/CODE_STATUS.md` を先に読んでください。

## Historical read order

1. `plan/PR-00_to_PR-08_implementation_plan.md`
2. `plan/PR-00_to_PR-08_TASK_CHAIN.yaml`
3. `plan/PR-00_python_313_migration_plan.md`
4. `plan/PR-00_TASK_CHAIN.yaml`
5. ZIP handoff の `00_READ_ME_FIRST.md`
6. ZIP handoff の `01_CURRENT_REPO_FACTS.md`
7. ZIP handoff の `02_GLOBAL_TARGET_ARCHITECTURE.md`
8. ZIP handoff の `03_DATA_CONTRACTS.md`
9. ZIP handoff の `04_ACCEPTANCE_MATRIX.md`
10. ZIP handoff の `06_FILE_BY_FILE_IMPLEMENTATION_MAP.md`
11. ZIP handoff の `pr_specs/PR-00_*.md` から順番に読む

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

上記のうち、PR-01以降で対象になるものは `plan/PR-00_to_PR-08_implementation_plan.md` にPR別に定義する。
