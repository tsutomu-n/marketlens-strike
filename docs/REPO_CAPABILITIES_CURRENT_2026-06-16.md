<!--
作成日: 2026-06-16_06:46 JST
更新日: 2026-06-18_05:20 JST
-->

# Repo Capabilities Current

## 結論

`marketlens-strike` は、Python 3.13 / `uv` 前提の CLI workspace である。現在できることは、戦略研究、Strategy Authoring、backtest、paper-only preview、NDX research gate、Trade[XYZ] read-only data collection、read-only / paper operation、ops audit、remediation、artifact validation を local artifact と schema でつなぐこと。

現在できないことは、production live trading、wallet / signing / exchange write、backtest だけによる alpha / paper pass / live readiness の主張、Bitget / Hyperliquid production venue の正式 schema 対応、credentialed external API を暗黙に使う workflow である。

この文書は、コード、CLI help、schema、current docs を正として、repo でできることを漏れなく読む入口にする。

AI / Codex / LLM が戦略作成、編集、backtest、結果解釈を進める場合は [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md) を読む。人間が戦略と backtest 結果を専門用語少なめで理解したい場合は [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md) を読む。

## 追加調査での補正

この更新では、`uv run sis --help` の public command 一覧、`src/sis/cli.py` の command registration、`schemas/*.json`、`tests/`、既存 current docs を再確認した。

補正した点:

- Public CLI Command Catalog は [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) へ分離した。固定の command count を current truth にせず、確認時は `uv run sis --help` と `uv run python scripts/check_cli_catalog.py` を再実行する。
- Strategy Review には `strategy-review-build` と `strategy-review-record` がある。
- 本文側で薄かった `research-dag-*`、`strategy-backtest-framework-run`、legacy `build-backtest`、Trade[XYZ] data cycle、historical archive quote normalization、market-session utility、Strategy Lifecycle docs、Algo / Strategy Factory docs、schema family の説明を補った。
- `docs/strategy_lifecycle/` は current-docs 検査対象に追加した。
- `operator_strategy_review.v1` と `operator_review.yaml` の境界を追記した。これは paper / live 許可ではなく、Strategy Review packet に対する人間判断と source hash 再検証の artifact である。

## 正本と検証方法

優先順位:

1. `src/`, `tests/`, `schemas/`, `configs/`, `scripts/`, `pyproject.toml`, `uv.lock`
2. `uv run sis --help`
3. current docs
4. generated artifacts under `data/`
5. `docs/archive/` と `plan/archive/`

検証 command:

```bash
uv run python -V
uv run sis --help
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
./scripts/check
```

`data/` は runtime / generated state であり、fresh checkout では再生成が必要になる。

## 1. Runtime / Repo Operation

できること:

- Python 3.13 固定の CLI workspace として動かせる。
- `uv sync --dev --locked` で lockfile 通りに環境を作れる。
- `sis` CLI を `pyproject.toml` の script entrypoint から実行できる。
- `./scripts/check` で lock sync、Python version、Ruff lint、Ruff format check、current docs check、Pyrefly、ty、Pytest をまとめて検証できる。
- current docs の metadata、links、EOF、legacy root reference を `scripts/check_current_docs.py` で検査できる。
- `implementation-status`, `current-state-index`, `readiness-snapshot` などで repo 状態や readiness を artifact / report 化できる。

主要ファイル:

- `pyproject.toml`
- `uv.lock`
- `.python-version`
- `scripts/check`
- `scripts/check_current_docs.py`
- `src/sis/cli.py`
- `src/sis/commands/`

## 2. Strategy Research Lab

できること:

- Strategy Lab の experiment spec から signal、trial、evaluation、candidate、promotion、paper intent preview を作れる。
- `strategy-preview` で組み込み preview を生成できる。
- `strategy-experiment-run --spec` で spec から strategy signal artifact を生成できる。
- `evaluate-strategy-lab` で signal / evaluation を評価できる。
- `build-paper-candidate-pack` で paper candidate pack を作れる。
- `promotion-decision` で hold / promote などの promotion decision を artifact 化できる。
- `build-paper-intent-preview` で paper-only の intent preview を作れる。
- `paper-from-intents` で paper intent を paper flow へ渡せる。
- venue suitability gate により、NDX/QQQ family などは valid promotion evidence がない限り fail closed できる。

主な schema:

- `strategy_experiment_spec.v1.schema.json`
- `strategy_signal.v1.schema.json`
- `evaluation_plan.mls.v1.schema.json`
- `trial_record.v1.schema.json`
- `trade_candidate.v1.schema.json`
- `paper_candidate_pack.v1.schema.json`
- `promotion_decision.v1.schema.json`
- `paper_intent_preview.v1.schema.json`

境界:

- `PaperIntentPreview` は paper-only。live order ではない。
- Strategy Lab の tracked JSON Schema は interoperability guard で、詳細 validation は Pydantic model が正本。

## 3. Algo Strategy Docs / Strategy Factory

できること:

- `docs/algo/` で、戦略仮説、戦略部品、blueprint、実験準備、scorecard、validation playbook、source note index を読める。
- `docs/algo/strategy_factory/` で、1戦略1枚の候補シート、reject taxonomy、backlog 台帳、gate review checklist、duplicate control、operator guide を使える。
- これはコード実行 surface ではなく、Strategy Lab / Strategy Authoring に入れる前の設計・選別・記録のための文書 surface である。

