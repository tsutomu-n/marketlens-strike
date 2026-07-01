<!--
作成日: 2026-07-01_19:35 JST
更新日: 2026-07-01_19:55 JST
-->

# Profit Core P12 Actual Cash Report Gate Plan

## Checkpoint

P12: Actual Cash Report Gate

## Purpose

P11 の `profit_core_tiny_actual_cash_measurement.v1` を Profit Core candidate lineage に接続し、actual-cash sample を `NO_TRADE` と比較したうえで `promote` / `wait` / `kill` を local artifact として出す。

この checkpoint は report gate artifact を作るだけであり、actual cash order execution、credential use、external network、exchange write、wallet、signing、live/tiny-live permission は行わない。

## Current State

- P11 は `profit_core_tiny_actual_cash_measurement.v1` と `edge-candidate-tiny-actual-cash-measurement-record` を実装済み。
- P11 measurement は P9 readiness packet、P10 external venue adapter、human approval、order intent、submitted order、fills、fees/funding、cash ledger、actual-cash rows、flat reconciliation、stop condition を candidate lineage に接続する。
- 既存 Crypto Perp `crypto-perp-actual-cash-report-gate` は actual-cash tournament rows を report/gate 化するが、3 action 同一 event set を前提にする。
- P11 measurement は `measured non-NO_TRADE action + NO_TRADE` の同一 event set を許すため、P12 は existing Crypto Perp gate の単純 wrapper では足りない。
- P9 readiness packet は evidence packet ref を持ち、evidence packet は protocol、candidate set、bridge manifest、multiplicity account、backtest kill gate、virtual gate の refs を持つ。

## Constraints

- Code, tests, schemas, CLI help, and current docs are authoritative.
- `actual_cash` と `simulation` / `virtual_exchange` / `estimate` を同じ proof として扱わない。
- `actual_cash_edge_over_NO_TRADE` が存在し、正でなければ `promote` にしない。
- `wait` と `kill` を first-class decision として扱う。
- `READY_FOR_HUMAN_RISK_REVIEW`、P12 `promote`、または positive fill を live readiness と読ませない。
- P12 command must keep:
  - `network_attempted=false`
  - `credentials_used=false`
  - `exchange_write_used=false`
  - `live_order_submitted=false`
  - `order_submitted_by_this_command=false`
  - `permits_live_order=false`
  - `permits_actual_cash_execution=false`

## Target Files

