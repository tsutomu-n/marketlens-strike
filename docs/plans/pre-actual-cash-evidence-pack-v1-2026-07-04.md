<!--
作成日: 2026-07-04_17:09 JST
更新日: 2026-07-04_18:00 JST
-->

# Pre Actual Cash Evidence Pack v1 Implementation Plan

## Checkpoint ID

CP1

## Purpose

Implement a local `pre_actual_cash_evidence_pack_v1` path that aggregates multiple Crypto Perp event/outcome artifacts and classifies the candidate into one of:

```text
KILL
REVISE_EVENT_DEFINITION
COLLECT_MORE_SOURCES
HOLD_FOR_FUTURE_ACTUAL_CASH
```

This is not a profit proof, actual-cash readiness proof, tiny-live proof, or live-trading proof.

## Current State

- Existing flat CLI commands include `crypto-perp-profit-readiness-run-local`, `crypto-perp-source-availability`, `crypto-perp-replay-slice`, `crypto-perp-feature-pack`, `crypto-perp-edge-score`, `crypto-perp-tournament-rows-v2`, and `crypto-perp-bias-guard`.
- `crypto-perp-profit-readiness-run-local` currently runs one event/outcome pair.
- Existing lower-level builders can already create source availability, replay, feature pack, edge score, tournament rows v2, and bias guard artifacts.
- Current real runtime data may still be only 1 event / 1 outcome / public candles, with `selected_action=UNKNOWN`, `leader_action=NO_TRADE`, and `pbo_status=NOT_ESTIMABLE`.

## Constraints

- Do not implement actual cash source, actual cash ledger, actual cash rows, actual-cash report gate, live measurement, tiny-live execution, wallet/signing, exchange write, credentials, or live orders.
- Do not read public candle outcomes, before-cost proxy, cost-adjusted estimate, `actual_cash_result_usd=null`, `selected_action=UNKNOWN`, `leader_action=NO_TRADE`, or sample-insufficient bias guard as profit evidence.
- Do not add a new public CLI for this gate. Use the internal builder and schema/tests.
- Use `uv` for Python commands.

## Target Files

- `src/sis/crypto_perp/pre_actual_cash.py`
- `src/sis/crypto_perp/profit_readiness.py`
- `src/sis/commands/crypto_perp_profit_readiness.py`
- `schemas/crypto_perp_pre_actual_cash_decision.v1.schema.json`
- `tests/crypto_perp/test_profit_readiness_local_automation.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/IMPLEMENTED_SURFACES.md`
- `docs/crypto_perp/PRE_ACTUAL_CASH_DECISION_GATE.md`
- `docs/crypto_perp/PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md`
- `docs/final-summary.md`

## Implementation Approach

Add a focused pack builder in `sis.crypto_perp.pre_actual_cash` that:

1. Scans a data directory with `build_profit_readiness_inventory`, including known local profit-readiness inventory / plan / replay / feature / edge / bias / run artifacts.
2. Loads valid `crypto_perp_event.v1` artifacts and matured `crypto_perp_outcome.v1` artifacts.
3. Matches at most one matured outcome per event for v1.
4. Builds or summarizes source availability per selected event.
5. Builds replay summaries, feature packs, and edge scores per selected event.
6. Builds one aggregate `crypto_perp_tournament_rows.v2` artifact over selected outcomes.
7. Builds one aggregate bias guard over the aggregate tournament rows.
8. Reads existing `crypto_perp_profit_readiness_run.v1` manifests when present and reflects their `status` / `known_gap_count`.
9. Keeps known local profit-readiness chain artifacts out of `UNKNOWN_SCHEMA_VERSION` inventory gaps.
10. Writes the required summary files and a `decision.json` / `decision.md`.

Do not add a public CLI. The builder returns summary payloads and `decision.md` text for tests and future operator surfaces.

## Implementation Steps

1. Add decision constants, Pydantic model, summary helpers, and pack build/write functions.
2. Add Markdown renderer for `decision.md`.
3. Keep the surface as an internal builder; do not register a Typer command.
4. Add schema validation for `decision.json`.
5. Add focused tests with 10 synthetic event/outcome pairs.
6. Update CLI catalog and current docs that mention the surface.
7. Run focused and repository documentation checks.

## Test Plan

- Focused pytest:

```bash
uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py -q
```

- CLI/catalog/docs checks:

```bash
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
git diff --check
```

Run broader checks if the focused changes touch shared behavior unexpectedly.

## Completion Conditions

- The pack can run over at least 10 events / 10 outcomes.
- All required summary payload keys are returned.
- `decision.json` contains:
  - `decision`
  - `reason_codes`
  - `event_count`
  - `outcome_count`
  - `source_gap_summary`
  - `edge_summary`
  - `tournament_summary`
  - `bias_guard_summary`
  - `non_goal_flags`
- `created_at`
- `decision.md` contains the human-readable decision, reasons, main gaps, NO_TRADE comparison, selected action state, bias guard state, and explicit non-goals.
- Existing run manifests are reflected as `run_manifest.status` and `run_manifest.known_gap_count`; missing manifests are reported as missing, not silently treated as pass.
- Existing local profit-readiness chain artifacts are classified by inventory as known categories, not as unknown schemas.
- `uv run sis --help` and the CLI catalog do not expose `crypto-perp-pre-actual-cash-evidence-pack`.
- The decision is always one of the four allowed decisions.
- No actual cash or live execution path is added.

## Failure Conditions

- Pack output implies profit proof, actual cash readiness, tiny-live readiness, or live readiness.
- Public candle-only data is treated as actual cash evidence.
- `actual_cash_result_usd=null` is treated as zero PnL.
- Bias guard sample insufficiency is treated as robustness pass.
- Schema/doc updates drift from builder behavior or current docs checks.

## Impact

This adds a local read-only evidence aggregation surface. It does not change exchange behavior, credentials, data fetching, account access, live trading, or existing actual cash commands.

## Rollback

Revert the new builder/model, CLI wrapper, schema, tests, and docs changes on this branch. No migration or data cleanup is required because runtime pack output is under ignored `data/`.

## Alternatives

- Extend `crypto-perp-profit-readiness-run-local` for multiple inputs: rejected because it currently means one event/outcome run and changing that semantic would be harder to reason about.
- Library-only pack builder with no CLI: selected because the request explicitly forbids a new CLI.
- Actual cash rows/gate: rejected by scope.

## Unresolved Items

None blocking. The current repository data may not contain 10 real event/outcome pairs; v1 functionality will be proven by deterministic tests and can still output a blocked decision on smaller runtime samples.

## Destructive Change

No destructive change. No dependency change. No external side effect. An internal builder and JSON schema are added; no public CLI is added.

## Branch

`ai/pre-actual-cash-evidence-pack-20260704-1709`

## Migration

No migration is required. Existing commands continue to work. The pack surface is internal builder output.

## Critique Pass 1

Risk: adding a new CLI would conflict with the explicit constraint for this gate.

Correction: keep this as an internal builder/schema implementation. Do not register a Typer command for `crypto-perp-pre-actual-cash-evidence-pack`.

## Critique Pass 2

Risk: using current 1-event runtime evidence as proof would create a false success story.

Correction: tests must construct 10 event/outcome pairs and validate all required payloads. Current runtime data remains allowed to produce `COLLECT_MORE_SOURCES` because sample/source evidence is insufficient.
