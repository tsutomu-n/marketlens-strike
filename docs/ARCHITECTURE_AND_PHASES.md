<!--
作成日: 2026-05-25_19:45 JST
更新日: 2026-06-18_01:50 JST
-->

# Architecture And Phases

この文書は current codebase を migration 後の構成として読むための要約です。

## Subsystems

- `src/sis/venues/trade_xyz`: universe mapping, HIP-3 registry, quote collection, normalization, venue quality inputs
- `src/sis/real_market`: research-side bars, quality, feature builder, provider policy
- `src/sis/tracking`: real-market vs venue comparison and trade-allowed decisions
- `src/sis/research/strategy_lab`: strategy experiment specs, strategy signal records, evaluation plans, trial ledger, trade candidates, paper candidate packs, promotion decisions, paper intent previews
- `src/sis/venues/suitability`: venue suitability catalog and fail-closed stage checks for research, paper candidate, paper intent, and live boundaries
- `src/sis/research/dag`: NDX Layer 2.2 DAG config validation, lint, export, manual review pack/import, and exit gate decision contracts
- `src/sis/research/ndx`: NDX Layer 2.3/2.4/2.5 fixture-first source resolution, feature panel, open-gap residual, diagnostics, neutralization pre-report, artifact lineage checks, residual validation gate, and research-only Strategy Lab export bridge
- `src/sis/research/strategy_lifecycle`: Strategy Authoring backtest acceptance and integrated lifecycle review over backtest, paper observation, and phase gate artifacts
- `src/sis/backtest/engine` and `src/sis/backtest/trade_xyz`: Trade[XYZ] pure backtest v0.1, long-only single-symbol accounting, fill, cost, gate, metrics, report artifacts
- `src/sis/paper`: venue-gated paper fills, portfolio state, reports
- `src/sis/execution`: `Trade[XYZ]` micro live safety code, `bitget_demo` local/mock-first adapter, and execution read-only surfaces
- `src/sis/reports`, `src/sis/ops`, `src/sis/state`: operations, dashboards, remediation, daemon, notifications
- `src/sis/cli.py` and `src/sis/commands/`: root Typer app registration plus feature-specific command modules
- `archive/gtrade_ostium_legacy_archive_*.zip`: legacy gTrade/Ostium source and sidecar history

## Phase Interpretation

`plan/archive/PR-00_to_PR-08_implementation_plan.md` の phase ではなく、運用境界としての読み方:

- Phase 1: quote / evidence / Go-No-Go inputs
- Phase 2: real-market and tracking quality gates
- Phase 3: Strategy Research Lab evaluation, trial ledger, and candidate selection
- Phase 4: paper candidate promotion, paper-only intent preview, paper execution, and operations loop
- Phase 5: read-only execution observation
- Phase 6: micro live safety surface
- Phase 7: full live integration and external operations

current truth:

- Phase 1 から Phase 6 の code surface は存在する
- Trade[XYZ] read-only PR12 の generated artifact gate は `phase-gate-review` と runtime artifact で再確認する。`READ_ONLY_GO` は live readiness ではない
- Strategy Research Lab の schema / model / command surface は存在する
- NDX Layer 2.2 DAG foundation と Exit Gate Review Harness v3 Minimal の local/manual review surface は存在する
- NDX Layer 2.3 Preflight / Feature Panel / Open Gap Residual の local fixture-first surface は存在する
- NDX Layer 2.4 Residual Validation Gate の local validation surface は存在する。現在の default artifacts は `APPROVE_STRATEGY_LAB_EXPORT` まで進み、Layer 2.5 の research-only Strategy Lab export bridge を許可する
- Trade[XYZ] pure backtest v0.1 の Python API surface は存在する
- Phase 7 は未完了
- operational promotion は generated artifact gate に依存する

## Migration Boundary

- 現在の新規戦略評価の主軸は backtest-first / venue-neutral
- `trade_xyz` は実装済み主要 venue だが、当面の注文口主軸ではない
- `bitget_demo` は demo execution 検証用の venue id。production Bitget live とは分ける
- `gtrade` / `ostium` は active implementation tree ではなく archive zip と historical artifacts として残る
- `ostium-python-sdk` は active dependency ではない

## Data Boundary

- `trade_xyz` quote は venue execution-side data
- `real_market` data は price truth / feature truth
- `tracking` はその差分を gate に変換する
- `strategy_lab` は research signal, trial, candidate, promotion, paper preview を order と分離して管理する
- `research.dag` は DAG artifact、counter DAG、temporal availability、manual review gate を管理し、feature panel、residual calculation、backtest、paper/live order を扱わない
- `research.ndx` は NDX Layer 2.3/2.4/2.5 の local source resolution、feature panel、residual、diagnostics、neutralization pre-report、residual validation、research-only Strategy Lab export bridge を管理し、backtest、paper/live order を扱わない
- `backtest.engine` は pure backtest の accounting / fill / cost / artifact 契約を管理し、live execution や wallet/signing を扱わない
- `strategy_lifecycle` は backtest acceptance、paper observation review、phase gate summary を統合するが、live order、wallet/signing、exchange write を扱わない
- `paper` は tracking and quality-gated execution simulation
- `micro_live` は tiny live safety sequence のみを扱い、strategy promotionは扱わない

## Strategy Research Lab Boundary

Strategy Lab の現在の流れ:

```text
StrategyExperimentSpec
  -> StrategySignalRecord
  -> EvaluationPlan
  -> TrialRecord / TrialLedger
  -> TradeCandidate
  -> PaperCandidatePack
  -> PromotionDecision
  -> PaperIntentPreview
  -> paper-from-intents
```

境界:

- `StrategyExperimentSpec` は戦略実験定義であり、売買候補ではない。
- `TradeCandidate` は売買候補であり、paper/live order ではない。
- `PaperCandidatePack.selected_candidate_ids` は `status="candidate"`、空の `block_reasons`、venue-suitable の候補だけを受け入れる。
- `PromotionDecision` は paper へ進める人間判断 artifact。
- `PaperIntentPreview` は paper-only の仮注文意図であり、live order へ変換しない。
- NDX/QQQ family は research/backtest record としては残せるが、現行 paper path では selected candidate、paper intent、raw intent JSON、legacy `paper-step` order generation の各境界で止める。
- JSON Schema は薄い guard として存在し、詳細な runtime validation は Pydantic model にある。
- 詳細仕様は `docs/strategy_research_lab/README.md` 以下にある。

## NDX Research Boundary

現行 Layer 2.2 の流れ:

```text
configs/research_layer_2_2/ndx
  -> research-layer22-validate
  -> research-layer22-export
  -> research-layer22-review-pack
  -> manual review JSON
  -> research-layer22-review-import
  -> research-layer22-exit-gate
```

境界:

- `research-layer22-*` は local-only の research artifact harness。
- `review-pack` は inert artifact と evidence catalog を生成する。
- `review-import` は schema、pack hash、evidence refs、severity counts を検証する。
- `exit-gate` は `APPROVE_2_3` / `REVISE_2_2` / `REJECT_SEED` を出す。
- `APPROVE_2_3` の時だけ freeze manifest を生成し、`REVISE_2_2` / `REJECT_SEED` では同じ出力先の古い freeze manifest も削除する。
- external API、credentials、feature panel、residual calculation、neutralization、Strategy Lab export、backtest、paper/live order は対象外。

現行 Layer 2.3/2.4 の流れ:

```text
layer_2_2_freeze_manifest.json
  -> research-ndx-source-resolve
  -> research-ndx-feature-panel
  -> research-ndx-residual
  -> research-ndx-diagnostics
  -> research-ndx-residual-validate
  -> research-ndx-strategy-lab-export
```

境界:

- Layer 2.3 は fixture-first source resolution、feature panel、open-gap residual、diagnostics / neutralization pre-report、counter-DAG refutation skeleton を生成する。
- Layer 2.4 は feature/residual artifacts の lineage、timestamp、neutralization、counter-DAG refutation を検査し、`APPROVE_STRATEGY_LAB_EXPORT` / `REVISE_2_3` / `REVISE_2_2` / `REJECT_RESIDUAL` を出す。
- 現在の default fixture artifacts は `APPROVE_STRATEGY_LAB_EXPORT` になり、Layer 2.5 research-only export bridge を許可する。
- Layer 2.5 は approved residual から `strategy_signals.parquet` と manifest を生成するが、research-only block reason を付け、既存 Strategy Lab artifact は `--replace-existing` なしでは上書きしない。
- Layer 2.3/2.4/2.5 は backtest、paper candidate approval、`PaperIntentPreview` 通過、paper/live order、external API、credentials、dependency追加、NQ / VXN / SOX direct / options / gamma input を扱わない。

詳細は `docs/research/ndx/README.md`、`docs/research/ndx/09_LLM_REVIEW_GATE.md`、`docs/research/ndx/10_LAYER_2_3_NDX_PREFLIGHT.md`、`docs/research/ndx/11_LAYER_2_4_RESIDUAL_VALIDATION_GATE.md`、`docs/research/ndx/12_LAYER_2_5_STRATEGY_LAB_RESEARCH_EXPORT.md` にある。

## Backtest Boundary

現行 backtest surface は 3 つに分けて読む。

- Trade[XYZ] pure backtest v0.1: `run_backtest()` を入口にする Python API surface。
- Strategy Authoring fixed-horizon backtest: YAML authoring flow の paper-only 研究評価。
- Legacy backtest bridge: `uv run sis build-backtest` の互換 command。

Trade[XYZ] pure backtest v0.1 は public CLI を持たない。live order、wallet、signing、exchange write、MT5 / IC Markets / CFD は対象外。

詳細は `docs/backtest/README.md` と `docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md` にある。

## Execution Boundary

`src/sis/execution` には 3 系統ある:

- execution read-only observation / reporting surfaces
- `Trade[XYZ]` micro live safety surface: policy, adapter, canary
- `bitget_demo` local/mock-first surface: demo API header/signature boundary and fail-closed local smoke

micro live の current boundary:

- `scheduleCancel`
- tiny post-only / passive limit order
- `orderStatus` by `cloid`
- cancel by `cloid`
- filled 時の reduce-only close
- safety report and audit bundle

未完了:

- signing
- wallet / exchange secrets
- public micro live operator surface
- bot decision / live order preview の正式 surface
- Bitget credentialed read-only network smoke
- Bitget demo order lifecycle
- production live trading

## Ops Boundary

`refresh-operations-artifacts` 以下の operations chain は paper / execution artifact を束ねる restart surface である。Trade[XYZ] read-only PR12 は phase gate まで接続済みだが、execution drift や legacy generated report の文脈は bot/live readiness と分けて読む。

つまり:

- migration 実装完了
- Trade[XYZ] read-only phase gate cutover 完了
- live trading / production operations 未完了

これらは同時に真になり得る。