主要 docs:

- [algo/README.md](algo/README.md)
- [algo/strategy_factory/README.md](algo/strategy_factory/README.md)
- [algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md](algo/strategy_factory/STRATEGY_FACTORY_OPERATOR_GUIDE.md)
- [algo/RESEARCH_VALIDATION_PLAYBOOK.md](algo/RESEARCH_VALIDATION_PLAYBOOK.md)

境界:

- 外部メモや動画由来の勝率・利益主張は検証済み事実として扱わない。
- 実弾運用ではなく、研究、設計、検証のための作業資料である。

## 4. Strategy Authoring YAML

できること:

- `strategy_authoring_spec.v1` YAML を初期化、検証、説明、実行できる。
- rule-based long / short / hold / close / reduce / add / rebalance signal を作れる。
- derived features を多数作れる。例: true range, ATR, Bollinger bands, Donchian channels, Keltner channels, Ichimoku cloud, MACD line, stochastic K/D, ADX, OBV, volume z-score, calendar features, rolling correlation / beta / spread z-score / tracking error / information ratio, flow / carry / liquidity / options-vol, on-chain / sentiment / event / fundamental / factor-ranking, execution-constraint, data-quality / ensemble / capacity, lag, return / log-return, rolling return / sum / volatility / percentile-rank / skew / kurtosis, annualized volatility, realized variance, downside volatility, Sharpe / Sortino-like ratios, Kelly fraction, historical VaR, expected shortfall, cumulative return, slope, mean-reversion score, EMA, RSI, rolling min / max。
- column-to-column condition、cross / trend / consecutive condition、exclusion-none condition、regime membership filter、regime-specific override を扱える。
- paper-only dynamic multi-leg、leg exit、order override、execution override、group metadata、group aggregate metrics、pair-trade signal を扱える。
- paper-only linear model score と `strategy-author-train-model` adapter を使える。
- group-wise cross-sectional top-bottom / fraction-tail rotation、minimum candidates、score thresholds を扱える。
- opposite-signal exit、explicit close-signal exit、reduce-signal partial exit、add-signal scale-in、rebalance-signal exposure resize、rebalance band skip を扱える。
- bracket-OCO、partial-profit break-even lifecycle、trailing stop、minimum / maximum holding period、exit priority を扱える。
- order-style entry、time-in-force、post-only、reduce-only、execution-profile preset を扱える。
- slippage with row cost、partial-fill with row fill、min-fill gate、spread gate、depth-based fill、latency gate、queue-position gate を扱える。
- short-borrow availability / cost gate、tax drag、turnover / capacity / crowding fee gate を扱える。
- grouped / group-net / row-level / global net portfolio exposure limits、portfolio turnover budget、risk throttle profiles、volatility targeting、target-weight、inverse-vol、dollar-neutral、beta-neutral、group-neutral allocation を扱える。
- multi-timeframe confirmation、temporal cadence、event-window calendar filters、parameter sweep、era metrics、executed signal summary、strategy scorecard を出せる。
- `strategy_authoring_bundle.v1` で複数 strategy spec の paper portfolio 比較ができる。

主要 command:

- `strategy-author-init`
- `strategy-author-validate`
- `strategy-author-explain`
- `strategy-author-run`
- `strategy-author-bundle-run`
- `strategy-author-train-model`

主な schema:

- `strategy_authoring_spec.v1.schema.json`
- `strategy_authoring_bundle.v1.schema.json`
- `strategy_authoring_backtest_result.v1.schema.json`
- `strategy_authoring_bundle_result.v1.schema.json`

境界:

- `strategy-author-run --through backtest` は research / paper-only backtest であり、live order ではない。
- `rules.sizing.notional_usd` は signal の想定 notional であり、backtest initial capital とは混ぜない。

## 5. Backtest

できること:

- Strategy Authoring の native backtest を実行できる。
- `strategy-backtest-suite` で複数 spec / 複数 case / walk-forward / purged walk-forward / bootstrap を比較できる。
- `strategy-backtest-pack` で backtest artifact chain を一括生成できる。
- `strategy-backtest-pack-validate` で path / hash / method / paper-only boundary / framework policy を検査できる。
- `strategy-backtest-artifact-summary` で主要 artifact field を JSON stdout にまとめられる。
- `strategy-backtest-html-report` で既存 artifact から損益グラフ、benchmark 比較、期間指定 trade table、stress summary、結果ラベル付きの単一 HTML / JS report を作れる。
- `strategy-review-build` で既存 backtest artifact chain から人間レビュー用 `review.md` と機械検証用 `review_manifest.json` を作れる。
- `strategy-backtest-compare` で native result、suite、adapter spike、external result、portfolio comparison、metric extension、report extension、stress、regime split、rolling stability、benchmark relative、completion artifact を比較 artifact に正規化できる。
- `strategy-backtest-data-availability` で local source hash、row count、timestamp range、gap / duplicate、future candidate を記録できる。
- `strategy-backtest-baseline-compare` で cash / no-trade と return-series control を比較できる。
- `strategy-backtest-no-lookahead-diff` で future mutation replay と coverage / false-negative risk を記録できる。
- `strategy-backtest-execution-sim` で paper-only order intents / fill events を作れる。
- `strategy-backtest-assumption-ledger` と `strategy-backtest-trial-ledger` で仮定と試行履歴を残せる。
- `strategy-backtest-framework-run` で optional extra の `vectorbt`, `bt`, `empyrical_reloaded`, `quantstats` runner / extension を明示 framework list から実行できる。
- `build-backtest` で legacy bridge 系の backtest decision summary / decision log を作れる。
- stress、regime split、rolling stability、benchmark relative を出せる。
- `strategy-review-record` で `review.md` / `review_manifest.json` を読んだ人間判断を `operator_review.yaml` として保存し、`--validate-existing` で path と hash を再照合できる。

