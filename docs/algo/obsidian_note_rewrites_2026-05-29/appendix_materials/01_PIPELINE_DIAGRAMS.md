<!--
作成日: 2026-05-29_21:42 JST
更新日: 2026-06-05_08:11 JST
-->

# Pipeline Diagrams

この付録は、現行 Strategy Research Lab の artifact chain を図として読むための資料です。旧 `data/research/signals.csv` 中心の図は legacy paper path であり、現行 Strategy Lab の正本ではありません。

## 1. Strategy Research Lab full chain

```text
Strategy idea
  |
  v
StrategyExperimentSpec
  |
  v
Signal generator registry
  |
  v
StrategySignalRecord rows
  |
  v
data/research/strategy_signals.parquet
  |
  v
EvaluationPlan
  |
  v
TrialRecord rows
  |
  v
data/research/trial_ledger.jsonl
  |
  v
TradeCandidate rows
  |
  v
data/research/paper_candidate_pack.json
  |
  v
PromotionDecision
  |
  v
data/bot/paper_intent_preview.json
  |
  v
paper-from-intents revalidation
  |
  v
paper orders/fills/positions only
```

## 2. Symbol binding diagram

```text
real market data                         execution venue
----------------                         ----------------
QQQ bars / features / tracking  ----->   XYZ100 on trade_xyz
SPY bars / features / tracking  ----->   SP500 on trade_xyz
```

`real_market_symbol` は feature truth、`execution_symbol` は paper/execution-side quote lookup です。ここを同一視しないでください。

## 3. Candidate selection diagram

```text
StrategySignalRecord
  |
  | evaluate with EvaluationPlan
  v
TrialRecord
  |
  | selected_for_next_stage?
  +-- false --> TradeCandidate(status=blocked, block_reasons=[...])
  |
  +-- true  --> TradeCandidate(status=candidate, side=long/short)
                    |
                    v
              PaperCandidatePack
```

`selected_for_next_stage=true` は paper candidate へ進むだけです。paper-ready / live-ready ではありません。

## 4. Promotion diagram

```text
PaperCandidatePack
  |
  v
PromotionDecision(decision=hold)
  |
  +--> no intent or empty preview

PromotionDecision(decision=reject)
  |
  +--> no intent or empty preview

PromotionDecision(decision=promote)
  |
  v
PaperIntentPreview(paper_only=true)
```

`promote` は live order 許可ではありません。paper observation に進む許可です。

## 5. Paper revalidation diagram

```text
PaperIntentPreview
  |
  | validate model guards
  v
latest normalized quote lookup
  |
  +-- missing --> blocked: LATEST_QUOTE_MISSING
  |
  v
valid_until check
  |
  +-- expired --> blocked: INTENT_EXPIRED
  |
  v
PaperBroker validation
  |
  +-- blocked --> blocked: PAPER_BROKER_REVALIDATION_BLOCKED
  |
  v
paper order + paper fill + paper position
```

Observation ledger は `live_order_submitted=false`, `wallet_used=false`, `exchange_write_used=false` を残します。

## 6. Legacy bridge diagram

`paper-from-intents` の内部では、既存 paper runner に接続するため `DecisionContext` と `ExecutionPlan` が使われます。

```text
PaperIntentPreview
  |
  v
DecisionContext / ExecutionPlan internal bridge
  |
  v
PaperBroker
```

これは internal bridge です。Strategy Lab の設計入口は `StrategySignalRecord`, `TradeCandidate`, `PaperIntentPreview` です。

## 7. Current docs map

詳細仕様:

- `docs/strategy_research_lab/README.md`
- `docs/strategy_research_lab/01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md`
- `docs/strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md`
- `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md`

入口監査:

- `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`
