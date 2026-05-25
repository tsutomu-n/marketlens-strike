# 13. Implementation Tasks

## Epic 0: Repository setup

- [ ] `uv init --package`
- [ ] Python dependencies追加
- [ ] TypeScript sidecar作成
- [ ] directory構成作成
- [ ] `.env.example` 作成

## Epic 1: Data models

- [ ] `InstrumentSpec`
- [ ] `QuoteLog`
- [ ] `CostSnapshot`
- [ ] `MarketSession`
- [ ] `GoNoGoResult`
- [ ] JSON Schema出力

## Epic 2: gTrade sidecar

- [ ] `npm install @gainsnetwork/sdk zod tsx typescript`
- [ ] `/trading-variables`取得
- [ ] `transformGlobalTradingVariables`適用
- [ ] SPY/QQQ/XAU抽出
- [ ] spreadP/feeIndex/groupIndex抽出
- [ ] isIndicesOpen/isCommoditiesOpen抽出
- [ ] JSONL出力
- [ ] raw payload hash保存

## Epic 3: Python storage

- [ ] JSONL store
- [ ] Parquet converter
- [ ] DuckDB loader
- [ ] raw→normalized replay

## Epic 4: gTrade report

- [ ] registry生成
- [ ] quote normalize
- [ ] stale計算
- [ ] tradable率計算
- [ ] spread集計
- [ ] cost matrix生成

## Epic 5: Risk policy

- [ ] scalping policy
- [ ] halt policy
- [ ] session close guard
- [ ] stale guard
- [ ] spread guard
- [ ] mark/index divergence guard

## Epic 6: Ostium probe

- [ ] SDK import確認
- [ ] feed list取得
- [ ] symbol search
- [ ] latest price取得
- [ ] trading hours取得
- [ ] fees/OI caps取得
- [ ] registry化
- [ ] quote normalize

## Epic 7: Backtest bridge

- [ ] research price loader
- [ ] execution price joiner
- [ ] virtual execution
- [ ] cost integration
- [ ] metrics

## Epic 8: Go/No-Go

- [ ] criteria loader
- [ ] metrics evaluator
- [ ] markdown report
- [ ] evidence_card生成

## 最初の実装スプリント

### Day 1

- gTrade sidecarで `/trading-variables` を取得
- SPY/QQQ/XAUを抽出
- JSONL出力

### Day 2

- PythonでJSONLをParquet化
- scalping_policy実装
- cost matrix初版

### Day 3

- Go/No-Go report初版
- Ostium SDK import/probe開始