optional OSS:

- `vectorbt==1.0.0`: signal runner / external check
- `bt==1.2.0`: portfolio allocation / rebalance comparison
- `empyrical-reloaded==0.5.12`: metrics normalization
- `quantstats==0.0.81`: report / tear sheet

reference-only / 採用前 contract:

- `strategy-backtest-microstructure-readiness`: HftBacktest などの L2/L3/tick/latency/queue input readiness
- `strategy-backtest-qstrader-contract`: qstrader local input contract
- `strategy-backtest-portfolio-validation-contract`: skfolio / Riskfolio-Lib portfolio validation contract
- `strategy-backtest-pybroker-contract`: PyBroker local DataFrame input contract
- `strategy-backtest-constraint-breaker-decision`: 制約破壊の scorecard decision

標準 engine:

- `strategy_authoring_native`

境界:

- optional OSS は標準 engine を置き換えない。
- `framework_run` は pack に入るが、pack completion の必須条件ではない。
- pack validation `PASS` は alpha / paper pass / live readiness ではない。
- strategy review output は human-review artifact であり、pack validation `PASS` を収益性、paper 移行可否、live 実行可否の証明にしない。
- operator strategy review output は non-permission artifact であり、`PAPER_OBSERVATION_CANDIDATE` は validation candidate だけを意味する。`live_allowed=false` と `paper_execution_allowed=false` は固定である。
- HftBacktest / qstrader / PyBroker / skfolio / Riskfolio-Lib は dependency 追加前 contract まで。engine 実行ではない。
- `build-backtest` は Trade[XYZ] pure backtest v0.1 や Strategy Authoring native backtest の入口ではなく、既存 bridge 系 command として読む。

詳細:

- [backtest/README.md](backtest/README.md)
- [backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md](backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md)
- [backtest/OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md](backtest/OPERATOR_BACKTEST_PACK_RECIPE_2026-06-13.md)

## 6. Strategy Lifecycle / Paper Observation

できること:

- `strategy-backtest-acceptance` で backtest acceptance decision を作れる。
- `strategy-paper-observation-cycle` で paper observation cycle artifact を作れる。
- `strategy-lifecycle-review` で backtest acceptance、paper observation、phase gate summary を統合して lifecycle decision を出せる。
- `strategy-paper-observation-status` で既存 paper observation review / session manifest / lifecycle review を読み、normal threshold と smoke threshold を分けた status artifact を作れる。
- decision は `REJECT_OR_REVISE`, `CONTINUE_RESEARCH`, `BACKTEST_ACCEPTED`, `CONTINUE_PAPER_OBSERVATION`, `CONTINUE_EXECUTION_READINESS`, `ELIGIBLE_FOR_LIVE_CANARY_PLAN`, `BLOCKED_BOUNDARY_VIOLATION` などを扱える。

主な schema:

- `strategy_backtest_acceptance_decision.v1.schema.json`
- `paper_observation_session_manifest.v1.schema.json`
- `strategy_lifecycle_review.v1.schema.json`
- `strategy_paper_observation_status.v1.schema.json`

主要 docs:

- [strategy_lifecycle/README.md](strategy_lifecycle/README.md)
- [strategy_lifecycle/TARGET_OPERATING_MODEL.md](strategy_lifecycle/TARGET_OPERATING_MODEL.md)
- [strategy_lifecycle/PAPER_OBSERVATION_CYCLE.md](strategy_lifecycle/PAPER_OBSERVATION_CYCLE.md)
- [strategy_lifecycle/LIVE_CANARY_PLAN_GATE.md](strategy_lifecycle/LIVE_CANARY_PLAN_GATE.md)

境界:

- lifecycle review は live order を許可しない。
- paper observation status は paper intent 生成、paper order 実行、ledger 再集計をしない。
- smoke pass は normal paper observation pass ではない。
- `ELIGIBLE_FOR_LIVE_CANARY_PLAN` は live order 実行許可ではなく、別計画を書いてよい候補という意味。
- `strategy-lifecycle-review` は `lifecycle-report` とは別物。前者は strategy promotion control plane、後者は operations / recovery report である。

## 7. NDX / Research DAG Gates

できること:

- `research-dag-validate` と `research-dag-export` で core DAG YAML、variable inventory、counter DAG、data source registry を検証・export できる。
- Layer 2.2 DAG foundation を local-only で validate / export できる。
- Layer 2.2 manual review pack を作り、手動 review JSON を import し、exit gate を判定できる。
- Layer 2.3 source resolve / feature panel / open-gap residual / diagnostics を fixture-first で作れる。
- Layer 2.4 residual validation gate を実行できる。
- Layer 2.5 research-only Strategy Lab export を作れる。
- Layer 2.6 paper-observation gate で research export hash / signal hash / local quote evidence を検査できる。
- Layer 2.7 operator promotion で valid approval evidence がある場合だけ paper observation に進める。
- Layer 2.8 paper observation review で fills、観測日数、block rate、連続 block、artifact completeness、boundary violation を見られる。

