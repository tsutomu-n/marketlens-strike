<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# 02_SCOPE_AND_BOUNDARIES

## 対象

```text
Layer:
  2.2 Exit Gate

Market scope:
  NDX / QQQ / optional NQ

Repo scope:
  src/sis/research/dag/
  schemas/
  tests/research/
  docs/research/ndx/
  src/sis/commands/research.py
```

## 非対象

```text
2.3 feature builder
QQQ / SPY / SMH / VIX / DGS10 のデータ取得
NQ futures ingestion
LLM API integration
OpenAI / Anthropic SDK
credentials
backtest
paper order
live order
Trade[XYZ]
Strategy Lab export
```

## 外部API方針

```text
external_api:
  not_required

credentials:
  not_required

LLM call:
  repo内では実装しない

運用:
  review_pack.md / review_prompt.md を人間が別LLMへ貼る
  返ってきたJSONだけを repo artifact として import する
```

## 依存追加

```text
dependency_change:
  none

pyproject.toml:
  no-touch

uv.lock:
  no-touch
```

## DB / deploy / CI

```text
DB schema:
  no-touch

deploy:
  no-touch

CI:
  no external API
  fixture tests only
```

## paper/live/order境界

```text
paper_live_order:
  not_touched

禁止:
  - src/sis/paper/
  - src/sis/execution/
  - src/sis/venues/trade_xyz/
  - src/sis/bot/
  - PaperIntentPreview生成
  - Strategy Lab signal export
```

## LLMの責務

LLMに任せるもの。

```text
- causal interpretation concern
- temporal leakage suspicion
- NDX / QQQ / NQ role confusion
- ETF tracking noise concern
- futures price discovery concern
- counter-DAG gap
- index methodology blind spot
```

LLMに任せないもの。

```text
- YAML parse
- JSON Schema validation
- DAG acyclicity
- edge existence
- unknown variable detection
- pack hash comparison
- severity count consistency
- final gate mechanics
```

## second review 方針

標準では1件のLLM reviewでよい。

second adversarial review が必要な条件。

```text
- first review has BLOCKER or HIGH
- first review overall_decision is REVISE_REQUIRED / REJECT_SEED
- required_human_decisions is not empty
- core DAG or temporal contract changed after last freeze
- operator passes --require-second-review
```
