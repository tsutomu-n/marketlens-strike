<!--
作成日: 2026-07-03_13:50 JST
更新日: 2026-07-03_13:50 JST
-->

# Profit Core Stdout Next Action

## Checkpoint

RC10: Surface `next_action` in `profit-core-reality-check` stdout.

## Purpose

`profit-core-reality-check` already writes `summary.next_action` to JSON and Markdown. The terminal output only prints `status` and `next_single_blocker_to_fix`, so an operator can see the blocker but miss whether the next step is input collection or an implementation fix.

Expose the existing `summary.next_action` value in stdout without changing schema, options, artifact shape, or readiness semantics.

## Current State

- Current dogfood is blocked with `next_single_blocker_to_fix=BLOCKED_MISSING_EVENT_OR_OUTCOME`.
- Current JSON has `summary.next_action=COLLECT_INPUTS`.
- Current Markdown has an `Input Collection` section.
- Current stdout does not print `next_action=COLLECT_INPUTS`.

## Constraints

- Do not run network, credentials, exchange write, demo/testnet, actual cash rows build, or actual-cash gate.
- Do not infer real event, matured outcome, or actual cash evidence from C9 bridge, dogfood/status/viewer, preview, estimate, virtual, or backtest artifacts.
- Do not change public CLI options, schema, or runtime artifact contract.
- Keep `permits_live_order=false`.

## Target Files

- `src/sis/commands/profit_core_reality_check.py`
- `tests/profit_core_reality_check/test_profit_core_reality_check.py`
- `docs/final-summary.md`
- `.ai-work/state.md`

## Implementation Plan

1. Add a focused CLI assertion that stdout includes `next_action=RUN_EXISTING_PIPELINE` for the candidate+ledger-only case.
2. Add `typer.echo(f"next_action={check.summary.next_action}")` beside the existing status/blocker stdout.
3. Re-run the current dogfood `profit-core-reality-check` command and confirm stdout includes `next_action=COLLECT_INPUTS`.
4. Update final summary and local work state.

## Test Plan

```bash
uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q
uv run sis profit-core-reality-check ...dogfood inputs...
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Completion Conditions

- CLI stdout includes `next_action=<value>`.
- JSON and Markdown remain unchanged except regeneration timestamp/output path when dogfood is rerun.
- Current dogfood still blocks at `BLOCKED_MISSING_EVENT_OR_OUTCOME` with `next_action=COLLECT_INPUTS`.
- Permission boundary remains false.
- Focused and full checks pass.

## Failure Conditions

- Stdout wording implies live readiness, execution permission, or actual cash proof.
- The command starts running upstream pipeline steps instead of reading explicit artifacts.
- Any schema, CLI option, or public artifact shape changes.

## Impact

Low. This is an observability-only CLI stdout addition.

## Rollback

Remove the stdout line and focused test assertion.

## Alternatives

- Do nothing: safe but leaves terminal output less actionable.
- Add more verbose operator guidance to stdout: rejected for now because Markdown already carries detailed instructions.

## Critique Pass 1

This does not move the profit system past the missing real event/outcome blocker. That is intentional. The value is preventing a terminal-only operator from treating `BLOCKED_MISSING_EVENT_OR_OUTCOME` as a code fix instead of an input collection stop.

## Critique Pass 2

The change should not add a new domain concept. It must only surface the existing model field. If more guidance is needed, it belongs in Markdown, not stdout.

## Destructive Change

No.

## Branch

`ai/profit-core-reality-check-impl-20260703-1157`
