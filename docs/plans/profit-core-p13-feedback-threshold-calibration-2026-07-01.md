<!--
作成日: 2026-07-01_19:55 JST
更新日: 2026-07-01_20:06 JST
-->

# Profit Core P13 Feedback Threshold Calibration Plan

## Checkpoint

P13: Feedback And Threshold Calibration

## Purpose

P12 actual-cash report gate と failure log を使い、次 protocol / next multiplicity account へ反映すべき generator、event_count_policy、unexecutable_rate、cost model、operator burden の変更案を local artifact として固定する。

この checkpoint は feedback / calibration artifact を作るだけであり、既存 protocol、multiplicity account、threshold、config、strategy、runtime workflow を自動変更しない。

## Current State

- P12 `profit_core_actual_cash_report_gate.v1` は `promote` / `wait` / `kill`、actual-cash edge、sample size、event diversity、profit concentration、largest loss、operator burden、reconcile mismatch、protocol / multiplicity refs を出す。
- `candidate_protocol_manifest.v1` には `protocol_id`、`families`、`exclusion_rules`、`family_event_count_policy`、sealed holdout、false execution boundary がある。
- `trial_multiplicity_account.v1` には `account_id`、trial counts、`validation_peek_count`、`success_only_reporting=false` がある。
- 既存 `strategy_input_feedback` は Strategy Input Contract 向けの generic feedback であり、Profit Core の protocol version / multiplicity / holdout reuse ルールを直接表現しない。

## Constraints

- Code, tests, schemas, CLI help, and current docs are authoritative.
- P13 output must not auto-apply threshold or protocol changes.
- Success-only feedback is blocked.
- Threshold or family policy changes require a new protocol id and new multiplicity account id.
- Holdout peek after changes cannot reuse the same family/version.
- Validation peek / trial accounting impact must be explicit.
- Live/tiny-live/actual-cash execution permission remains false.

## Target Files

- `schemas/profit_core_feedback_threshold_calibration.v1.schema.json`
- `src/sis/edge_candidates/feedback_calibration.py`
- `src/sis/edge_candidates/__init__.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_feedback_calibration.py`
- `docs/final-summary.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` if CLI catalog check requires updating
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Policy

Add a Profit Core-specific artifact:

- schema version: `profit_core_feedback_threshold_calibration.v1`
- CLI command: `edge-candidate-feedback-calibration-build`
- inputs:
  - `--protocol candidate_protocol_manifest.v1`
  - `--multiplicity-account trial_multiplicity_account.v1`
  - `--report-gate profit_core_actual_cash_report_gate.v1`
  - `--feedback-log` local JSON/YAML
- output: `profit_core_feedback_threshold_calibration.json`

The `feedback-log` is a local operator/research artifact with:

- `next_protocol_id`
- `next_multiplicity_account_id`
- `next_validation_peek_count`
- `holdout_peek_performed`
- `same_family_version_reuse_requested`
- `killed_candidates`
- `actual_execution_failures`
- `generator_updates`
- `family_event_count_policy_updates`
- `exclusion_rule_updates`
- `cost_model_updates`
- `operator_burden_updates`

The builder will:

1. Validate protocol, multiplicity account, P12 report gate, and feedback log.
2. Require protocol / multiplicity ids to match P12 source refs where possible.
3. Derive failure summary from killed candidates, actual execution failures, and P12 decision/blockers.
4. Block success-only feedback when no failure source is present.
5. Require new protocol id and new multiplicity account id when threshold / family / generator / cost / burden updates are proposed.
6. Require next validation peek count to advance when holdout peek or threshold/family policy changes are reported.
7. Block same family/version reuse after holdout peek.
8. Emit proposed updates without applying them.

## Test Policy

Focused tests must cover:

- complete failure-inclusive feedback produces `READY_FOR_NEXT_PROTOCOL_REVIEW`;
- schema validates output;
- success-only feedback is blocked;
- threshold/family policy change with same protocol or same multiplicity account is blocked;
- holdout peek with same family/version reuse is blocked;
- validation peek count must advance when threshold/family policy changes are proposed;
- CLI writes the artifact and prints false auto-apply/execution fields.

## Done Conditions

- `profit_core_feedback_threshold_calibration.v1` schema exists.
- P13 builder and writer exist.
- `edge-candidate-feedback-calibration-build` is registered.
- P13 output includes:
  - current protocol id;
  - current multiplicity account id;
  - P12 report gate ref and decision;
  - failure summary;
  - proposed generator / family event policy / exclusion rule / cost model / operator burden updates;
  - next protocol id;
  - next multiplicity account id;
  - validation peek accounting;
  - holdout reuse decision;
  - false auto-apply/execution boundary fields.
- Focused tests pass.
- Current-doc checker passes.

## Fail Conditions

- P13 mutates protocol or multiplicity files directly.
- P13 treats good actual-cash results only as enough feedback.
- P13 permits threshold/family policy changes without new protocol id and new multiplicity account id.
- P13 permits holdout-peek changes to return to the same family/version.
- P13 omits validation peek / trial accounting impact.
- P13 grants live, tiny-live, exchange write, or actual-cash execution permission.

## Impact Scope

Profit Core edge candidate workflow only. No external venue adapter, credential handling, order path, wallet/signing, exchange write, runtime data fetch, or live/tiny-live execution path changes.

## Rollback Policy

Remove the P13 schema, module, tests, CLI registration, and docs updates. P12 and earlier Profit Core artifacts remain untouched.

## Alternatives

- Reuse `strategy_input_feedback`: rejected because it is generic Strategy Input Contract feedback and does not enforce Profit Core protocol version, multiplicity, holdout, or success-only rules.
- Directly write the next protocol manifest: rejected because P13 should produce review input, not apply protocol changes.
- Ignore actual execution failures when P12 is positive: rejected because P13's purpose is to prevent success-only calibration.

## Migration

No migration is required. New artifacts are additive. Existing P12 outputs remain valid.

## Critical Review Pass 1

Risk: P13 becomes an automatic optimizer that silently changes thresholds.

Correction:

- Artifact stores proposed updates only.
- Boundary fields include `auto_applied=false`, `protocol_mutated=false`, `multiplicity_account_mutated=false`, and `thresholds_applied=false`.

Risk: positive P12 `promote` hides failed execution details.

Correction:

- Success-only feedback is blocked unless `killed_candidates` or `actual_execution_failures` are present.

Risk: threshold updates create unaccounted extra trials.

Correction:

- Require `next_multiplicity_account_id` and `next_validation_peek_count`.

## Critical Review Pass 2

Risk: "same family/version" is not a first-class field in current protocol.

Correction:

- Put `same_family_version_reuse_requested` in the feedback log and block it after holdout peek. Future protocol version fields can refine this without changing P13's safety rule.

Risk: actual execution failure can be absent because no actual execution occurred.

Correction:

- P13 does not require a non-empty actual-execution failure list if killed candidates or P12 kill/wait blockers are present, but it records the count and blocks entirely success-only reports.

Risk: P13 may not be able to prove every proposed update was applied to the next protocol because no next protocol file exists yet.

Correction:

- P13 verifies the required ids and accounting inputs for the next cycle, but it intentionally does not claim the next protocol has already been created.

## Grill Readiness

仕様化 readiness: ready

Assumption: P13 emits review-ready calibration input only; creating the actual next protocol manifest is a separate later action.
