<!--
作成日: 2026-06-10_12:02 JST
更新日: 2026-06-10_12:02 JST
-->

# Code truth and risk audit

## Confirmed local facts

- Current package root is `src/sis/`; do not create `src/strat_tool/`.
- Layer 2.4 explicitly does not write `strategy_signals.parquet`.
- `schemas/ndx_residual_validation_decision.v1.schema.json` permits only research export and keeps backtest, paper candidate, PaperIntentPreview, and live order permissions false.
- `src/sis/research/ndx/residual_validation.py` sets `permits_strategy_lab_research_only_export` only when decision is `APPROVE_STRATEGY_LAB_EXPORT`.
- Existing Strategy Lab canonical signal outputs are `data/research/strategy_signals.parquet` and `data/research/strategy_signal_manifest.json`.
- Existing `StrategySignalRecord` accepts `execution_venue` values from `VenueId`, currently including `trade_xyz` and `bitget_demo`.
- Existing `SymbolBinding` permits `trade_xyz` / `XYZ100` only when `real_market_symbol` is `QQQ`.
- Existing paper candidate flow blocks `trade_xyz` / `XYZ100` / `QQQ` at paper candidate stage with `VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION`.

## Main risks

1. Ideal narrative risk: treating `APPROVE_STRATEGY_LAB_EXPORT` as alpha proof.
   - Mitigation: export manifest must say `research_only: true` and all paper/live permissions false.

2. Artifact escalation risk: writing canonical `strategy_signals.parquet` makes downstream Strategy Lab commands able to see NDX signals.
   - Mitigation: preserve existing venue suitability block, add tests proving candidate pack remains blocked and PaperIntentPreview remains empty even after operator promotion.

3. Trading-intent risk: mapping residual sign to `long` / `short` can look like a deployable strategy.
   - Mitigation: emitted rows must include `reason_codes` and `block_reasons` that mark the export as research-only and not operator-promoted. Any future paper/live promotion must be a separate plan.

4. Leakage risk: residual rows alone do not carry `feature_ts`.
   - Mitigation: join residual / neutralized rows to `ndx_feature_panel.parquet` by `date` and use `feature_ts` for `ts_signal`; validate `source_ts_max <= feature_ts` through existing NDX leakage checks where applicable.

5. Hash lineage risk: export could read stale artifacts from mixed runs.
   - Mitigation: validate path existence, manifest hashes, decision `summary_path`, residual diagnostics `neutralized_residuals_hash`, and shared `dag_artifact_hash` / `feature_manifest_hash`.

6. Schema drift risk: Strategy Lab signal frame has many optional fields and a strict canonical schema.
   - Mitigation: build rows through `StrategySignalRecord`, cast through `STRATEGY_SIGNAL_SCHEMA`, then call `validate_strategy_signal_frame`.

7. Test optimism risk: only testing an approved fixture hides fail-closed behavior.
   - Mitigation: include rejection, missing artifact, hash mismatch, and downstream paper/live non-permission tests.

## Deliberate non-goals

- Do not decide whether residual scores are economically useful.
- Do not add portfolio construction.
- Do not add position sizing beyond a nullable `position_weight`.
- Do not use live or historical broker/exchange data.
- Do not rewrite Strategy Lab architecture.
