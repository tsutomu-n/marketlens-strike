<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# 05_TASKS

## T0: Repo current truth確認

### 目的

現RepoのLayer 2.2実装状態を確認し、旧ZIPではなく現Repoを正本にする。

### 入力

```text
README.md
AGENTS.md
docs/CURRENT_STATE.md
docs/research/ndx/README.md
docs/research/ndx/09_LLM_REVIEW_GATE.md
src/sis/research/dag/
tests/research/
configs/research_layer_2_2/ndx/
```

### コマンド

```bash
uv run sis --help
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run pytest -q tests/research
```

### 完了条件

```text
- 5つのresearch-layer22系CLIの存在を確認
- validate/export/review-packが通る
- tests/researchが通る
```

---

## T1: Exit Gate意味論監査

### 対象ファイル

```text
src/sis/research/dag/exit_gate.py
tests/research/test_layer22_exit_gate.py
schemas/layer_2_2_exit_decision.v1.schema.json
```

### 監査内容

```text
- decision=APPROVE_2_3の場合だけfreeze_manifestを書いているか
- second_review_required=trueでAPPROVE_2_3にならないか
- unresolved_human_decisionsがある場合REVISE_2_2になるか
- BLOCKERがある場合REVISE_2_2になるか
- REJECT_SEEDの条件が明示的か
```

### 推奨修正

`_decision_value()` が `second_review_required` 相当の条件を見落とさないようにする。実装方針は2案ある。

#### 案A: 最小修正

```python
second_review_required = _second_review_required(...)
decision_value = _decision_value(
    review=review,
    unresolved=unresolved,
    require_second_review=(require_second_review or second_review_required),
    resolved_ids=resolved_ids,
)
```

ただし、この場合、HIGHがhuman resolution済みでも `_second_review_required()` が常にtrueなら通らない。HIGH解消済みを通したい場合は案B。

#### 案B: 推奨修正

`_second_review_required()` に `resolved_ids` と `unresolved` を渡し、HIGH unresolvedのみをsecond_review_requiredにする。

仕様:

```text
BLOCKER > 0:
  second_review_required=true
  decision=REVISE_2_2

HIGH with unresolved human decision:
  second_review_required=true
  decision=REVISE_2_2

HIGH with no human_decision_id:
  second_review_required=true
  decision=REVISE_2_2

HIGH with resolved human_decision_id:
  second_review_required=false
  decision can APPROVE_2_3 if no other blocker
```

### 完了条件

```text
- APPROVE_2_3ならsecond_review_required=false
- APPROVE_2_3ならfreeze_manifestあり
- REVISE_2_2ならfreeze_manifestなし
- REJECT_SEEDならfreeze_manifestなし
```

---

## T2: テスト追加・修正

### 対象ファイル

```text
tests/research/test_layer22_exit_gate.py
tests/fixtures/research_layer_2_2/reviews/
```

### 追加fixture候補

```text
high_without_human_decision.json
high_with_unresolved_human_decision.json
high_with_resolved_human_decision.json
approve_but_second_review_required_regression.json
reject_seed_without_resolution.json
reject_seed_with_resolution.json
```

### 追加テスト

```text
1. HIGH finding without human_decision_id
   -> REVISE_2_2
   -> second_review_required=true
   -> freeze_manifestなし

2. HIGH finding with unresolved human_decision_id
   -> REVISE_2_2
   -> second_review_required=true
   -> freeze_manifestなし

3. HIGH finding with resolved human_decision_id
   -> APPROVE_2_3可能
   -> second_review_required=false
   -> freeze_manifestあり

4. BLOCKER with resolution
   -> REVISE_2_2
   -> freeze_manifestなし

5. REJECT_SEED without resolution
   -> REVISE_2_2
   -> freeze_manifestなし

6. REJECT_SEED with causal/temporal confirmed resolution
   -> REJECT_SEED
   -> freeze_manifestなし

7. APPROVE_2_3 regression guard
   -> decision.second_review_required must be false
```

---

## T3: Review Import整合性の再確認

### 対象ファイル

```text
src/sis/research/dag/review_contracts.py
src/sis/research/dag/review_import.py
tests/research/test_llm_review_schema.py
tests/research/test_llm_review_import.py
```

### 確認項目

```text
- pack_hash mismatchを拒否
- unknown evidence_refsを拒否
- severity_counts mismatchを拒否
- BLOCKER with APPROVEを拒否
- human_decision_id参照不整合を拒否
```

### 完了条件

既存テストがすでに網羅していれば新規実装は不要。足りないケースだけ追加する。

---

## T4: Operator docs最小更新

### 対象ファイル

```text
docs/research/ndx/09_LLM_REVIEW_GATE.md
docs/research/ndx/LAYER_2_2_IMPLEMENTATION_RECORD_2026-06-07.md
```

### 更新内容

```text
- old v2/v5 ZIPはhistorical design backgroundと明記
- current code/tests/config/schemas/CLI helpが正本と明記
- APPROVE_2_3 implies second_review_required=false と明記
- second_review_required=trueでは2.3へ進まないと明記
```

### 完了条件

```bash
uv run python scripts/check_current_docs.py
```

---

## T5: Acceptance closeout

### コマンド

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import --pack data/research/ndx/review/llm_review_input.json --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate --root configs/research_layer_2_2/ndx --pack data/research/ndx/review/llm_review_input.json --review data/research/ndx/review/normalized_review.json --out data/research/ndx/review
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

### 完了条件

```text
- layer_2_2_exit_decision.json が生成される
- decision=APPROVE_2_3なら second_review_required=false
- decision=APPROVE_2_3なら freeze_manifestあり
- freeze_manifestのpack_hashがexit_decisionのpack_hashと一致
```
