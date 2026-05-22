# 11. Backtest Bridge Spec

## 方針

研究価格でsignalを作り、venue quote logで仮想執行する。

```txt
Signal generation:
  QQQ / SPY / GLD / XAU proxy / VIX / DGS10 / DXY

Execution simulation:
  gTrade mark price
  Ostium bid/ask or execution price

Liquidation simulation:
  gTrade index price
  Ostium requires_probe
```

## 対象時間軸

比較対象:

```txt
30m
4h
1d
3d
5d
```

主対象:

```txt
4h
1d
3d
```

## Virtual execution rules

### gTrade

```txt
entry/exit price = mark_price
liquidation ref = index_price
if market_status != open: reject
```

### Ostium

```txt
entry buy = ask or price-after-impact
entry sell = bid or price-after-impact
liquidation ref = unresolved until probe
market order closed session = reject
limit/stop closed session = venue-specific queued behavior, requires_probe
```

## Cost integration

```txt
net_pnl = gross_pnl - open_fee - close_fee - spread - holding_cost - slippage_or_impact
```

## Required metrics

```txt
total_return
annual_return
max_drawdown
sharpe
win_rate
profit_factor
trade_count
avg_trade_return
worst_trade
exposure_ratio
cost_drag_bps
stale_rejected_count
halt_rejected_count
```

## Go/No-Go判定への接続

4h〜3dで以下を満たすならGO候補。

```txt
- コスト控除後の期待値が残る
- event blackoutでDDが改善する
- 短期スキャルなしで成立する
- spread/staleによるrejectが過剰でない
```
