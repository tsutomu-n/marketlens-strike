<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# 04 Tasks

## 実装フェーズ一覧

```text
Phase A: Layer 0〜2.1 の前段contract
Phase B: Layer 2.2 Core DAG Compiler
Phase C: Deferred / 今回は実装しない
```

---

# Phase A: 前段contract

## A0. Scope Contract

### 目的

NASDAQ単独、NDX/QQQ/NQ責務分離、非対象を固定する。

### 入力

なし。手書きYAML。

### 出力

```text
configs/research_layer_2_2/ndx/scope.yaml
docs/research/ndx/00_SCOPE.md
```

### 作業内容

```text
1. included / excluded を定義する。
2. NDX / QQQ / NQ の責務を分ける。
3. external API / paper/live / backtest / Trade[XYZ] を scope外とする。
```

### 完了条件

```text
- scope.yaml を loader で読める。
- excluded に Nikkei / TOPIX / TradeXYZ_order_execution / live_trading がある。
- QQQ が initial observed proxy であることが明記される。
```

---

## A1. Seed Registry

### 目的

「説のSeed」をDAG化前の素材として保存する。

### 出力

```text
configs/research_layer_2_2/ndx/seed_registry.yaml
src/sis/research/hypothesis/contracts.py
src/sis/research/hypothesis/loader.py
src/sis/research/hypothesis/validator.py
docs/research/ndx/01_SEED_REGISTRY.md
tests/research/test_seed_registry.py
```

### 初期Seed

```text
NDX-SEED-001: NDX Open Gap Residual
NDX-SEED-002: QQQ vs Equal Weight Breadth Fragility
NDX-SEED-003: VXN Regime Sign Flip
NDX-SEED-004: SOX Neutralized NDX Residual
NDX-SEED-005: Rates Neutralized NDX Residual
```

### 完了条件

```text
- seed_id が一意。
- status は seed_only / promoted_to_dag / rejected のいずれか。
- next_layer が layer_2_0_variable_inventory または layer_2_2_core_dag を示す。
- seed から paper/live/order action が出ない。
```

---

## A2. Mechanism Parts Library

### 目的

Seedを構成する再利用可能な市場メカニズム部品を保存する。

### 出力

```text
configs/research_layer_2_2/ndx/mechanism_parts.yaml
src/sis/research/hypothesis/mechanisms.py
docs/research/ndx/02_MECHANISM_PARTS.md
tests/research/test_mechanism_parts.py
```

### 必須部品

```text
SPX_BETA
RATES_DURATION
SOX_SEMI
VIX_VXN_REGIME
MEGA_CAP_CONCENTRATION
NDX_INDEX_METHODOLOGY
NDX_WEIGHT_CAP_PRESSURE
NDX_FAST_ENTRY_FLOW
NDX_REBALANCE_FLOW
QQQ_ETF_TRACKING_NOISE
NQ_FUTURES_PRICE_DISCOVERY
CALENDAR_EVENT_RISK
```

### 完了条件

```text
- 各partに id / name / category / role_hint / proxies / failure_modes がある。
- Nasdaq index methodology系部品が最低4つある。
- mechanism partから直接売買signalを生成しない。
```

---

## A3. Data Source Contract

### 目的

将来feature panelを作る時に必要なsource tierとproxyを固定する。ただし今回は取得しない。

### 出力

```text
configs/research_layer_2_2/ndx/data_sources.yaml
docs/research/ndx/03_DATA_SOURCE_CONTRACT.md
tests/research/test_data_source_contract.py
```

### 必須source

```text
QQQ:
  default_proxy_for actual_open_gap and open_to_close_outcome

SPY:
  broad market proxy

SMH:
  default semiconductor proxy if SOX unavailable

DGS10:
  rates proxy, provider future: FRED

VIX:
  default vol regime proxy if VXN unavailable

VXN:
  optional provider-dependent proxy

NQ:
  optional futures price discovery proxy
```

### 完了条件

