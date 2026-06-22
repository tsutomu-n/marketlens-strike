<!--
作成日: 2026-05-26_19:07 JST
更新日: 2026-06-22_17:16 JST
-->

# marketlens-strike implementation planning docs

## 結論

この `plan/` は、historical planning record と implementation handoff を残す場所です。

現行コードでは PR-00〜PR-08 の migration code/test surface は完了済みです。Trade[XYZ] real data / backtest 関連の top-level plan、2026-06-07 の Layer 2.2 plan pack、2026-06-08 の Layer 2.2 acceptance hardening plan、2026-06-08 の Layer 2.3 NDX preflight / feature residual plan は、実装順序、判断、acceptance、handoff を確認するための履歴資料です。current status の正本ではありません。current status は `docs/CURRENT_STATE.md`、`docs/CODE_STATUS.md`、`docs/IMPLEMENTED_SURFACES.md`、`docs/research/ndx/README.md`、`docs/OPERATIONS_RUNBOOK.md`、生成済み manifest を先に読んでください。

重要: `plan/marketlens_strategy_research_lab_migration_pack/` は historical migration contract です。`execution_venue: Literal["trade_xyz"]` のような記述は当時の実装前契約であり、現在の contract ではありません。現在の venue contract は code/schema の `trade_xyz`, `bitget_demo` です。

## 2026-06-09 venue plans

No 2026-06-09 venue plan remains a current unimplemented root plan. Code,
tests, schemas, CLI help, and docs are the source of truth.

Implemented / historical:

- `plan/archive/2026-06-17-plan-routing/0609ここからの計画/01_ndx_qqq_venue_suitability_gate/`
- `plan/archive/2026-06-17-plan-routing/0609ここからの計画/02_bitget_hyperliquid_venue_design_gate/`

Implemented / dogfooded / historical:

- `plan/archive/2026-06-17-plan-routing/0609ここからの計画/03_venue_read_only_capability_probe/`

The final decision in that archive is `NO_ACTION`: `venue-read-only-probe` is
implemented and dogfooded as a fixture-first local boundary artifact, but it
does not justify credentialed network probing, paper bridge validation,
Strategy Case registry work, schema widening, paper execution, or live
execution.

## Historical 2026-06-10 review plans

These are historical docs-only review or adoption plans. They do not authorize
code, schema, dependency, paper, or live-execution changes by themselves.

- [plan/archive/2026-06-17-plan-routing/0610ここからの計画/01_grok_architecture_adoption_review/README.md](archive/2026-06-17-plan-routing/0610ここからの計画/01_grok_architecture_adoption_review/README.md)

## Historical 2026-06-16 review builder plan

This implementation handoff now has corresponding code, schema, CLI help,
focused tests, and docs. The Strategy Review Builder turns existing Strategy
Authoring / backtest artifacts into a human review markdown file and a
machine-readable manifest. The follow-up Operator Strategy Review Artifact in
`plan/archive/2026-06-17-plan-routing/ねくすと.md` is also implemented as `strategy-review-record` /
`operator_review.yaml`. Treat this group as historical implementation context,
not as the current unimplemented next action. It does not create a Strategy
Case registry, UI, paper gate, live readiness proof, wallet/signing path, or
exchange-write path.

- [plan/archive/2026-06-17-plan-routing/0616ここからの計画/01_strategy_review_builder/README.md](archive/2026-06-17-plan-routing/0616ここからの計画/01_strategy_review_builder/README.md)
- [plan/archive/2026-06-17-plan-routing/STRATEGY_REVIEW_CONTRACT_AND_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md](archive/2026-06-17-plan-routing/STRATEGY_REVIEW_CONTRACT_AND_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md)
- [plan/archive/2026-06-17-plan-routing/STRATEGY_REVIEW_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md](archive/2026-06-17-plan-routing/STRATEGY_REVIEW_NEXT_IMPLEMENTATION_PLAN_2026-06-16.md)
- [plan/archive/2026-06-17-plan-routing/ねくすと.md](archive/2026-06-17-plan-routing/ねくすと.md)

## Current Direction

現行 repo truth から見た実務的な次方向は
[`docs/NEXT_DIRECTION_CURRENT.md`](../docs/NEXT_DIRECTION_CURRENT.md) を読む。
`計画あり` は `実装決定` ではなく、`catalog known` は `venue enabled` ではない。

## Historical implemented 2026-06-20 Crypto Perp Truth-Cycle MVP Plan

