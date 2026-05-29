# Repo Implementation Map

このrepoに戦略を落とす時の対応表です。最初にlive executionを触らないための境界表でもあります。

## 1. Main Mapping

| やりたいこと | 触る場所 | 触らない場所 |
|---|---|---|
| signal generatorを作る | `src/sis/strategies/` | `src/sis/execution/` |
| signal CSVを読む | `src/sis/backtest/signals.py` | live adapter |
| signalをrisk gateに通す | `src/sis/backtest/bridge.py`, `src/sis/risk/risk_gate.py` | external exchange API |
| order planを作る | `src/sis/core/execution_plan.py` | secret/env |
| paperで見る | `src/sis/paper/runner.py` | live order policy |
| reportを見る | `data/reports/`, `data/research/decision_summary.json` | production deploy |

## 2. Initial Slice

```text
src/sis/strategies/trend_pullback.py
tests/test_strategies.py
data/research/signals.csv
```

最初のsliceでは、signal frameを作れることだけを固定する。paperやexecution planの拡張は後。

## 3. Existing Contracts

### Signal CSV

```text
ts_signal,canonical_symbol,side,timeframe,signal_strength
```

### DecisionContext

```text
decision_ts
venue
canonical_symbol
timeframe
quote_ts
signal_ts
signal_side
signal_strength
strategy_name
market_status
is_tradable
notes
```

### ExecutionPlan

現状で持つもの:

```text
action
venue
canonical_symbol
timeframe
price_reference
source_confidence
venue_quality_score
tracking_trade_allowed
fee_mode
estimated_round_trip_cost_bps
fill_price_source
notes
```

将来足す候補:

```text
side
quantity
entry_ref
invalidation_price
max_slippage_bps
risk_amount
participation_reason
```

## 4. Do Not Touch First

| path | 理由 |
|---|---|
| `src/sis/execution/trade_xyz_adapter.py` | live executionは戦略検証後 |
| `src/sis/execution/live_order_policy.py` | 実弾境界に近い |
| secrets/env files | docs作業・paper検証に不要 |
| external API write path | まずread-only/paperで十分 |

## 5. Implementation Readiness Gate

```text
signal generator exists
tests pass
signal CSV parses
decision log records block reasons
paper orders/fills are explainable
quantity / exit limitations are documented
```

このgateを満たす前にBot化しない。