主要 command:

- `research-layer22-validate`
- `research-layer22-export`
- `research-layer22-review-pack`
- `research-layer22-review-import`
- `research-layer22-exit-gate`
- `research-ndx-source-resolve`
- `research-ndx-feature-panel`
- `research-ndx-residual`
- `research-ndx-diagnostics`
- `research-ndx-residual-validate`
- `research-ndx-strategy-lab-export`
- `research-ndx-paper-observation-gate`
- `research-ndx-operator-promotion`
- `research-ndx-paper-observation-review`

境界:

- `research-dag-*` は generic core DAG artifact の検証・export surface。NDX Layer 2.2 command 群とは分けて読む。
- Layer 2.2 は manual review plumbing。feature panel、residual、backtest、paper/live order には直接接続しない。
- Layer 2.4 approval は Layer 2.5 research-only export bridge の許可であり、alpha / backtest / paper / live readiness ではない。
- Layer 2.5 export は research-only。valid Layer 2.6 / 2.7 evidence がない限り paper path では fail closed する。

## 8. Trade[XYZ] Data / Venue Surface

できること:

- Trade[XYZ] probe を実行できる。
- Trade[XYZ] quotes を収集し、summary / report を書ける。
- `collect-trade-xyz-data-cycle` で registry refresh、quote collection、normalization、coverage / readiness / bundle 更新をまとめて実行できる。
- WebSocket capture、WS quality、REST parity を作れる。
- quotes を normalize できる。
- quote coverage を build できる。
- reference data、real market reference、signal candles、account fee を収集できる。
- historical L2 archive、historical asset contexts archive、bulk archive preflight / execute / normalize を扱える。
- `normalize-trade-xyz-historical-archive-quotes` で単体の historical L2 / asset context archive から raw quote rows を作り、必要なら normalized quotes を再構築できる。
- funding history を収集し、funding events を history から build できる。
- Trade[XYZ] data readiness を build できる。
- Trade[XYZ] collection status と data bundle を作れる。
- Trade[XYZ] pure backtest v0.1 を Python API から実行できる。

主要 command:

- `probe trade-xyz`
- `collect-trade-xyz-quotes`
- `collect-trade-xyz-ws`
- `build-trade-xyz-ws-quality`
- `build-trade-xyz-rest-parity`
- `normalize-quotes`
- `normalize-trade-xyz-ws-quotes`
- `build-trade-xyz-quote-coverage`
- `build-trade-xyz-reference-data`
- `collect-trade-xyz-real-market-reference`
- `collect-trade-xyz-signal-candles`
- `collect-trade-xyz-account-fee`
- `collect-trade-xyz-historical-l2-archive`
- `collect-trade-xyz-historical-asset-ctxs-archive`
- `plan-trade-xyz-historical-archive-bulk`
- `check-trade-xyz-historical-archive-preflight`
- `execute-trade-xyz-historical-archive-bulk`
- `normalize-trade-xyz-historical-archive-bulk`
- `build-trade-xyz-session-state`
- `collect-trade-xyz-funding-history`
- `build-trade-xyz-funding-events-from-history`
- `build-trade-xyz-data-readiness`
- `trade-xyz-collection-status`
- `build-trade-xyz-data-bundle`

境界:

- Trade[XYZ] は実装済み venue surface だが、現在の開発主軸は backtest-first / venue-neutral。
- Trade[XYZ] pure backtest v0.1 は public CLI ではなく Python API surface。
- 実 live order integration は opt-in safety surface 止まりで、標準 operator CLI には micro-live 実行 command を出していない。

## 9. Real Market / Tracking / Alpaca

できること:

- cost matrix、research data ingest、event calendar、feature panel、signals を build できる。
- Alpaca smoke を実行できる。
- real market data layer と provider quality gate を扱える。
- real market vs venue tracking、lead/lag、source confidence、venue quality を扱える。

主要 command:

- `build-cost-matrix`
- `ingest-research-data`
- `build-event-calendar`
- `build-feature-panel`
- `build-signals`
- `alpaca-smoke`

境界:

- Alpaca credentials がない場合は unavailable / failed として扱う。
- fresh live `status=pass` は市場時間中の fresh bar 取得で再確認が必要。
- read-only provider connectivity は live trading readiness ではない。

## 10. Execution / Paper / Read-Only Operations

できること:

- `bot-preview` で read-only HOLD preview artifact を作れる。
- execution snapshot、venue comparison、venue diagnostics、read-only surfaces を作れる。
- Trade[XYZ] read-only execution state collector contract を使える。public user address と明示 opt-in がある場合だけ `/info` 由来の account state / open orders / fills を読み、通常実行では external API、wallet、signing、exchange write を使わず未設定理由を出す。
- order status、estimate order、balance status、fill status、cancel、close、reconcile などの execution utility command がある。
- `bitget-demo-smoke` で local/mock-first Bitget demo smoke を実行できる。
- `paper-step`, `paper-from-intents`, `paper-report`, `paper-operations-cycle` で paper operation artifact を扱える。
- daemon manifest / dry-run / run、state export / restore、monitoring status、kill switch、schedule run、notification outbox を扱える。
- `check-timeframe`, `market-session`, `next-live-window` で timeframe policy と market session / next recommended window を確認できる。