- `schemas/profit_core_actual_cash_report_gate.v1.schema.json`
- `src/sis/edge_candidates/actual_cash_report_gate_models.py`
- `src/sis/edge_candidates/actual_cash_report_gate.py`
- `src/sis/edge_candidates/__init__.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_actual_cash_report_gate.py`
- `docs/final-summary.md`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md` if CLI catalog check requires updating
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Policy

Add a Profit Core specific gate:

- schema version: `profit_core_actual_cash_report_gate.v1`
- CLI command: `edge-candidate-actual-cash-report-gate`
- primary input: `--measurement profit_core_tiny_actual_cash_measurement.v1`
- output: `profit_core_actual_cash_report_gate.json`

The builder will:

1. Validate P11 measurement.
2. Verify the referenced actual-cash rows file hash.
3. Verify the referenced readiness packet hash.
4. Verify the readiness packet candidate and measurement ids match P11.
5. Verify the readiness packet evidence packet hash and candidate id.
6. Pull protocol / multiplicity / backtest kill gate / virtual gate refs from evidence packet source refs.
7. Compute measured action total, `NO_TRADE` total, and `actual_cash_edge_over_NO_TRADE`.
8. Report sample size, event diversity, profit concentration, largest loss, operator burden, and reconcile mismatch.
9. Emit evidence-basis separation for `actual_cash`, `virtual_exchange`, `simulation/backtest`, and `estimate`.
10. Decide:
    - `promote` only when actual-cash edge is positive, actual-cash basis is valid, sample size meets policy, concentration/loss/operator burden are within policy, reconciliation matches, and required lineage refs exist.
    - `wait` when evidence is valid but too small, too concentrated, missing required lineage refs, or otherwise inconclusive.
    - `kill` when actual-cash edge is zero/negative or largest loss breaches the policy.

## Implementation Steps

1. Add failing tests in `tests/edge_candidates/test_actual_cash_report_gate.py`.
2. Add schema constant in `src/sis/edge_candidates/__init__.py`.
3. Add `actual_cash_report_gate_models.py` with Pydantic model, policy model, source-ref model, and blocker model.
4. Add `actual_cash_report_gate.py` with builder, writer, metrics, decision, and path/hash helpers.
5. Register CLI command in `src/sis/commands/edge_candidates.py`.
6. Add JSON schema.
7. Update docs only where current-doc/CLI checks require it.
8. Run focused tests and format/lint checks.
9. Update `.ai-work` and final summary.

## Test Policy

Focused tests must cover:

- complete positive actual-cash edge produces `decision=promote` while all execution permission fields remain false;
- schema validates output;
- missing or non-positive `actual_cash_edge_over_NO_TRADE` prevents promotion;
- negative edge produces `decision=kill`;
- insufficient sample size produces `decision=wait`;
- high profit concentration produces `decision=wait`;
- largest loss beyond threshold produces `decision=kill`;
- operator burden beyond threshold produces `decision=wait`;
- P11 blocked/non-actual measurement produces `decision=wait` and `promotion_allowed=false`;
- candidate/readiness/evidence lineage mismatch is blocked/wait;
- actual-cash rows ref hash mismatch fails safely;
- CLI writes the gate and prints false network/exchange/live fields.

## Done Conditions

- `profit_core_actual_cash_report_gate.v1` schema exists.
- P12 builder and writer exist.
- `edge-candidate-actual-cash-report-gate` is registered.
- P12 output includes:
  - candidate id and measurement id;
  - source refs for measurement, readiness packet, evidence packet, rows, protocol, multiplicity, backtest kill gate, and virtual gate when available;
  - `actual_cash_edge_over_NO_TRADE`;
  - sample size;
  - event diversity;
  - profit concentration;
  - largest loss;
  - operator burden;
  - reconcile mismatch;
  - separated evidence-basis summary;
  - `decision` as `promote` / `wait` / `kill`;
  - false execution/network/live boundary fields.
- Focused tests pass.
- Current-doc checker passes.

## Fail Conditions

- P12 treats virtual/backtest/estimate evidence as actual-cash profit proof.
- P12 promotes without a positive actual-cash edge over `NO_TRADE`.
- P12 omits sample size, event diversity, concentration, largest loss, operator burden, or reconciliation mismatch.
- P12 uses existing Crypto Perp tournament gate without handling P11's one-measured-action shape.
- P12 implies live readiness, tiny-live permission, exchange write permission, or automatic trading.
- P12 silently ignores mismatched candidate id, measurement id, hash, or evidence lineage.

## Impact Scope

Profit Core edge candidate workflow only. No external venue adapter, credential handling, order path, wallet/signing, exchange write, runtime data fetch, or live/tiny-live execution path changes.

## Rollback Policy

Remove the P12 schema, module, tests, CLI registration, and docs updates. P11 and earlier Profit Core artifacts remain untouched.

## Alternatives

- Reuse `crypto-perp-actual-cash-report-gate`: rejected because it requires all three tournament actions for the same event set, while P11 records one measured trade action plus `NO_TRADE`.
- Extend P11 measurement instead of adding P12: rejected because P11 records actual-cash evidence lineage and P12 makes report/gate decisions.
- Add a broad statistical promotion engine: rejected for this checkpoint. P12 is a thin conservative gate, not a full statistical proof engine.

## Migration

No migration is required. New artifacts are additive. Existing P11 outputs remain valid.

## Critical Review Pass 1

Risk: a small positive fill could be presented as broad profit proof.

Correction:

- The output decision is named `promote`, but schema must also include `promotion_allowed`, `permits_live_order=false`, and `permits_actual_cash_execution=false`.
- `promote` means candidate can move to a conservative next review artifact, not live execution.

Risk: P12 could accidentally depend on non-actual evidence through P9/P6 refs.

Correction:

- Evidence packet refs are lineage context only.
- Official P12 edge uses only P11 actual-cash rows and P11 measurement state.

Risk: missing rows or stale rows could be hidden by measurement totals.

Correction:

- Re-read the rows from `actual_cash_rows_ref.path`.
- Verify `actual_cash_rows_ref.sha256` before computing metrics.

Risk: existing `crypto-perp_actual_cash_report_gate_run.v1` could be mistaken as sufficient.

Correction:

- P12 schema is Profit Core specific and requires candidate lineage refs.

## Critical Review Pass 2

Risk: `wait` can become a dumping ground for both valid inconclusive evidence and broken lineage.

Correction:

- Include blocker codes and sources.
- Use `report_status=blocked` when lineage/hash/basis is broken and `report_status=complete` only when metrics were computed from valid actual-cash rows.

Risk: event diversity is too thin if it is only event count.

Correction:

- Include `event_set`, `event_count`, measured action set, and policy threshold. More domain-specific diversity can be added later when event metadata exists.

Risk: profit concentration can hide a one-event jackpot.

Correction:

- Compute positive measured-action concentration and make high concentration a `wait` condition even when edge is positive.

Risk: no-trade comparison can be present but not the same event set.

Correction:

- Recompute measured action event set and `NO_TRADE` event set from rows; mismatch blocks metrics.

Risk: output could omit operator burden or reconciliation status because P11 already checked them.

Correction:

- P12 repeats them in summary fields: `operator_burden_minutes`, `flat_reconciled`, `reconcile_mismatch`.

## Grill Readiness

仕様化 readiness: ready

Assumption: P12 implements a Profit Core specific actual-cash-vs-`NO_TRADE` gate rather than reusing the Crypto Perp tournament gate as-is.
