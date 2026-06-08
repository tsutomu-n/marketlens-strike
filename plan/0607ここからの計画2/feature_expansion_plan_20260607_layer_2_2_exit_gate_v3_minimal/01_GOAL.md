<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# 01_GOAL

## 目的

`marketlens-strike` の Layer 2.2 実装完了後に、2.3へ進めるかを判定する **Exit Gate Review Harness** を作る。

## 完成扱い

以下がすべてできたら完成です。

```text
1. completed Layer 2.2 artifact bundle を読み込める
2. deterministic precheck を実行できる
3. LLM review pack を生成できる
4. manual LLM review result JSON を strict import できる
5. review result と pack hash を照合できる
6. finding の evidence_refs を検証できる
7. exit decision を生成できる
8. freeze manifest を生成できる
9. Markdown report を生成できる
10. tests/research が通る
```

## ユーザーにとって使えるようになるもの

ユーザーは、2.2成果物について次の判断を低負荷で行える。

```text
APPROVE_2_3:
  2.3 feature/residual builder 設計へ進める

REVISE_2_2:
  core_dag / temporal / counter_dag / source contract を修正する

REJECT_SEED:
  HYP-NDX-001 seed を一旦棄却する
```

## 目的の言い換え

```text
人間がCore DAG全文を読むのではなく、
deterministic checks + LLM review + hash-bound artifact によって、
人間はBLOCKERと未解決判断だけを見る。
```

## 今回の対象仮説

```text
dag_id:
  HYP-NDX-001

name:
  NDX / QQQ Open Gap Residual

scope:
  Nasdaq-100 / NDX / QQQ / optional NQ
```

## まだ完成扱いにしないもの

以下は今回の完成条件に含めません。

```text
feature panel
open_gap_residuals.parquet
expected gap model
neutralization report
strategy_signals.parquet
EvaluationPlan
TrialLedger
paper candidate
PaperIntentPreview
live order
```
