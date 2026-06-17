<!--
作成日: 2026-05-25_19:45 JST
更新日: 2026-06-17_20:44 JST
-->

# Current State

この文書は `marketlens-strike` の tracked docs 側の current truth を短く読むための入口です。最終的な正本はコード、設定、tests、生成 artifact です。

## 結論

- `plan/archive/PR-00_to_PR-08_implementation_plan.md` の PR-00 から PR-08 まで、コードとテストの実装は完了している。
- 現在の開発主軸は backtest-first / venue-neutral。Trade[XYZ] は実装済みの主要 venue で、将来の注文口候補として残すが、当面の注文口前提にはしない。
- ここからの現実的な方向は `docs/NEXT_DIRECTION_CURRENT.md` に分ける。current status はこの文書、実装済み surface は `docs/IMPLEMENTED_SURFACES.md`、実務的な次方向は `docs/NEXT_DIRECTION_CURRENT.md` を読む。
- `VenueId` は `trade_xyz` と `bitget_demo` を許可する。Strategy Lab の signal / candidate / paper intent schema も同じ enum に揃っている。
- `VENUE_SUITABILITY_CATALOG` は `trade_xyz`, `bitget_demo`, `bitget_futures`, `hyperliquid_perp` を持つが、`bitget_futures` と `hyperliquid_perp` は catalog-only で、現行 `VenueId` や Strategy Lab artifact schema には入らない。
- `src/sis/venues/capabilities.py` は `bitget_futures` と `hyperliquid_perp` を known but schema-disabled / paper-disabled / network-disabled / live-disabled として固定する。`bitget_demo` は execution-venue schema では許可されるが、`evaluation_plan.mls.v1` の `target_venue` としてはまだ disabled。
- `venue-read-only-probe` は 4 venue の capability boundary を fixture-first local artifact として出す。external API、credentials、wallet、signing、exchange write、live order、network attempt は使わない。これは network readiness、paper permission、live permission ではない。
- Strategy Authoring baseline は外部 API なしの fixture seed で backtest まで通せる。
- Strategy Lifecycle control plane は `strategy-backtest-acceptance`、`strategy-paper-observation-cycle`、`strategy-lifecycle-review`、`strategy-paper-observation-status` に実装済み。Backtest acceptance、fresh paper intent generation、session manifest / session ledger、NDX paper observation review、phase gate summary を local artifact で統合し、`REJECT_OR_REVISE` / `CONTINUE_RESEARCH` / `BACKTEST_ACCEPTED` / `CONTINUE_PAPER_OBSERVATION` / `CONTINUE_EXECUTION_READINESS` / `ELIGIBLE_FOR_LIVE_CANARY_PLAN` / `BLOCKED_BOUNDARY_VIOLATION` を出す。`strategy-paper-observation-status` は既存 review / session / lifecycle artifact を読み、normal threshold と smoke threshold を分けて status artifact にする。これは paper intent 生成、paper order 実行、ledger 再集計、live order、wallet、exchange write を許可しない。`strategy-backtest-suite` は `strategy_backtest_suite.v1` YAML から複数spec / 複数backtest case を実行し、suite result / report に集約し、標準例では `single_window`、`walk_forward:trading_day`、`purged_walk_forward:trading_day`、`purged_walk_forward:trading_day+return_bootstrap`、`purged_walk_forward:trading_day+block_bootstrap` の手法別 run 数を `method_matrix` に記録する。resampling case は実行済み signal return から deterministic bootstrap 分布を作り、`summary.resampling` に p05 / p50 / p95 / positive rate を残す。`strategy-backtest-stress`、`strategy-backtest-regime-split`、`strategy-backtest-rolling-stability`、`strategy-backtest-benchmark-relative` は paper-only robustness artifact を作る。`strategy-backtest-benchmark-relative` は row-level、明示 external series、quote-derived benchmark return を source hash 付きで扱える。`strategy-backtest-compare` は現行 backtest metrics を比較用 canonical artifact に正規化し、native overall / walk-forward era / optimizer sweep、suite result、adapter spike、external framework result、portfolio comparison、metric extension、report extension、stress、regime split、rolling stability、benchmark relative を同じ artifact に記録する。`strategy-backtest-pack` は標準 artifact chain を一括生成し、標準 engine は `strategy_authoring_native`、標準完成線は `complete_without_locked_external_dependency`、`external_adapters_required_for_completion=false` である。`vectorbt==1.0.0` は `vectorbt` optional extra、`bt==1.2.0` は `bt` optional extra、`empyrical-reloaded==0.5.12` は `metrics` optional extra、`quantstats==0.0.81` は `reports` optional extra として採用済みで、それぞれ `dependency_source=optional_extra_available` を artifact に記録する。`vectorbt` は `Apache 2.0 with Commons Clause` の license decision を owner 承認済みとして扱う。live 許可は出さない。
- Strategy Review は `strategy-review-build` と `strategy-review-record` に実装済み。前者は既存 backtest pack / validation / optional authoring spec / optional lifecycle review から人間レビュー用の `review.md` と機械検証用の `review_manifest.json` を作る。後者は人間判断を `operator_review.yaml` として hash 付きで保存し、現在の `review.md` / `review_manifest.json` と再照合する。これは alpha、paper readiness、live readiness、paper execution permission を証明しない。入口は `docs/strategy_review/README.md`、copy-paste 手順は `docs/strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md`。
- Bitget demo local smoke は実装済み。ただし `status=configured` は local credential env が揃った意味だけで、Bitget network/account/order readiness ではない。
- PR9a-PR12 の read-only smoke と P2 gate restore まで完了しており、phase gate は `READ_ONLY_GO` になり得る。
- Trade[XYZ] 実データ readiness はまだ `NOT_READY`。現在の fail は `quote_coverage` だけで、known gap は `funding_events` と `oracle_timestamp_provenance` である。
- Trade[XYZ] の対象銘柄は fee mode / taker fee / maker fee を registry と raw quote row に持つ。`fee_mode_unknown_rate` は current gate blocker ではない。
- Trade[XYZ] pure backtest v0.1 は `src/sis/backtest/engine/` と `src/sis/backtest/trade_xyz/` に実装済み。入口は Python API の `run_backtest()` で、public CLI は未公開。
- Strategy Research Lab の schema / model / CLI surface は実装済み。`StrategyExperimentSpec` から `PaperIntentPreview` までを研究、候補生成、評価、paper昇格判断として扱う。
- NDX/QQQ family は research record と backtest input として保持できる。valid な Layer 2.7 operator promotion evidence がない場合、Strategy Lab paper path では `selected_candidate_ids`、`PaperIntentPreview`、raw JSON の `paper-from-intents`、legacy `paper-step` order generation で fail closed する。valid evidence がある場合だけ paper observation に進める。
- Strategy authoring YAML flow は実装済み。`strategy_authoring_spec.v1` から rule-based long / short / hold / close / reduce / add / rebalance signal、derived features including true range, ATR, Bollinger bands, Donchian channels, Keltner channels, Ichimoku cloud, MACD line, stochastic K/D, ADX, OBV, volume z-score, calendar features, rolling correlation / beta / spread z-score / tracking error / information ratio, flow/carry/liquidity/options-vol, on-chain/sentiment/event/fundamental/factor-ranking, execution-constraint, data-quality/ensemble/capacity features, lag, return/log-return, rolling return/sum/volatility/percentile-rank/skew/kurtosis, annualized volatility, realized variance, downside volatility, Sharpe/Sortino-like ratios, Kelly fraction, historical VaR, expected shortfall, cumulative return, slope, mean-reversion score, EMA, RSI, and rolling min/max、column-to-column and cross/trend/consecutive condition、exclusion-none condition、regime membership filter、regime-specific overrides、paper-only dynamic multi-leg with leg exit, order, execution overrides, group metadata, and group aggregate metrics / pair-trade signal、paper-only linear model score / train-model adapter、group-wise cross-sectional top-bottom and fraction-tail rotation with minimum candidates and score thresholds、opposite-signal exit / explicit close-signal exit / reduce-signal partial exit / add-signal scale-in / rebalance-signal exposure resize / rebalance band skip、bracket-OCO / partial-profit break-even lifecycle、order-style entry / time-in-force / post-only / reduce-only、execution-profile presets、slippage with row cost、partial-fill with row fill、min-fill gate with row threshold、spread gate、depth-based fill、latency gate、queue-position gate with row threshold、short-borrow availability/cost gate with row threshold / tax-drag-with-row-threshold / turnover-capacity-crowding-fee gate、fixed-horizon backtest metrics、partial exit / trailing stop with optional activation / minimum/maximum holding period with row thresholds / exit priority / sizing / grouped, group-net, row-level portfolio exposure, and global net portfolio exposure limits / portfolio turnover budget / data guard presets with row thresholds / risk throttle profiles with row thresholds and cooldown / volatility targeting / target-weight / inverse-vol / dollar-neutral / beta-neutral / group-neutral allocation / marker-aware, pyramiding-aware, and opposing-side position-state controls / multi-timeframe confirmation panels / temporal-cadence control / event-window calendar filters / parameter sweep / era metrics と executed_signal_summary と strategy_scorecard 付き paper-only preview artifacts を作れる。`strategy_authoring_bundle.v1` で複数 spec の paper portfolio 比較もできる。
- NDX Layer 2.2 DAG foundation は `configs/research_layer_2_2/ndx/`、`src/sis/research/dag/`、`tests/research/` に実装済み。`research-layer22-validate` / `research-layer22-export` で local-only DAG artifact を検証・生成できる。
- Layer 2.2 Exit Gate Review Harness は受入監査済み。`research-layer22-review-pack`、`research-layer22-review-import`、`research-layer22-exit-gate` で手動 review JSON を local import し、Layer 2.3 へ進めるかを判定する。`APPROVE_2_3` は `second_review_required=false`、未解決 human decision なし、BLOCKER なしの場合だけ成立し、非APPROVE時は同じ出力先の古い freeze manifest も削除する。これは external LLM API、feature panel、residual calculation、Strategy Lab export、backtest、paper/live order には接続しない。
- NDX Layer 2.3 Preflight / Feature Panel / Open Gap Residual は `src/sis/research/ndx/` と `research-ndx-source-resolve` / `research-ndx-feature-panel` / `research-ndx-residual` / `research-ndx-diagnostics` に実装済み。fixture-first artifact を作り、same-day close leakage、per-source timestamp、`source_ts_max <= feature_ts`、DAG lineage を検査する。
- NDX Layer 2.4 Residual Validation Gate は `research-ndx-residual-validate` に実装済み。Layer 2.3 artifact の lineage、timestamp、neutralization、counter-DAG refutation を検査する。現在の default fixture artifact は `APPROVE_STRATEGY_LAB_EXPORT` まで進み、Layer 2.5 の research-only Strategy Lab export bridge を許可する。
- NDX Layer 2.5 Strategy Lab research-only export は `research-ndx-strategy-lab-export` に実装済み。approved residual から `data/research/strategy_signals.parquet` と manifest を生成するが、research-only block reason を付け、既存 artifact は `--replace-existing` なしでは上書きしない。
- NDX Layer 2.6 paper-observation gate は `research-ndx-paper-observation-gate` に実装済み。Layer 2.5 export hash、Strategy Lab signal hash、local `trade_xyz` / `XYZ100` quote evidence を検査し、operator promotion review 可否を記録する。これは alpha proof や robust out-of-sample proof ではない。
- NDX Layer 2.7 operator promotion は `research-ndx-operator-promotion` に実装済み。valid な Layer 2.6 gate hash と operator approval reason がある場合だけ、NDX/QQQ paper candidate / `PaperIntentPreview` を paper observation に限って unlock する。live order、wallet、exchange write は引き続き許可しない。
- NDX Layer 2.8 paper observation review は `research-ndx-paper-observation-review` に実装済み。Layer 2.7 promotion と session manifest または `paper_observation_ledger.jsonl` / paper artifacts を照合し、fills、観測日数、block rate、連続 block、artifact completeness、boundary violation を見て `PASS_PAPER_OBSERVATION_REVIEW`、`NEEDS_MORE_PAPER_OBSERVATION`、`STOP_PAPER_OBSERVATION` を出す。session manifest 指定時は manifest の ledger path / thresholds / source hash を使い、live order、wallet、exchange write は引き続き許可しない。
- `gtrade` / `ostium` の legacy source, sidecar, raw data, registry, 専用テストは ZIP 化済みで、展開済み file tree は active repo から削除済み。
- 実 live order integration はまだ opt-in safety surface 止まりで、現行の public CLI surface には micro live 実行コマンドを出していない。execution drift は live-readiness blocker として残る。

