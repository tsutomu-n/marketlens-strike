<!--
作成日: 2026-07-01_06:46 JST
更新日: 2026-07-01_06:46 JST
-->

# Profit Core P4 Edge Candidate Factory V1 Implementation Plan

## Checkpoint ID

P4 Edge Candidate Factory V1

## Purpose

Implement a protocol-bound candidate factory that turns an existing
`candidate_protocol_manifest.v1` plus validated input evidence into a complete
candidate inventory and accounting bundle. This is discovery plumbing only; it
must not claim alpha, paper readiness, live readiness, exchange-write readiness,
or actual-cash permission.

## Current State

- `edge-candidate-protocol-validate` validates `candidate_protocol_manifest.v1`.
- `strategy-idea-candidates-build` can build deterministic crypto-perp candidate
  sets, search ledgers, and related reports, but it is not protocol-bound.
- `strategy-idea-candidates-multiplicity-account-build` can attach
  `trial_multiplicity_account.json` from an existing candidate set and ledger.
- The authoring bridge can carry protocol and multiplicity references, and can
  write candidate-scoped thin backtest kill-gate artifacts.

## Constraints

- Require an explicit protocol manifest; no protocol means no factory run.
- P4 supports `verification_throughput` only.
- P4 supports only `classical_rule` and `grammar_based` family declarations.
  `risk_taker_sprint`, random, GA, ranking-only, ML, LLM generation, network
  reads, dependency changes, paper/live/tiny-live execution, and actual-cash
  work are out of scope.
- Candidate families and parameter grids must come from the protocol manifest.
  The factory must not silently add families or use default grids outside the
  protocol search space.
- Best-only reporting is prohibited; all candidates and all rejected candidates
  must be persisted.

## Target Files

- `src/sis/edge_candidates/factory.py`
- `src/sis/commands/edge_candidates.py`
- `tests/edge_candidates/test_factory.py`
- `docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md`
- `docs/final-summary.md`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`
- `.ai-work/notes.md`

## Implementation Approach

Add a thin factory module under `sis.edge_candidates` that:

1. Loads and validates protocol, input contract, and input validation artifacts.
2. Rejects unsupported protocol modes and generator types before building.
3. Converts protocol `parameter_spaces` to explicit deterministic parameter
   grids. A `grid: [object, ...]` key is treated as an explicit grid; otherwise
   list-valued keys are expanded as a cartesian product.
4. Calls the existing deterministic candidate generator with only the protocol
   families and converted grids.
5. Writes the existing candidate set and search ledger artifacts.
6. Writes a P4 rejection ledger containing every rejected candidate.
7. Writes a trial multiplicity account using the P1-P3 sidecar helper.
8. Writes `edge_candidate_factory_summary.json` with protocol refs, artifact
   refs, counts, `best_only_report=false`, unexecutable KPI fields, and false
   cash/live/exchange-write boundaries.

## Implementation Steps

1. Add failing tests for protocol-bound output, risk-taker rejection, unsupported
   generator rejection, and CLI artifact creation.
2. Implement the factory data/result helpers and protocol-to-generator config
   conversion.
3. Register `edge-candidate-factory-run` in `src/sis/commands/edge_candidates.py`.
4. Update CLI catalog and final summary.
5. Run focused tests, related regressions, CLI/current-doc checks, Ruff, and
   whitespace checks.

## Test Policy

- Focused: `uv run pytest tests/edge_candidates/test_factory.py -q`
- Related:
  `uv run pytest tests/strategy_idea_candidates/test_candidate_generator.py tests/strategy_idea_candidates/test_profit_core_attachment.py tests/strategy_idea_candidates/test_candidate_cli.py tests/edge_candidates/test_protocol_manifest.py -q`
- CLI catalog: `uv run python scripts/check_cli_catalog.py`
- Current docs: `uv run python scripts/check_current_docs.py`
- Ruff:
  `uv run ruff check src/sis/edge_candidates src/sis/commands/edge_candidates.py tests/edge_candidates`
  and matching `ruff format --check`
- Whitespace: `git diff --check`

## Completion Conditions

- Factory cannot run without a protocol manifest.
- Protocol families and parameter grids fully determine the candidate search
  space.
- `risk_taker_sprint` and non-P4 generator types fail with explicit errors.
- `strategy_idea_candidate_set.json`, `search_ledger.jsonl`,
  `rejection_ledger.jsonl`, `trial_multiplicity_account.json`, and
  `edge_candidate_factory_summary.json` are written.
- Summary includes total/shortlisted/rejected counts, family count,
  unexecutable reason count/rate, `best_only_report=false`, and false
  cash/live/exchange-write boundary fields.
- Existing P1-P3 tests remain passing.

## Failure Conditions

- The factory falls back to default families or grids not declared by protocol.
- The factory produces a best-only or success-only report.
- The factory accepts `risk_taker_sprint`, GA/random/ML/LLM-first generation, or
  live/actual-cash permission.
- The factory writes paper/live/tiny-live/exchange side effects.

## Impact Scope

The change adds a new CLI surface and factory module. It should not change
existing `strategy-idea-candidates-build` behavior, existing protocol validation
semantics, candidate-set schema, multiplicity schema, or authoring bridge output
shape.

## Rollback Policy

Remove `src/sis/edge_candidates/factory.py`, the new CLI registration code, the
new tests, and the docs/catalog/final-summary updates. No migration is required
because the factory writes new sidecar artifacts only.

## Alternatives

- Reuse `strategy-idea-candidates-build` directly and add protocol options there:
  rejected for P4 because it would widen an existing CLI and make legacy default
  generation harder to distinguish from protocol-bound generation.
- Add a new candidate-set schema field for protocol refs: rejected for this
  slice because P1-P3 already use compatible sidecars and bridge refs.

## Unresolved Items

- A future P8 slice may implement isolated `risk_taker_sprint` candidate
  expansion. P4 deliberately rejects it.
- A future slice may add a formal JSON schema for
  `edge_candidate_factory_summary.json` if it becomes an inter-tool contract.

## Destructive Change

No.

## Branch

`ai/profit-core-p4-factory-20260701-0642`

## Migration

None.

## Grill Verdict

Ready with assumptions: P4 is treated as a protocol-bound wrapper around the
existing deterministic generator, not a new alpha engine or risk-taker expansion.
