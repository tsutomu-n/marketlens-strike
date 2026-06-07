<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# 03 Tasks

## 優先順位表

| Rank | ID | カテゴリ | 実装時期 | 重要度 | 目的 |
|---:|---|---|---|---:|---|
| 1 | A0 | Scope / Boundary | 今すぐ | 最高 | スコープ外を明示し、実装暴走を止める |
| 2 | A1 | Seed Registry | 今すぐ | 最高 | 説のSeedをDAG前に保存する |
| 3 | A2 | Mechanism Parts | 今すぐ | 高 | 再利用可能な市場メカニズム部品を定義する |
| 4 | A3 | Variable Inventory | 今すぐ | 最高 | DAG node候補を棚卸しする |
| 5 | A4 | Causal Roles | 今すぐ | 最高 | 変数を因果ロールへ分類する |
| 6 | A5 | Temporal Availability | 今すぐ | 最高 | 未来情報とpost-treatmentを止める |
| 7 | B0 | Core DAG Contract | 今すぐ | 最高 | 2.2本体の型を作る |
| 8 | B1 | Loader / Validator | 今すぐ | 最高 | 壊れたDAGを拒否する |
| 9 | B2 | Forbidden Edge Linter | 今すぐ | 最高 | leakage/path汚染を拒否する |
| 10 | B3 | HYP-NDX-001 Registry | 今すぐ | 高 | 最初のCore DAGを登録する |
| 11 | B4 | Counter-DAG Artifact | 今すぐ | 高 | 反証DAGを保存する |
| 12 | B5 | Report Export | 今すぐ | 高 | レビュー可能なMarkdown/Mermaidを出す |
| 13 | B6 | Data Requirements | 今すぐ | 中〜高 | 後続feature builderの入力を定義する |
| 14 | C0 | Feature Panel | 次 | 中 | 実データ特徴量へ進む |
| 15 | C1 | Residual Builder | 次 | 中 | expected move / residual を計算する |
| 16 | C2 | Neutralization Report | 次 | 中 | 既知ファクター露出を診断する |
| 17 | C3 | Strategy Lab Export | 後 | 中 | signal artifactへ接続する |
| 18 | D0 | Causal Discovery | 後 | 低〜中 | PC/FCI/NOTEARS等を反対尋問として使う |
| 19 | D1 | DoWhy Graph Refutation | 後 | 低〜中 | 観測データでDAG仮定を検査する |

## A0 Scope / Boundary

### 追加ファイル

```text
docs/research/ndx/00_SCOPE.md
configs/research_layer_2_2/ndx/scope.yaml
```

### 実装内容

```text
- included / excluded をYAML化
- NDX / QQQ / NQ の扱いを記録
- 日経平均・Trade[XYZ]注文・Bitget・paper/liveを除外
```

### テスト

```text
tests/research/test_hypothesis_scope.py
```

### Done

```text
- scope.yamlを読める
- included/excludedが空ならfail
- excludedにTradeXYZ_order_execution/live_tradingが含まれる
```

## A1 Seed Registry

### 追加ファイル

```text
configs/research_layer_2_2/ndx/seed_registry.yaml
src/sis/research/hypothesis/seed_contracts.py
src/sis/research/hypothesis/seed_loader.py
tests/research/test_seed_registry.py
```

### 実装内容

```text
- Seed modelを作る
- seed_id, scope, intuition, candidate_known_factors, candidate_outcomeを必須にする
- HYP化前のstatus=seed_onlyを表現する
```

### 初期Seed

```text
NDX-SEED-001:
  ndx_open_gap_residual

NDX-SEED-002:
  qqq_vs_equal_weight_breadth_fragility

NDX-SEED-003:
  vxn_regime_sign_flip
```

### Done

```text
- 3 seedを読み込める
- seed_id重複を拒否
- next_layerが未指定ならfail
```

## A2 Mechanism Parts

### 追加ファイル

```text
configs/research_layer_2_2/ndx/mechanism_parts.yaml
src/sis/research/hypothesis/mechanism_contracts.py
src/sis/research/hypothesis/mechanism_loader.py
tests/research/test_mechanism_parts.py
```

### 初期部品

```text
SPX_BETA
RATES_DURATION
SOX_SEMI
VIX_VXN_REGIME
MEGA_CAP_CONCENTRATION
BREADTH_FRAGILITY
NQ_PRICE_DISCOVERY
OPEN_GAP_RESIDUAL
KNOWN_FACTOR_MIRAGE
REGIME_SIGN_FLIP
```

### Done

```text
- parts id重複拒否
- role_hintをenumでvalidate
- proxyが空ならfail
```

## A3 Variable Inventory

### 追加ファイル

```text
configs/research_layer_2_2/ndx/variable_inventory.yaml
src/sis/research/hypothesis/variable_contracts.py
src/sis/research/hypothesis/variable_loader.py
tests/research/test_variable_inventory.py
```

### 初期変数

