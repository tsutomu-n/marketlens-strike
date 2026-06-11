<!--
作成日: 2026-05-22_11:36 JST
更新日: 2026-06-11_14:29 JST
-->

# Code Status

この文書は current codebase を PR-00 から PR-08 の migration 軸で読むための要約です。実装の正本はコードと tests です。

## Summary

| PR | Title | Status | Evidence |
|---|---|---|---|
| PR-00 | Python 3.13 migration | DONE | pyproject.toml, .python-version, uv.lock, .github/workflows/ci.yml, scripts/check |
| PR-01 | Archive legacy venues | DONE | archive/gtrade_ostium_legacy_archive_*.zip, package.json legacy note, pyproject.toml without ostium-python-sdk |
| PR-02 | Generalize models and schemas | DONE | src/sis/models.py, schemas/, configs/*.yaml, configs/instrument_registry.seed.json |
| PR-03 | Build Trade[XYZ] universe mapping | DONE | src/sis/venues/trade_xyz/registry.py, src/sis/venues/trade_xyz/report.py, tests/test_trade_xyz_registry.py, `perpDexs` fallback |
| PR-04 | Add Trade[XYZ] read-only collector | DONE | src/sis/venues/trade_xyz/collector.py, src/sis/venues/trade_xyz/normalizer.py, tests/test_trade_xyz_collector.py, quote collection summary/report |
| PR-05 | Add real market data layer | DONE | src/sis/real_market/*, tests/test_real_market_models.py, tests/test_real_market_quality.py, tests/test_real_market_features.py |
| PR-06 | Add real vs venue tracking | DONE | src/sis/tracking/*, tests/test_tracking_models.py, tests/test_real_vs_venue_tracking.py, tests/test_lead_lag.py |
| PR-07 | Gate paper execution by venue quality | DONE | src/sis/paper/*, src/sis/core/execution_plan.py, tests/test_paper_trading.py, tests/test_paper_runner.py |
| PR-08 | Add Trade[XYZ] micro live safety canary | DONE | src/sis/execution/trade_xyz_adapter.py, src/sis/execution/live_order_policy.py, src/sis/execution/micro_live_canary.py, PR-08 tests |

## Post-PR08 / PR9a-PR12 Status

| Slice | Status | Evidence |
|---|---|---|
| PR9a CLI import recovery | DONE | `uv run sis --help`, `uv run python -m sis.cli --help` |
| PR9b HIP-3 mapping and contexts | DONE | `perpDexs` asset-id fallback, `metaAndAssetCtxs` enrichment, `tests/test_trade_xyz_registry.py` |
| PR9c fresh quote window | DONE | `collect-trade-xyz-quotes --duration-minutes --interval-seconds --write-summary --write-report`, `data/ops/trade_xyz_quote_collection_summary.json` |
| PR10 strict validation and diagnostics | DONE | `validate-artifacts --strict`, `diagnose-quotes --venue trade_xyz`, `tests/test_validate_artifacts_trade_xyz.py` |
| PR11 operations cutover | DONE | `phase-gate-review` consumes Trade[XYZ] artifacts and emits `READ_ONLY_GO` / `CONDITIONAL_INDEX_ONLY` / `NO_GO` |
| PR12 fresh read-only smoke | DONE | `data/ops/pr12_fresh_read_only_smoke_summary.json`, `data/reports/pr12_fresh_read_only_smoke_report.md` |
| P2 gate restore / fee mode resolution | DONE | `configs/fee_model.trade_xyz.yaml`, `tests/test_trade_xyz_registry.py`, `tests/test_trade_xyz_collector.py`, `tests/test_phase_gate_review.py` |
| P2 execution drift classification | DONE | `src/sis/reports/phase_gate_review.py`, `data/ops/phase_gate_review_summary.json` |
| P2 Alpaca provider stub removal | DONE | `src/sis/real_market/providers/alpaca.py`, `tests/test_alpaca_provider.py` |
| Strategy Research Lab schemas/models | DONE | `src/sis/research/strategy_lab/`, `src/sis/research_protocol/`, `schemas/strategy_authoring_spec.v1.schema.json`, `schemas/strategy_authoring_bundle.v1.schema.json`, `schemas/strategy_authoring_backtest_result.v1.schema.json`, `schemas/strategy_authoring_bundle_result.v1.schema.json`, `schemas/strategy_experiment_spec.v1.schema.json`, `schemas/strategy_signal.v1.schema.json`, `schemas/evaluation_plan.mls.v1.schema.json`, `schemas/trial_record.v1.schema.json`, `schemas/trade_candidate.v1.schema.json`, `schemas/paper_candidate_pack.v1.schema.json`, `schemas/promotion_decision.v1.schema.json`, `schemas/paper_intent_preview.v1.schema.json`, `schemas/data_snapshot_manifest.v1.schema.json`, `schemas/feature_snapshot_manifest.v1.schema.json` |
| Strategy Lab paper-only workflow | DONE | `strategy-preview`, `strategy-experiment-run --spec`, `evaluate-strategy-lab`, `build-paper-candidate-pack`, `promotion-decision`, `build-paper-intent-preview`, `paper-from-intents` |
| Strategy authoring YAML workflow | DONE | `strategy-author-init`, `strategy-author-validate`, `strategy-author-explain`, `strategy-author-run`, `strategy-author-train-model`, `strategy-author-bundle-run`; entry / hold / close / reduce / add / rebalance / long / short / derived features including true range, ATR, Bollinger bands, Donchian channels, Keltner channels, Ichimoku cloud, MACD line, stochastic K/D, ADX, OBV, volume z-score, calendar features, rolling correlation / beta / spread z-score / tracking error / information ratio, flow/carry/liquidity/options-vol, on-chain/sentiment/event/fundamental/factor-ranking, execution-constraint, data-quality/ensemble/capacity features, lag, return/log-return, rolling return/sum/volatility/percentile-rank/skew/kurtosis, annualized volatility, realized variance, downside volatility, Sharpe/Sortino-like ratios, Kelly fraction, historical VaR, expected shortfall, cumulative return, slope, mean-reversion score, EMA, RSI, and rolling min/max / column-to-column and cross/trend/consecutive condition / exclusion-none condition / regime membership filter / regime-specific overrides / paper-only dynamic multi-leg with leg exit, order, execution overrides, group metadata, and group aggregate metrics / pair-trade signal / paper-only linear model score / train-model adapter / group-wise cross-sectional top-bottom and fraction-tail rotation with minimum candidates and score thresholds / opposite-signal exit / explicit close-signal exit / reduce-signal partial exit / add-signal scale-in / rebalance-signal exposure resize / rebalance band skip / bracket-OCO / partial-profit break-even lifecycle / order-style entry / time-in-force / post-only / reduce-only / execution-profile presets / slippage with row cost / partial-fill with row fill / min-fill gate with row threshold / spread gate / depth-based fill / latency gate / queue-position gate with row threshold / short-borrow availability/cost gate with row threshold / tax-drag-with-row-threshold / turnover-capacity-crowding-fee gate / stop-loss / take-profit / stop/target width guard / reward-risk gate / close-signal exit / partial exit / trailing stop with optional activation / minimum/maximum holding period with row thresholds / exit priority / sizing / grouped, group-net, row-level portfolio exposure, and global net portfolio exposure limits / portfolio turnover budget / data guard presets with row thresholds / risk throttle profiles with row thresholds and cooldown / volatility targeting / target-weight / inverse-vol / dollar-neutral / beta-neutral / group-neutral allocation / marker-aware, pyramiding-aware, and opposing-side position-state controls / multi-timeframe confirmation panels / temporal-cadence control / event-window calendar filters / parameter sweep / era metrics / executed_signal_summary / strategy_scorecard / multi-strategy bundle / risk-parity allocation paper backtest; `tests/strategy_authoring/` |
| Trade[XYZ] pure backtest v0.1 | DONE / CLI not public | `src/sis/backtest/engine/`, `src/sis/backtest/trade_xyz/`, `tests/backtest/`, `docs/backtest/` |
| Backtest-first baseline seed | DONE | `scripts/seed_strategy_authoring_baseline_data.py`, `docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml`, `strategy-author-run --through backtest` |
| Venue-neutral Strategy Lab contract | DONE | `src/sis/venues/ids.py`, `src/sis/research/strategy_lab/specs.py`, `schemas/strategy_signal.v1.schema.json`, `schemas/trade_candidate.v1.schema.json`, `schemas/paper_intent_preview.v1.schema.json` |
| NDX/QQQ venue suitability paper-path gate | DONE / fail-closed | `src/sis/venues/suitability.py`, `src/sis/research/strategy_lab/paper_candidate_pack.py`, `src/sis/research/strategy_lab/paper_intent_preview.py`, `src/sis/paper/runner.py`, `tests/test_venue_suitability.py`, `tests/test_strategy_lab_candidate_pack.py`, `tests/test_paper_from_intents.py`, `tests/test_paper_runner.py` |
| Bitget / Hyperliquid venue capability gate | DONE / fixture-first capability contract with evaluation-plan split | `src/sis/venues/capabilities.py`, `tests/test_venue_capabilities.py`, `docs/venues/bitget_hyperliquid_capability_gate.md` |
| Bitget demo local smoke | DONE / external network not proven | `src/sis/execution/bitget_demo_adapter.py`, `tests/test_bitget_demo_adapter.py`, `tests/test_bitget_demo_cli.py`, `uv run sis bitget-demo-smoke` |
| Venue-specific paper fee lookup | DONE | `src/sis/paper/broker.py`, `src/sis/paper/runner.py`, `configs/fee_model.bitget_demo.yaml`, `tests/test_paper_from_intents.py` |
| NDX Layer 2.2 DAG foundation | DONE / local-only | `configs/research_layer_2_2/ndx/`, `src/sis/research/dag/`, `tests/research/`, `research-layer22-validate`, `research-layer22-export` |
| Layer 2.2 Exit Gate Review Harness | DONE / acceptance-hardened / manual local review only | `schemas/llm_dag_review.v1.schema.json`, `schemas/layer_2_2_*.schema.json`, `research-layer22-review-pack`, `research-layer22-review-import`, `research-layer22-exit-gate`, `docs/research/ndx/09_LLM_REVIEW_GATE.md`; `APPROVE_2_3` requires no second review, no unresolved human decisions, no blockers, and non-approve runs remove stale freeze manifests |
| NDX Layer 2.3 Preflight / Feature Panel / Open Gap Residual | DONE / local fixture-first / no Strategy Lab export | `src/sis/research/ndx/`, `configs/research_layer_2_3/ndx/`, `schemas/ndx_data_source_resolution.v1.schema.json`, `schemas/ndx_feature_manifest.v1.schema.json`, `schemas/ndx_open_gap_residual_manifest.v1.schema.json`, `research-ndx-source-resolve`, `research-ndx-feature-panel`, `research-ndx-residual`, `research-ndx-diagnostics`, `tests/research/test_ndx_layer23.py`, `docs/research/ndx/10_LAYER_2_3_NDX_PREFLIGHT.md` |
| NDX Layer 2.4 Residual Validation Gate | DONE / current default artifacts approve research export | `configs/research_layer_2_4/ndx/`, `schemas/ndx_residual_validation_decision.v1.schema.json`, `schemas/ndx_residual_validation_summary.v1.schema.json`, `research-ndx-residual-validate`, `tests/research/test_ndx_layer24_residual_validation.py`, `docs/research/ndx/11_LAYER_2_4_RESIDUAL_VALIDATION_GATE.md`; current default decision is `APPROVE_STRATEGY_LAB_EXPORT` |
| NDX Layer 2.5 Strategy Lab research-only export | DONE / paper path fail-closed | `src/sis/research/ndx/strategy_lab_export.py`, `schemas/ndx_strategy_lab_research_export_manifest.v1.schema.json`, `research-ndx-strategy-lab-export`, `tests/research/test_ndx_layer25_strategy_lab_export.py`, `docs/research/ndx/12_LAYER_2_5_STRATEGY_LAB_RESEARCH_EXPORT.md`; writes research-only `strategy_signals.parquet` and preserves overwrite guard |
| NDX Layer 2.6/2.7 paper observation gate and operator promotion | DONE / paper-only unlock with evidence | `src/sis/research/ndx/paper_observation_gate.py`, `src/sis/research/ndx/operator_promotion.py`, `schemas/ndx_paper_observation_gate_decision.v1.schema.json`, `schemas/ndx_operator_promotion_decision.v1.schema.json`, `research-ndx-paper-observation-gate`, `research-ndx-operator-promotion`, `tests/research/test_ndx_layer26_paper_observation_gate.py`, `tests/research/test_ndx_layer27_operator_promotion.py`, `docs/research/ndx/13_LAYER_2_6_PAPER_OBSERVATION_GATE.md`, `docs/research/ndx/14_LAYER_2_7_OPERATOR_PROMOTION.md`; unlocks NDX/QQQ paper observation only when evidence hashes match and keeps live disabled |

## Current Operational Interpretation

- migration 実装は完了している。
- current development path は backtest-first / venue-neutral。Trade[XYZ] は実装済み主要 venue だが、現時点の注文口主軸ではない。
- `VenueId` は `trade_xyz` と `bitget_demo`。`bitget_demo` は demo execution 検証用で、production Bitget live とは分ける。
- Strategy Authoring baseline fixture は local seed で作れる。これは Trade[XYZ] `backtest_data_ready=true` ではない。
- Trade[XYZ]実データ収集の非秘密な対象symbol、quote収集間隔、signal candle interval、readiness閾値、archive対象coinは `configs/trade_xyz_data_collection.yaml` が正本。shell wrapperは空のenv設定時にこのYAMLを読む。
- 2026-05-30以前の実データは現行Trade[XYZ] backtest/readiness作業では使用禁止。該当artifactは `data/archive/pre_2026_05_31_unusable_real_data/` に移動済み。
- `src/sis/cli.py` は root Typer app registration と `main()` に近い構成へ分割済み。
- Trade[XYZ] read-only artifacts は strict validation / diagnostics / phase gate に接続済み。
- Trade[XYZ] pure backtest v0.1 は既存 bridge / Strategy Authoring fixed-horizon backtest と分離した Python API surface として実装済み。
- Trade[XYZ] fee fields は `configs/fee_model.trade_xyz.yaml` の explicit classification から registry / raw quote row へ伝播する。
- phase gate は execution drift を `P2_BLOCKER` と `LIVE_READINESS_BLOCKER` に分類する。
- phase gate は `phase2_entry_allowed=true` かつ `P2_BLOCKER=0` の場合、live-readiness-only drift を P2 remediation order に入れない。
- Alpaca provider は silent empty stub ではない。credentials 未設定時は controlled failure、成功時は Alpaca stock bars response を `RealMarketBar` に変換する。
- `bot-preview` は実行時に read-only HOLD decision と preview report を生成する。
- Strategy Research Lab は strategy definition / signal / evaluation / trial ledger / candidate pack / promotion decision / paper intent preview の code surface を持つ。
- Venue suitability は `src/sis/venues/suitability.py` が正本。catalog には `trade_xyz`, `bitget_demo`, `bitget_futures`, `hyperliquid_perp` があるが、現行 `VenueId` と Strategy Lab schema は `trade_xyz` / `bitget_demo` のまま。
- Venue capability は `src/sis/venues/capabilities.py` が正本。`bitget_futures` と `hyperliquid_perp` は known future venues だが、現行では schema / paper / network / live が disabled。`bitget_demo` は execution-venue schema では enabled だが、`evaluation_plan.mls.v1` の `target_venue` では disabled。
- NDX/QQQ family は research/backtest record として保持できるが、`PaperCandidatePack.selected_candidate_ids`、`PaperIntentPreview`、raw JSON の `paper-from-intents`、legacy `paper-step` order generation では fail closed する。
- Strategy authoring は `strategy_authoring_spec.v1` YAML から rule-based long / short / hold / close / reduce / add / rebalance signal、derived features including true range, ATR, Bollinger bands, Donchian channels, Keltner channels, Ichimoku cloud, MACD line, stochastic K/D, ADX, OBV, volume z-score, calendar features, rolling correlation / beta / spread z-score / tracking error / information ratio, flow/carry/liquidity/options-vol, on-chain/sentiment/event/fundamental/factor-ranking, execution-constraint, data-quality/ensemble/capacity features, lag, return/log-return, rolling return/sum/volatility/percentile-rank/skew/kurtosis, annualized volatility, realized variance, downside volatility, Sharpe/Sortino-like ratios, Kelly fraction, historical VaR, expected shortfall, cumulative return, slope, mean-reversion score, EMA, RSI, and rolling min/max、column-to-column and cross/trend/consecutive condition、exclusion-none condition、regime membership filter、regime-specific overrides、paper-only dynamic multi-leg with leg exit, order, execution overrides, group metadata, and group aggregate metrics / pair-trade signal、paper-only linear model score / train-model adapter、group-wise cross-sectional top-bottom and fraction-tail rotation with minimum candidates and score thresholds、opposite-signal exit / explicit close-signal exit / reduce-signal partial exit / add-signal scale-in / rebalance-signal exposure resize / rebalance band skip、bracket-OCO / partial-profit break-even lifecycle、order-style entry / time-in-force / post-only / reduce-only、execution-profile presets、slippage with row cost、partial-fill with row fill、min-fill gate with row threshold、spread gate、depth-based fill、latency gate、queue-position gate with row threshold、short-borrow availability/cost gate with row threshold / tax-drag-with-row-threshold / turnover-capacity-crowding-fee gate、fixed-horizon backtest metrics、partial exit / trailing stop with optional activation / minimum/maximum holding period with row thresholds / exit priority / sizing / grouped, group-net, row-level portfolio exposure, and global net portfolio exposure limits / portfolio turnover budget / data guard presets with row thresholds / risk throttle profiles with row thresholds and cooldown / volatility targeting / target-weight / inverse-vol / dollar-neutral / beta-neutral / group-neutral allocation / marker-aware, pyramiding-aware, and opposing-side position-state controls / multi-timeframe confirmation panels / temporal-cadence control / event-window calendar filters / parameter sweep / era metrics と executed_signal_summary と strategy_scorecard 付き paper-only preview artifacts を作れる。`strategy_authoring_bundle.v1` は複数 spec の paper portfolio 比較を作る。
- `PaperIntentPreview` は paper-only artifact で、`requires_revalidation=true`, `live_conversion_allowed=false`, `wallet_used=false`, `exchange_write_used=false` を model validation で守る。
- `bitget-demo-smoke` の `status=configured` は local credential env が揃った意味だけであり、Bitget network connectivity / account read / demo order submit / fill sync を証明しない。
- tracked JSON Schema は guard / interoperability 用の薄い契約であり、詳細 validation は Pydantic model が正本。claim guard は `*_claimed` 名に統一済み。
- NDX Layer 2.2 review gate は手動 review JSON を local import する harness。`APPROVE_2_3` は `second_review_required=false`、未解決 human decision なし、BLOCKER なしの場合だけ成立し、`REVISE_2_2` / `REJECT_SEED` では freeze manifest を残さない。外部 LLM API、credentials、feature panel、residual calculation、neutralization、Strategy Lab export、backtest、paper/live connection は実装範囲外。
- NDX Layer 2.3/2.4/2.5 は Layer 2.2 approval/freeze 後の local research gates。feature panel、open-gap residual、diagnostics、residual validation、research-only Strategy Lab export を扱うが、backtest、paper candidate approval、`PaperIntentPreview` 通過、paper/live order、external API、credentials、dependency追加には接続しない。
- 現在の NDX Layer 2.4 default artifact 判断は `APPROVE_STRATEGY_LAB_EXPORT`。これは Layer 2.5 research-only export bridge の許可であり、alpha、backtest、paper/live readiness ではない。
- NDX Layer 2.5 export 由来の Strategy Lab signal は `RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED` を持つため、paper candidate selection と `PaperIntentPreview` は fail closed する。
- production live trading は未接続なので、"read-only gate complete" と "live trading ready" は分けて扱う。
- Trade[XYZ] pure backtest artifact は live order artifact ではない。`backtest_run.json` は `no_live_order=true`, `wallet_used=false`, `exchange_write_used=false` を記録する。
- `probe trade-xyz` は live `perpDexs` から `asset_id` を解決できる。解決不能時は従来どおり `api_orderable=false` で fail-closed。

## Verified Acceptance Highlights

PR-07:

- best bid / ask 優先の fill price selection
- tracking / source confidence / venue quality / spread / depth / funding gate
- `configs/fee_model.trade_xyz.yaml` を使う round-trip cost model
- paper report に `source_confidence`, `venue_quality_score`, `block_reasons`, `fee_mode`, `estimated_round_trip_cost_bps`, `fill_price_source`

PR-08:

- disabled micro live, confirm flag, scheduleCancel, market order, notional, leverage, session, event blackout, source confidence, venue quality, open-position gate
- `scheduleCancel -> place limit order -> orderStatus by cloid -> cancelByCloid or reduce-only close`
- `micro_live_safety_report` と audit bundle の生成
- standard verification は mock / fake exchange / dry-run policy tests のみ

## Known Gaps By Design

- manual signing, wallet secrets, exchange write credentials
- public CLI からの micro live 実行 surface
- production live trading
- live order preview / 注文候補生成の正式 artifact surface
- Strategy Lab から micro live への直接昇格 surface
- Trade[XYZ] pure backtest の public CLI
- NDX/QQQ family の paper candidate / paper intent / legacy paper-step 通過
- NDX Layer 2.6 backtest acceptance gate for NDX residual-derived Strategy Lab signals
- NDX residual-derived signals の operator promotion path
- Bitget credentialed read-only network smoke
- Bitget demo order lifecycle
- Alpaca historical connectivity smoke は確認済み。fresh live `status=pass` は市場時間中の fresh bar 取得で再確認する
- execution drift の live-readiness blocker 解消
- side-specific depth は quote field と tracking gate に存在する。read-only phase gate は spread / stale / l2-only / fee unknown を current blocker として見る。

## Verification

current verification は固定の pass count ではなく、作業時点で次を再実行して確認する:

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```

2026-06-06 docs-only spot check:

- `uv run python scripts/check_current_docs.py`: pass, current-doc allowlist checked successfully

2026-06-10 NDX Layer 2.2/2.3/2.4/2.5 local research gate snapshot:

- `uv run sis --help`: `research-layer22-review-pack`, `research-layer22-review-import`, `research-layer22-exit-gate`, `research-ndx-source-resolve`, `research-ndx-feature-panel`, `research-ndx-residual`, `research-ndx-diagnostics`, `research-ndx-residual-validate`, `research-ndx-strategy-lab-export` registered
- latest local exit decision artifact: `APPROVE_2_3`, `second_review_required=false`, unresolved human decision count `0`, blocker count `0`, pack hash `sha256:7fc0d644d4a8d7432df29a8dfd6c878fc97342b5745febc26e6cd6206a01dd6a`
- latest Layer 2.4 decision artifact: `APPROVE_STRATEGY_LAB_EXPORT`, `reason_codes=[]`, `permits_strategy_lab_research_only_export=true`
- latest Layer 2.5 export artifact: `export_id=sha256:6e205549d2bc81ae8a99f316b29a3c1b496272f30b417cff71e2404e21f3465d`, `signal_count=84`, `replace_existing=true`, previous signal hash `sha256:8eb8fde20b1decf3e473d5122213e9cca3c31c6b00ebb343ee41b26d360d83e7`
- latest paper candidate check after NDX Layer 2.5 export: `selected_candidate_ids=[]`; first candidate is blocked by `RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED` and `VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION`
- latest `PaperIntentPreview` after promotion decision: empty list, `intent_count=0`

2026-06-05 runtime artifact snapshot:

- targeted P2 tests: Trade[XYZ] / quote diagnostics / phase gate / Alpaca / tracking tests pass
- latest strict validation: `checked_files=12`, `issues=0`
- latest phase gate: `READ_ONLY_GO`, `phase2_entry_allowed=true`, `blockers=[]`, `P2_BLOCKER=0`, `LIVE_READINESS_BLOCKER=5`
- latest data readiness: `NOT_READY`, fail=`quote_coverage`, known gaps=`funding_events`,`oracle_timestamp_provenance`; `real_market_reference`, `signal_candles`, and `account_specific_fee` are pass. `funding_events_from_history` is usable but partial: `row_count=605`, `skipped.missing_oracle_quote_within_lag=671`.

## Reading Pointers

- historical migration contract: `plan/archive/PR-00_to_PR-08_implementation_plan.md`
- Strategy Lab doc audit and schema spec: `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`
- backtest surface guide: `docs/backtest/README.md`
- Trade[XYZ] pure backtest v0.1: `docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md`
- Strategy Lab detailed specs: `docs/strategy_research_lab/README.md`
- runtime status: `docs/CURRENT_STATE.md`
- NDX docs: `docs/research/ndx/README.md`
- Layer 2.2 review gate: `docs/research/ndx/09_LLM_REVIEW_GATE.md`
- Layer 2.3 preflight / feature panel / residual: `docs/research/ndx/10_LAYER_2_3_NDX_PREFLIGHT.md`
- Layer 2.4 residual validation gate: `docs/research/ndx/11_LAYER_2_4_RESIDUAL_VALIDATION_GATE.md`
- operator procedure: `docs/OPERATIONS_RUNBOOK.md`
- architecture and boundaries: `docs/ARCHITECTURE_AND_PHASES.md`
- historical Trade[XYZ] implementation audit: `docs/archive/2026-06-05-doc-cleanup/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md`
