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

## Current Operational Interpretation

- migration 実装は完了している。
- `src/sis/cli.py` は root Typer app registration と `main()` に近い構成へ分割済み。
- Trade[XYZ] read-only artifacts は strict validation / diagnostics / phase gate に接続済み。
- Trade[XYZ] fee fields は `configs/fee_model.trade_xyz.yaml` の explicit classification から registry / raw quote row へ伝播する。
- phase gate は execution drift を `P2_BLOCKER` と `LIVE_READINESS_BLOCKER` に分類する。
- phase gate は `phase2_entry_allowed=true` かつ `P2_BLOCKER=0` の場合、live-readiness-only drift を P2 remediation order に入れない。
- Alpaca provider は silent empty stub ではない。credentials 未設定時は controlled failure、成功時は Alpaca stock bars response を `RealMarketBar` に変換する。
- `bot-preview` は実行時に read-only HOLD decision と preview report を生成する。
- Strategy Research Lab は strategy definition / signal / evaluation / trial ledger / candidate pack / promotion decision / paper intent preview の code surface を持つ。
- Strategy authoring は `strategy_authoring_spec.v1` YAML から rule-based long / short / hold / close / reduce / add / rebalance signal、derived features including true range, ATR, Bollinger bands, Donchian channels, Keltner channels, Ichimoku cloud, MACD line, stochastic K/D, ADX, OBV, volume z-score, calendar features, rolling correlation / beta / spread z-score / tracking error / information ratio, flow/carry/liquidity/options-vol, on-chain/sentiment/event/fundamental/factor-ranking, execution-constraint, data-quality/ensemble/capacity features, lag, return/log-return, rolling return/sum/volatility/percentile-rank/skew/kurtosis, annualized volatility, realized variance, downside volatility, Sharpe/Sortino-like ratios, Kelly fraction, historical VaR, expected shortfall, cumulative return, slope, mean-reversion score, EMA, RSI, and rolling min/max、column-to-column and cross/trend/consecutive condition、exclusion-none condition、regime membership filter、regime-specific overrides、paper-only dynamic multi-leg with leg exit, order, execution overrides, group metadata, and group aggregate metrics / pair-trade signal、paper-only linear model score / train-model adapter、group-wise cross-sectional top-bottom and fraction-tail rotation with minimum candidates and score thresholds、opposite-signal exit / explicit close-signal exit / reduce-signal partial exit / add-signal scale-in / rebalance-signal exposure resize / rebalance band skip、bracket-OCO / partial-profit break-even lifecycle、order-style entry / time-in-force / post-only / reduce-only、execution-profile presets、slippage with row cost、partial-fill with row fill、min-fill gate with row threshold、spread gate、depth-based fill、latency gate、queue-position gate with row threshold、short-borrow availability/cost gate with row threshold / tax-drag-with-row-threshold / turnover-capacity-crowding-fee gate、fixed-horizon backtest metrics、partial exit / trailing stop with optional activation / minimum/maximum holding period with row thresholds / exit priority / sizing / grouped, group-net, row-level portfolio exposure, and global net portfolio exposure limits / portfolio turnover budget / data guard presets with row thresholds / risk throttle profiles with row thresholds and cooldown / volatility targeting / target-weight / inverse-vol / dollar-neutral / beta-neutral / group-neutral allocation / marker-aware, pyramiding-aware, and opposing-side position-state controls / multi-timeframe confirmation panels / temporal-cadence control / event-window calendar filters / parameter sweep / era metrics と executed_signal_summary と strategy_scorecard 付き paper-only preview artifacts を作れる。`strategy_authoring_bundle.v1` は複数 spec の paper portfolio 比較を作る。
- `PaperIntentPreview` は paper-only artifact で、`requires_revalidation=true`, `live_conversion_allowed=false`, `wallet_used=false`, `exchange_write_used=false` を model validation で守る。
- tracked JSON Schema は guard / interoperability 用の薄い契約であり、詳細 validation は Pydantic model が正本。claim guard は `*_claimed` 名に統一済み。
- production live trading は未接続なので、"read-only gate complete" と "live trading ready" は分けて扱う。
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
- Alpaca credentials ありの API connectivity は確認済み。fresh live `status=pass` は市場時間中の fresh bar 取得で再確認する
- execution drift の live-readiness blocker 解消
- side-specific depth は quote field と tracking gate に存在する。read-only phase gate は spread / stale / l2-only / fee unknown を current blocker として見る。

## Verification

2026-05-31 code/docs verification:

- `uv run python -V`: pass
- `uv run ruff check .`: pass
- `uv run pyrefly check`: pass
- `uv run pytest -q`: 593 passed via `./scripts/check`
- `./scripts/check`: pass, 593 passed
- `uv run python scripts/check_current_docs.py`: pass, `checked 78 current docs`

2026-05-28 runtime artifact snapshot:

- targeted P2 tests: Trade[XYZ] / quote diagnostics / phase gate / Alpaca / tracking tests pass
- latest strict validation: `checked_files=12`, `issues=0`
- latest phase gate: `READ_ONLY_GO`, `phase2_entry_allowed=true`, `blockers=[]`, `P2_BLOCKER=0`, `LIVE_READINESS_BLOCKER=5`

## Reading Pointers

- historical migration contract: `plan/archive/PR-00_to_PR-08_implementation_plan.md`
- Strategy Lab doc audit and schema spec: `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`
- Strategy Lab detailed specs: `docs/strategy_research_lab/README.md`
- runtime status: `docs/CURRENT_STATE.md`
- operator procedure: `docs/OPERATIONS_RUNBOOK.md`
- architecture and boundaries: `docs/ARCHITECTURE_AND_PHASES.md`
- historical Trade[XYZ] implementation audit: `docs/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md`