```text
qqq_open_gap
qqq_open_to_close_return
spy_gap
smh_gap
dgs10_delta
vix_level
vix_change
mega_cap_basket_gap
expected_ndx_move
open_gap_residual
```

### Done

```text
- formula / proxy / source_symbol / temporal_classを持つ
- outcome候補のtemporal_classがt_after_closeである
- duplicate variable idを拒否
```

## A4 Causal Roles

### 追加ファイル

```text
configs/research_layer_2_2/ndx/causal_roles.yaml
src/sis/research/hypothesis/role_contracts.py
src/sis/research/hypothesis/role_validator.py
tests/research/test_causal_roles.py
```

### Role enum

```text
treatment_candidate
outcome
confounder
mediator
moderator
modeled_latent
observed_proxy
selection_mechanism
data_quality
neutralizer
```

### Done

```text
- open_gap_residual = treatment_candidate
- qqq_open_to_close_return = outcome
- spy_gap/smh_gap/dgs10_delta/mega_cap_basket_gap = confounder
- vix_level = moderator
- unknown roleを拒否
```

## A5 Temporal Availability

### 追加ファイル

```text
configs/research_layer_2_2/ndx/temporal_availability.yaml
src/sis/research/hypothesis/temporal_contracts.py
src/sis/research/hypothesis/temporal_validator.py
tests/research/test_temporal_availability.py
```

### Temporal layers

```text
t_prev_close
t_pre_open
t_open
t_after_open
t_after_close
```

### Done

```text
- qqq_open_to_close_return は t_after_close
- open_gap_residual は t_after_open
- t_after_close -> t_after_open のedgeを forbidden として出せる
```

## B0 Core DAG Contract

### 追加ファイル

```text
schemas/core_dag.v1.schema.json
src/sis/research/dag/contracts.py
tests/research/test_core_dag_contracts.py
```

### Done

```text
- CoreDag Pydantic modelがある
- thin JSON Schemaがある
- node/edge/forbidden_edge/counter_dag/data_requirementを持てる
```

## B1 Loader / Validator

### 追加ファイル

```text
src/sis/research/dag/loader.py
src/sis/research/dag/validator.py
src/sis/research/dag/errors.py
tests/research/test_core_dag_validator.py
```

### Done

```text
- configs/research_layer_2_2/ndx/core_dag.yamlを読める
- unknown node edgeを拒否
- self-loop拒否
- duplicate edge拒否
- duplicate node拒否
```

## B2 Forbidden Edge Linter

### 追加ファイル

```text
src/sis/research/dag/linter.py
src/sis/research/dag/rules.py
tests/research/test_core_dag_linter.py
```

### Done

```text
- outcome -> treatment_candidate をfail
- t_after_close -> t_after_open をfail
- forbidden_edgesに登録されたedgeがedgesにあるとfail
- missing counter DAG はwarning以上
```

## B3 HYP-NDX-001 Core DAG

### 追加ファイル

```text
configs/research_layer_2_2/ndx/core_dag.yaml
docs/research/ndx/HYP_NDX_001_OPEN_GAP_RESIDUAL.md
tests/research/test_ndx_core_dag_config.py
```

### Done

```text
- core_dag.yamlがvalidate/lint pass
- HYP_NDX_001 docにDAG概要、非目的、反証DAGがある
```

## B4 Counter-DAG Artifact

### 追加ファイル

```text
configs/research_layer_2_2/ndx/counter_dags.yaml
src/sis/research/dag/counter.py
tests/research/test_counter_dags.py
```

### 初期Counter-DAG

```text
BroadMarketOnlyDAG
RatesOnlyDAG
SOXOnlyDAG
MegaCapOnlyDAG
VolRegimeOnlyDAG
SelectionBiasDAG
```

### Done

```text
- HYP-NDX-001は最低6 counter DAGを持つ
- counter DAGなしならlint warning
```

## B5 Report Export

### 追加ファイル

```text
src/sis/research/dag/export.py
src/sis/research/dag/report.py
tests/research/test_core_dag_export.py
```

### CLI

```bash
uv run sis research-dag-validate --config configs/research_layer_2_2/ndx/core_dag.yaml
uv run sis research-dag-export --config configs/research_layer_2_2/ndx/core_dag.yaml --out data/research/ndx
```

### 出力

```text
data/research/ndx/core_dag.json
data/research/ndx/core_dag.mmd
data/research/ndx/counter_dags.md
data/research/ndx/data_requirements.yaml
data/reports/ndx_core_dag_report.md
```

### Done

```text
- CLIで出力できる
- reportに「DAGは真因果の証明ではない」と明記
```

## B6 Data Requirements

### 追加ファイル

```text
src/sis/research/dag/data_requirements.py
tests/research/test_data_requirements_export.py
```

### Done

```text
- core DAGのproxyから必要データ一覧を出す
- QQQ/SPY/SMH/VIX/DGS10/mega-cap basketを列挙する
- provider候補はmetadataで持つが実APIを呼ばない
```
