<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 09_DIAGNOSTICS_AND_REFUTATION

## 目的

Open Gap Residualができても、すぐStrategy Labやbacktestへ流さない。まず、既知ファクターで消えるか、counter-DAGで説明できるかを診断する。

## Diagnostics

```text
- row_count
- missing rate
- residual mean/std
- residual autocorrelation
- correlation with outcome
- correlation with each factor
- sign stability
- regime split by VIX level/change
- sample count by year/month
```

## Neutralization pre-report

見るもの:

```text
raw residual -> qqq_open_to_close_return
SPY-adjusted
SMH-adjusted
VIX-adjusted
DGS10-adjusted
mega-cap-adjusted
combined-adjusted
```

この段階では、Numerai風の「既知ファクター中和後に残るか」を見るだけ。利益や売買sideは主張しない。

## Counter-DAG Refutation Skeleton

初期で診断する:

```text
BroadMarketOnlyDAG:
  SPY factorで説明できるか

RatesOnlyDAG:
  DGS10で説明できるか

SOXOnlyDAG:
  SMHで説明できるか

MegaCapOnlyDAG:
  mega_cap_basketで説明できるか

VolRegimeOnlyDAG:
  VIX regimeで説明できるか

SelectionBiasDAG:
  gap size bucketの選択バイアスか

DataSourceLagDAG:
  source_ts/provider timingの問題か
```

deferredとして明記する:

```text
ETFTrackingNoiseDAG:
  QQQ premium/discount sourceが未実装

FuturesPriceDiscoveryDAG:
  NQ sourceが未実装

IndexRebalanceDAG:
  NDX methodology event calendar未実装

MacroEventDAG:
  macro event calendar未実装

CalendarEffectDAG:
  OPEX/month-end/weekday診断は別PR
```

## 出力

```text
data/reports/ndx_neutralization_report.md
data/reports/ndx_counter_dag_refutation_report.md
data/research/ndx/neutralized_residuals.parquet
```

## 判断

```text
残差が全部消える:
  Factor MirageとしてREVISE_2_2に戻す候補

一部regimeだけ残る:
  Regime-specific seedへ分割候補

残差が安定して残る:
  Strategy Lab research-only export計画へ進む候補
```