## Source Of Truth

優先順位:

1. `src/`, `tests/`, `configs/`, `schemas/`, `scripts/`
2. generated runtime artifacts under `data/ops/` and `data/reports/`
3. tracked docs under `docs/`
4. `plan/` historical migration contracts
5. `docs/archive/`

`docs/archive/` は historical context です。現行判断の正本にはしません。

## Implemented Surfaces

現行コードで確認できる主要 surface:

- Python 3.13 前提の runtime / lock / CI
- root CLI split: `src/sis/cli.py` は command registration と `main()` が中心で、command 実装は `src/sis/commands/` に分割済み
- legacy `gtrade` / `ostium` の ZIP archive 化と active file tree からの削除
- venue id contract: `src/sis/venues/ids.py` の `VenueId = Literal["trade_xyz", "bitget_demo"]`
- Strategy Authoring baseline seed: `scripts/seed_strategy_authoring_baseline_data.py`
- `Trade[XYZ]` registry builder, universe report, quote collector, quote normalizer
- `Trade[XYZ]` `perpDexs` fallback による HIP-3 `asset_id` 解決
- `Trade[XYZ]` quote collection summary / report / strict artifact validation
- `Trade[XYZ]` diagnostics / strict validation / phase gate cutover for read-only PR12
- `Trade[XYZ]` fee mode resolution through `configs/fee_model.trade_xyz.yaml`, registry rows, raw quote rows, diagnostics, and phase gate
- `Trade[XYZ]` pure backtest engine v0.1: long-only / single-symbol / market-like taker fill / next-row fill / fee, slippage, funding v0 / metrics and report artifacts
- `bot-preview` による read-only HOLD decision / orders preview artifact 生成
- `real_market` feature builder、Alpaca provider、free-source quality gating
- `tracking` layer による real-market vs venue 判定
- venue quality gate 付き paper fill / fee model / paper report
- `Trade[XYZ]` micro live safety adapter / policy / canary code path
- `Trade[XYZ]` read-only execution state collector contract: public user address と明示 opt-in がある時だけ `/info` 由来の account state / open orders / fills を読み、通常実行では external API、wallet、signing、exchange write を使わず未設定理由を出す
- Bitget demo local/mock-first adapter and smoke: `src/sis/execution/bitget_demo_adapter.py`, `uv run sis bitget-demo-smoke`
- read-only execution surfaces, operations dashboard, remediation chain, daemon loop, notification outbox
- Strategy Research Lab models and commands: `StrategyExperimentSpec`, `StrategySignalRecord`, `EvaluationPlan`, `TrialRecord`, `TradeCandidate`, `PaperCandidatePack`, `PromotionDecision`, `PaperIntentPreview`
- Strategy authoring commands: `strategy-author-init`, `strategy-author-validate`, `strategy-author-explain`, `strategy-author-run`, `strategy-author-bundle-run`, `strategy-author-train-model`
- Strategy backtest comparison, suite, adapter spike, optional framework adoption review, vectorbt license decision, external result, portfolio comparison, metric extension, report extension, stress, regime split, rolling stability, benchmark relative, pack, and pack validation commands/docs: `strategy-backtest-compare`, `strategy-backtest-suite`, `strategy-backtest-adapter-spike`, `docs/backtest/OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md`, `docs/backtest/VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md`, `strategy-backtest-external-run`, `strategy-backtest-portfolio-compare`, `strategy-backtest-metric-extension`, `strategy-backtest-report-extension`, `strategy-backtest-stress`, `strategy-backtest-regime-split`, `strategy-backtest-rolling-stability`, `strategy-backtest-benchmark-relative`, `strategy-backtest-pack`, `strategy-backtest-pack-validate`
- Strategy review packet / operator decision artifact: `strategy-review-build`, `strategy-review-record`, `src/sis/strategy_review/`, `schemas/strategy_review_manifest.v1.schema.json`, `schemas/operator_strategy_review.v1.schema.json`, `tests/strategy_review/`, `docs/strategy_review/`
- Strategy Lab JSON schema files under `schemas/`; full runtime validation is in `src/sis/research/strategy_lab/` and `src/sis/research_protocol/`
- venue suitability policy: `src/sis/venues/suitability.py` with `trade_xyz`, `bitget_demo`, `bitget_futures`, `hyperliquid_perp`; current schemas still accept only `trade_xyz` and `bitget_demo`
- venue capability contract: `src/sis/venues/capabilities.py`; `bitget_futures` and `hyperliquid_perp` are known future venues but disabled for schema, paper, network, and live; `bitget_demo` is disabled for `evaluation_plan.mls.v1` target venue
- fixture-first venue read-only capability probe: `venue-read-only-probe`, `src/sis/venues/read_only_probe.py`, `schemas/venue_read_only_probe_summary.v1.schema.json`, `docs/venues/read_only_capability_probe.md`
- NDX Layer 2.2 DAG/review gate schemas: `schemas/research_*.schema.json`, `schemas/core_dag.v1.schema.json`, `schemas/counter_dag.v1.schema.json`, `schemas/llm_dag_review.v1.schema.json`, `schemas/layer_2_2_human_resolutions.v1.schema.json`, `schemas/layer_2_2_exit_decision.v1.schema.json`, `schemas/layer_2_2_freeze_manifest.v1.schema.json`
- NDX Layer 2.3/2.4 schemas: `schemas/ndx_data_source_resolution.v1.schema.json`, `schemas/ndx_feature_manifest.v1.schema.json`, `schemas/ndx_open_gap_residual_manifest.v1.schema.json`, `schemas/ndx_residual_validation_decision.v1.schema.json`, `schemas/ndx_residual_validation_summary.v1.schema.json`

