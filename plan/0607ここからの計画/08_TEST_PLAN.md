<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# 08 Test Plan

## 1. テスト方針

今回のテストは、外部API・実データ・注文系を使わない。

```text
unit:
  Pydantic validation
  YAML loading
  linter rule
  export formatting

integration-light:
  config一式を読み込んでHYP-NDX-001をvalidate/lint/export

CLI:
  research-dag-validate
  research-dag-export
```

## 2. 最低限通すコマンド

通常の開発中:

```bash
uv run pytest -q tests/research
uv run python scripts/check_current_docs.py
```

PR最終:

```bash
./scripts/check
```

## 3. Acceptance test詳細

### Scope

```text
- includedが空ならfail
- excludedが空ならfail
- excludedにlive_trading / TradeXYZ_order_execution が含まれる
```

### Seed

```text
- seed_id重複fail
- scope未指定fail
- intuition空文字fail
- candidate_outcome空fail
- next_layer未指定fail
```

### Mechanism Parts

```text
- part id重複fail
- role_hint unknown fail
- proxies空fail
```

### Variable Inventory

```text
- variable id重複fail
- formula/proxy/source_symbolの最低1つがない場合fail
- temporal_class unknown fail
```

### Causal Role

```text
- unknown role fail
- variable_inventoryにない変数のrole指定fail
- outcomeがt_after_open以前にいる場合warningまたはfail
```

### Temporal Availability

```text
- temporal layer未定義fail
- same variableが複数layerにいる場合fail
- t_after_close -> t_after_open forbidden rule生成
```

### Core DAG

```text
- unknown node edge fail
- self-loop fail
- duplicate edge fail
- duplicate node id fail
- role unknown fail
```

### Linter

```text
- outcome -> treatment_candidate fail
- t_after_close -> t_after_open fail
- forbidden_edgesに登録済みedgeがedgesに存在するとfail
- counter DAGなし warning
```

### Export

```text
- JSON出力にschema_version/dag_id/nodes/edgesがある
- Mermaid出力にflowchartがある
- Markdown reportにlint resultがある
- data requirementsにQQQ/SPY/SMH/VIX/DGS10がある
```

### CLI

```text
- valid configでexit 0
- invalid configでexit 2
- export先にcore_dag.json/core_dag.mmd/data_requirements.yamlが出る
```

## 4. Full Check 方針

```text
- 各小修正では targeted pytest でよい
- PR完了時は ./scripts/check を実行
- docsだけのPRなら current docs checker + git diff --checkでも可
- ただし今回はcode/schema/testsを追加するため、最終的には ./scripts/check が必要
```

## 5. テストでやらないこと

```text
- yfinance / FRED / Alpaca / Bitget / Trade[XYZ] network call
- live order
- paper order
- Strategy Lab evaluation
- backtest
- pyproject dependency changes
```

## 6. 推奨fixture

```text
tests/fixtures/research_layer_2_2/
  valid_ndx_core_dag.yaml
  invalid_unknown_node_core_dag.yaml
  invalid_future_to_signal_core_dag.yaml
  invalid_missing_counter_dag.yaml
```

## 7. 完了時の証跡

PR descriptionに以下を書く。

```text
Verification:
  - uv run pytest -q tests/research
  - uv run python scripts/check_current_docs.py
  - ./scripts/check

Generated artifacts:
  - data/research/ndx/core_dag.json
  - data/research/ndx/core_dag.mmd
  - data/reports/ndx_core_dag_report.md

Not done:
  - no external API
  - no strategy_signals.parquet
  - no paper/live order
```
