<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# A_SCHEMA_SKETCHES

## llm_dag_review.v1 の要点

完全なJSON Schemaは実装時に `schemas/llm_dag_review.v1.schema.json` へ置く。ここでは実装者向けの構造を示す。

```json
{
  "schema_version": "llm_dag_review.v1",
  "review_id": "review.20260607.001",
  "dag_id": "HYP-NDX-001",
  "pack_hash": "sha256:...",
  "prompt_contract_version": "llm_dag_review_prompt.v1",
  "prompt_hash": null,
  "review_mode": "standard",
  "reviewer": {
    "provider": "manual",
    "model": "unspecified",
    "model_version": "unspecified",
    "invocation": "manual_paste",
    "temperature": 0
  },
  "overall_decision": "APPROVE_WITH_WARNINGS",
  "coverage": {
    "causal_structure": "ok",
    "temporal_leakage": "ok",
    "market_structure": "concern",
    "counter_dag_coverage": "ok",
    "repo_boundary": "ok"
  },
  "severity_counts": {
    "BLOCKER": 0,
    "HIGH": 0,
    "MEDIUM": 1,
    "LOW": 0,
    "INFO": 2
  },
  "findings": [
    {
      "finding_id": "F001",
      "severity": "MEDIUM",
      "category": "market_structure_confusion",
      "claim": "ETF tracking noise is represented only as a counter-DAG.",
      "why_it_matters": "QQQ open gap may reflect ETF market price effects, not only index exposure.",
      "evidence_refs": ["CAT.COUNTER.ETFTrackingNoiseDAG"],
      "target_refs": ["CAT.NODE.actual_open_gap"],
      "suggested_actions": ["Add a note to actual_open_gap interpretation."],
      "requires_human_decision": false,
      "human_decision_id": null
    }
  ],
  "required_human_decisions": []
}
```

## severity

```text
BLOCKER:
  2.3へ進めない。human resolutionでも原則通さない。

HIGH:
  原則修正。ただし明示resolutionで通せる。

MEDIUM:
  修正推奨。gateは通せる。

LOW:
  メモ。

INFO:
  参考。
```

## overall_decision

```text
APPROVE
APPROVE_WITH_WARNINGS
REVISE_REQUIRED
REJECT_SEED
INSUFFICIENT_EVIDENCE
```

## layer_2_2_exit_decision.v1

```json
{
  "schema_version": "layer_2_2_exit_decision.v1",
  "dag_id": "HYP-NDX-001",
  "decision": "APPROVE_2_3",
  "pack_hash": "sha256:...",
  "review_ids": ["review.20260607.001"],
  "blocker_count": 0,
  "high_count": 0,
  "unresolved_human_decisions": [],
  "second_review_required": false,
  "created_at": "2026-06-07T21:35:00+09:00"
}
```

## layer_2_2_human_resolutions.v1

```json
{
  "schema_version": "layer_2_2_human_resolutions.v1",
  "dag_id": "HYP-NDX-001",
  "pack_hash": "sha256:...",
  "resolutions": [
    {
      "decision_id": "HD001",
      "selected_option": "accept_risk",
      "reason": "Known limitation is tracked as counter-DAG; not blocker for 2.3 design.",
      "resolved_by": "human",
      "resolved_at": "2026-06-07T21:35:00+09:00"
    }
  ]
}
```
