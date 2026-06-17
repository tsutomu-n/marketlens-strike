<!--
作成日: 2026-06-11_06:27 JST
更新日: 2026-06-11_06:45 JST
-->

# Code truth and risk audit

## Confirmed local facts

- `VenueId` currently permits only `trade_xyz` and `bitget_demo`.
- NDX/QQQ paper path is blocked in `src/sis/venues/suitability.py` by `VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION` for `trade_xyz`.
- `PaperCandidatePack.selected_candidate_ids` must reference candidates with `status="candidate"` and empty `block_reasons`.
- `PaperIntentPreview` validates venue suitability again at `paper_intent` stage.
- `PromotionDecision` is a paper-observation human decision artifact and rejects paper/live readiness claims.
- `PaperIntentPreview` forces `requires_revalidation=true`, `paper_only=true`, `live_conversion_allowed=false`, `wallet_used=false`, and `exchange_write_used=false`.
- `paper-from-intents` revalidates `PaperIntentPreview` models before writing paper orders/fills.
- `paper-from-intents` also requires `data/normalized/quotes.parquet` or an explicit quotes path and blocks rows with `LATEST_QUOTE_MISSING`.
- Layer 2.5 currently writes research-only Strategy Lab signal artifacts with `RESEARCH_ONLY_EXPORT_NOT_OPERATOR_PROMOTED`.
- Existing Strategy Authoring fixed-horizon backtest exists, but it is not an NDX residual lineage acceptance gate.

## Main risks

1. Block reason deletion risk.
   - Mitigation: do not remove NDX/QQQ block reasons globally. Add an evidence-aware override that requires matching Layer 2.6 and Layer 2.7 artifacts.

2. Paper/live boundary drift.
   - Mitigation: keep `PaperIntentPreview` paper-only constants unchanged and add tests proving live fields remain false after NDX promotion.

3. Backtest overclaim risk.
   - Mitigation: Layer 2.6 decision names paper-observation review only, records evidence tier, and must not set paper/live readiness claim fields.

4. Artifact mismatch risk.
   - Mitigation: Layer 2.6 and Layer 2.7 must record source export ids, hashes, run ids, and current signal artifact hash. Downstream commands must reject stale or mismatched promotion artifacts.

5. Raw JSON bypass risk.
   - Mitigation: `PaperIntentPreview` model validation and `paper-from-intents` must still reject NDX/QQQ unless the promotion evidence is present and valid.

6. Test optimism risk.
   - Mitigation: include rejection tests for missing Layer 2.6, stale Layer 2.7, hash mismatch, hold/reject decisions, live stage, and raw JSON bypass.

7. Paper-run feasibility risk.
   - Mitigation: Layer 2.6 must check local quote availability for the intended `trade_xyz` / `XYZ100` paper observation path, and downstream verification must include `paper-from-intents` revalidation, not just preview generation.

8. Small-sample fixture narrative risk.
   - Mitigation: record `sample_scope` / `evidence_tier`, require non-approve or warning reasons when the input is fixture-only, and never describe default fixture approval as robust out-of-sample performance.

## Deliberate non-goals

- Do not solve production live execution.
- Do not decide whether the residual model is economically useful beyond the configured local paper-observation criteria.
- Do not add new external data collection.
- Do not add a new venue.
- Do not rewrite Strategy Lab paper flow.
