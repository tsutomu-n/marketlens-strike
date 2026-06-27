<!--
作成日: 2026-06-28_07:40 JST
更新日: 2026-06-28_07:40 JST
-->

# Crypto Perp Profit-Readiness Local Automation Plan

## Checkpoint ID

CP-01 / CP-02

## Purpose

Add local-only automation for the remaining Crypto Perp profit-readiness steps after PR-I1a/I1b. The flow must generate blocker artifacts when real event, matured outcome, or actual cash evidence is missing. It must not fetch public data, use credentials, write to an exchange, submit live orders, run real tiny-live measurement, or treat previews/dogfood/status/viewer artifacts as actual cash evidence.

## Current State

Existing CLI surfaces can build source availability, replay slices, feature packs, edge scores, cost-aware rows-v2, bias guards, tournament reports, tournament gates, and tiny-live shadows. The missing work is local inventory, local command planning, a local chain runner, a cash ledger CLI, ledger-to-actual-cash rows conversion, report/gate chaining, human review packet generation, and a shadow readiness checker.

## Constraints

- Keep `crypto-perp-tournament-report` actual-cash-only input guard.
- Add new v1 schemas for new artifacts. Do not change existing v1 schemas unless existing models require it.
- Do not infer action assignment from ledger entries. Use a separate assignment artifact.
- If multiple event/outcome candidates exist, stop with `BLOCKED_MULTIPLE_EVENT_OR_OUTCOME_CANDIDATES`.
- If real event or matured outcome evidence is absent, stop with `BLOCKED_MISSING_EVENT_OR_OUTCOME`.
- Keep all live/exchange/order permission flags false.

## Target Files

- `src/sis/crypto_perp/`: new inventory, planning, actual cash rows, review packet, readiness modules.
- `src/sis/commands/crypto_perp_profit_readiness.py`: new Typer command registration.
- `schemas/`: new artifact schemas.
- `tests/crypto_perp/`: focused API/CLI/schema tests.
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`, `docs/IMPLEMENTED_SURFACES.md`, `docs/final-summary.md`: boundary and usage updates.

## Implementation Approach

1. Add Pydantic models and builders for inventory and plan artifacts.
2. Add local runner that reuses existing builders and writes all artifacts under one run directory.
3. Add cash ledger CLI around existing `build_cash_ledger()`.
4. Add assignment-based actual cash rows builder.
5. Add report/gate helper around existing tournament report and gate builders.
6. Add tiny-live review packet and shadow readiness builders.
7. Register all commands under the existing profit-readiness command module.
8. Add schemas and tests for CLI/API behavior and schema validity.
9. Update current docs with the local-only boundary.

## Test Approach

Run:

```bash
uv run pytest tests/crypto_perp -q
uv run python scripts/check_cli_catalog.py
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

If the full check is too slow or fails outside the touched surface, record exact failure output.

## Done Conditions

- New CLI commands are registered and discoverable.
- New artifacts validate against schemas.
- Missing real evidence blocks instead of producing fake success.
- Actual cash rows can only be produced from ledger plus assignment.
- Human review and readiness artifacts never permit live orders or exchange writes.
- Docs explain inventory to readiness order and the blocker behavior.

## Failure Conditions

- Preview, estimate, dogfood, status, or viewer artifacts are accepted as actual cash evidence.
- Missing ledger entries for trade actions are converted to zero.
- The implementation changes public network, credentialed read, exchange write, or live order behavior.
- Existing actual-cash guard is weakened.

## Impact Scope

Crypto Perp profit-readiness local artifacts and docs only.

## Rollback

Revert the new modules, schemas, tests, command registrations, and docs added by this branch. Existing builders and guards should remain unchanged except for imports and command registration additions.

## Alternatives

- Shell out to existing CLI commands from the runner: rejected for testability and because direct builder reuse is safer.
- Auto-select the newest event/outcome: rejected because the plan requires blocker behavior for multiple candidates.

## Unresolved Items

None requiring user action. Real event/outcome/cash collection remains out of scope.

## Destructive Change

No.

## Branch

`ai/crypto-perp-profit-readiness-local-automation-20260628-0000`
