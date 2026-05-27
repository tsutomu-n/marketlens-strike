# Architecture And Phases

この文書は current codebase を migration 後の構成として読むための要約です。

## Subsystems

- `src/sis/venues/trade_xyz`: universe mapping, HIP-3 registry, quote collection, normalization, venue quality inputs
- `src/sis/real_market`: research-side bars, quality, feature builder, provider policy
- `src/sis/tracking`: real-market vs venue comparison and trade-allowed decisions
- `src/sis/paper`: venue-gated paper fills, portfolio state, reports
- `src/sis/execution`: `Trade[XYZ]` micro live safety code and execution read-only surfaces
- `src/sis/reports`, `src/sis/ops`, `src/sis/state`: operations, dashboards, remediation, daemon, notifications
- `src/sis/cli.py` and `src/sis/commands/`: root Typer app registration plus feature-specific command modules
- `archive/gtrade_ostium_legacy_archive_*.zip`: legacy gTrade/Ostium source and sidecar history

## Phase Interpretation

`plan/archive/PR-00_to_PR-08_implementation_plan.md` の phase ではなく、運用境界としての読み方:

- Phase 1: quote / evidence / Go-No-Go inputs
- Phase 2: real-market and tracking quality gates
- Phase 3: decision and backtest
- Phase 4: paper execution and operations loop
- Phase 5: read-only execution observation
- Phase 6: micro live safety surface
- Phase 7: full live integration and external operations

current truth:

- Phase 1 から Phase 6 の code surface は存在する
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
- `paper` は tracking and quality-gated execution simulation
- `micro_live` は tiny live safety sequence のみを扱い、strategy promotionは扱わない

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
- Trade[XYZ] 主軸の operations/readiness/phase gate cutover
- production live trading

## Ops Boundary

`refresh-operations-artifacts` 以下の operations chain は paper / execution artifact を束ねる restart surface である。一部 generated reports は legacy read-only collector blocker を表示し得るため、Trade[XYZ] readiness とは分けて読む。

つまり:

- migration 実装完了
- full operational cutover 未完了

この 2 つは同時に真になり得る。
