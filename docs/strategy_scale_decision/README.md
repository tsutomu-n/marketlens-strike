<!--
作成日: 2026-06-19_01:31 JST
更新日: 2026-06-21_21:47 JST
-->

# Strategy Scale Decision

## 結論

`strategy-scale-decision` は、scale-up execution を許可する command ではありません。

`strategy_live_observation_manifest.v1` と任意の `strategy_micro_live_plan.v1` を読み、micro live canary 後に「次の scale plan を準備する候補か、止めるか、修正するか」を `strategy_scale_decision.v1` として記録します。

## Command

```bash
uv run sis strategy-scale-decision \
  --strategy-id ndx-breakout-001 \
  --live-observation data/strategy_live_observations/ndx-breakout-001/strategy_live_observation_manifest.json \
  --micro-live-plan data/strategy_micro_live_plans/ndx-breakout-001/strategy_micro_live_plan.json \
  --out data/strategy_scale_decisions
```

## Boundary

- CLI stdout は `READY_FOR_HUMAN_SCALE_REVIEW` を `status=pass` ではなく次のように表示する。

```text
status=needs_human_approval
requires_explicit_approval=true
permits_live_order=false
decision_status=READY_FOR_HUMAN_SCALE_REVIEW
```

blocked path でも `requires_explicit_approval=false` と `permits_live_order=false` を明示し、scale-up / live permission として読めないようにします。

- `READY_FOR_HUMAN_SCALE_REVIEW` は scale-up execution permission ではない。
- `PREPARE_NEXT_SCALE_PLAN` は次の計画 artifact を作る候補であり、live order permission ではない。
- wallet、signing、exchange write は使わない。
- next scale plan には別の人間承認と execution control が必要。

## Verification

```bash
uv run pytest tests/strategy_scale_decision -q
uv run sis strategy-scale-decision --help
uv run python scripts/check_current_docs.py
```
