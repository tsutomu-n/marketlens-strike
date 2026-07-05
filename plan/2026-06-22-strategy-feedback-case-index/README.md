<!--
作成日: 2026-07-05_11:55 JST
更新日: 2026-07-05_11:55 JST
-->

# Strategy Feedback Case Index Current Summary

## 結論

この folder は current proof ではなく、旧 active plan package の互換入口です。

2026-06-22 の implementation contract、00-33 の dogfood loop logs、completion audit、`TASK_CHAIN.yaml` は historical implementation context として `plan/archive/2026-07-05-strategy-feedback-case-index-history/` へ移動しました。

現行判断では code、schemas、tests、CLI help、domain README を先に読む。

## Current Surfaces

| 目的 | 読むもの |
|---|---|
| Strategy Input Contract | `docs/strategy_inputs/README.md` |
| Runtime Observation | `docs/strategy_runtime_observation/README.md` |
| Strategy Learning | `docs/strategy_learning/README.md` |
| Case Lite | `docs/strategy_case_lite/README.md` |
| Case Index | `docs/strategy_case_index/README.md` |
| Workbench Viewer | `docs/strategy_workbench_viewer/README.md` |
| 現在の方向性 | `docs/CURRENT_GOAL_AND_DIRECTION_2026-07-05.md` |

## Boundary

この summary は paper bridge、credentialed network probe、demo order lifecycle、production schema widening、wallet、signing、exchange write、live order を許可しません。

## Verification

```bash
uv run python scripts/check_current_docs.py
uv run sis --help
```