## Important Boundaries

- 新規戦略評価の主経路は backtest-first / venue-neutral。`trade_xyz` は実装済み主要 venue だが、現時点の注文口主軸ではない。
- `bitget_demo` は demo execution 検証用の venue id。production Bitget live とは分ける。
- `status=configured` は Bitget demo local credential env が揃った状態。network接続、account read、demo order submit、fill sync 成功とは読まない。
- legacy venue は `archive/gtrade_ostium_legacy_archive_*.zip` 内の履歴参照として扱う。
- `micro_live` はコードと tests では存在するが、標準の operator CLI にはまだ exposed していない。
- `collect-trade-xyz-quotes` は public CLI command として exposed している。
- `Trade[XYZ]` pure backtest v0.1 は public CLI ではなく Python API surface。`uv run sis build-backtest` は既存 bridge 系 command であり、pure backtest engine の入口ではない。
- `data/` は git 管理外。再開時は artifact を再生成する。
- NDX Layer 2.2/2.3/2.4/2.5 research artifacts under `data/research/ndx/`, `data/research/`, and `data/reports/` are git-ignored runtime outputs. Fresh checkout では `research-layer22-export`、`research-layer22-review-pack`、`research-ndx-source-resolve`、`research-ndx-feature-panel`、`research-ndx-residual`、`research-ndx-diagnostics`、`research-ndx-residual-validate`、`research-ndx-strategy-lab-export` から作り直す。
- `bot-preview` の `data/bot/bot_decision.json` と `data/reports/bot_orders_preview.md` は実行時生成 artifact。現 checkout に無い場合は `uv run sis bot-preview` で再生成する。
- Strategy Lab の canonical signal artifact は `data/research/strategy_signals.parquet`。旧 `data/research/signals.csv` は Strategy Lab 正本ではなく legacy export として読む。
- NDX Layer 2.5 export 由来の `strategy_signals.parquet` は research-only artifact。`evaluate-strategy-lab` と `build-paper-candidate-pack` には渡せるが、valid な Layer 2.6/2.7 paper-observation evidence がない場合は `RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED` と venue suitability gate により paper candidate selection / `PaperIntentPreview` で fail closed する。
- `PaperCandidatePack.selected_candidate_ids` は `status="candidate"`、空の `block_reasons`、venue-suitable の候補だけを受け入れる。NDX/QQQ の `trade_xyz` proxy は `VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION` で止まり、`bitget_demo` / future catalog venues では `VENUE_ASSET_UNIVERSE_MISMATCH` または operator-disabled 理由で止まる。
- Backtest surface の読み分けは `docs/backtest/README.md` に記録する。Trade[XYZ] pure backtest、Strategy Authoring fixed-horizon backtest、legacy bridge を混同しない。
- Strategy Review は existing artifact を読む human-review packet と operator decision artifact。`review_status=READY_FOR_HUMAN_REVIEW`、pack validation `PASS`、`PAPER_OBSERVATION_CANDIDATE` を alpha、paper execution permission、live readiness と読まない。`operator_review.yaml` は `live_allowed=false` / `paper_execution_allowed=false` を固定する。
- Strategy Lab で今できることは `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` に記録する。わかりやすい HTML 版は `docs/strategy_research_lab/08_CURRENT_CAPABILITIES_EXPLAINED.html`。現行では registered generator または `strategy-experiment-run --spec` から signal artifact を作り、threshold sweep、複数 selected signal の candidate 化、authoring YAML からの entry / hold / close / reduce / add / rebalance / long / short / derived features including true range, ATR, Bollinger bands, Donchian channels, Keltner channels, Ichimoku cloud, MACD line, stochastic K/D, ADX, OBV, volume z-score, calendar features, rolling correlation / beta / spread z-score / tracking error / information ratio, flow/carry/liquidity/options-vol, on-chain/sentiment/event/fundamental/factor-ranking, execution-constraint, data-quality/ensemble/capacity features, lag, return/log-return, rolling return/sum/volatility/percentile-rank/skew/kurtosis, annualized volatility, realized variance, downside volatility, Sharpe/Sortino-like ratios, Kelly fraction, historical VaR, expected shortfall, cumulative return, slope, mean-reversion score, EMA, RSI, and rolling min/max / column-to-column and cross/trend/consecutive condition / regime membership filter / regime-specific overrides / paper-only dynamic multi-leg with leg exit, order, execution overrides, group metadata, and group aggregate metrics / pair-trade signal / paper-only linear model score / train-model adapter / group-wise cross-sectional top-bottom and fraction-tail rotation with minimum candidates and score thresholds / opposite-signal exit / explicit close-signal exit / reduce-signal partial exit / add-signal scale-in / rebalance-signal exposure resize / rebalance band skip / bracket-OCO / partial-profit break-even lifecycle / order-style entry / time-in-force / post-only / reduce-only / execution-profile presets / slippage with row cost / partial-fill with row fill / min-fill gate with row threshold / spread gate / depth-based fill / latency gate / queue-position gate with row threshold / short-borrow availability/cost gate with row threshold / tax-drag-with-row-threshold / turnover-capacity-crowding-fee gate / stop-loss / take-profit / stop/target width guard / reward-risk gate / close-signal exit / partial exit / trailing stop with optional activation / minimum/maximum holding period with row thresholds / exit priority / sizing / grouped, group-net, row-level portfolio exposure, and global net portfolio exposure limits / portfolio turnover budget / data guard presets with row thresholds / risk throttle profiles with row thresholds and cooldown / volatility targeting / target-weight / inverse-vol / dollar-neutral / beta-neutral / group-neutral allocation / marker-aware, pyramiding-aware, and opposing-side position-state controls / multi-timeframe confirmation panels / temporal-cadence control / event-window calendar filters / parameter sweep / era metrics と executed_signal_summary と strategy_scorecard 付き fixed-horizon backtest、multi-strategy bundle / risk-parity allocation、paper-only preview まで進められる。
- `PaperIntentPreview` は paper-only の仮注文意図。`live_conversion_allowed=false`, `wallet_used=false`, `exchange_write_used=false` を守り、live order として扱わない。
- legacy `paper-step` は `data/research/signals.csv` 由来の NDX/QQQ family を paper order/fill に変換せず、`legacy_paper_blocked_count` と `legacy_paper_blocked_reason_counts` にブロックを記録する。
- Alpaca live fetch は credentials が必要。credentials なしでは明示的に unavailable として失敗するため、silent empty data と混同しない。
- `ostium-python-sdk` は active dependency から削除済み。

