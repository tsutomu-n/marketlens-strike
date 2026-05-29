# Factory Workflow

安全に戦略候補を量産するための状態遷移です。各gateを満たさない候補は次へ進めません。

## 1. State Machine

```text
idea
  -> specified
  -> data-ready
  -> backtest-ready
  -> backtested
  -> paper-observing
  -> continue | rejected | archived
```

## 2. Gates

| from | to | required |
|---|---|---|
| idea | specified | one sentence, archetype, trigger, invalidation, baseline |
| specified | data-ready | required inputs are available historically or by safe collection |
| data-ready | backtest-ready | leakage check, cost assumptions, no-trade conditions |
| backtest-ready | backtested | baseline comparison, cost/slippage included, reject rules applied |
| backtested | paper-observing | enough trade count, no obvious leakage, paper observation plan |
| paper-observing | continue | paper/backtest gap explainable, risk guard defined |
| any | rejected | fixed reject reason code |
| any | archived | duplicate, stale, or intentionally paused |

## 3. Stop Conditions

Do not continue when:

- invalidation is missing.
- baseline is missing.
- required data cannot be obtained without unsafe side effects.
- signal depends on future or corrected data.
- backtest only works without cost/slippage.
- paper fill gap cannot be explained.
- strategy requires live execution to validate the basic idea.

## 4. Minimal Review Loop

```text
Candidate Sheet
  -> Pre-backtest Score
  -> Backlog Entry
  -> Gate Review
  -> Reject or Next State
```

## 5. Batch Review Cadence

For a batch of candidates:

1. Remove duplicates.
2. Reject candidates without invalidation.
3. Reject candidates without available data.
4. Score remaining candidates.
5. Move only top candidates to data-ready.
6. Record every rejection with a taxonomy code.

## 6. What Not To Do

- Do not tune parameters before the signal contract is stable.
- Do not add ML before a rule baseline exists.
- Do not move to paper because an in-sample equity curve looks good.
- Do not use Crypto/DeFi execution topics as the default path.
