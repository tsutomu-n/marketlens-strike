# Pipeline Diagrams

## 1. Strategy Preparation Flow

```text
Idea
  -> Hypothesis Intake
  -> Data Availability Check
  -> Baseline Definition
  -> Parts Selection
  -> Feature Contract
  -> Signal Contract
  -> Backtest / Decision Log
  -> Paper Observation
  -> Reject / Continue / Archive
```

この流れでは、`Idea` から直接 `Bot` へ進まない。最初に作るのは実行Botではなく、仮説、データ契約、signal、decision logです。

## 2. Component Pipeline

```text
Universe Selector
  -> Data Collector
  -> Data Quality Gate
  -> Feature Factory
  -> Regime Detector
  -> Signal Generator
  -> Participation Filter
  -> Position Sizer
  -> Exit Module
  -> Risk Guard
  -> Execution Planner
  -> Paper Broker
  -> Evaluation Harness
  -> Monitoring
```

`Signal Generator` は中心ではあるが、単独では使わない。必ずfilter、sizer、risk、execution planを通す。

## 3. Repo Flow

```text
feature_frame
  -> src/sis/strategies/<strategy>.py
  -> signal frame
  -> data/research/signals.csv
  -> src/sis/backtest/signals.py
  -> src/sis/backtest/bridge.py
  -> DecisionRecord
  -> src/sis/risk/risk_gate.py
  -> src/sis/core/execution_plan.py
  -> src/sis/paper/runner.py
  -> data/paper/*.parquet
  -> data/reports/daily_paper_report.md
```

## 4. Reject-first Evaluation

```text
Candidate result looks good
  -> Check leakage
  -> Check cost/slippage x2
  -> Check walk-forward
  -> Check parameter neighborhood
  -> Check trade count
  -> Check paper/live gap
  -> reject if fragile
```

評価は、良い結果を正当化する作業ではなく、壊れる候補を早く捨てる作業です。

## 5. Solana / Meme Token Observer Flow

```text
Token Discovery
  -> Token Safety Filter
  -> Sellability Simulation
  -> Paper Observation
  -> Manual Review
  -> Small Canary Only If Preconditions Pass
```

禁止する短絡:

```text
Token Discovery -> Auto Buy
```

`safe_to_observe` は `safe_to_buy` ではありません。