## Repo Entry And Environment State

2026-05-31 の repo-entry cleanup 後の状態:

- `README.md` は repo 相対リンクを使い、詳細な Strategy Authoring capability の列挙は `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md` へ寄せている。
- `README.md` は `READ_ONLY_GO` を read-only / paper gate として説明し、production live trading ready とは扱わない。
- `pyproject.toml` の project description は `Trade[XYZ] research, Strategy Lab authoring, paper operations, and read-only safety gates`。
- `AGENTS.md` は Python/uv-first を明記し、CI の Bun lockfile integrity check と `package.json` legacy-note-only 境界を記録している。
- `AGENTS.md` の Python file size rule は、new or heavily edited Python files を 800 lines or fewer に保つ運用。Strategy Authoring 配下は `tests/strategy_authoring/test_module_boundaries.py` で 800 lines or fewer を強制する。既存 oversized modules は拡張前に分割を検討する。
- `.gitignore` の ignore 動作は変えず、tracked `.tmp/live_evidence_*` helper、legacy archive zip、generated live-evidence reports の意図をコメント化している。
- `.env.example` は `GTRADE_*` / `OSTIUM_*` live credential keys を持たない。Trade[XYZ] live write credentials も intentionally not defined で、manual micro-live preflight が文書化・承認されるまで local-only secrets として扱う。
- `.env.example` は Alpaca smoke 用の accepted credential keys を残す。`configs/env.example` は通常 repo settings 用の最小 sample として残す。

