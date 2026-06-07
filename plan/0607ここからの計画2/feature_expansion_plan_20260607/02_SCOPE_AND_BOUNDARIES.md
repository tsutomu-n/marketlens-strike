<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# 02 Scope And Boundaries

## 対象

今回の対象はNASDAQ単独である。

```text
Primary research target:
  Nasdaq-100 / NDX concept

Primary executable / observed proxy:
  QQQ

Optional price discovery proxy:
  NQ futures
```

初期実装では `NDX`, `QQQ`, `NQ` を混同しない。

```text
NDX:
  指数概念・ベンチマーク。初期実装では直接データ取得しない。

QQQ:
  ETF proxy。Open Gap と Open-to-Close outcome の初期観測proxy。

NQ:
  futures price discovery proxy。Phase A/Bでは data source contract に記録するだけで、取得・計算しない。
```

## 非対象

```text
- 日経平均
- TOPIX
- 日本株伝播
- USDJPY中心仮説
- 個別NASDAQ小型株
- 小型株FOMO short 仮説
- Trade[XYZ] order execution
- Bitget demo network/API
- PaperIntentPreview
- paper runner extension
- live order / wallet / signing / exchange write
```

## 外部API境界

今回のPhase A/Bでは外部APIを使わない。

```text
not allowed:
  - yfinance download
  - FRED API
  - Alpaca API
  - Polygon / Massive / Databento
  - Cboe data download
  - CME data download
  - Nasdaq API
  - Bitget API
  - Trade[XYZ] API
```

ただし、将来使う可能性のある provider 名や source tier は `data_sources.yaml` に contract として書いてよい。

## Credentials境界

```text
credentials_required: false
```

`.env` や secret は使わない。テストも fixture / YAML / local validation だけで通す。

## Paper / Live境界

今回のPRでは、以下に触らない。

```text
src/sis/paper/
src/sis/execution/
src/sis/bot/
data/bot/paper_intent_preview.json
```

`PaperIntentPreview` は paper-only artifact であり、live orderへ変換しない。今回の2.2機能からは生成しない。

## Backtest境界

今回のPRでは backtest を実装しない。

```text
src/sis/backtest/ は no-touch
uv run sis evaluate-strategy-lab は使わない
strategy-author-run は使わない
```

## DB / Deploy / Dependency境界

```text
DB schema: 変更しない
deploy: 変更しない
CI workflow: 原則変更しない
pyproject.toml: 変更しない
uv.lock: 変更しない
```

## CLI境界

Phase AはCLIなしでよい。

Phase Bの最後に、必要なら以下の2つだけ追加する。

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
```

CLIを追加する場合でも、ロジックは `src/sis/research/hypothesis/` と `src/sis/research/dag/` に置き、command wrapperに閉じ込めない。
