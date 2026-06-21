<!--
作成日: 2026-06-19_01:31 JST
更新日: 2026-06-21_21:47 JST
-->

# Strategy Micro Live Plan Gate

## 結論

`strategy-micro-live-plan` は、micro live execution を実行する command ではありません。

`strategy_stage_decision.v1`、`paper_vs_backtest_drift_review.v1`、人間承認 artifact、risk limits、monitoring / kill switch procedure、必要なら既存 `configs/micro_live_policy.yaml` を読み、`strategy_micro_live_plan.v1` JSON と Markdown を作る read-only plan gate です。

## Command

```bash
uv run sis strategy-micro-live-plan \
  --strategy-id ndx-breakout-001 \
  --stage-decision data/strategy_stage/ndx-breakout-001/strategy_stage_decision.json \
  --drift-review data/strategy_drift_reviews/ndx-breakout-001/drift.json \
  --human-approval data/strategy_micro_live_approvals/ndx-breakout-001/approval.json \
  --micro-live-policy configs/micro_live_policy.yaml \
  --max-order-notional-usd 10 \
  --max-position-notional-usd 20 \
  --max-daily-loss-usd 5 \
  --max-total-loss-usd 10 \
  --max-open-positions 1 \
  --allowed-symbol SPY \
  --session-window "XNYS regular session only" \
  --monitoring-owner operator \
  --monitoring-cadence "watch every fill and every 5 minutes" \
  --schedule-cancel-procedure "schedule cancel before submitting any canary order" \
  --kill-switch-procedure "stop new orders and cancel open orders immediately" \
  --out data/strategy_micro_live_plans
```

## Output

```text
data/strategy_micro_live_plans/<strategy-id>/
  strategy_micro_live_plan.json
  strategy_micro_live_plan.md
```

## Ready Status

`plan_status=READY_FOR_HUMAN_MICRO_LIVE_REVIEW` は、次の条件を満たした plan artifact です。

CLI stdout では、これを `status=pass` ではなく次のように表示します。

```text
status=needs_human_approval
requires_explicit_approval=true
permits_live_order=false
plan_status=READY_FOR_HUMAN_MICRO_LIVE_REVIEW
```

これは plan artifact が人間レビューに回せるという意味であり、micro live execution の許可ではありません。
blocked path でも `requires_explicit_approval=false` と `permits_live_order=false` を明示し、live permission として読めないようにします。

- stage decision が `selected_stage=micro_live_plan` かつ `READY_FOR_MICRO_LIVE_PLAN`。
- drift review が `READY_FOR_HUMAN_DRIFT_REVIEW`。
- drift review の recommended action が `REVISE_STRATEGY` / `REPAIR_ARTIFACTS` ではない。
- human approval artifact がある。
- risk limits と monitoring plan が埋まっている。
- 既存 micro live policy を渡した場合、notional / daily loss / open positions / symbols が矛盾しない。

## Boundary

- micro live execution を実行しない。
- Workbench 標準 CLI として live order command を追加しない。
- `MicroLivePolicy.enabled=true` を要求しない。これは plan gate であり実行 gate ではない。
- wallet、signing、exchange write は使わない。
- `READY_FOR_HUMAN_MICRO_LIVE_REVIEW` は live execution permission ではない。