Crypto Perp の implementation handoff は [archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/00_READ_ME_FIRST.md](archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/00_READ_ME_FIRST.md) に archive 済みです。これは旧 `Crypto Perp Personal Edge Lab Implementation Plan`、旧 `marketlens-strike-crypto-perp-personal-edge-plan-2026-06-20.zip`、旧 CP-00〜CP-10 をそのまま実装する指示を置き換えた historical implementation contract です。

実装順は [archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/07_TASK_CHAIN.yaml](archive/2026-06-22-crypto-perp-mvp-implemented/marketlens-strike-crypto-perp-mvp-final-plan-2026-06-20/07_TASK_CHAIN.yaml) の M00-M11 として完了済みです。現行の日常運用は `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`、`docs/IMPLEMENTED_SURFACES.md`、CLI help、生成 artifact を先に読みます。M09 の実ネットワーク live measurement は別の明示承認が必要です。

この plan は production live trading、全銘柄 L2 常時保存、Strategy Lab v2 全面移行、Svelte UI 先行、ML/LLM optimizer 先行、reference venue 先行実装、自動戦略発注 daemon、通常 CI での network 使用、secret の log / artifact 保存を許可しない。

## Current Strategy Operations First Slices

Strategy Input Contract / Idea Intake first gate と Strategy Review optional source connection は実装済みです。コーダー向けの設計と acceptance は次を読む。

- [../docs/archive/2026-06-22-doc-routing/STRATEGY_INPUT_CONTRACT_AND_IDEA_INTAKE_IMPLEMENTATION_PLAN_2026-06-18.md](../docs/archive/2026-06-22-doc-routing/STRATEGY_INPUT_CONTRACT_AND_IDEA_INTAKE_IMPLEMENTATION_PLAN_2026-06-18.md)

Strategy Stage Policy / Decision first slice、Strategy Paper Smoke Plan first slice、Strategy Runtime Observation Ingest first slice、Paper vs Backtest Drift Review first slice、Strategy Learning / Revision Request / Revision Request Review first slice、Strategy Case Lite、Daily Brief、AI Review、Model Loop、Micro Live Plan、Next Scale Plan、Live Observation、Scale Decision、Static Workbench Viewer も実装済みです。現行の使い方は次を読む。

- [../docs/strategy_stage/README.md](../docs/strategy_stage/README.md)
- [../docs/strategy_paper_smoke/README.md](../docs/strategy_paper_smoke/README.md)
- [../docs/strategy_runtime_observation/README.md](../docs/strategy_runtime_observation/README.md)
- [../docs/strategy_drift_review/README.md](../docs/strategy_drift_review/README.md)
- [../docs/strategy_learning/README.md](../docs/strategy_learning/README.md)
- [../docs/strategy_case_lite/README.md](../docs/strategy_case_lite/README.md)
- [../docs/strategy_daily_brief/README.md](../docs/strategy_daily_brief/README.md)
- [../docs/strategy_ai_review/README.md](../docs/strategy_ai_review/README.md)
- [../docs/strategy_model_loop/README.md](../docs/strategy_model_loop/README.md)
- [../docs/strategy_micro_live_plan/README.md](../docs/strategy_micro_live_plan/README.md)
- [../docs/strategy_next_scale_plan/README.md](../docs/strategy_next_scale_plan/README.md)
- [../docs/strategy_live_observation/README.md](../docs/strategy_live_observation/README.md)
- [../docs/strategy_scale_decision/README.md](../docs/strategy_scale_decision/README.md)
- [../docs/strategy_workbench_viewer/README.md](../docs/strategy_workbench_viewer/README.md)

これらは `Human-in-the-loop Strategy Operations Workbench` の最初の入口、stage decision、paper smoke plan、runtime observation ingest、drift review、learning / revision request / revision request review、case timeline、daily brief、AI review、model / optimizer ledger、micro live plan、next scale plan、live observation、scale decision、static viewer の土台です。Svelte UI、wallet、signing、exchange write、live execution はまだ別計画が必要です。

完成形を実装完了まで閉じるために使った plan は [../docs/archive/2026-06-22-doc-routing/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_PLAN_2026-06-19.md](../docs/archive/2026-06-22-doc-routing/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_PLAN_2026-06-19.md) に archive 済みです。対象ファイル、テスト方針、完了条件は implementation history として読みます。

