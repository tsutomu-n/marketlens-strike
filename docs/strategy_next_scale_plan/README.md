<!--
作成日: 2026-06-19_02:22 JST
更新日: 2026-06-19_02:22 JST
-->

# Strategy Next Scale Plan

## 結論

Strategy Next Scale Plan は、`strategy-scale-decision` 後に次の拡大計画を人間レビューへ出せるかを artifact 化する read-only planning surface です。

これは scale-up execution permission ではありません。live order、wallet、signing、exchange write は実行しません。

## CLI

```bash
uv run sis strategy-next-scale-plan \
  --strategy-id ndx-breakout-001 \
  --scale-decision data/strategy_scale_decisions/ndx-breakout-001/strategy_scale_decision.json \
  --micro-live-plan data/strategy_micro_live_plans/ndx-breakout-001/strategy_micro_live_plan.json \
  --next-max-order-notional-usd 15 \
  --next-max-position-notional-usd 30 \
  --next-max-daily-loss-usd 4 \
  --next-max-total-loss-usd 8 \
  --next-max-open-positions 1 \
  --allowed-symbols NDX \
  --session-window "XNYS regular session" \
  --monitoring-owner operator \
  --monitoring-cadence "every 15 minutes while active" \
  --schedule-cancel-procedure "cancel all orders before session close" \
  --kill-switch-procedure "stop strategy and flatten through approved manual process"
```

出力:

```text
data/strategy_next_scale_plans/<strategy-id>/
  strategy_next_scale_plan.json
  strategy_next_scale_plan.md
```

## 判定

主な status:

- `READY_FOR_HUMAN_NEXT_SCALE_REVIEW`
- `NEEDS_SCALE_DECISION`
- `NEEDS_RISK_REPAIR`
- `BLOCKED_BOUNDARY_VIOLATION`

主な guard:

- scale decision が `READY_FOR_HUMAN_SCALE_REVIEW`
- recommended action が `PREPARE_NEXT_SCALE_PLAN`
- 前回 micro live plan が存在する
- 次の order / position / daily loss limit が前回 plan の `max_scale_multiplier` 内

## 境界

- `READY_FOR_HUMAN_NEXT_SCALE_REVIEW` は人間レビュー候補であり、実行許可ではない。
- `next_scale_execution_allowed=false` 固定。
- `live_allowed=false` 固定。
- wallet、signing、exchange write は false 固定。
- 実際の scale-up execution CLI はこの surface では追加しない。

## 検証

```bash
uv run pytest tests/strategy_next_scale_plan -q
uv run sis strategy-next-scale-plan --help
uv run python scripts/check_current_docs.py
```
