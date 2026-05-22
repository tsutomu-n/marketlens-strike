# 04. Architecture

## 全体像

```txt
[gTrade SDK sidecar]
  └─ normalized JSONL
        ↓
[Python sis core]
  ├─ storage: JSONL / Parquet / DuckDB
  ├─ risk: scalping / halt / cost / liquidation
  ├─ reports: cost matrix / go-no-go / evidence
  └─ backtest bridge

[Ostium Python SDK probe]
  └─ normalized JSONL
        ↓
[Python sis core]
```

## レイヤー

### 1. Venue Adapter

- gTrade sidecar
- Ostium probe

役割:

```txt
raw API/SDK response
→ venue-specific parse
→ normalized QuoteLog
```

### 2. Registry

`InstrumentSpec` と `MarketSession` を管理する。

### 3. Storage

```txt
raw JSONL: 全payload保存
Parquet: 正規化済みquote
DuckDB: 集計・report
```

### 4. Risk / Halt

短期スキャルピング禁止、market close、event window、stale、spread、near liquidationをBLOCKする。

### 5. Reports

- `venue_cost_matrix.csv`
- `go_no_go_report.md`
- `evidence_card.json`

### 6. Backtest Bridge

研究価格シグナルをvenue価格で仮想執行する。

## 価格参照設計

### gTrade

```txt
execution price = mark
liquidation reference = index
```

### Ostium

```txt
execution price = bid/ask or price-after-impact
liquidation reference = requires_probe
```

## なぜrawを保存するか

- API仕様変更時に再parseできる
- parserバグを後から修正できる
- EvidenceCardにpayload digestを残せる
- SDK version差異を検証できる
