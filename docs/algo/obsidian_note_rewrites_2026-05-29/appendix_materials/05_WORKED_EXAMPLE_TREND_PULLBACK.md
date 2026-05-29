# Worked Example: Trend Pullback

Trend Pullbackを、仮説からpaper評価まで通す例です。

## 1. Hypothesis

```text
長期トレンドが上向きの時だけ、短期押し目からの再上昇候補を出すと、単純な常時押し目買いよりentry直後の逆行とDDが下がる。
```

比較対象:

- baseline: close > sma20 の単純long。
- candidate: regime + pullback + event filter + risk gate。

## 2. Required Inputs

| field | reason |
|---|---|
| `close` | 価格 |
| `sma_20` | 押し目判定 |
| `sma_50` | 中期trend |
| `sma_50_slope` | trend方向 |
| `realized_vol_20` | panic/high vol回避 |
| `trade_allowed` | repo側の許可 |
| `is_event_blackout` | イベント回避 |
| `data_status` | stale/missing除外 |

## 3. Regime

```text
if data_status != "valid":
    regime = "unknown"
elif realized_vol_20 > vol_p95:
    regime = "panic"
elif close > sma_50 and sma_50_slope > 0:
    regime = "trend"
else:
    regime = "range"
```

## 4. Signal

```text
precondition:
  regime == trend
  data_status == valid
  trade_allowed == true
  is_event_blackout == false

long:
  close > sma_50
  sma_50_slope > 0
  abs(distance_to_sma20_pct) <= 0.01
  short_momentum_turns_up == true
```

出力:

```csv
ts_signal,canonical_symbol,side,timeframe,signal_strength
2026-01-01T00:00:00+00:00,QQQ,long,4h,0.42
```

## 5. Participation Filter

```text
if spread_bps > max_spread_bps:
    skip("SPREAD_TOO_WIDE")
elif market_status != "open":
    skip("MARKET_CLOSED")
elif is_tradable is not true:
    skip("NOT_TRADABLE")
else:
    allow()
```

## 6. Position Sizer

初期paperでは `quantity=1.0` 固定でもよい。ただし、実装制約として明記する。

将来の式:

```text
risk_amount = equity * risk_per_trade
stop_distance = abs(entry_ref - invalidation_price)
raw_qty = risk_amount / stop_distance
qty = min(raw_qty, liquidity_cap, portfolio_cap)
```

## 7. Exit

最初から完璧なexitを実装しない場合でも、評価上のexit仮定は明記する。

| exit | condition |
|---|---|
| invalidation | recent swing low割れ |
| time | max holding bars超過 |
| risk | daily loss / panic |
| profit protection | ATR trail |

現状の簡易backtestが「次のquoteでexit」に近い場合、それを実戦的exitとして扱わない。

## 8. Paper Review

見る順番:

1. `decision_summary.json` の `signals_considered`。
2. `blocked_reason_counts`。
3. `orders.parquet` の action。
4. `fills.parquet` の価格参照。
5. `daily_paper_report.md` の損益。

## 9. Reject Rules

- cost/slippage x2で期待値が消える。
- `range` で発火している。
- skipした取引の方が良い。
- trade countが少なすぎる。
- event blackoutで入っている。
- exit仮定が曖昧なまま成績を採用している。

## 10. Continue Conditions

- baselineよりDDが下がる。
- trade countが十分。
- walk-forwardで改善方向が残る。
- parameter近傍で壊れない。
- paperで想定価格と観測価格の差が説明可能。
