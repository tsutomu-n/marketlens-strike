<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# F_TASK_TICKETS

## Ticket EG-1

```text
Title:
  Add LLM review schemas and Pydantic contracts

Files:
  schemas/llm_dag_review.v1.schema.json
  schemas/layer_2_2_human_resolutions.v1.schema.json
  schemas/layer_2_2_exit_decision.v1.schema.json
  schemas/layer_2_2_freeze_manifest.v1.schema.json
  src/sis/research/dag/review_contracts.py

Tests:
  tests/research/test_llm_review_schema.py

Done:
  valid/invalid fixtures behave as expected.
```

## Ticket EG-2

```text
Title:
  Add review pack generator

Files:
  src/sis/research/dag/review_pack.py
  tests/research/test_llm_review_pack.py

Done:
  generates llm_review_pack.md, llm_review_input.json, llm_review_prompt.md.
```

## Ticket EG-3

```text
Title:
  Add LLM review importer

Files:
  src/sis/research/dag/review_import.py
  tests/research/test_llm_review_import.py

Done:
  validates pack_hash, evidence_refs, severity_counts, and writes normalized_review.json.
```

## Ticket EG-4

```text
Title:
  Add exit gate decision and freeze manifest

Files:
  src/sis/research/dag/exit_gate.py
  src/sis/research/dag/freeze_manifest.py
  tests/research/test_layer22_exit_gate.py

Done:
  approve/revise/reject paths work with fixtures.
```

## Ticket EG-5

```text
Title:
  Add CLI wrappers

Files:
  src/sis/commands/research.py
  tests/research/test_research_layer22_review_commands.py

Done:
  review-pack, review-import, exit-gate commands work and return defined exit codes.
```

## Ticket EG-6

```text
Title:
  Add operator documentation

Files:
  docs/research/ndx/09_LLM_REVIEW_GATE.md

Done:
  scripts/check_current_docs.py passes.
```
