<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# 05_ACCEPTANCE

## 実装完了条件

次の条件をすべて満たすこと。

```text
1. review schemaが存在する
2. review packを生成できる
3. review resultをimportできる
4. pack_hash mismatchを拒否できる
5. unknown evidence_refを拒否できる
6. exit gate decisionを出せる
7. freeze manifestを出せる
8. CLIが動く
9. tests/researchが通る
10. ./scripts/checkが通る
```

## 必須生成物

```text
data/research/ndx/review/llm_review_pack.md
data/research/ndx/review/llm_review_input.json
data/research/ndx/review/llm_review_prompt.md
data/research/ndx/review/normalized_review.json
data/research/ndx/review/layer_2_2_exit_decision.json
data/research/ndx/review/layer_2_2_freeze_manifest.json
data/reports/ndx_llm_review_report.md
data/reports/ndx_layer_2_2_exit_gate_report.md
```

## 最小成功コマンド

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx

uv run sis research-layer22-review-pack \
  --root configs/research_layer_2_2/ndx \
  --out data/research/ndx/review

uv run sis research-layer22-review-import \
  --pack data/research/ndx/review/llm_review_input.json \
  --result data/research/ndx/review/llm_review_result.json

uv run sis research-layer22-exit-gate \
  --root configs/research_layer_2_2/ndx \
  --pack data/research/ndx/review/llm_review_input.json \
  --review data/research/ndx/review/normalized_review.json \
  --out data/research/ndx/review

uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

## 期待するexit code

```text
review-pack:
  0: pack generated
  2: config/input error
  3: deterministic precheck fail

review-import:
  0: review imported
  2: schema/hash/evidence error

exit-gate:
  0: APPROVE_2_3
  2: config/input error
  3: REVISE_2_2
  4: REJECT_SEED
```

## 合格しないケース

```text
- 外部APIが必要
- credentialsが必要
- pyproject.toml / uv.lockを変更
- Strategy Lab exportへ接続
- paper/live/order pathへ接続
- feature panelを生成
- residual calculationを実装
```

## artifact判定

`layer_2_2_exit_decision.json` は以下を含むこと。

```json
{
  "schema_version": "layer_2_2_exit_decision.v1",
  "dag_id": "HYP-NDX-001",
  "decision": "APPROVE_2_3",
  "pack_hash": "sha256:...",
  "review_ids": ["..."],
  "unresolved_human_decisions": [],
  "blocker_count": 0,
  "created_at": "2026-06-07T21:35:00+09:00"
}
```