主要 command:

- `bot-preview`
- `execution-snapshot`
- `execution-venue-comparison`
- `execution-venue-diagnostics`
- `execution-read-only-surfaces`
- `order-status`
- `estimate-order`
- `balance-status`
- `bitget-demo-smoke`
- `fill-status`
- `cancel-order`
- `close-position`
- `reconcile-positions`
- `healthcheck`
- `daemon-manifest`
- `daemon-dry-run`
- `daemon-run`
- `export-state`
- `restore-state`
- `monitoring-status`
- `kill-switch`
- `schedule-run`
- `render-alert`
- `notification-outbox`
- `paper-step`
- `paper-from-intents`
- `paper-report`
- `paper-operations-cycle`
- `check-timeframe`
- `market-session`
- `next-live-window`

境界:

- `bot-preview` は read-only HOLD preview。wallet、signing、exchange write は使わない。
- `bitget-demo-smoke` の `status=configured` は local env が揃った意味だけ。network / account / order submit / fill sync 成功ではない。
- Trade[XYZ] read-only execution state collector は public user address と `SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1` がない限り external API を呼ばない。未設定時の current reason は `trade_xyz_execution_state_user_address_missing`。
- execution utility command が存在しても、production live trading ready ではない。

## 11. Operations / Audit / Remediation

できること:

- operations dashboard、timeline、bundle、audit pack を作れる。
- audit timeline、dashboard、bundle、bundle history を作れる。
- paper cycle history、execution gap history、execution state comparison history、execution snapshot drift history、execution drift overview を作れる。
- readiness snapshot、current state index を作れる。
- remediation planner、execution plan、session、checkpoint、evidence ingest、scoreboard、evaluator、evidence、command results を作れる。
- weekly review、lifecycle report、comparison report、ops review を作れる。
- phase gate review を実行できる。
- artifact strict validation、quote diagnostics、halt policy、go/no-go、evidence card を扱える。

主要 command:

- `lifecycle-report`
- `comparison-report`
- `ops-review`
- `operations-dashboard`
- `paper-operations-runbook`
- `paper-cycle-history`
- `execution-gap-history`
- `execution-state-comparison-history`
- `execution-snapshot-drift-history`
- `execution-drift-overview`
- `phase-gate-review`
- `operations-bundle`
- `operations-timeline`
- `operations-audit-pack`
- `audit-timeline`
- `audit-dashboard`
- `audit-bundle`
- `audit-bundle-history`
- `current-state-index`
- `readiness-snapshot`
- `remediation-planner`
- `remediation-execution-plan`
- `remediation-session`
- `remediation-session-checkpoint`
- `remediation-evidence-ingest`
- `remediation-scoreboard`
- `remediation-evaluator`
- `remediation-evidence`
- `remediation-command-results`
- `weekly-review`
- `refresh-operations-artifacts`
- `check-halt-policy`
- `check-go-no-go`
- `build-evidence-card`
- `implementation-status`
- `validate-artifacts`
- `diagnose-quotes`

境界:

- `phase-gate-review` は read-only / paper gate の判断正本。production live trading ready の証明ではない。
- operations artifacts は runtime state なので再生成が必要になる。

## 12. Venue Policy / Suitability

できること:

- `VenueId` は現行で `trade_xyz` と `bitget_demo` を許可する。
- venue suitability catalog には `trade_xyz`, `bitget_demo`, `bitget_futures`, `hyperliquid_perp` がある。
- venue capability contract では `bitget_futures` と `hyperliquid_perp` を known future venues として持つが、schema / paper / network / live は disabled。
- `bitget_demo` は execution-venue schema では許可されるが、Strategy Lab `evaluation_plan.mls.v1` の target venue としてはまだ disabled。
- `venue-read-only-probe` で 4 venue の capability boundary を fixture-first local artifact として出せる。external API、credentials、wallet、signing、exchange write、live order、network attempt は使わない。

境界:

- `bitget_futures` と `hyperliquid_perp` は current `VenueId` ではない。
- NDX/QQQ は research / backtest record として保持できるが、valid paper-observation evidence がない限り paper candidate / paper intent path で fail closed する。
- `venue-read-only-probe` は network readiness、credential readiness、paper permission、live permission ではない。

## 13. Schemas / Artifact Contracts

できること:

- Strategy Lab、Strategy Authoring、Backtest、NDX gates、Trade[XYZ] data readiness、paper lifecycle などの JSON Schema を tracked file として持つ。
- artifact path / source hash / no-live boundary / decision / report hash を多くの artifact に残せる。
- `jsonschema` と Pydantic validation により、CLI output を schema-valid に保てる。

主な schema families:

- Strategy Lab / lifecycle: `strategy_experiment_spec.v1`, `strategy_signal.v1`, `strategy_signal_manifest.v1`, `evaluation_plan.mls.v1`, `trial_record.v1`, `trade_candidate.v1`, `paper_candidate_pack.v1`, `promotion_decision.v1`, `paper_intent_preview.v1`, `strategy_lifecycle_review.v1`, `paper_observation_session_manifest.v1`, `strategy_paper_observation_status.v1`
- Strategy Review: `strategy_review_manifest.v1`, `operator_strategy_review.v1`
- Strategy Authoring / Backtest: `strategy_authoring_*`, `strategy_backtest_*`, `backtest_data_availability_ledger.v1`
- NDX / research gates: `ndx_*`, `layer_2_2_*`, `core_dag.v1`, `counter_dag.v1`, `llm_dag_review.v1`
- Research protocol: `research_seed_registry.v1`, `research_scope.v1`, `research_variable_inventory.v1`, `research_temporal_availability.v1`, `research_causal_roles.v1`, `research_mechanism_parts.v1`
- Market / venue / quote artifacts: `quote_log_v1`, `quote_log_v2`, `quote_log_v2.trade_xyz.strict`, `trade_xyz_*`, `instrument_registry*`, `cost_snapshot`, `fee_snapshot`, `funding_event`, `funding_history_event`, `session_calendar_snapshot`, `session_state_observation`
- Venue capability: `venue_read_only_probe_summary.v1`
- Snapshot / operations guard: `data_snapshot_manifest.v1`, `feature_snapshot_manifest.v1`, `go_no_go_report`

境界:

- tracked JSON Schema は薄い guard と interoperability 用。詳細 validation は `src/sis/` の Pydantic model / builder が正本。

## 14. Tests / Quality Gates

できること:

- `tests/backtest` で backtest surfaces を検査できる。
- `tests/strategy_authoring` で authoring / backtest CLI bundle / module boundaries を検査できる。
- `tests/research` で NDX / lifecycle / research gates を検査できる。
- `tests/paper` で paper surfaces を検査できる。
- `tests/test_cli_help_contract.py`, `tests/test_cli_smoke.py`, `tests/test_docs_current_truth.py` で CLI help / smoke / docs current-truth の drift を検査できる。
- repo 全体は `./scripts/check` でまとめて検証できる。

主要 test dirs:

- `tests/backtest`
- `tests/strategy_authoring`
- `tests/research`
- `tests/paper`
- `tests/fixtures`
- `tests/support`

## Public CLI Command Catalog

Public CLI command list は [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) に分離済みです。新しい command を追加した時は次を実行して、catalog と Typer registration の差分を確認します。

```bash
uv run sis --help
uv run python scripts/check_cli_catalog.py
```

この文書は capability overview と境界説明に寄せ、command 名の網羅表は CLI catalog 側で管理します。

## 2026-06-18 差分追記: 2026-06-16版から何が変わったか

この節は、2026-06-16 に作成したこの capability document と、2026-06-18_04:56 JST 時点の repo を比較した具体差分である。

確認した正本:

- `uv run sis --help`
- `uv run python scripts/check_cli_catalog.py`
- `schemas/*.json`
- `src/sis/commands/`
- `tests/`
- この文書自身と current docs

### 1. Public CLI surface は増え、catalog は機械照合に分離された

2026-06-16 版では public command catalog をこの文書内に持っていた。現在は command list を [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md) に分離し、`scripts/check_cli_catalog.py` で Typer registration と照合する方式になった。

現在の確認方法:

```bash
uv run python scripts/check_cli_catalog.py
```

増えた主要 command:

- `strategy-review-build`
- `strategy-review-record`
- `strategy-paper-observation-append`
- `strategy-paper-observation-status`
- `venue-read-only-probe`

意味:

- 「command 名一覧を手で保守する文書」から、「CLI registration と照合できる catalog」に変わった。
- command 数の固定値は current truth ではなくなり、`uv run sis --help` と `scripts/check_cli_catalog.py` の再実行が確認手順になった。

### 2. Backtest の後段に Strategy Review が増えた

2026-06-16 版では、backtest pack / comparison / validation までは扱っていたが、人間が読む review packet と operator review record はまだ中心機能として分離されていなかった。

現在できること:

- `strategy-review-build` で既存 backtest artifact chain から `review.md` と `review_manifest.json` を作れる。
- `review_manifest.json` は入力 artifact の path / hash / producer / source safety を保持する。
- `strategy-review-record` で、人間が review packet を読んだ判断を `operator_review.yaml` として保存できる。
- `strategy-review-record --validate-existing` で、保存済み operator review が同じ `review.md` / `review_manifest.json` を見ていたかを path / hash で再照合できる。

追加された schema family:

- `strategy_review_manifest.v1`
- `operator_strategy_review.v1`

境界:

- Strategy Review は paper / live 許可ではない。
- `PAPER_OBSERVATION_CANDIDATE` は validation candidate であり、paper execution permission ではない。
- `live_allowed=false` と `paper_execution_allowed=false` を維持する。

関連 docs:

- [strategy_review/README.md](strategy_review/README.md)
- [strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md](strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md)
- [strategy_review/DOGFOOD_REVIEW_2026-06-16.md](strategy_review/DOGFOOD_REVIEW_2026-06-16.md)

### 3. Paper observation は「作る」だけでなく「追記する」「状態を読む」能力が増えた

2026-06-16 版では、`strategy-paper-observation-cycle` で paper observation cycle artifact を作れることが中心だった。

