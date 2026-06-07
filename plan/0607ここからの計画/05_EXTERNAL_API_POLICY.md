<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# 05 External API Policy

## 1. 結論

今回の計画では、外部APIも注文系APIも許可しない。

```text
allowed:
  - local YAML
  - local JSON Schema
  - local Markdown
  - Pydantic validation
  - pytest
  - tmp_path artifacts
  - data/research/ndx artifact generation

not allowed:
  - Bitget API
  - Trade[XYZ] API
  - Alpaca API
  - yfinance network call
  - FRED network call
  - broker/order API
  - live order
  - paper order
  - wallet
  - signing
```

## 2. Bitget

```text
今回:
  使わない

read-only network call:
  許可しない

demo order submit/cancel/fill sync:
  許可しない

credentials:
  使わない
```

`bitget-demo-smoke` は既存境界の確認対象ではあるが、本計画の実装対象ではない。

## 3. Trade[XYZ]

```text
今回:
  使わない

read-only quote collection:
  実行しない

Trade[XYZ] readiness:
  変更しない

backtest_data_ready:
  目指さない

production/live:
  対象外
```

## 4. Alpaca / yfinance / FRED

```text
今回:
  実API呼び出しなし

Phase C以降:
  既存providerを使う可能性あり
  ただし別計画・別PRで扱う
```

## 5. データ保存方針

今回生成するのは、研究DAGのartifactだけ。

```text
runtime output:
  data/research/ndx/core_dag.json
  data/research/ndx/core_dag.mmd
  data/research/ndx/counter_dags.md
  data/research/ndx/data_requirements.yaml
  data/reports/ndx_core_dag_report.md
```

以下は生成しない。

```text
data/research/strategy_signals.parquet
data/research/trial_ledger.jsonl
data/research/paper_candidate_pack.json
data/research/promotion_decision.json
data/bot/paper_intent_preview.json
data/paper/*
```

## 6. 将来の外部API解禁条件

外部APIを使うのは Phase C 以降。

事前条件:

```text
1. DAG artifact foundationが完了
2. data requirementが確定
3. source tier policyが確定
4. APIごとの利用規約・rate limit・保存方針が別docにある
5. mock/fixture testsが先にある
6. external callは明示フラグでopt-in
```

## 7. 誤謬リスク

| リスク | 悪い判断 | 正しい判断 |
|---|---|---|
| yfinanceで取れるから即実装 | 外部データ依存が混ざる | Phase Cへ延期 |
| Bitget demoがあるから使う | scope creep | 今回は使わない |
| DAG exportに価格取得を混ぜる | 2.2と2.3が混ざる | data requirement exportまで |
| Strategy Labに出したくなる | signal生成へ進みすぎ | 後続PRへ切る |
