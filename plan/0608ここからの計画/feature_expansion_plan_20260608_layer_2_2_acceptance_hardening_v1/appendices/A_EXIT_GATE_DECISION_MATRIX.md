<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# A_EXIT_GATE_DECISION_MATRIX

## 目的

`exit_gate.py`の判断を曖昧にしないための決定表。

| 入力条件 | expected decision | second_review_required | freeze manifest |
|---|---|---:|---:|
| APPROVE, no findings | APPROVE_2_3 | false | yes |
| APPROVE_WITH_WARNINGS, only LOW/INFO | APPROVE_2_3 | false | yes |
| MEDIUM only, no human decision | APPROVE_2_3 | false | yes |
| HIGH with resolved human_decision_id | APPROVE_2_3 | false | yes |
| HIGH with unresolved human_decision_id | REVISE_2_2 | true | no |
| HIGH without human_decision_id | REVISE_2_2 | true | no |
| BLOCKER any | REVISE_2_2 | true | no |
| required_human_decisions unresolved | REVISE_2_2 | true | no |
| REVISE_REQUIRED | REVISE_2_2 | true | no |
| INSUFFICIENT_EVIDENCE | REVISE_2_2 | true | no |
| REJECT_SEED without confirmed resolution | REVISE_2_2 | true | no |
| REJECT_SEED with confirmed causal/temporal resolution | REJECT_SEED | false or true allowed, but no advance | no |
| pack_hash mismatch | input error | n/a | no |
| current pack hash mismatch | input error | n/a | no |

## invariant

```text
APPROVE_2_3 => second_review_required=false
APPROVE_2_3 => unresolved_human_decisions=[]
APPROVE_2_3 => blocker_count=0
APPROVE_2_3 => freeze_manifest_path is not None
REVISE_2_2 or REJECT_SEED => freeze_manifest_path is None
```
