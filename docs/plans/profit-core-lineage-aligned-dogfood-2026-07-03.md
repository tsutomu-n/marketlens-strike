<!--
作成日: 2026-07-03_18:11 JST
更新日: 2026-07-03_18:11 JST
-->

# Profit Core Lineage-Aligned Dogfood

## Checkpoint

RC11: Ensure the final dogfood uses a candidate set, export manifest, and authoring bridge from the same run.

## Purpose

The latest dogfood proved `next_action=COLLECT_INPUTS`, but the first command used an older export manifest path. The reality check correctly surfaced lineage blockers:

- `SHORTLISTED_IDS_MISSING_FROM_EXPORT_MANIFEST`
- `EXPORTED_IDS_MISSING_FROM_BRIDGE`

Those blockers were not the real profit-readiness stop. They were caused by mixing artifacts from different dogfood runs. The practical fix is to rerun the dogfood with the matching export manifest and add a focused test for the important `COLLECT_INPUTS` CLI path.

## Current State

- Matching candidate set: `data/profit_core_reality_check/dogfood/c9-volatility-bridge/candidates/strategy_idea_candidate_set.json`
- Matching search ledger: `data/profit_core_reality_check/dogfood/c9-volatility-bridge/candidates/search_ledger.jsonl`
- Matching export manifest: `data/profit_core_reality_check/dogfood/c9-volatility-bridge/candidates/exported_strategy_ideas/strategy_idea_candidate_export_manifest.json`
- Matching authoring bridge: `data/profit_core_reality_check/dogfood/c9-volatility-bridge/authoring_bridge/strategy_idea_candidate_authoring_bridge_manifest.json`
- Profit-readiness inventory still reports missing real event/outcome inputs.

## Constraints

- Do not convert dogfood artifacts into profit evidence.
- Do not run actual cash rows build, actual-cash gate, demo/testnet, external LLM API, credentials, or exchange write.
- Do not change schema, CLI options, or readiness semantics.
- Keep `permits_live_order=false`.

## Target Files

- `tests/profit_core_reality_check/test_profit_core_reality_check.py`
- `docs/plans/2026-07-03-profit-core-reality-check/04_DOGFOOD_RUNBOOK.md`
- `docs/final-summary.md`
- `.ai-work/state.md`

## Implementation Plan

1. Add a CLI test that passes aligned candidate/export/bridge/profit-readiness artifacts and asserts stdout includes `next_action=COLLECT_INPUTS`.
2. Assert the aligned fixture does not report `SHORTLISTED_IDS_MISSING_FROM_EXPORT_MANIFEST` or `EXPORTED_IDS_MISSING_FROM_BRIDGE`.
3. Add a runbook warning that candidate set, export manifest, and authoring bridge must come from the same run.
4. Record the corrected dogfood path and final blocker in final summary and local state.

## Test Plan

```bash
uv run pytest tests/profit_core_reality_check/test_profit_core_reality_check.py -q
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## Completion Conditions

- Focused test covers the `COLLECT_INPUTS` CLI stdout path.
- Corrected dogfood has no export/bridge lineage blockers.
- Corrected dogfood still blocks at `BLOCKED_MISSING_EVENT_OR_OUTCOME`.
- Docs warn against mixing artifact runs.

## Failure Conditions

- The fix hides lineage blockers instead of keeping them visible when inputs are mismatched.
- The fix implies that aligned dogfood proves profit.
- The fix runs network, credentials, exchange write, actual-cash gate, or live order paths.

## Critique Pass 1

This is not a reason to push toward risk review or actual-cash gate. The corrected dogfood only removes a false artifact-mixing blocker. It leaves the real input blocker intact.

## Critique Pass 2

The test should not hard-code the current runtime `data/` artifacts because those are ignored and local. It should use small fixture payloads and validate the behavior contract directly.

## Rollback

Remove the focused test assertion and docs additions.

## Destructive Change

No.

## Branch

`ai/profit-core-reality-check-impl-20260703-1157`
