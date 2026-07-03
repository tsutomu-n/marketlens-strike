<!--
作成日: 2026-07-03_12:53 JST
更新日: 2026-07-03_13:03 JST
-->

# Action Required

## AR-2026-07-03-001: C9 `side_bias=both` semantics

Status: resolved for C9 v0 bridge-first dogfood

Context:

- Current `profit-core-reality-check` dogfood returns `next_single_blocker_to_fix=UNSUPPORTED_SIDE_BIAS_DOMINATES`.
- The blocked candidate is `cand-003-perp_reversal_after_liquidation_move`.
- Its `parameter_set.side_bias` is `both`.
- C9 authoring bridge currently supports only directional `long` and `short` candidates because Strategy Authoring specs require one executable side.

Decision needed:

Choose one explicit semantics for `side_bias=both` before C9 bridge can convert it into a trade spec:

1. Expand into two explicit candidates, one `long` and one `short`, with separate candidate ids and lineage.
2. Treat it as a non-directional filter candidate, not as a Strategy Authoring trade spec.
3. Keep it permanently blocked for C9 v0 and require generator/profile policy to avoid shortlisting it for bridge-first dogfood.

Resolution applied:

- C9 v0 uses option 3.
- `crypto-perp-risk-taker` profile now rejects non-directional `side_bias` before shortlist.
- Rejected candidates remain in candidate inventory and search ledger with an explicit rejection reason.
- C9 authoring bridge still does not convert `both` to a trade spec.

Remaining future decision:

If a later version needs `side_bias=both` as an executable strategy, choose option 1 or 2 explicitly in a new plan before changing bridge semantics.

Rejected without decision:

- Do not silently map `both` to `long`.
- Do not silently map `both` to `short`.
- Do not infer a direction from `abs(...)` signal text.
- Do not treat `both` as `NO_TRADE`.

Why this needs a decision:

Changing `both` into an executable order direction changes candidate meaning. That is a strategy semantics decision, not a safe local bug fix.

## AR-2026-07-03-002: C9 liquidation notional source

Status: open

Context:

- Current regenerated dogfood returns `next_single_blocker_to_fix=MISSING_SOURCE_COLUMNS_DOMINATES`.
- The remaining bridge-blocked candidate is `cand-004-perp_reversal_after_liquidation_move`.
- It requires `liquidation_notional`.
- Current repo-native Bitget public source refresh writes contracts, tickers, 5m candles, latest snapshot, and scanner rows.
- Current local source root has no liquidation stream or liquidation notional column.

Decision needed:

Choose one evidence source for `liquidation_notional` before reversal-after-liquidation candidates can be bridged:

1. Add a public, credential-free liquidation feed if a vetted source exists and its license/terms allow local artifact use.
2. Add an authenticated/private exchange source only under a separate permissioned plan.
3. Keep `perp_reversal_after_liquidation_move` blocked in C9 v0 and avoid shortlisting this family for bridge-first dogfood until liquidation source exists.

Rejected without decision:

- Do not infer liquidation notional from candle return.
- Do not infer liquidation notional from ordinary trade fills.
- Do not infer liquidation notional from open interest alone.
- Do not mark `liquidation_notional` as present using an estimate-only proxy.

Why this needs a decision:

`liquidation_notional` is evidence-specific. Substituting candles, OI, or regular fills would make the bridge look more complete while weakening the hypothesis semantics.
