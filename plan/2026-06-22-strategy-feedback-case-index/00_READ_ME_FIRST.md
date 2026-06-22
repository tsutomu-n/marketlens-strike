<!--
作成日: 2026-06-22_17:55 JST
更新日: 2026-06-22_20:28 JST
-->

# Strategy Feedback And Case Index Plan

## 結論

このフォルダーは、現行コードを正として未実装分を実装するための active implementation plan です。コーダーはこの順番で読みます。

1. [01_IMPLEMENTATION_CONTRACT.md](01_IMPLEMENTATION_CONTRACT.md)
2. [02_TASKS.md](02_TASKS.md)
3. [03_FILE_MAP.md](03_FILE_MAP.md)
4. [04_TEST_AND_ACCEPTANCE.md](04_TEST_AND_ACCEPTANCE.md)
5. [05_RISKS_AND_BOUNDARIES.md](05_RISKS_AND_BOUNDARIES.md)
6. [06_DEFERRED_WORK_AND_ENTRY_CRITERIA.md](06_DEFERRED_WORK_AND_ENTRY_CRITERIA.md)
7. [07_IMPLEMENTABLE_REMAINING_RISK_DETAIL.md](07_IMPLEMENTABLE_REMAINING_RISK_DETAIL.md)
8. [08_USER_INPUTS_AND_PROVISION_GUIDE.md](08_USER_INPUTS_AND_PROVISION_GUIDE.md)
9. [09_LOCAL_DOGFOOD_EXISTING_ARTIFACT_INVENTORY.md](09_LOCAL_DOGFOOD_EXISTING_ARTIFACT_INVENTORY.md)
10. [10_LOCAL_DOGFOOD_LOOP_01_PLAN_REVIEW_RESULTS.md](10_LOCAL_DOGFOOD_LOOP_01_PLAN_REVIEW_RESULTS.md)
11. [11_LOCAL_DOGFOOD_LOOP_02_SOURCE_CONTRACT_RESULTS.md](11_LOCAL_DOGFOOD_LOOP_02_SOURCE_CONTRACT_RESULTS.md)
12. [12_LOCAL_DOGFOOD_LOOP_03_TREND_PULLBACK_RESULTS.md](12_LOCAL_DOGFOOD_LOOP_03_TREND_PULLBACK_RESULTS.md)
13. [13_LOCAL_DOGFOOD_LOOP_04_CASE_LITE_BACKTEST_ARTIFACT_RESULTS.md](13_LOCAL_DOGFOOD_LOOP_04_CASE_LITE_BACKTEST_ARTIFACT_RESULTS.md)
14. [14_LOCAL_DOGFOOD_LOOP_05_INPUT_FEEDBACK_BOUNDARY_RESULTS.md](14_LOCAL_DOGFOOD_LOOP_05_INPUT_FEEDBACK_BOUNDARY_RESULTS.md)
15. [15_LOCAL_DOGFOOD_LOOP_06_PLAN_ALIGNMENT_RESULTS.md](15_LOCAL_DOGFOOD_LOOP_06_PLAN_ALIGNMENT_RESULTS.md)
16. [16_LOCAL_DOGFOOD_LOOP_07_VERIFICATION_RESULTS.md](16_LOCAL_DOGFOOD_LOOP_07_VERIFICATION_RESULTS.md)
17. `TASK_CHAIN.yaml`

この計画で作るものは、Strategy Operations の次の小さい実装単位です。

- Strategy Runtime Observation / Strategy Learning Event から、Strategy Input Contract の更新候補を作る。
- 作った候補は自動適用せず、人間レビュー用 artifact として止める。
- Strategy Case Lite の複数 artifact を index 化し、既存 Static Workbench Viewer で見やすくする。

## この計画で作らないもの

次は未実装または承認待ちの別計画です。この計画に混ぜません。

- paper bridge validation
- credentialed Bitget / Hyperliquid read-only network probe
- Bitget demo order lifecycle
- production venue schema widening
- wallet、signing、exchange write
- live order、production live trading、automatic trading daemon
- Svelte UI または常駐サーバー UI
- Strategy Case の完全 registry / DB / merge workflow

## 根拠として読む現行ドキュメント

- [docs/NEXT_DIRECTION_CURRENT.md](../../docs/NEXT_DIRECTION_CURRENT.md)
- [docs/IMPLEMENTED_SURFACES.md](../../docs/IMPLEMENTED_SURFACES.md)
- [docs/strategy_inputs/README.md](../../docs/strategy_inputs/README.md)
- [docs/strategy_runtime_observation/README.md](../../docs/strategy_runtime_observation/README.md)
- [docs/strategy_learning/README.md](../../docs/strategy_learning/README.md)
- [docs/strategy_case_lite/README.md](../../docs/strategy_case_lite/README.md)
- [docs/strategy_workbench_viewer/README.md](../../docs/strategy_workbench_viewer/README.md)

## 実行前提

- まず `git status --short --branch` で `main` が clean か確認する。
- CLI surface は `uv run sis --help` を正とする。
- schema / model / docs の実装済み事実は、既存 code、tests、schemas、CLI help を優先する。
- 作業中に既存 docs と code が衝突した場合、code / tests / schemas / CLI help を優先し、この plan を必要最小限で更新する。
