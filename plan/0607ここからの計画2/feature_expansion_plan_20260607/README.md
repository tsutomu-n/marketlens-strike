<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# Feature Expansion Plan 2026-06-07

## 結論

この計画は、`marketlens-strike` に **Layer 2.2 Research DAG Compiler** を追加するための実装計画 v2 である。

今回の完成扱いは、売買戦略・backtest・paper/live ではない。完成扱いは次の状態に限定する。

```text
HYP-NDX-001 Open Gap Residual を、
Seed → Mechanism Parts → Variable Inventory → Causal Roles → Temporal Availability → Core DAG
まで機械可読な artifact として定義し、
validator / linter / counter-DAG / data-requirements / Mermaid / Markdown report を生成できる。
```

## なぜ v2 か

前回案は方向性としては正しかったが、実装直前計画としては以下が弱かった。

```text
1. NDX / QQQ / NQ の責務分離が不足していた。
2. Nasdaq-100 index methodology 部品が不足していた。
3. Temporal Availability が粗かった。
4. Counter-DAG が少なかった。
5. Linter rule が最低限すぎた。
6. 初期PRで CLI を入れるべきかの判断が曖昧だった。
7. Data Source Contract の粒度が曖昧だった。
```

この v2 では、これらを修正し、コーダーがこのディレクトリだけを読めば実装順・対象ファイル・テスト・停止条件まで分かるようにした。

## 読み順

```text
1. README.md
2. 01_GOAL.md
3. 02_SCOPE_AND_BOUNDARIES.md
4. 03_CURRENT_REPO_CONTEXT.md
5. 04_TASKS.md
6. 05_ACCEPTANCE.md
7. 06_TARGET_FILE_MAP.md
8. 07_TEST_PLAN.md
9. 08_RISK_AND_STOP_CONDITIONS.md
10. 10_IMPLEMENTER_CHECKLIST.md
```

詳細スケッチは `appendices/` を読む。

## 最重要境界

```text
外部API: 使わない
credentials: 使わない
DB schema: 触らない
dependency: 追加しない
backtest: 今回は作らない
paper/live order: 触らない
Trade[XYZ] readiness: 混ぜない
Strategy Lab export: 今回は作らない
```

## 実装フェーズ

```text
Phase A: Layer 0〜2.1 の薄い前段 contract
  A0 Scope / Boundary
  A1 Seed Registry
  A2 Mechanism Parts
  A3 Data Source Contract
  A4 Variable Inventory
  A5 Causal Roles
  A6 Temporal Availability

Phase B: Layer 2.2 Core DAG Compiler
  B0 Core DAG Contract
  B1 Loader / Validator
  B2 Linter Rules v2
  B3 HYP-NDX-001 Core DAG
  B4 Counter-DAG Catalog
  B5 Data Requirements Export
  B6 Report / Mermaid / JSON Export
  B7 Minimal CLI wrappers

Phase C: Deferred
  Feature panel, residual model, neutralization, Strategy Lab export, backtest
```

## 実装者への短い指示

```text
まず Phase A/B だけ実装する。
Feature panel、Open Gap Residual 計算、Neutralization、Strategy Lab export、Backtest、Paper/Live は実装しない。

完成条件は、HYP-NDX-001 Core DAG を validate / lint / export でき、
Core DAG report と Mermaid と data requirements を生成できること。
```
