# 05. CLI Spec

## コマンド一覧

```bash
uv run sis probe gtrade
uv run sis probe ostium

uv run sis log-quotes --venue gtrade --duration-hours 24
uv run sis log-quotes --venue ostium --duration-hours 24

uv run sis normalize-quotes
uv run sis build-cost-matrix
uv run sis check-halt-policy
uv run sis check-go-no-go
uv run sis build-evidence-card
```

## `sis probe gtrade`

### 目的

対象ペアのregistryを生成する。

### 出力

```txt
data/registry/gtrade_instrument_registry.json
```

### 対象

```txt
SPY/USD pairIndex 86
QQQ/USD pairIndex 87
XAU/USD pairIndex 90
```

## `sis log-quotes --venue gtrade`

### 目的

gTrade sidecarの出力を保存、またはPython側で直接HTTP/WS取得する。

### 出力

```txt
data/raw/quotes/gtrade/YYYY-MM-DD.jsonl
```

## `sis normalize-quotes`

### 目的

raw JSONLを正規化し、Parquetへ変換する。

### 出力

```txt
data/normalized/quotes.parquet
```

## `sis build-cost-matrix`

### 目的

venue/symbol/timeframe別に実効コストを集計する。

### 出力

```txt
data/research/venue_cost_matrix.csv
```

## `sis check-go-no-go`

### 目的

研究を継続すべきかを判定する。

### 出力

```txt
data/research/go_no_go_report.md
```
