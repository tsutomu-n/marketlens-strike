<!--
作成日: 2026-06-07_19:17 JST
更新日: 2026-06-07_19:17 JST
-->

# 09 Schema And Config Sketches

## 1. scope.yaml

```yaml
schema_version: research_scope.v1
scope_id: NDX_SCOPE_V1
name: ndx_research_scope

included:
  primary:
    - NDX
    - QQQ
  future_optional:
    - NQ
  known_factors:
    - SPY
    - SMH
    - VIX
    - DGS10
    - mega_cap_basket

excluded:
  - Nikkei
  - TOPIX
  - Japan_equities
  - USDJPY_as_primary
  - TradeXYZ_order_execution
  - Bitget_demo_network
  - paper_order
  - live_trading
  - wallet
  - signing
  - exchange_write

policy:
  external_api_allowed: false
  strategy_lab_export_allowed: false
  paper_preview_allowed: false
```

## 2. seed_registry.yaml

```yaml
schema_version: research_seed_registry.v1

seeds:
  - seed_id: NDX-SEED-001
    name: ndx_open_gap_residual
    status: seed_only
    scope: NDX_SCOPE_V1
    intuition: >
      Known factor expected move と actual QQQ open gap の差分が
      open-to-close return に情報を持つ可能性がある。
    candidate_known_factors:
      - spy_gap
      - smh_gap
      - dgs10_delta
      - vix_change
      - mega_cap_basket_gap
    candidate_treatment:
      - open_gap_residual
    candidate_outcome:
      - qqq_open_to_close_return
    next_layer: layer_2_0_variable_inventory
```

## 3. mechanism_parts.yaml

```yaml
schema_version: research_mechanism_parts.v1

parts:
  - part_id: SPX_BETA
    name: Broad Market Beta
    role_hint: confounder
    proxies:
      - spy_gap
      - spy_return

  - part_id: RATES_DURATION
    name: Growth Duration Shock
    role_hint: confounder
    proxies:
      - dgs10_delta

  - part_id: SOX_SEMI
    name: Semiconductor Shock
    role_hint: confounder
    proxies:
      - smh_gap

  - part_id: VIX_VXN_REGIME
    name: Nasdaq Volatility Regime
    role_hint: moderator
    proxies:
      - vix_level
      - vix_change

  - part_id: MEGA_CAP_CONCENTRATION
    name: Mega-cap Concentration
    role_hint: confounder
    proxies:
      - mega_cap_basket_gap
```

## 4. variable_inventory.yaml

```yaml
schema_version: research_variable_inventory.v1

variables:
  qqq_open_gap:
    description: QQQ open gap from previous close.
    source_symbol: QQQ
    formula: log(open / prev_close)
    temporal_class: t_after_open
    role_candidates:
      - observed_proxy

  qqq_open_to_close_return:
    description: Same-day QQQ open-to-close return.
    source_symbol: QQQ
    formula: log(close / open)
    temporal_class: t_after_close
    role_candidates:
      - outcome

  spy_gap:
    source_symbol: SPY
    formula: log(open / prev_close)
    temporal_class: t_after_open
    role_candidates:
      - confounder

  smh_gap:
    source_symbol: SMH
    formula: log(open / prev_close)
    temporal_class: t_after_open
    role_candidates:
      - confounder

  dgs10_delta:
    source_symbol: DGS10
    formula: value_t_minus_1 - value_t_minus_2
    temporal_class: t_pre_open
    role_candidates:
      - confounder

  vix_change:
    source_symbol: VIX
    formula: value_t_minus_1 - value_t_minus_2
    temporal_class: t_pre_open
    role_candidates:
      - moderator

  mega_cap_basket_gap:
    source_symbol: AAPL_MSFT_NVDA_AMZN_META_GOOGL_AVGO
    formula: weighted_mean(log(open / prev_close))
    temporal_class: t_after_open
    role_candidates:
      - confounder

  expected_ndx_move:
    description: Modeled expected QQQ open gap from known factors.
    temporal_class: t_after_open
    role_candidates:
      - modeled_latent

  open_gap_residual:
    formula: qqq_open_gap - expected_ndx_move
    temporal_class: t_after_open
    role_candidates:
      - treatment_candidate
```

