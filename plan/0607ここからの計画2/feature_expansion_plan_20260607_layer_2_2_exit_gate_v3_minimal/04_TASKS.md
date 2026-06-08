<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# 04_TASKS

## 全体方針

今回の実装は Phase EG として扱う。

```text
EG = Exit Gate
```

Phase A/B、つまり2.2基盤本体は完了済みと仮定する。

---

## EG-0: 実装前確認

### 目的

completed Layer 2.2 bundle が存在するか確認する。

### 入力

```text
configs/research_layer_2_2/ndx/
data/research/ndx/core_dag.json
data/research/ndx/core_dag.mmd
data/research/ndx/data_requirements.yaml
data/reports/ndx_core_dag_report.md
```

### 作業

```text
1. root bundle path が存在するか確認
2. research-layer22-validate が通るか確認
3. research-layer22-export が通るか確認
4. data/research/ndx/ の生成物が存在するか確認
```

### 完了条件

```text
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
```

---

## EG-1: Review schemas

### 目的

LLM review result、human resolution、exit decision、freeze manifest のschemaを追加する。

### 追加ファイル

```text
schemas/llm_dag_review.v1.schema.json
schemas/layer_2_2_human_resolutions.v1.schema.json
schemas/layer_2_2_exit_decision.v1.schema.json
schemas/layer_2_2_freeze_manifest.v1.schema.json
```

### 追加コード

```text
src/sis/research/dag/review_contracts.py
```

### 実装内容

```text
- LlmDagReview
- LlmReviewFinding
- LlmRequiredHumanDecision
- HumanResolution
- Layer22ExitDecision
- Layer22FreezeManifest
```

### 完了条件

```text
- Pydantic validationで正常/異常fixtureを判定できる
- JSON Schemaを書き出せる、または手動schemaと整合する
- additionalProperties=false 相当のguardがある
```

---

## EG-2: Review Pack Generator

### 目的

LLMに渡すreview packを生成する。

### 追加コード

```text
src/sis/research/dag/review_pack.py
```

### 入力

```text
configs/research_layer_2_2/ndx/
data/research/ndx/core_dag.json
data/research/ndx/core_dag.mmd
data/research/ndx/data_requirements.yaml
data/reports/ndx_core_dag_report.md
```

### 出力

```text
data/research/ndx/review/llm_review_pack.md
data/research/ndx/review/llm_review_input.json
data/research/ndx/review/llm_review_prompt.md
```

### 実装内容

```text
- artifact bundleを読み込む
- deterministic precheckを実行する
- evidence_catalogを作る
- canonical JSONからpack_hashを作る
- prompt injection対策としてartifact contentをinert dataとして扱う文言を入れる
- Markdown packを生成する
- JSON packを生成する
```

### deterministic precheck

```text
- validator pass
- linter pass
- DAG acyclic
- temporal monotonic matrix pass
- source tier required integrity pass
- counter-DAG minimum category coverage pass
- evidence catalog completeness pass
- no paper/live/order path
```

### 完了条件

```text
- pack_hashが安定している
- same inputならsame hash
- evidence_refsとして使えるCAT.* IDが生成される
- pack生成時に外部APIを呼ばない
```

---

## EG-3: Review Result Importer

### 目的

別LLMから返ってきたJSONを検証・正規化する。

### 追加コード

```text
src/sis/research/dag/review_import.py
```

### 入力

```text
data/research/ndx/review/llm_review_input.json
data/research/ndx/review/llm_review_result.json
```

### 出力

```text
data/research/ndx/review/normalized_review.json
data/reports/ndx_llm_review_report.md
```

### 実装内容

```text
- review JSONをPydanticでparse
- pack_hash一致を確認
- evidence_refsがcatalog内にあるか確認
- severity_countsとfindingsの整合を確認
- human_decision_idとrequired_human_decisionsの整合を確認
- overall_decisionとseverityの矛盾を拒否
- normalized_review.jsonを書き出す
```

### 完了条件

```text
- invalid JSONを拒否
- extra propertyを拒否
- pack_hash mismatchを拒否
- unknown evidence refを拒否
- BLOCKERがあるのにAPPROVEなら拒否
```

---

## EG-4: Exit Gate Decision

### 目的

deterministic checks + LLM review result + optional human resolutions から最終判定を出す。

### 追加コード

```text
src/sis/research/dag/exit_gate.py
```

### 入力

```text
configs/research_layer_2_2/ndx/
data/research/ndx/review/llm_review_input.json
data/research/ndx/review/normalized_review.json
data/research/ndx/review/layer_2_2_human_resolutions.json  # optional
```

### 出力

```text
data/research/ndx/review/layer_2_2_exit_decision.json
data/research/ndx/review/layer_2_2_freeze_manifest.json
data/reports/ndx_layer_2_2_exit_gate_report.md
```

### 判定ルール

```text
APPROVE_2_3:
  deterministic precheck pass
  review exists
  BLOCKER = 0
  unresolved required_human_decisions = 0
  pack_hash matches current artifacts
  if HIGH exists, human resolution exists or second review waived by config

REVISE_2_2:
  deterministic precheck fail
  BLOCKER > 0
  unresolved human decision exists
  review suggests REVISE_REQUIRED
  HIGH finding without resolution

REJECT_SEED:
  review suggests REJECT_SEED and category is causal_misspecification or temporal_leakage
  operator confirms reject through resolution
```

### second review trigger

```text
require_second_review if:
  --require-second-review
  first review has BLOCKER or HIGH
  first review overall_decision in [REVISE_REQUIRED, REJECT_SEED]
  required_human_decisions not empty
  config says review_policy.second_review_required=true
```

### 完了条件

```text
- approve fixtureでAPPROVE_2_3
- blocker fixtureでREVISE_2_2
- reject fixtureでREJECT_SEED
- unresolved human decisionがあるとREVISE_2_2
```

---

## EG-5: Minimal CLI Wrappers

### 目的

実運用できるCLIを追加する。

### 編集ファイル

```text
src/sis/commands/research.py
```

必要な場合のみ。

```text
src/sis/cli.py
```

### 追加CLI

```bash
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
```

### Exit codes

```text
0:
  success / APPROVE_2_3

2:
  config/input/schema error

3:
  REVISE_2_2

4:
  REJECT_SEED
```

### 完了条件

```text
- CLI helpに表示される
- tempdir fixtureでファイルを書ける
- external APIを呼ばない
```

---

## EG-6: Documentation

### 目的

operatorが手動LLMレビューを実行できるようにする。

### 追加ファイル

```text
docs/research/ndx/09_LLM_REVIEW_GATE.md
```

### 内容

```text
- review pack生成手順
- LLMへ貼る手順
- JSONだけ返させる手順
- import手順
- exit gate手順
- よくある失敗
- stop conditions
```

### 完了条件

```text
- Markdownに東京時間metadata headerがある
- scripts/check_current_docs.py が通る
```

---

## EG-7: Tests

### 目的

外部APIなしで全分岐を検証する。

### 追加ファイル

```text
tests/research/test_llm_review_schema.py
tests/research/test_llm_review_pack.py
tests/research/test_llm_review_import.py
tests/research/test_layer22_exit_gate.py
tests/research/test_research_layer22_review_commands.py

tests/fixtures/research_layer_2_2/reviews/
```

### 完了条件

```bash
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```
