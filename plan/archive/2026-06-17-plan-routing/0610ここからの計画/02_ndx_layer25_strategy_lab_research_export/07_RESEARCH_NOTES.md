<!--
作成日: 2026-06-10_15:06 JST
更新日: 2026-06-10_15:06 JST
-->

# Research notes

## Purpose

This note records the external research implications that changed the implementation plan. It is not a claim that Layer 2.5 proves alpha.

## Numerai lessons

Numerai's diagnostics guidance warns that validation metrics can be overfit and should not be treated as future-performance proof. Numerai's feature-neutral correlation and feature exposure materials support using neutralization and exposure checks as diagnostics, not as deployment permission.

Implementation consequence:

- Layer 2.5 may export research signals after Layer 2.4 approval.
- Layer 2.5 must not claim alpha, backtest readiness, paper readiness, or live readiness.
- Signal rows must preserve research-only `block_reasons`.
- Any optimization over neutralization proportion, side policy, thresholds, or ranking policy belongs to a later validation gate, not this export slice.

## Backtest overfitting lessons

Bailey and Lopez de Prado's Deflated Sharpe Ratio work and PBO / CSCV work warn that strategy selection and repeated backtests inflate apparent performance. Harvey, Liu, and Zhu's multiple-testing work similarly warns that finance factor discovery needs higher evidence thresholds than ordinary single-test significance.

Implementation consequence:

- Layer 2.5 should record `tested_variant_count: 1`.
- Layer 2.5 should record `side_policy`, `rank_policy`, and `hash_excludes`.
- Layer 2.5 should not add threshold search, parameter optimization, portfolio construction, or backtest selection.
- A later Layer 2.6 backtest gate should explicitly handle PBO, DSR, purged/embargoed validation, and multiple-testing accounting before any paper/live path is considered.

## Plan correction from local code review

The existing `build-paper-candidate-pack` command builds selected candidate block reasons from venue suitability and does not automatically propagate selected signal `block_reasons`.

Implementation consequence:

- The implementation must add a narrow propagation path from selected signal `block_reasons` to `TradeCandidate.block_reasons`.
- Tests must prove `RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED` survives into candidate pack output.
- Venue suitability remains required but is not enough by itself.
