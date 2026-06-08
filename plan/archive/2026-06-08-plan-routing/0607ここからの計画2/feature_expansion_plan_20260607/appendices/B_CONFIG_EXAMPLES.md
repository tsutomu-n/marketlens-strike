<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# Appendix B: Config Examples

## scope.yaml

```yaml
schema_version: research_scope.v1
scope_id: NDX_SCOPE_V1
name: nasdaq_100_single_scope

included:
  primary_concepts:
    - NDX
  observed_proxies:
    - QQQ
  optional_price_discovery:
    - NQ

excluded:
  - Nikkei
  - TOPIX
  - JapanEquities
  - USDJPY_as_primary
  - TradeXYZ_order_execution
  - Bitget_demo_network
  - paper_live_order
  - external_api_fetch
```

## data_sources.yaml

```yaml
schema_version: research_data_sources.v1
scope_id: NDX_SCOPE_V1

sources:
  QQQ:
    source_tier: defined_proxy
    role: etf_observed_proxy
    initial_required: true
    provider_future: yfinance_or_alpaca
    fetch_in_this_phase: false

  NDX:
    source_tier: benchmark_concept
    role: index_concept
    initial_required: false
    fetch_in_this_phase: false

  NQ:
    source_tier: deferred_optional
    role: futures_price_discovery_proxy
    initial_required: false
    fetch_in_this_phase: false

  SPY:
    source_tier: defined_proxy
    role: broad_market_proxy
    initial_required: true
    fetch_in_this_phase: false

  SMH:
    source_tier: defined_proxy
    role: semiconductor_proxy
    initial_required: true
    fetch_in_this_phase: false

  SOX:
    source_tier: optional_provider_dependent
    role: semiconductor_index_proxy
    initial_required: false
    fetch_in_this_phase: false

  VIX:
    source_tier: defined_proxy
    role: vol_regime_proxy
    initial_required: true
    fetch_in_this_phase: false

  VXN:
    source_tier: optional_provider_dependent
    role: nasdaq_vol_regime_proxy
    initial_required: false
    fetch_in_this_phase: false

  DGS10:
    source_tier: defined_future_provider
    role: rates_proxy
    initial_required: true
    provider_future: fred
    fetch_in_this_phase: false
```

## core_dag.yaml

```yaml
schema_version: core_dag.v1
dag_id: HYP-NDX-001
name: ndx_open_gap_residual
scope_id: NDX_SCOPE_V1

nodes:
  - node_id: spx_broad_market
    role: confounder
    variable_ref: spy_gap
    proxy: SPY
    temporal_layer: t_open_plus_buffer

  - node_id: rates_duration
    role: confounder
    variable_ref: dgs10_delta
    proxy: DGS10
    temporal_layer: t_pre_open

  - node_id: semiconductor_shock
    role: confounder
    variable_ref: smh_gap
    proxy: SMH
    temporal_layer: t_open_plus_buffer

  - node_id: vol_regime
    role: moderator
    variable_ref: vix_level
    proxy: VIX
    temporal_layer: t_pre_open

  - node_id: mega_cap_concentration
    role: confounder
    variable_ref: mega_cap_basket_gap
    proxy: MEGA_CAP_BASKET
    temporal_layer: t_open_plus_buffer

  - node_id: expected_ndx_move
    role: modeled_latent
    variable_ref: expected_ndx_move
    temporal_layer: t_open_plus_buffer

  - node_id: actual_open_gap
    role: observed_proxy
    variable_ref: qqq_open_gap
    proxy: QQQ
    temporal_layer: t_open_plus_buffer

  - node_id: open_gap_residual
    role: treatment_candidate
    variable_ref: open_gap_residual
    temporal_layer: t_open_plus_buffer

  - node_id: open_to_close_return
    role: outcome
    variable_ref: qqq_open_to_close_return
    temporal_layer: t_after_close

edges:
  - source: spx_broad_market
    target: expected_ndx_move
    rationale: Broad US equity market explains part of QQQ/NDX gap.
  - source: rates_duration
    target: expected_ndx_move
    rationale: Growth duration pressure explains part of NDX move.
  - source: semiconductor_shock
    target: expected_ndx_move
    rationale: Semiconductor complex explains part of NDX move.
  - source: vol_regime
    target: expected_ndx_move
    rationale: Vol regime changes expected gap behavior.
  - source: mega_cap_concentration
    target: expected_ndx_move
    rationale: Mega-cap basket can dominate Nasdaq-100 move.
  - source: expected_ndx_move
    target: open_gap_residual
    rationale: Residual is actual open gap net of known expected component.
  - source: actual_open_gap
    target: open_gap_residual
    rationale: Residual is actual gap minus expected gap.
  - source: open_gap_residual
    target: open_to_close_return
    rationale: Research question: residual gap may predict RTH reversal or continuation.

forbidden_edges:
  - source: open_to_close_return
    target: open_gap_residual
    reason: future_to_signal_leakage
  - source: qqq_close
    target: actual_open_gap
    reason: same_day_close_is_post_open_outcome_information

counter_dag_refs:
  - BroadMarketOnlyDAG
  - RatesOnlyDAG
  - SemiconductorOnlyDAG
  - MegaCapOnlyDAG
  - VolRegimeOnlyDAG
  - ETFTrackingNoiseDAG
  - FuturesPriceDiscoveryDAG
  - IndexRebalanceDAG
```
