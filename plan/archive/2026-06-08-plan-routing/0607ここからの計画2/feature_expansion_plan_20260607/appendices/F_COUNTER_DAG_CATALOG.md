<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# Appendix F: Counter-DAG Catalog

HYP-NDX-001 では、以下を最低限登録する。

## 1. BroadMarketOnlyDAG

```text
SPX broad market beta explains QQQ open gap and open-to-close behavior.
```

Proxy:

```text
SPY gap, ES return, SPY open-to-close
```

## 2. RatesOnlyDAG

```text
US rates / real yield shock explains Nasdaq movement.
```

Proxy:

```text
DGS10, US2Y, real yield proxy
```

## 3. SemiconductorOnlyDAG

```text
SOX/SMH or semiconductor complex explains the apparent NDX residual.
```

Proxy:

```text
SMH, SOX optional, NVDA, AMD, AVGO
```

## 4. MegaCapOnlyDAG

```text
Mega-cap basket alone explains QQQ gap and RTH behavior.
```

Proxy:

```text
AAPL, MSFT, NVDA, AMZN, META, GOOGL, AVGO basket
```

## 5. VolRegimeOnlyDAG

```text
VIX/VXN volatility regime explains gap fade/continuation.
```

Proxy:

```text
VIX, VXN optional, realized vol
```

## 6. ETFTrackingNoiseDAG

```text
QQQ ETF market price noise, spread, or premium/discount creates residual.
```

Proxy:

```text
QQQ premium/discount optional, bid-ask spread, volume
```

## 7. FuturesPriceDiscoveryDAG

```text
NQ futures correctly price overnight information before QQQ cash open; residual is a measurement artifact.
```

Proxy:

```text
NQ overnight move optional, QQQ premarket optional
```

## 8. IndexRebalanceDAG

```text
Nasdaq-100 rebalance / weight cap / fast entry event creates temporary pressure.
```

Proxy:

```text
rebalance calendar, special rebalance, fast entry event
```

## 9. MacroEventDAG

```text
CPI/FOMC/NFP event window explains residual behavior.
```

Proxy:

```text
event calendar, yield surprise, first reaction window
```

## 10. CalendarEffectDAG

```text
weekday, month-end, OPEX, quarter-end explains the observed effect.
```

Proxy:

```text
calendar features, OPEX calendar optional
```

## 11. SelectionBiasDAG

```text
Only large gap days are selected, creating an apparent reversal effect.
```

Proxy:

```text
gap threshold selection, same-vol random control
```

## 12. DataSourceLagDAG

```text
Data timestamp lag or provider-specific open definitions create artificial residual.
```

Proxy:

```text
source_ts, provider, open timestamp quality, missing rate
```
