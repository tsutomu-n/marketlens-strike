<!--
作成日: 2026-06-09_15:07 JST
更新日: 2026-06-09_16:13 JST
-->

# Acceptance

Implementation is complete only when all are true:

- the plan package exists under this directory
- `src/sis/venues/suitability.py` exists and is tested
- NDX/QQQ cannot route to `bitget_demo`, `bitget_futures`, or
  `hyperliquid_perp` at paper candidate, paper intent, or live stages
- `trade_xyz` NDX/QQQ paper candidate and paper intent are blocked until a later
  validation/promotion gate explicitly changes that
- blocked `TradeCandidate` rows remain valid artifacts
- selected candidates with `status != "candidate"`, non-empty `block_reasons`,
  or venue-unsuitable symbols fail closed
- `PaperIntentPreview` fails closed for venue-unsuitable NDX/QQQ family rows
- raw JSON passed to `paper-from-intents` is revalidated and cannot bypass
  `PaperIntentPreview`
- legacy `paper-step` does not write paper orders/fills for NDX/QQQ family rows
  and records `legacy_paper_blocked_*` summary metrics
- BTCUSDT `bitget_demo` fixture tests still pass
- `bitget_futures` and `hyperliquid_perp` are not added to `VenueId`
- Strategy Lab artifact schemas still allow only `trade_xyz` and `bitget_demo`
- `README.md` explains the NDX/QQQ venue boundary
- no Strategy Lab export, backtest, paper order, live order, or credentialed API
  flow is introduced
- focused tests and `./scripts/check` pass