現在できること:

- `strategy-paper-observation-append` で既存 paper observation session manifest を読み、manifest hash を確認した上で同じ session ledger に観察行を追記できる。
- `strategy-paper-observation-status` で既存 paper observation review / session manifest / lifecycle review を読み、normal observation と smoke observation を分けた status artifact を作れる。
- `data/research/strategy_lifecycle/paper_observation_status.json` に `observation_state`, `next_action`, `normal_session_count`, `smoke_session_count`, `latest_normal_requirement_gaps`, `normal_thresholds_met`, `smoke_pass_counts_as_normal_pass`, `live_conversion_allowed`, `permits_live_order`, `wallet_used`, `signing_used`, `exchange_write_used` などを出せる。

追加された schema:

- `strategy_paper_observation_status.v1`

実務上の違い:

- 同じ日の artifact 再生成を「新しい観察」と誤読しにくくなった。
- smoke pass と normal paper observation pass を分けて読めるようになった。
- 既存 session artifact がある場合、`strategy-paper-observation-cycle` は同じ session id の使い回しを避け、追記は専用 command に分離された。

境界:

- paper observation status は paper intent 生成、paper order 実行、ledger 再集計をしない。
- `needs_more_normal_paper_observation` は live へ進む意味ではない。
- `trading_days` は同一日の fill 増加では代替できない。

### 4. Venue capability は fixture-first の read-only probe として独立した

2026-06-16 版では、venue policy は `VenueId` / suitability catalog / capability contract の説明が中心だった。

現在できること:

- `venue-read-only-probe` で `trade_xyz`, `bitget_demo`, `bitget_futures`, `hyperliquid_perp` の capability boundary を local artifact として出せる。
- `venue_read_only_probe_summary.v1` schema で probe summary を検査できる。
- probe result は fixture-first で、external API、credentials、network attempt、wallet、signing、exchange write、live order を使わない。

実務上の違い:

- future venue を「実装済み live venue」と誤読せず、schema / paper / network / live disabled の境界を artifact として確認できる。
- Bitget / Hyperliquid は known future venues のままだが、current `VenueId` ではなく、Strategy Lab の正式 target venue でもないという説明が強くなった。

### 5. Trade[XYZ] は read-only execution state collector contract が増えた

2026-06-16 版では、Trade[XYZ] data / quote / readiness / pure backtest の説明が中心だった。

現在できること:

- Trade[XYZ] の read-only execution state collector contract を持つ。
- public user address と `SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1` がある場合だけ、`/info` 由来の account state / open orders / fills を読む設計になった。
- 未設定時は external API を呼ばず、`trade_xyz_execution_state_user_address_missing` のような reason を出す。
- `execution-snapshot`, `execution-read-only-surfaces`, `execution-drift-overview`, `phase-gate-review` が concrete reason / next action を伝播する。

実務上の違い:

- 「execution drift がある」だけでなく、「何が未設定で、次に何を設定すべきか」を artifact で追いやすくなった。
- ただし wallet secrets、signing、live order、exchange write credentials は引き続き使わない。

### 6. Strategy Lab / Research Data / Operations 系 CLI の help が IO と境界を明示するようになった

2026-06-16 版では、できることの一覧はあったが、個々の CLI が「何を読むか」「何を書くか」「何をしないか」の help 契約は薄かった。

現在強化された例:

- `build-paper-intent-preview`: paper-only intent preview の入力と live conversion 禁止を明示。
- `promotion-decision`: promotion decision artifact の入力と decision の意味を明示。
- `build-paper-candidate-pack`: candidate pack の入力、selected candidate、paper-only 境界を明示。
- `evaluate-strategy-lab`: Strategy Lab signal 評価の入力と output を明示。
- `strategy-experiment-run`: experiment spec から paper-only signal artifact を作る境界を明示。
- `build-signals`, `build-feature-panel`, `check-research-quality`, `build-cost-matrix`, `alpaca-smoke`: local / read-only / generated artifact の IO を明示。
- `diagnose-quotes`: local quote rows を診断し operator report を書くことを明示。
- `validate-artifacts`: local `data/` と `schemas/` を読み、`checked_files` / `issues` を出し、`--strict` で Trade[XYZ] artifact chain を要求し、issue 時に exit 2 になることを明示。
- `check-go-no-go`: local Go/No-Go evidence summary の入力、出力、no external API / no paper order / no live permission 境界を明示。

実務上の違い:

- operator が command help だけを見ても、local artifact command と external/API/order command を混同しにくくなった。
- CLI smoke tests が help text の重要表現を守るようになった。

### 7. Docs は「巨大な current state」から「入口 + domain docs + archive」へ再編された

2026-06-16 版では、この文書自体に public command catalog や幅広い capability detail を多く抱えていた。

現在の分割:

- [CURRENT_STATE.md](CURRENT_STATE.md): short current-state index。
- [CODE_STATUS.md](CODE_STATUS.md): thin code-status index。
- [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md): 実装済み surface の一覧。
- [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md): 次に見るべき方向と external-input restart checklist。
- [REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md](REPO_CAPABILITIES_PLAIN_JA_2026-06-17.md): 非専門向けの plain Japanese capability guide。
- [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md): public CLI command catalog。
- [runbooks/README.md](runbooks/README.md): domain runbook index。
- [strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md](strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md): Strategy Lab capability detail。

