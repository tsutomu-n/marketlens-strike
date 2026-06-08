<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# Layer 2.2 Acceptance Audit And Exit-Gate Hardening v1

## 結論

このZIPは、Layer 2.2を**これから新規実装するための計画**ではない。  
現在のRepoには、すでにLayer 2.2 DAG foundationとExit Gate Review Harnessが実装済みである。したがって今回の目的は、**既存実装の受入監査、Exit Gate意味論の曖昧さ除去、2.3へ進めるかの判定**に絞る。

## つまりどうするか

```text
旧判断:
  v2 ZIP + v5 ZIPをそのままコーダーへ渡して実装

新判断:
  旧ZIPは historical design background として読む。
  現Repoの code/tests/schemas/config/CLI help を正本にする。
  既存2.2実装の受入監査と exit_gate.py の意味論ハードニングだけを行う。
```

## 読む順番

```text
README.md
01_GOAL.md
02_SCOPE_AND_BOUNDARIES.md
03_CURRENT_REPO_CONTEXT.md
04_FINDINGS_AND_DECISIONS.md
05_TASKS.md
06_ACCEPTANCE.md
07_TARGET_FILE_MAP.md
08_TEST_PLAN.md
09_RISK_AND_STOP_CONDITIONS.md
10_IMPLEMENTER_CHECKLIST.md
appendices/A_EXIT_GATE_DECISION_MATRIX.md
appendices/B_TEST_FIXTURE_PLAN.md
appendices/C_CODER_HANDOFF_PROMPT.md
appendices/D_PREVIOUS_ZIP_ROUTING.md
```

## 最重要境界

今回やること:

```text
- 現行Layer 2.2 CLIの受入確認
- existing code truthの確認
- exit_gate.pyのdecision/freeze意味論監査
- second_review_required=trueとAPPROVE_2_3の矛盾可能性の除去
- tests/researchの追加・修正
- 必要ならdocs/research/ndx/09_LLM_REVIEW_GATE.mdの最小更新
```

今回やらないこと:

```text
- Layer 2.2 foundationの作り直し
- v2/v5 ZIPの全面再実装
- feature panel
- Open Gap Residual計算
- residual model
- neutralization
- Strategy Lab export
- strategy_signals.parquet生成
- backtest
- paper candidate
- PaperIntentPreview
- live order
- external API
- credentials
- dependency追加
```
