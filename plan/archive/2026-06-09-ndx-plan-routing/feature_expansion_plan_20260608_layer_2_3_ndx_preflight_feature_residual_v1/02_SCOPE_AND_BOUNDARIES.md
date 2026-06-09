<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 02_SCOPE_AND_BOUNDARIES

## 対象

```text
対象:
  NDX research の HYP-NDX-001
  QQQ observed ETF proxy
  SPY broad market proxy
  SMH semiconductor proxy
  VIX volatility proxy
  DGS10 rates proxy
  mega-cap basket proxy
```

## 初期必須proxy

```text
required:
  QQQ
  SPY
  SMH
  VIX
  DGS10
  mega_cap_basket
```

## 初期optional / deferred

```text
optional_or_deferred:
  NDX index level
  NQ futures
  VXN
  SOX direct
  options / gamma / 0DTE
  ETF premium/discount
  macro event calendar
  OPEX calendar
```

## 非目的

```text
- Strategy Lab export
- `data/research/strategy_signals.parquet` 生成
- backtest
- paper candidate
- PromotionDecision
- PaperIntentPreview
- paper-from-intents
- live order
- Trade[XYZ] execution
- external API自動呼び出し
- credentials要求
- dependency追加
- CI変更
```

## 安全境界

```text
- `data/research/signals.csv` を正本にしない
- `PaperIntentPreview` を作らない
- `Strategy Lab` modelやschemaを変更しない
- `src/sis/paper/`, `src/sis/execution/`, `src/sis/venues/trade_xyz/` に触らない
- `pyproject.toml`, `uv.lock` に触らない
```

## データ取得方針

初期PRでは **fixture-first** とする。  
real provider経由のfetchは実装可能な設計にするが、CIや受入テストでは外部APIを使わない。

```text
Phase 2.3A:
  source resolution artifact only
  no fetch

Phase 2.3B:
  fixture/local parquet/csv inputからfeature panel生成

Phase 2.3C:
  provider連携は別PRでopt-in
```
