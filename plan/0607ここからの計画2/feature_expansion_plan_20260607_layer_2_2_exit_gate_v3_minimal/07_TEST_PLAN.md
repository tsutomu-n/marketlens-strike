<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# 07_TEST_PLAN

## 方針

外部APIを呼ばず、fixtureだけで検証する。

## 追加テスト

### test_llm_review_schema.py

検証内容。

```text
- valid review passes
- extra property fails
- invalid severity fails
- missing pack_hash fails
- malformed evidence_refs fails
```

### test_llm_review_pack.py

検証内容。

```text
- same inputs produce same pack_hash
- evidence_catalog contains nodes, edges, counter_dags, prechecks
- prompt contains inert-data instruction
- pack generation fails if deterministic precheck fails
- no external network call
```

### test_llm_review_import.py

検証内容。

```text
- valid review imports
- pack_hash mismatch fails
- unknown evidence_ref fails
- severity_counts mismatch fails
- BLOCKER with APPROVE fails
- human_decision_id link mismatch fails
```

### test_layer22_exit_gate.py

検証内容。

```text
- APPROVE_2_3 path
- REVISE_2_2 for BLOCKER
- REVISE_2_2 for unresolved required_human_decisions
- REJECT_SEED path
- second review required path
- freeze manifest written only when allowed
```

### test_research_layer22_review_commands.py

検証内容。

```text
- review-pack CLI writes expected files
- review-import CLI writes normalized JSON
- exit-gate CLI writes decision and report
- expected exit codes
```

## Fixture一覧

```text
tests/fixtures/research_layer_2_2/reviews/valid_approve.json
tests/fixtures/research_layer_2_2/reviews/valid_warn_requires_resolution.json
tests/fixtures/research_layer_2_2/reviews/invalid_pack_hash_mismatch.json
tests/fixtures/research_layer_2_2/reviews/invalid_unknown_evidence_ref.json
tests/fixtures/research_layer_2_2/reviews/blocker_temporal_leakage.json
tests/fixtures/research_layer_2_2/reviews/reject_seed.json
```

## 最小コマンド

```bash
uv run pytest -q tests/research/test_llm_review_schema.py
uv run pytest -q tests/research/test_llm_review_pack.py
uv run pytest -q tests/research/test_llm_review_import.py
uv run pytest -q tests/research/test_layer22_exit_gate.py
uv run pytest -q tests/research/test_research_layer22_review_commands.py
```

## フル確認

```bash
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
./scripts/check
```

## 禁止

```text
- test内で外部LLMを呼ばない
- network fixtureを作らない
- credentialsを読むテストを作らない
```