実務上の違い:

- current docs から古い fixed runtime snapshot / fixed pass count / dated artifact hash を減らし、必要なときは runtime command を再実行する方針になった。
- 実装済み plan や古い audit は `docs/archive/` と `plan/archive/` に移り、current proof と historical context を分けた。
- HTML current docs には同名 Markdown source を求める checker が追加された。

### 8. Current-docs checker と full gate が強化された

2026-06-16 版では `scripts/check_current_docs.py` が metadata / links / EOF / legacy root reference を見るのが中心だった。

現在の checker / gate:

- `scripts/check_current_docs.py` は current docs の semantic drift、HTML source 対応、plan routing も検査する。
- `scripts/check_cli_catalog.py` が public CLI catalog と Typer registration を照合する。
- `./scripts/check` は CLI catalog check も含む。
- full gate の現行構成は `./scripts/check` を再実行して確認する。handoff は最後に実行した結果の記録であり、current proof の代わりにはしない。

実務上の違い:

- command を追加して docs catalog を忘れる drift を検出できる。
- current docs に古い runtime snapshot を残す drift を検出しやすくなった。
- ただし `data/` は git-ignored runtime state なので、artifact 値は都度再生成または再確認が必要である。

### 9. CI / runtime 運用まわりは Node24 対応と external-input checklist が増えた

2026-06-16 版には、CI action runtime と external input restart checklist の説明は薄かった。

現在の変化:

- GitHub Actions は Node24 runtime 対応 action に更新された。
- `docs/NEXT_DIRECTION_CURRENT.md` に external input restart checklist が追加され、Trade[XYZ] public user address、Bitget demo env、normal paper observation の再開条件を current docs から辿れる。
- README、CURRENT_STATE、CODE_STATUS、OPERATIONS_RUNBOOK、Strategy Lifecycle docs が external-input checklist へルーティングする。

実務上の違い:

- external input が必要な作業と、local-only で続けてよい作業を分けやすくなった。
- read-only / paper observation の再開手順を live permission と混同しにくくなった。

### 10. 変わっていない重要境界

機能は増えたが、次は変わっていない。

- production live trading ready ではない。
- wallet secrets、signing、exchange write は使わない。
- `READ_ONLY_GO` は live readiness ではない。
- backtest pass、pack validation pass、strategy review、operator review、paper observation status は、単独では alpha / paper execution permission / live permission を証明しない。
- Bitget futures / Hyperliquid perp は known future venues だが、current `VenueId` ではなく、Strategy Lab の正式 target venue でもない。
- `PaperIntentPreview` は paper-only artifact であり、live order へ変換しない。

## できないこと / 未証明

この repo は現時点で次を証明または実行しない。

- production live trading ready
- wallet secrets / signing / exchange write
- public operator CLI からの Trade[XYZ] micro-live 実行
- Bitget production futures / Hyperliquid perp の正式 Strategy Lab venue
- Bitget credentialed read-only network smoke の完了証明
- Bitget demo order lifecycle の完了証明
- Alpaca fresh live `status=pass` の常時保証
- backtest 結果だけによる alpha / paper pass / live readiness
- HftBacktest / qstrader / PyBroker / skfolio / Riskfolio-Lib の dependency 採用または engine 実行
- market replay からの market impact proof
- NDX Layer 2.4 approval からの paper / live readiness 直接主張
- `PaperIntentPreview` の live order 変換
- `bitget_demo` を production Bitget futures として扱うこと

## まず読む順番

1. [CURRENT_STATE.md](CURRENT_STATE.md)
2. [AI_AGENT_STRATEGY_BACKTEST_GUIDE.md](AI_AGENT_STRATEGY_BACKTEST_GUIDE.md)
3. [STRATEGY_AND_BACKTEST_USER_GUIDE.md](STRATEGY_AND_BACKTEST_USER_GUIDE.md)
4. [CODE_STATUS.md](CODE_STATUS.md)
5. [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
6. [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md)
7. [algo/README.md](algo/README.md)
8. [strategy_research_lab/README.md](strategy_research_lab/README.md)
9. [strategy_research_lab/08_CURRENT_CAPABILITIES.md](strategy_research_lab/08_CURRENT_CAPABILITIES.md)
10. [strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md](strategy_research_lab/08_CURRENT_CAPABILITIES_DETAILS.md)
11. [backtest/README.md](backtest/README.md)
12. [backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md](backtest/BACKTEST_CURRENT_TECHNICAL_REFERENCE.md)
13. [strategy_review/README.md](strategy_review/README.md)
14. [strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md](strategy_review/OPERATOR_REVIEW_PACKET_RECIPE.md)
15. [strategy_lifecycle/README.md](strategy_lifecycle/README.md)
16. [research/ndx/README.md](research/ndx/README.md)
17. [OPERATIONS_RUNBOOK.md](OPERATIONS_RUNBOOK.md)
18. [ARCHITECTURE_AND_PHASES.md](ARCHITECTURE_AND_PHASES.md)
19. [MIGRATION_HISTORY.md](MIGRATION_HISTORY.md)
20. [REPO_CLI_CATALOG_CURRENT_2026-06-17.md](REPO_CLI_CATALOG_CURRENT_2026-06-17.md)
