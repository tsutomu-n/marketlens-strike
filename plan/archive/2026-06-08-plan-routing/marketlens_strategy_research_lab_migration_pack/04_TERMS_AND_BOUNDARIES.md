# 04 Terms And Boundaries

## Term Definitions

### StrategyExperimentSpec

戦略仮説を定義する。取引候補ではない。

```text
- strategy_id
- parameter_grid
- symbol binding
- evaluation plan
- validation policy
```

### StrategySignalRecord

戦略が出したsignal。注文候補ではない。

```text
- strategy_id
- execution_symbol
- real_market_symbol
- side
- score
- refs
```

### TradeCandidate

戦略signalから生成された取引候補。paper orderではない。live orderでもない。

### PaperCandidatePack

paperへ進めるか検討する候補束。注文ではない。

### PromotionDecision

人間判断artifact。paper昇格可否を記録する。

### PaperIntentPreview

paper実験用の仮注文意図。live注文には変換できない。

### PaperObservation

paper実行後の観測結果。intentがどうなったかを記録する。

## Boundary Summary

```text
StrategyExperimentSpec:
- 仮説

StrategySignalRecord:
- signal

TradeCandidate:
- 候補

PaperCandidatePack:
- paper候補束

PromotionDecision:
- 人間承認

PaperIntentPreview:
- paper仮注文意図

PaperObservation:
- paper結果
```

## Common Misreadings

```text
TradeCandidate == order        # false
PaperCandidatePack == paper order # false
PaperIntentPreview == live order # false
phase-gate-review == paper approval # false
bot-preview == strategy bot # false
READ_ONLY_GO == live ready # false
```
