<!--
作成日: 2026-07-04_22:37 JST
更新日: 2026-07-04_22:37 JST
-->

# Pre Actual Cash Varied Dogfood Plan

## Checkpoint ID

PAC-VARIED-DOGFOOD-2026-07-04

## Purpose

Dogfood the existing internal `write_pre_actual_cash_evidence_pack()` with 10 event / 10 outcome inputs that are not fixture clones. The inputs must vary by event time, outcome identity/result, and schema-supported regime proxy. Record the resulting `decision.json`, `decision.md`, and `docs/final-summary.md`.

## Current State

`write_pre_actual_cash_evidence_pack()` already writes the 11 expected artifacts by calling `build_pre_actual_cash_evidence_pack()`. The current writer dogfood test uses `_write_event_outcome_pairs(root, 10)`, which copies one `_event()` template into 10 event ids and writes `_outcome(event_id)` with the same settled time and price window. That proves the writer handles a count of 10, but it does not prove a realistic varied ten-pair pack.

The Crypto Perp event schema has no literal `regime` field. Current schema-supported regime-like evidence is `event_family` plus detection features and market context. `events_summary.json` exposes `event_family` and `information_cutoff_at`; `outcomes_summary.json` exposes `outcome_id` and `settled_at`; `decision.source_gap_summary.artifact_usage.event_outcome_pairs` exposes the selected pair identities.

## Constraints

- Use existing `write_pre_actual_cash_evidence_pack()`.
- Do not add a public pre-actual-cash CLI.
- Do not add actual cash source, cash ledger, actual-cash rows, actual-cash gate, tiny-live behavior, live orders, external exchange writes, wallet/signing, production deploy, credential changes, or ML/LLM trade decisions.
- Keep behavior local and deterministic.
- Do not use external API calls.
- Keep production code unchanged unless the existing writer cannot satisfy the dogfood requirement.
- For docs edited by the agent, keep the hidden Tokyo-time metadata header current.

## Target Files

- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `docs/crypto_perp/pre_actual_cash_varied_dogfood_2026_07_04/decision.json`
- `docs/crypto_perp/pre_actual_cash_varied_dogfood_2026_07_04/decision.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Approach

Replace the weak ten-pair fixture helper with a deterministic varied helper for this writer dogfood path. Build each event from the existing valid `_event()` model, but change event identity, artifact identity, `event_family`, `first_detected_at`, `information_cutoff_at`, `created_at`, universe/market snapshot ids, and detection feature values. Build each outcome through `build_outcome()` with a distinct `settled_at`, price window, market return, high/low ordering, and known-gap marker, so each `outcome_id` is generated from real varied outcome inputs instead of copied payloads.

Treat `event_family` as the explicit regime proxy because no `regime` field exists in `CryptoPerpEvent`. The test must assert multiple event families and distinct times instead of relying on prose.

Generate the tracked dogfood result under `docs/crypto_perp/pre_actual_cash_varied_dogfood_2026_07_04/` by running the existing writer on the same varied helper input. Add metadata to the generated `decision.md` because it is a tracked Markdown doc under the current-docs directory. Do not add metadata to `decision.json`.

## Implementation Steps

1. Add or replace a deterministic varied ten-pair helper in `tests/crypto_perp/test_profit_readiness_local_automation.py`.
2. Update `test_pre_actual_cash_pack_writer_dogfoods_ten_pairs` to write varied pairs, call the existing writer, validate `decision.json`, and assert:
   - 10 unique `event_id` values.
   - 10 unique `outcome_id` values.
   - 10 distinct event cutoff times.
   - 10 distinct outcome settled times.
   - at least 3 distinct `event_family` values as regime proxies.
   - varied outcome raw returns.
   - all `non_goal_flags` remain `false`.
3. Create the dogfood output directory under `docs/crypto_perp/` and generate `decision.json` / `decision.md` from `write_pre_actual_cash_evidence_pack()`.
4. Update `docs/final-summary.md` with branch, achieved work, changed files, verification, boundary, destructive-change status, migration, rollback, residual risk, and artifact path.
5. Update `.ai-work/state.md` after each checkpoint.

## Test Plan

- `uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py -q`
- `uv run ruff check tests/crypto_perp/test_profit_readiness_local_automation.py src/sis/crypto_perp/pre_actual_cash.py`
- `uv run ruff format --check tests/crypto_perp/test_profit_readiness_local_automation.py src/sis/crypto_perp/pre_actual_cash.py`
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `uv run sis --help | rg "pre-actual-cash|pre_actual_cash|evidence-pack" || true`
- If focused checks pass, run `./scripts/check` unless time or environment prevents it.

## Completion Conditions

- The writer dogfood test uses 10 non-cloned event/outcome pairs with varied time, outcome, and event-family regime proxy.
- The existing writer writes a schema-valid `decision.json`.
- The tracked `decision.md` records the dogfood result and preserves no-actual-cash/no-profit/no-live-readiness boundary text.
- `docs/final-summary.md` records the result and verification.
- No public pre-actual-cash CLI is added.
- No actual cash, tiny-live, live order, exchange write, wallet/signing, or ML/LLM decision path is added.

## Failure Conditions

- The dogfood still passes by copying one event shape and one outcome shape ten times.
- The test only checks counts and not uniqueness/variation.
- Generated docs imply profit proof, actual cash readiness, tiny-live readiness, or live trading readiness.
- A new public CLI command appears.
- Schema validation is skipped for `decision.json`.

## Impact Scope

Test fixture/data helper, tracked dogfood result artifacts, and durable summary only. Production writer behavior should remain unchanged unless a current-code gap is proven.

## Rollback

Revert this plan, the focused test changes, the `docs/crypto_perp/pre_actual_cash_varied_dogfood_2026_07_04/` artifact directory, and the `docs/final-summary.md` addendum. No migration rollback is required.

## Alternatives

- Keep the current duplicated ten-pair fixture and document it as dogfood. Rejected because it does not satisfy the explicit non-clone requirement.
- Add a public CLI to generate the pack. Rejected because the goal explicitly forbids a new public CLI.
- Add a `regime` field to `CryptoPerpEvent`. Rejected because this would be a schema/API change when `event_family` already provides a schema-supported regime proxy for this task.

## Critique Pass 1

Risk: using `event_family` as "regime" can be mistaken for a new domain guarantee. Correction: the test and final summary must call it a schema-supported regime proxy, not a new regime field.

Risk: varying event fields with `model_copy()` could still look like fixture cloning. Correction: the outcome must be rebuilt through `build_outcome()` with distinct price windows and settled times, and the test must assert unique outcome ids and varied returns. Event variation must include time, family, and feature values.

Risk: recording only `decision.md` would lose machine-checkable proof. Correction: track and schema-validate `decision.json` as the primary result artifact.

## Critique Pass 2

Risk: a tracked `decision.md` in `docs/crypto_perp` will fail current-doc metadata checks if generated raw. Correction: add the required hidden metadata header after generation.

Risk: a dogfood result under `.tmp/` would not satisfy "record" durably. Correction: commit-ready result artifacts belong under `docs/crypto_perp/pre_actual_cash_varied_dogfood_2026_07_04/`.

Risk: the plan could drift into production code changes. Correction: do not edit `src/sis/crypto_perp/pre_actual_cash.py` unless a failing focused test proves a real writer problem. The likely implementation is test/docs/artifact-only.

## Open Issues

None requiring user action.

## Destructive Change

No destructive operation is planned. The user allowed destructive changes if needed, but this checkpoint should be additive and reversible.

## Branch

`ai/pre-actual-cash-varied-dogfood-20260704-2237`

## Migration

No migration is required.