## 5. causal_roles.yaml

```yaml
schema_version: research_causal_roles.v1

roles:
  qqq_open_gap: observed_proxy
  qqq_open_to_close_return: outcome
  spy_gap: confounder
  smh_gap: confounder
  dgs10_delta: confounder
  vix_change: moderator
  mega_cap_basket_gap: confounder
  expected_ndx_move: modeled_latent
  open_gap_residual: treatment_candidate
```

## 6. temporal_availability.yaml

```yaml
schema_version: research_temporal_availability.v1

layers:
  t_prev_close:
    - qqq_prev_close
    - spy_prev_close
    - smh_prev_close

  t_pre_open:
    - dgs10_delta
    - vix_change

  t_after_open:
    - qqq_open_gap
    - spy_gap
    - smh_gap
    - mega_cap_basket_gap
    - expected_ndx_move
    - open_gap_residual

  t_after_close:
    - qqq_open_to_close_return

forbidden_layer_edges:
  - from: t_after_close
    to: t_after_open
    reason: future_to_signal_leakage
```

## 7. core_dag.yaml

```yaml
schema_version: core_dag.v1
dag_id: HYP-NDX-001
name: ndx_open_gap_residual
scope_id: NDX_SCOPE_V1

nodes:
  - id: spy_gap
    role: confounder
  - id: smh_gap
    role: confounder
  - id: dgs10_delta
    role: confounder
  - id: vix_change
    role: moderator
  - id: mega_cap_basket_gap
    role: confounder
  - id: expected_ndx_move
    role: modeled_latent
  - id: qqq_open_gap
    role: observed_proxy
  - id: open_gap_residual
    role: treatment_candidate
  - id: qqq_open_to_close_return
    role: outcome

edges:
  - from: spy_gap
    to: expected_ndx_move
  - from: smh_gap
    to: expected_ndx_move
  - from: dgs10_delta
    to: expected_ndx_move
  - from: vix_change
    to: expected_ndx_move
  - from: mega_cap_basket_gap
    to: expected_ndx_move
  - from: expected_ndx_move
    to: open_gap_residual
  - from: qqq_open_gap
    to: open_gap_residual
  - from: open_gap_residual
    to: qqq_open_to_close_return

forbidden_edges:
  - from: qqq_open_to_close_return
    to: open_gap_residual
    reason: future_to_signal_leakage
  - from: qqq_open_to_close_return
    to: expected_ndx_move
    reason: outcome_to_model_input

counter_dag_refs:
  - BroadMarketOnlyDAG
  - RatesOnlyDAG
  - SOXOnlyDAG
  - MegaCapOnlyDAG
  - VolRegimeOnlyDAG
  - SelectionBiasDAG
```

## 8. counter_dags.yaml

```yaml
schema_version: counter_dag_registry.v1
dag_id: HYP-NDX-001

counter_dags:
  - id: BroadMarketOnlyDAG
    description: SPY broad market factor explains both QQQ open gap and O2C behavior.
    changed_assumption: open_gap_residual is an SPY beta artifact.

  - id: RatesOnlyDAG
    description: US rate shock explains the apparent residual.
    changed_assumption: dgs10_delta is insufficiently modeled.

  - id: SOXOnlyDAG
    description: Semiconductor shock explains the apparent residual.
    changed_assumption: SMH/SOX proxy underfits semiconductor factor.

  - id: MegaCapOnlyDAG
    description: Mega-cap basket explains the apparent residual.
    changed_assumption: top-name concentration is the true driver.

  - id: VolRegimeOnlyDAG
    description: VIX/VXN regime explains gap behavior.
    changed_assumption: residual effect is regime-only.

  - id: SelectionBiasDAG
    description: Large gap day selection creates apparent effect.
    changed_assumption: candidate selection is a collider/selection mechanism.
```
