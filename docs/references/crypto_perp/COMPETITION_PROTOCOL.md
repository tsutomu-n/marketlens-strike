<!--
作成日: 2026-06-21_15:07 JST
更新日: 2026-06-21_15:07 JST
-->

# Crypto Perp Competition Protocol

## Purpose

Compare hypotheses without turning one early narrative into the product.

The tournament candidates are equal at entry:

- `REVERSAL_SHORT`
- `CONTINUATION_LONG`
- `NO_TRADE`
- `UNKNOWN`
- later human/system variants that keep the same artifact contracts

## Required Inputs

- immutable event artifact
- prospective decision artifact created before outcome evidence
- matured outcome artifact
- known data gaps
- cost and execution assumptions for the compared horizon

## Scoring Order

1. Actual cash ledger when live measurement is explicitly approved and reconciled.
2. Prospective paper decision versus matured outcome.
3. Fixture/golden parser validation.
4. Backfilled or external sidecar diagnostics.

Win rate, Sharpe, and model scores are secondary. They cannot override actual cash.

## Anti-Overfit Rules

- Store all variants, not only winners.
- Keep no-trade as a benchmark.
- Mark PBO / deflated Sharpe as `not_estimable` while event count is too small.
- A strategy does not graduate because a sample day, fixture, or sidecar report passes.
- All boundary changes need a new decision version or replacement chain.

## M07 Validation Role

M07 accelerates bug discovery:

- Tardis-style fixture checks parser, book reconstruction, and VWAP arithmetic.
- pybotters spike checks whether an alternate Bitget WS backend hides or exposes gaps.
- Freqtrade sidecar checks lookahead/recursive style mistakes without GPL code entering core.
- Hummingbot notes check connector assumptions against official Bitget docs.
