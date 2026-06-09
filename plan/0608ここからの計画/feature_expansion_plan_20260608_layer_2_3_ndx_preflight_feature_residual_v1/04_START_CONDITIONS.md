<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 04_START_CONDITIONS

## 2.3へ進む開始条件

2.3実装に入る前に、必ず以下を確認する。

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review
```

## 必須artifact

```text
data/research/ndx/review/layer_2_2_exit_decision.json
data/research/ndx/review/layer_2_2_freeze_manifest.json
data/research/ndx/core_dag.json
data/research/ndx/data_requirements.yaml
```

## 開始可能条件

```text
layer_2_2_exit_decision.json:
  decision = APPROVE_2_3
  second_review_required = false
  unresolved_human_decisions = []

layer_2_2_freeze_manifest.json:
  exists
  dag_id = HYP-NDX-001
  pack_hash matches current exported artifacts
```

## 開始不可条件

```text
- decision = REVISE_2_2
- decision = REJECT_SEED
- second_review_required = true
- unresolved_human_decisions がある
- freeze_manifest がない
- pack_hash mismatch
- research-layer22-validate が落ちる
- research-layer22-export が落ちる
```

## 開始不可時の対応

```text
2.3へ進まず、2.2 Acceptance / Hardeningへ戻る。
```
