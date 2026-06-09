<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# 06_ACCEPTANCE

## 実装受入条件

```text
A. 現行2.2実装の受入
  - research-layer22-validate pass
  - research-layer22-export pass
  - research-layer22-review-pack pass
  - review-import pass
  - exit-gate pass

B. Exit Gate意味論
  - APPROVE_2_3 + second_review_required=true が発生しない
  - APPROVE_2_3 + unresolved_human_decisions != [] が発生しない
  - APPROVE_2_3 の時だけ freeze manifest が存在する
  - BLOCKER は必ず REVISE_2_2
  - unresolved human decision は必ず REVISE_2_2
  - REJECT_SEED は明示条件を満たす場合だけ

C. 境界
  - external APIなし
  - credentialsなし
  - dependency追加なし
  - feature panelなし
  - residual calculationなし
  - Strategy Lab exportなし
  - paper/live/order path変更なし
```

## 必須コマンド

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

review JSONがある場合:

```bash
uv run sis research-layer22-review-import \
  --pack data/research/ndx/review/llm_review_input.json \
  --result data/research/ndx/review/llm_review_result.json

uv run sis research-layer22-exit-gate \
  --root configs/research_layer_2_2/ndx \
  --pack data/research/ndx/review/llm_review_input.json \
  --review data/research/ndx/review/normalized_review.json \
  --out data/research/ndx/review
```

## 期待する生成物

```text
data/research/ndx/core_dag.json
data/research/ndx/core_dag.mmd
data/research/ndx/counter_dags.md
data/research/ndx/data_requirements.yaml
data/reports/ndx_core_dag_report.md
data/research/ndx/review/llm_review_pack.md
data/research/ndx/review/llm_review_input.json
data/research/ndx/review/llm_review_prompt.md
data/research/ndx/review/normalized_review.json
data/research/ndx/review/layer_2_2_exit_decision.json
data/reports/ndx_llm_review_report.md
data/reports/ndx_layer_2_2_exit_gate_report.md
```

`layer_2_2_freeze_manifest.json` は `APPROVE_2_3` の時だけ生成される。