```text
- provider_name は書けるが fetch 実装はない。
- source_tier が defined / optional_provider_dependent / deferred のいずれか。
- optional sourceを必須proxyにすると linter warning が出せる設計になっている。
```

---

## A4. Variable Inventory

### 目的

DAGに入れる変数とproxy、formula、temporal classを棚卸しする。

### 出力

```text
configs/research_layer_2_2/ndx/variable_inventory.yaml
src/sis/research/hypothesis/variables.py
docs/research/ndx/04_VARIABLE_INVENTORY.md
tests/research/test_variable_inventory.py
```

### 必須変数

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
nq_overnight_move_optional
qqq_premium_discount_optional
```

### 完了条件

```text
- variable_id が一意。
- formula / proxy / temporal_class / availability_rule / role_candidates がある。
- qqq_open_to_close_return は outcome 候補であり、signal input ではない。
- same-day closeを t_after_open で利用可能にしない。
```

---

## A5. Causal Roles

### 目的

Variable Inventoryの変数を因果ロールへ分類する。

### 出力

```text
configs/research_layer_2_2/ndx/causal_roles.yaml
src/sis/research/hypothesis/causal_roles.py
docs/research/ndx/05_CAUSAL_ROLES.md
tests/research/test_causal_roles.py
```

### 必須ロール

```text
open_gap_residual: treatment_candidate
qqq_open_to_close_return: outcome
spy_gap: confounder
smh_gap: confounder
dgs10_delta: confounder
vix_level: moderator
mega_cap_basket_gap: confounder
expected_ndx_move: modeled_latent
actual_open_gap: observed_proxy
```

### 完了条件

```text
- role が許可語彙に含まれる。
- outcome と treatment_candidate が同一変数にならない。
- confounder には proxy がある。
- role と variable_inventory.role_candidates が矛盾しない。
```

---

## A6. Temporal Availability

### 目的

いつ利用可能な情報かを固定し、未来情報リークを防ぐ。

### 出力

```text
configs/research_layer_2_2/ndx/temporal_availability.yaml
src/sis/research/hypothesis/temporal.py
docs/research/ndx/06_TEMPORAL_AVAILABILITY.md
tests/research/test_temporal_availability.py
```

### 必須availability layer

```text
t_prev_close
  previous close values

t_pre_open
  values known before current open

t_open_observed
  open prices after market open is observed

t_open_plus_buffer
  features allowed after opening data is stable

t_after_close
  close prices and open-to-close outcome

provider_dependent
  VXN / NQ / SOX direct sources that require later source decision
