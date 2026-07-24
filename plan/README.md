<!--
作成日: 2026-05-26_19:07 JST
更新日: 2026-07-25_00:56 JST
-->

# marketlens-strike Planning Records

## 結論

`plan/` は current proof ではなく、planning record と historical implementation handoff を残す場所です。

現在の status、readiness、実装有無は、code、tests、schemas、configs、scripts、CLI help、current docs を先に確認します。

## Current-Compatible Entries

| 目的 | 入口 |
|---|---|
| 現在の方向性 | `docs/CURRENT_GOAL_AND_DIRECTION_2026-07-05.md` |
| current docs index | `docs/CURRENT_DOCS_INDEX_2026-07-05.md` |
| 実装済み surface map | `docs/IMPLEMENTED_SURFACES.md` |
| SCR論文の価値抽出判断と最小検証指示 | `docs/plans/SCR_VALUE_EXTRACTION_MINIMUM_EXPERIMENT_2026-07-25.md` |
| Strategy Feedback / Case Index 旧 active package summary | `plan/2026-06-22-strategy-feedback-case-index/README.md` |

## Historical Planning Records

Historical plan packages live under `plan/archive/`. They may contain old branch names, old HEAD values, fixed pass counts, artifact snapshots, and completed implementation contracts.

Use them only for implementation history after checking current code and CLI help.

The former active `plan/2026-06-22-strategy-feedback-case-index/` package was reduced to a short current summary. Its 00-33 dogfood logs, completion audit, and `TASK_CHAIN.yaml` are now under `plan/archive/2026-07-05-strategy-feedback-case-index-history/`.

## Boundaries

Planning records do not authorize:

- credentialed network probe
- paper order
- live order
- wallet
- signing
- exchange write
- schema widening
- production deployment
- dependency change

## Verification

```bash
uv run python scripts/check_current_docs.py
uv run sis --help
```
