<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# 02 Scope And Boundaries

## 1. スコープ

### Included

```text
研究対象:
  - NDX
  - QQQ
  - NQ futures は設計だけ。初期実装ではデータ取得しない。

既知ファクター:
  - SPY / SPX broad market
  - DGS10 / US10Y proxy
  - SMH or SOX proxy
  - VIX or VXN
  - mega-cap basket

機構:
  - Seed Registry
  - Mechanism Parts Library
  - Variable Inventory
  - Causal Role Assignment
  - Temporal Availability
  - Core DAG
  - Counter-DAG
  - Forbidden Edge Linter
  - Data Requirement Export
  - DAG Report Export
```

### Excluded

```text
今回除外:
  - 日経平均
  - TOPIX
  - USDJPY中心仮説
  - 日本株伝播
  - 個別NASDAQ小型株FOMO
  - Trade[XYZ] data readiness
  - Bitget credentialed API
  - demo order lifecycle
  - paper order
  - live order
  - wallet
  - signing
  - exchange write
  - NQ futures ingestion
  - options chain / gamma / 0DTE
  - NOTEARS / PCMCI / DoWhy 実行
```

## 2. 外部API境界

今回のPR群では、外部API呼び出しは禁止。

```text
許可:
  - local fixture
  - YAML / JSON / Markdown
  - Pydantic validation
  - pytest
  - generated artifact under data/research/ndx in tests via tmp_path

禁止:
  - yfinance実API
  - FRED実API
  - Alpaca実API
  - Bitget実API
  - Trade[XYZ]実API
  - broker/order API
```

実データ取得は Phase C 以降の別計画にする。

## 3. 注文系境界

```text
今回許可しない:
  - TradeCandidate生成
  - PaperCandidatePack生成
  - PromotionDecision生成
  - PaperIntentPreview生成
  - paper-from-intents実行
  - live conversion
  - exchange write
```

特に、DAG artifactから直接 `strategy_signals.parquet` を出してはいけない。Strategy Lab Exportは後続Phase。

## 4. データ方針

今回のデータ方針は次。

```text
Phase A/B:
  データ取得なし。
  設定・schema・validator・linter・reportのみ。

Phase C以降:
  QQQ/SPY/SMH/VIX/DGS10等の既存provider利用を検討。
  ただし今回のZIP計画では実装対象外。
```

`backtest_data_ready=true` は今回の目標ではない。

## 5. 変更してよい範囲

```text
OK:
  docs/research/ndx/
  configs/research_layer_2_2/ndx/
  schemas/research_*.schema.json
  schemas/core_dag.v1.schema.json
  src/sis/research/hypothesis/
  src/sis/research/dag/
  src/sis/commands/research.py
  tests/research/
  scripts/check_current_docs.py

NG:
  src/sis/execution/
  src/sis/paper/
  src/sis/backtest/
  src/sis/venues/trade_xyz/
  src/sis/bot/
  configs/trade_xyz_*.yaml
  pyproject.toml
  uv.lock
```

## 6. Stop Conditions

次の場合は即停止し、別タスクへ切る。

```text
- 外部APIが必要になった
- credentialsが必要になった
- 新規依存が必要になった
- paper/live注文に触れる必要が出た
- Strategy Lab signal exportへ進みたくなった
- backtestへ進みたくなった
- Trade[XYZ] readinessを変えたくなった
```

## 7. 誤謬リスク

| リスク | 悪い実装 | 正しい扱い |
|---|---|---|
| 2.2だけ作る | DAG nodeの前提が不明 | 0〜2.1の薄いcontractを先に作る |
| DAGを真因果扱い | reportで因果証明と書く | research hypothesis artifactと書く |
| Counter-DAG省略 | 自説だけ保存 | 反証DAGを必須にする |
| residual計算へ早すぎる移行 | データや時点が曖昧 | まずcontract/lint/report |
| Strategy Lab直結 | signal artifact化 | Phase C以降 |
| live/paper混入 | PaperIntentPreview生成 | 禁止 |
