<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# Layer 2.3 NDX Preflight / Feature Panel / Open Gap Residual Plan v1

## 結論

この計画は、現Repoの **既存 Layer 2.2 実装** を前提に、次に進むべき **Layer 2.3 NDX Preflight / Feature Panel / Open Gap Residual** を実装するためのコーダー向け資料である。

旧 `feature_expansion_plan_20260607_layer_2_2_v2.zip` や `feature_expansion_plan_20260608_layer_2_2_exit_gate_v5_final.zip` を新規実装指示として使わない。現Repoでは 2.2 DAG foundation と Exit Gate Review Harness は既に存在するため、本計画の目的は **2.2の承認結果を入力に、2.3のデータ化へ安全に進むこと**である。

## このZIPで完成扱いにするもの

```text
1. Layer 2.2 exit decision を確認し、2.3へ進める前提を機械的に検査できる
2. NDX/QQQ/SPY/SMH/VIX/DGS10/mega-cap basket の Data Source Resolution を作れる
3. 外部APIやcredentialsなしのfixture modeで NDX feature panel を生成できる
4. feature_ts / source_ts_max / same-day close 禁止の leakage check を実装できる
5. rolling OLS の最小 residual builder を実装できる
6. open_gap_residuals artifact と manifest を生成できる
7. residual diagnostics / neutralization pre-report を作れる
```

## このZIPで完成扱いにしないもの

```text
- Strategy Lab export
- strategy_signals.parquet 生成
- evaluate-strategy-lab
- backtest
- paper candidate
- PaperIntentPreview
- live order
- external API を前提にした自動運用
- credentials
- provider SDK追加
- NQ futures本格対応
- VXN直接取得
- SOX直接取得
- options / gamma / 0DTE
```

## 読む順番

```text
README.md
01_GOAL.md
02_SCOPE_AND_BOUNDARIES.md
03_CURRENT_REPO_CONTEXT.md
04_START_CONDITIONS.md
05_TASKS.md
06_DATA_SOURCE_RESOLUTION.md
07_FEATURE_PANEL_SPEC.md
08_RESIDUAL_MODEL_SPEC.md
09_DIAGNOSTICS_AND_REFUTATION.md
10_ACCEPTANCE.md
11_TARGET_FILE_MAP.md
12_TEST_PLAN.md
13_RISK_AND_STOP_CONDITIONS.md
14_IMPLEMENTER_CHECKLIST.md
15_CODER_HANDOFF_PROMPT.md
appendices/
```

## 最短指示

```text
このZIPを展開し、まず 04_START_CONDITIONS.md を満たすか確認してください。
2.2 Exit Decision が APPROVE_2_3 で、freeze manifest があり、second_review_required=false でなければ2.3実装へ進まないでください。

条件を満たす場合だけ、05_TASKS.md の T0〜T8 を順番に実装してください。
Strategy Lab export、backtest、paper/live、external API、credentials、dependency追加は今回実装しないでください。
```
