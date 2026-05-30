# Architecture And Phases

この文書は current codebase を migration 後の構成として読むための要約です。

## Subsystems

- `src/sis/venues/trade_xyz`: universe mapping, HIP-3 registry, quote collection, normalization, venue quality inputs
- `src/sis/real_market`: research-side bars, quality, feature builder, provider policy
- `src/sis/tracking`: real-market vs venue comparison and trade-allowed decisions
- `src/sis/research/strategy_lab`: strategy experiment specs, strategy signal records, evaluation plans, trial ledger, trade candidates, paper candidate packs, promotion decisions, paper intent previews
- `src/sis/paper`: venue-gated paper fills, portfolio state, reports
- `src/sis/execution`: `Trade[XYZ]` micro live safety code and execution read-only surfaces
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
- Trade[XYZ] read-only PR12 の generated artifact gate は `READ_ONLY_GO` まで確認済み
- Strategy Research Lab の schema / model / command surface は存在する
- Phase 7 は未完了
- operational promotion は generated artifact gate に依存する

## Migration Boundary

- 新規コードの主軸は `trade_xyz`
- `gtrade` / `ostium` は active implementation tree ではなく archive zip と historical artifacts として残る
- `ostium-python-sdk` は active dependency ではない

## Data Boundary

- `trade_xyz` quote は venue execution-side data
- `real_market` data は price truth / feature truth
- `tracking` はその差分を gate に変換する
- `strategy_lab` は research signal, trial, candidate, promotion, paper preview を order と分離して管理する
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
- `PromotionDecision` は paper へ進める人間判断 artifact。
- `PaperIntentPreview` は paper-only の仮注文意図であり、live order へ変換しない。
- JSON Schema は薄い guard として存在し、詳細な runtime validation は Pydantic model にある。
- 詳細仕様は `docs/strategy_research_lab/README.md` 以下にある。

## Execution Boundary

`src/sis/execution` には 2 系統ある:

- execution read-only observation / reporting surfaces
- `Trade[XYZ]` micro live safety surface: policy, adapter, canary

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
- production live trading

## Ops Boundary

`refresh-operations-artifacts` 以下の operations chain は paper / execution artifact を束ねる restart surface である。Trade[XYZ] read-only PR12 は phase gate まで接続済みだが、execution drift や legacy generated report の文脈は bot/live readiness と分けて読む。

つまり:

- migration 実装完了
- Trade[XYZ] read-only phase gate cutover 完了
- live trading / production operations 未完了

これらは同時に真になり得る。