```

### 完了条件

```text
- t_after_close -> t_open_plus_buffer は forbidden。
- qqq_close は t_after_close。
- qqq_open_gap は t_open_observed or t_open_plus_buffer。
- dgs10 same-day value is not assumed available at t_open unless explicitly configured.
```

---

# Phase B: 2.2 Core DAG Compiler

## B0. Core DAG Contract

### 目的

Core DAGの機械可読contractを作る。

### 出力

```text
schemas/core_dag.v1.schema.json
src/sis/research/dag/contracts.py
tests/research/test_core_dag_contracts.py
```

### 完了条件

```text
- CoreDag / DagNode / DagEdge / ForbiddenEdge / CounterDagRef / DataRequirement model がある。
- JSON Schemaは薄いguardとして存在する。
- 詳細validationはPydantic model側で行う。
```

---

## B1. DAG Loader / Validator

### 出力

```text
src/sis/research/dag/loader.py
src/sis/research/dag/validator.py
src/sis/research/dag/errors.py
tests/research/test_core_dag_loader.py
tests/research/test_core_dag_validator.py
```

### 完了条件

```text
- YAMLを読める。
- unknown node edge をfail。
- self-loopをfail。
- duplicate node / edgeをfail。
- unknown roleをfail。
- core_dag.yaml と variable_inventory / causal_roles / temporal_availability の参照整合性を検査できる。
```

---

## B2. Linter Rules v2

### 出力

```text
src/sis/research/dag/linter.py
src/sis/research/dag/rules.py
tests/research/test_core_dag_linter.py
```

### 必須ルール

```text
no_outcome_to_treatment
no_future_to_signal
no_post_treatment_to_pre_treatment
no_forbidden_edge_in_edges
role_required_rule
proxy_required_rule
temporal_layer_required_rule
unknown_variable_rule
role_consistency_rule
data_source_tier_rule
counter_dag_minimum_rule
no_model_output_to_input_rule
```

### 完了条件

```text
- open_to_close_return -> open_gap_residual をfail。
- qqq_close を actual_open_gap の入力に入れる定義をfailまたは強warn。
- optional_provider_dependent proxyを必須扱いするとwarn。
- counter-DAG不足をfailまたはwarn。HYP-NDX-001ではfail。
```

---

## B3. HYP-NDX-001 Core DAG

### 出力

```text
configs/research_layer_2_2/ndx/core_dag.yaml
docs/research/ndx/07_CORE_DAG.md
tests/research/test_hyp_ndx_001_core_dag.py
```

### 完了条件

```text
- HYP-NDX-001 がvalidate pass。
- Linter errors = 0。
- Warningsは許容理由がreportに出る。
- node数は最初は15以下。
```

---

## B4. Counter-DAG Catalog

### 出力

```text
configs/research_layer_2_2/ndx/counter_dags.yaml
src/sis/research/dag/counter.py
docs/research/ndx/08_COUNTER_DAGS.md
tests/research/test_counter_dags.py
```

### 必須counter-DAG

```text
BroadMarketOnlyDAG
RatesOnlyDAG
SemiconductorOnlyDAG
MegaCapOnlyDAG
VolRegimeOnlyDAG
ETFTrackingNoiseDAG
FuturesPriceDiscoveryDAG
IndexRebalanceDAG
MacroEventDAG
CalendarEffectDAG
SelectionBiasDAG
DataSourceLagDAG
```

### 完了条件

```text
- HYP-NDX-001 に最低8本のcounter-DAGが登録される。
- 各counter-DAGに risk / proxy / refutation_test_hint がある。
- Counter-DAGなしではCore DAG reportがfail扱い。
```

---

## B5. Data Requirements Export

### 出力

```text
src/sis/research/dag/data_requirements.py
data/research/ndx/data_requirements.yaml
tests/research/test_dag_data_requirements.py
```

### 完了条件

```text
- Core DAGとvariable inventoryから必要データ一覧を出せる。
- required / optional / deferred を分ける。
- Phase Cで使う provider は候補として出すがfetchしない。
```

---

## B6. Report / Mermaid / JSON Export

### 出力

```text
src/sis/research/dag/export.py
src/sis/research/dag/report.py
data/research/ndx/core_dag.json
data/research/ndx/core_dag.mmd
data/research/ndx/counter_dags.md
data/reports/ndx_core_dag_report.md
tests/research/test_core_dag_export.py
```

### 完了条件

```text
- core_dag.json が出る。
- core_dag.mmd が出る。
- ndx_core_dag_report.md に nodes / edges / forbidden_edges / warnings / counter-DAG / data requirements が出る。
- reportに「DAGは真因果の証明ではない」と明記する。
```

---

## B7. Minimal CLI Wrappers

### 目的

実装者とレビュアーが同じコマンドでvalidate/exportできるようにする。

### 出力

```text
src/sis/commands/research.py への最小追加
tests/research/test_research_layer22_commands.py
```

### 追加コマンド

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
```

### 完了条件

```text
- validate command はlint errorがあれば exit code 2。
- export command は validate を先に行う。
- 外部APIを呼ばない。
- paper/live/orderに触らない。
```

---

# Phase C: Deferred

今回は実装しない。

```text
C0 NDX feature panel
C1 Open gap residual builder
C2 Neutralization report
C3 Strategy Lab signal export
C4 Evaluation / backtest
C5 Paper candidate
```
