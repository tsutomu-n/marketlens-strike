<!--
作成日: 2026-07-01_20:47 JST
更新日: 2026-07-01_20:47 JST
-->

# Refactor Strategy Idea Authoring Bridge Models Plan

## Checkpoint ID

CP2: authoring bridge model split

## Purpose

`src/sis/strategy_idea_candidates/authoring_bridge.py` から schema/model 型を分離し、bridge runtime logic と artifact model contract の責務を分ける。public command と既存 import surface は維持する。

## Current State

- `authoring_bridge.py` は 1000 行超で、Pydantic model、result dataclass、error class、bridge runtime logic、artifact builders、normalization helpers を同居させている。
- 外部 caller は `build_strategy_idea_candidate_authoring_bridge`、`StrategyIdeaCandidateAuthoringBridgeOutputExistsError`、`StrategyIdeaCandidateAuthoringBridgeManifest` を `authoring_bridge.py` から import している。
- Focused tests exist under `tests/strategy_idea_candidates/` and P6 evidence packet consumes the bridge manifest type.

## Constraints

- Existing imports from `sis.strategy_idea_candidates.authoring_bridge` remain valid.
- Artifact schema version and serialized timestamp format remain unchanged.
- CLI registration and output paths are untouched.
- No dependency changes.

## Target Files

- `src/sis/strategy_idea_candidates/authoring_bridge.py`
- `src/sis/strategy_idea_candidates/authoring_bridge_models.py`
- `docs/final-summary.md`

## Implementation Policy

1. Add `authoring_bridge_models.py` for:
   - `AUTHORING_BRIDGE_SCHEMA_VERSION`
   - `BridgeStatus`
   - `ProfitCoreArtifactRef`
   - `StrategyIdeaCandidateAuthoringBridgeCandidate`
   - `StrategyIdeaCandidateAuthoringBridgeManifest`
   - `StrategyIdeaCandidateAuthoringBridgeResult`
   - `StrategyIdeaCandidateAuthoringBridgeOutputExistsError`
2. Import those symbols into `authoring_bridge.py`.
3. Leave `authoring_bridge.py` as the compatibility import surface.
4. Remove only now-unused model imports/helpers from `authoring_bridge.py`.

## Test Policy

- `uv run ruff check src/sis/strategy_idea_candidates/authoring_bridge.py src/sis/strategy_idea_candidates/authoring_bridge_models.py`
- `uv run pytest tests/strategy_idea_candidates/test_authoring_bridge.py tests/strategy_idea_candidates/test_bitget_public_source.py tests/edge_candidates/test_evidence_packet.py -q`
- Include CP2 in final full verification.

## Done Conditions

- `authoring_bridge.py` is below 1000 lines.
- `authoring_bridge_models.py` owns model declarations.
- Existing tests pass.
- No public command or artifact path changes.

## Fail Conditions

- Any existing import from `authoring_bridge.py` breaks.
- Artifact timestamp serialization changes.
- Evidence packet can no longer validate bridge manifests.
- Focused tests fail.

## Impact Scope

Strategy idea candidate authoring bridge internals only. No schema file, CLI behavior, external network, order path, credential, or runtime data fetch changes.

## Rollback Policy

Inline the moved model declarations back into `authoring_bridge.py` and remove `authoring_bridge_models.py`.

## Alternatives

- Split command registration first: rejected because Typer nested command functions make movement higher churn.
- Split candidate artifact writers first: rejected because model split is cleaner and lower behavior risk.
- Do nothing: rejected because the file is already the largest active source module.

## Unresolved Items

Remaining large modules such as `src/sis/commands/edge_candidates.py`, `src/sis/crypto_perp/profit_readiness.py`, and `src/sis/strategy_idea_candidates/generator.py` should be handled only with focused behavior tests and separate checkpoints.

## Destructive Change

No.

## Branch

`ai/refactor-repo-hygiene-20260701-2042`

## Migration

No migration is required. Existing imports from `authoring_bridge.py` remain valid.

## Critical Review Pass 1

Risk: Moving model classes creates a new module without improving real maintainability.

Correction: The split separates stable artifact contract types from runtime artifact generation and reduces the largest active source module below 1000 lines without changing behavior.

Risk: Type movement breaks hidden callers.

Correction: `authoring_bridge.py` imports the moved symbols, preserving the old import path.

## Critical Review Pass 2

Risk: Timestamp serializer changes artifact output.

Correction: The serializer is copied into the model module and keeps UTC `Z` output.

Risk: More aggressive splitting would be more "thorough" but riskier.

Correction: Stop at this low-risk boundary and leave further command/runtime splits as residual work.

## Readiness

Implementation readiness: ready.