## Verification Status

current verification は固定の pass count ではなく、作業時点で次を再実行して確認する:

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_current_docs.py
./scripts/check
```

2026-06-06 docs-only spot check:

- `uv run python scripts/check_current_docs.py`: pass, current-doc allowlist checked successfully

2026-06-13 NDX Layer 2.2/2.3/2.4/2.5/2.6/2.7 local paper-observation snapshot:

- `uv run sis --help`: `research-layer22-review-pack`, `research-layer22-review-import`, `research-layer22-exit-gate`, `research-ndx-source-resolve`, `research-ndx-feature-panel`, `research-ndx-residual`, `research-ndx-diagnostics`, `research-ndx-residual-validate`, `research-ndx-strategy-lab-export` registered
- latest local exit decision artifact: `APPROVE_2_3`, `second_review_required=false`, unresolved human decision count `0`, blocker count `0`, pack hash `sha256:7fc0d644d4a8d7432df29a8dfd6c878fc97342b5745febc26e6cd6206a01dd6a`
- latest Layer 2.4 decision artifact: `APPROVE_STRATEGY_LAB_EXPORT`, `reason_codes=[]`, `permits_strategy_lab_research_only_export=true`
- latest Layer 2.5 export artifact: `export_id=sha256:6e205549d2bc81ae8a99f316b29a3c1b496272f30b417cff71e2404e21f3465d`, `signal_count=84`, `replace_existing=true`, previous signal hash `null`
- latest Layer 2.6 paper-observation gate artifact: `decision=APPROVE_PAPER_OBSERVATION_REVIEW`, `decision_id=sha256:31076e5cee546e770f68d5786b619640399cabe72dbf7b997e05d94051376205`, `permits_operator_promotion_review=true`, `permits_live_order=false`
- latest Layer 2.7 operator promotion artifact: `decision=promote_to_paper_observation`, `promotion_id=sha256:edb0ab4452f950ddbaaf86db520f0a75bd399ded263b1e8e381f2c80772c34fb`, `permits_paper_candidate=true`, `permits_paper_intent_preview=true`, `permits_paper_observation=true`, `permits_live_order=false`
- latest paper candidate check after valid Layer 2.7 promotion: `selected_candidate_ids=["candidate-trial-d4cd44be5491-dce21eb2f5461d85"]`, `candidate_count=1`, first candidate block reasons `[]`
- latest `PaperIntentPreview` after valid Layer 2.7 promotion: `intent_count=1`, `paper_only=true`, `requires_revalidation=true`, `live_conversion_allowed=false`, `wallet_used=false`, `exchange_write_used=false`
- latest Strategy Backtest Pack uses isolated signal artifacts under `data/research/backtest_pack/source_artifacts/`, so pack generation no longer overwrites the NDX Strategy Lab canonical `data/research/strategy_signals.parquet`.

2026-06-09 NDX/QQQ venue suitability paper-path snapshot:

- `VenueId` and Strategy Lab schemas still allow only `trade_xyz` and `bitget_demo`.
- `bitget_futures` and `hyperliquid_perp` are catalog-only entries in `src/sis/venues/suitability.py`.
- `bitget_futures` and `hyperliquid_perp` are also explicit disabled capability entries in `src/sis/venues/capabilities.py`.
- NDX/QQQ family records remain usable for research/backtest artifacts. Paper candidate selection, `PaperIntentPreview`, raw `paper-from-intents` JSON, and legacy `paper-step` order generation remain blocked unless valid Layer 2.6/2.7 paper-observation evidence is present.

2026-06-17_20:44 JST runtime validation snapshot:

- `uv run sis validate-artifacts --strict`: `checked_files=13`, `issues=0`
- latest `uv run sis phase-gate-review`: `READ_ONLY_GO`, `phase2_entry_allowed=true`, `blockers=[]`, `next_actions=[]`, `latest_evidence_card_path=data/evidence/evidence_card_20260617_111729.json`
- latest phase gate can be `READ_ONLY_GO` while execution lineage remains degraded. Current classification is `P2_BLOCKER=0`, `LIVE_READINESS_BLOCKER=6`; read-only/paper readiness and live execution readiness are separate surfaces.
- latest local execution lineage refresh reran `execution-read-only-surfaces`, `execution-snapshot`, `execution-venue-comparison`, `execution-venue-diagnostics`, `operations-bundle`, `execution-gap-history`, `execution-state-comparison-history`, `execution-snapshot-drift-history`, `execution-drift-overview`, `phase-gate-review`, and `readiness-snapshot`. It did not clear live-readiness blockers: Trade[XYZ] now reports `trade_xyz_execution_state_user_address_missing`, `phase-gate-review` propagates `set_trade_xyz_execution_state_public_user_address` as the execution gap next action, and Bitget demo still reports missing demo credentials / read-only network probe not executed.
- latest `execution-drift-overview` reason-code hardening distinguishes the current `venue_count=2` unavailable collector path from the old empty snapshot path. It now reports `execution_drift_overview_reason_codes=["trade_xyz_execution_state_user_address_missing"]` for this state.
- latest supplemental `uv run sis diagnose-quotes --venue trade_xyz` completed for current Trade[XYZ] symbols; `check-go-no-go` returned `GO`; `build-evidence-card` wrote `data/evidence/evidence_card_20260617_111729.json`. These are supplemental reports. They do not override `phase-gate-review` and do not prove live readiness.
- latest `refresh-operations-artifacts` regenerated local operations/audit/remediation reports but did not clear execution readiness: operations dashboard is `overall_status=degraded`, `monitoring_status=degraded`, `execution_venue_count=2`, `execution_comparison_all_registries_present=false`, and readiness snapshot has `operations_ready=false`.
- latest phase gate remediation order is `none` when only live-readiness blockers remain. Do not repeatedly run `refresh-operations-artifacts` as a P2 remediation loop for those blockers; it can refresh local reports, but it does not create missing execution evidence.
- latest available Trade[XYZ] data readiness artifact: `data/manifests/trade_xyz_data_readiness_manifest.json` has `decision=NOT_READY`, `backtest_data_ready=false`, `fail_count=1`, `known_gap_count=2`.

PR-08 専用確認:

- `tests/test_trade_xyz_live_order_policy.py`
- `tests/test_trade_xyz_adapter_safety.py`
- `tests/test_micro_live_canary.py`

上記は `./scripts/check` に含まれる。

## What Is Still Not Proven

- production live order smoke
- signing / wallet / exchange write integration
- live order preview / 注文候補生成の正式 command surface
- Bitget credentialed read-only network smoke
- Bitget demo order lifecycle
- Alpaca credentials ありの API connectivity smoke。historical IEX bar で `provider_connectivity_status=pass`, `data_availability_status=pass` は確認済み。fresh 15m は `BLOCK_ALPACA_NO_BARS` で blocked になり得るため、live `status=pass` は市場時間中の fresh bar 取得で再確認する
- `check-go-no-go` / `build-evidence-card` は補助reportであり、Bot前の現行判定正本は `phase-gate-review`

## Recommended Read Order

1. `docs/CURRENT_STATE.md`
2. `docs/CODE_STATUS.md`
3. `docs/IMPLEMENTED_SURFACES.md`
4. `docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md`
5. `docs/NEXT_DIRECTION_CURRENT.md`
6. `docs/research/ndx/README.md`
7. `docs/research/ndx/09_LLM_REVIEW_GATE.md`
8. `docs/research/ndx/10_LAYER_2_3_NDX_PREFLIGHT.md`
9. `docs/research/ndx/11_LAYER_2_4_RESIDUAL_VALIDATION_GATE.md`
10. `docs/backtest/README.md`
11. `docs/backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md`
12. `docs/strategy_review/README.md`
13. `docs/strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md`
14. `docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md`
15. `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`
16. `docs/strategy_research_lab/README.md`
17. `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md`
18. `docs/strategy_research_lab/01_SCHEMA_CONTRACTS_FOR_TRADING_STRATEGIES.md`
19. `docs/venues/read_only_capability_probe.md`
20. `docs/OPERATIONS_RUNBOOK.md`
21. `docs/ARCHITECTURE_AND_PHASES.md`
22. `docs/trade_xyz_bot_beginner_guide.html`
23. `plan/README.md`

historical focused audit:

1. `docs/archive/2026-06-05-doc-cleanup/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-28.md`
2. `docs/archive/2026-06-05-doc-cleanup/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md`

その後、必要に応じて:

1. `data/reports/current_state_index.md`
2. `data/reports/readiness_snapshot.md`
3. `data/reports/phase_gate_review.md`
4. `data/reports/operations_dashboard.md`

artifact が古い場合:

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
uv run sis bot-preview
```
