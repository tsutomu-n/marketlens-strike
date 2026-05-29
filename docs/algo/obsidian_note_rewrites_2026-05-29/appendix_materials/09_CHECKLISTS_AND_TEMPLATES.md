# Checklists And Templates

戦略検討時にそのまま使う作業用テンプレートです。

## 1. Hypothesis Intake

```md
# Hypothesis: <name>

- one sentence:
- market:
- symbol/token universe:
- timeframe:
- expected edge:
- why it may persist:
- how it fails:
- baseline:
- source notes:
- decision: draft | ready-for-data | reject
```

## 2. Parts Selection

```md
## Parts

- Universe Selector:
- Data Collector:
- Data Quality Gate:
- Feature Factory:
- Regime Detector:
- Signal Generator:
- Participation Filter:
- Token Safety Filter:
- Position Sizer:
- Exit Module:
- Risk Guard:
- Evaluation Harness:
- Monitoring:
```

## 3. Backtest Readiness

- signal CSVの必須列がある。
- normalized quoteの必須列がある。
- cost/slippage前提がある。
- baselineがある。
- train/testまたはwalk-forwardが決まっている。
- leakage checkがある。
- reject rulesが先に書かれている。

## 4. Paper Readiness

- decision logが出る。
- blocked reasonが集計される。
- paper order/fillの価格参照が分かる。
- fillが0の時に理由が分かる。
- paper/live gapを記録する欄がある。
- daily lossやmanual stopの考え方がある。

## 5. Bot Boundary Checklist

- read-only/paperで十分な期間を見た。
- unknown orderで止まる。
- unknown positionで止まる。
- stale dataで新規停止。
- daily lossで停止。
- max exposureがある。
- secretをdocs/repoに置かない。
- manual kill switchがある。

## 6. Decision Log Review Template

```md
# Decision Log Review

- run id:
- signals_considered:
- executed_count:
- blocked_count:
- top blocked reasons:
- unexpected enters:
- unexpected skips:
- stale count:
- halt count:
- action:
```

## 7. Reject Record

```md
# Reject Record

- candidate:
- rejected at stage:
- primary reason:
- evidence:
- could be revived if:
- source notes:
- date:
```

## 8. Continue Record

```md
# Continue Record

- candidate:
- continue reason:
- required next test:
- risk to watch:
- max scope for next step:
- live execution allowed: no
```