T0〜T12b の実装証跡と対象外範囲は [../docs/archive/2026-06-22-doc-routing/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_AUDIT_2026-06-19.md](../docs/archive/2026-06-22-doc-routing/STRATEGY_OPERATIONS_WORKBENCH_COMPLETION_AUDIT_2026-06-19.md) を読む。

## Historical 2026-06-10 implementation plans

These implementation handoff plans have corresponding code, schema, tests, CLI
help, and docs. Treat them as implementation history, not current status proof.

- [plan/archive/2026-06-17-plan-routing/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/README.md](archive/2026-06-17-plan-routing/0610ここからの計画/02_ndx_layer25_strategy_lab_research_export/README.md)

## Historical 2026-06-11 implementation plans

These implementation handoff plans for the NDX paper-observation gate and the
strategy lifecycle control plane have corresponding code, schema, tests, CLI
help, and docs. Treat them as implementation history, not current status proof.

- [plan/archive/2026-06-17-plan-routing/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/README.md](archive/2026-06-17-plan-routing/0611ここからの計画/01_ndx_layer26_27_backtest_operator_promotion/README.md)
- [plan/archive/2026-06-17-plan-routing/0611ここからの計画/02_strategy_lifecycle_control_plane/README.md](archive/2026-06-17-plan-routing/0611ここからの計画/02_strategy_lifecycle_control_plane/README.md)
- [plan/archive/2026-06-17-plan-routing/0611ここからの計画/03_paper_observation_cycle_completion/README.md](archive/2026-06-17-plan-routing/0611ここからの計画/03_paper_observation_cycle_completion/README.md)

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

- `plan/archive/2026-06-08-plan-routing/TRADE_XYZ_BACKTEST_V0_1_2_REAL_DATA_HARDENING_PLAN_REV5.md`
- `plan/archive/2026-06-08-plan-routing/TRADE_XYZ_DATA_COLLECTION_EXPANSION_IMPLEMENTATION_PLAN_2026-06-01.md`
- `plan/archive/2026-06-08-plan-routing/TRADE_XYZ_AFTER_WS_SMOKE_DATA_READY_PLAN_2026-06-01.md`
- `plan/archive/2026-06-08-plan-routing/TRADE_XYZ_BACKTEST_REAL_DATA_INGESTION_HANDOFF_2026-06-01.md`
- `plan/archive/2026-06-08-plan-routing/TRADE_XYZ_WS_TO_BACKTEST_INGESTION_FINAL_PLAN_2026-06-04.md`
- `plan/archive/TRADE_XYZ_BACKTEST_V0_1_1_REAL_DATA_STABILIZATION_PLAN_REV4.md`

## NDX historical plans

2026-06-07 Layer 2.2 plan packs, the 2026-06-08 Layer 2.2 acceptance hardening plan, and the 2026-06-08 Layer 2.3 preflight / feature residual plan are implemented historical contracts. Code, configs, schemas, tests, CLI help, and `docs/research/ndx/README.md` remain current status proof.

- `plan/archive/2026-06-08-plan-routing/README.md`
- `plan/archive/2026-06-09-ndx-plan-routing/feature_expansion_plan_20260608_layer_2_2_acceptance_hardening_v1/`
- `plan/archive/2026-06-09-ndx-plan-routing/feature_expansion_plan_20260608_layer_2_3_ndx_preflight_feature_residual_v1/`
- `plan/archive/2026-06-08-plan-routing/0607ここからの計画2/zip_intake_guide/`
- `plan/0607ここからの計画2/*.zip` is ignored by git and treated as historical source packages.
- `plan/0608ここからの計画/feature_expansion_plan_20260608_layer_2_2_acceptance_hardening_v1.zip` is ignored by git and treated as a historical source package.
- `plan/0608ここからの計画/feature_expansion_plan_20260608_layer_2_3_ndx_preflight_feature_residual_v1.zip` is ignored by git and treated as a historical source package.
- `plan/0608ここからの計画/01_layer_2_2_foundation/` and `plan/0608ここからの計画/02_layer_2_2_exit_gate/` contain ignored historical ZIP inputs and are not new implementation instructions.
- `plan/archive/2026-06-08-plan-routing/0607ここからの計画/`
- `plan/archive/2026-06-08-plan-routing/0607ここからの計画2/feature_expansion_plan_20260607/`
- `plan/archive/2026-06-08-plan-routing/0607ここからの計画2/feature_expansion_plan_20260607_layer_2_2_exit_gate_v3_minimal/`
- `plan/archive/2026-06-08-plan-routing/marketlens_strategy_research_lab_migration_pack/`

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
