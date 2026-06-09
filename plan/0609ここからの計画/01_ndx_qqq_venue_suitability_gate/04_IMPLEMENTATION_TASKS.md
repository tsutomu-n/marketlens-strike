<!--
作成日: 2026-06-09_15:07 JST
更新日: 2026-06-09_16:13 JST
-->

# Implementation Tasks

1. Add `src/sis/venues/suitability.py`.
   - Define `VenueSuitability` and `VenueSuitabilityDecision`.
   - Define `VENUE_SUITABILITY_CATALOG`.
   - Add pure helpers:
     - `is_ndx_qqq_family(...)`
     - `venue_suitability(...)`
     - `assess_venue_suitability(...)`
     - `venue_suitability_block_reasons(...)`

2. Implement the initial catalog.
   - `trade_xyz`: NDX proxy research/read-only context only; paper/live blocked.
   - `bitget_demo`: crypto demo fixture only; NDX/QQQ blocked.
   - `bitget_futures`: catalog only, disabled by default, no paper/live.
   - `hyperliquid_perp`: catalog only, crypto perp direct, NDX/QQQ blocked.

3. Implement NDX/QQQ family detection.
   - Match `execution_symbol` in `XYZ100`, `NDX`, `QQQ`.
   - Match `real_market_symbol` in `QQQ`, `NDX`, `^NDX`.

4. Do not reject `TradeCandidate` construction.
   - A blocked candidate is an artifact and must remain recordable.

5. Add selected-candidate guard in `PaperCandidatePack`.
   - Compute suitability for each selected candidate at `paper_candidate` stage.
   - Reject selected candidates whose `status` is not `candidate`.
   - Reject selected candidates with non-empty `block_reasons`.
   - If blocked, raise with text containing:
     `selected_candidate_ids contain venue-unsuitable candidates`.

6. Add paper-intent guard in `PaperIntentPreview`.
   - Compute suitability at `paper_intent` stage.
   - Reject NDX/QQQ `trade_xyz` and `bitget_demo` paper intents for now.
   - Preserve BTCUSDT `bitget_demo` fixture intents.

7. Update Strategy Authoring paper preview.
   - Add suitability block reasons to candidate `block_reasons`.
   - Move suitability-blocked candidates to `rejected_candidate_ids`.
   - Keep `paper_intent_preview.json` as an empty array.

8. Update `build-paper-candidate-pack` in `src/sis/commands/research.py`.
   - Apply suitability to selected signal candidates.
   - Suitability-blocked selected signals become rejected candidates.
   - Keep candidate rows as evidence with explicit block reasons.
   - Report selected/rejected counts accurately.

9. Harden raw intent JSON execution.
   - Ensure `paper-from-intents` validates every raw JSON row through
     `PaperIntentPreview.model_validate`.
   - Direct NDX/QQQ family JSON must fail with the same paper-intent suitability
     reason as generated artifacts.

10. Harden legacy `paper-step`.
    - Keep `data/research/signals.csv` as legacy research/backtest export.
    - Do not generate paper orders or fills for NDX/QQQ family rows.
    - Record `legacy_paper_blocked_count`.
    - Record `legacy_paper_blocked_reason_counts`.

11. Update README Current Boundaries.
   - State Bitget/Hyperliquid direct are not NDX/QQQ execution venues.
   - State `bitget_demo` is fixture/demo, not NDX/QQQ paper/live.
   - State `trade_xyz` NDX proxy cannot advance to paper/live before later gates.
