<!--
作成日: 2026-07-01_20:42 JST
更新日: 2026-07-01_20:42 JST
-->

# Refactor Repo Hygiene Archive Cleanup Plan

## Checkpoint ID

CP1: ignored legacy archive hygiene

## Purpose

root `archive/` を Git 管理対象ではなく ignored local archive として扱い、24MB の legacy gTrade / Ostium zip を tracked artifact から外す。fresh clone、test、current docs が zip の存在を前提にしない状態へ揃える。

## Current State

- `.gitignore` は `*.zip` を ignore しているが、`!archive/gtrade_ostium_legacy_archive_*.zip` で例外的に tracked zip を許可している。
- `archive/gtrade_ostium_legacy_archive_20260527_013818.zip` は Git 管理されている。
- `tests/test_legacy_archive.py` は root archive zip の存在を必須にしている。
- Current docs / package note / implementation status が zip を tracked evidence として読める。
- `docs/archive/` と `plan/archive/` は historical docs であり、今回の root archive cleanup とは別物。

## Constraints

- worktree の zip を削除しない。`git rm --cached` で index からだけ外す。
- `docs/archive/` と `plan/archive/` は動かさない。
- historical docs 内の historical references は変更しない。
- live / external network / credential / dependency changes は行わない。
- docs を編集する場合は Tokyo timestamp を更新する。

## Target Files

- `.gitignore`
- `tests/test_legacy_archive.py`
- `README.md`
- `docs/MIGRATION_HISTORY.md`
- `docs/ARCHITECTURE_AND_PHASES.md`
- `docs/runbooks/PAPER_EXECUTION_RUNBOOK.md`
- `src/sis/reports/implementation_status.py`
- `package.json`
- `docs/final-summary.md`
- `archive/gtrade_ostium_legacy_archive_20260527_013818.zip` Git index entry

## Implementation Policy

1. Change `.gitignore` so root `archive/` stays ignored and remove the zip unignore.
2. Remove `archive/gtrade_ostium_legacy_archive_20260527_013818.zip` from Git index with `git rm --cached`.
3. Update current references to say the legacy archive may be kept locally under ignored `archive/`, but it is not required in fresh clones.
4. Update `tests/test_legacy_archive.py` to assert there is no active legacy sidecar tree and, when `.git` exists, no root archive zip is tracked.
5. Update `docs/final-summary.md` with the checkpoint result.

## Test Policy

- `uv run pytest tests/test_legacy_archive.py -q`
- `uv run python scripts/check_current_docs.py`
- `git diff --check`
- If the diff is broader than expected, run `./scripts/check`.

## Done Conditions

- root `archive/` is ignored.
- root legacy zip is not tracked.
- local zip remains on disk if it existed.
- Fresh clone does not need the zip to pass tests.
- Current docs no longer present the zip as tracked proof.
- Focused verification passes.

## Fail Conditions

- The local zip is deleted from disk.
- Current docs checker fails.
- Tests still require `archive/gtrade_ostium_legacy_archive_*.zip`.
- `docs/archive/` or `plan/archive/` are moved or rewritten.

## Impact Scope

Repository hygiene only. No runtime code path, CLI behavior, schema, dependency, execution, credential, network, or data fetch behavior changes.

## Rollback Policy

Revert `.gitignore`, docs, test, package/status string changes, and restore the zip to the Git index from history if the repo must continue tracking it.

## Alternatives

- Keep tracking the zip: rejected because the user explicitly wants archive ignored and the file adds repo weight.
- Delete the local zip: rejected because the user asked for archive, not irreversible deletion.
- Move historical docs: rejected because `docs/archive/` and `plan/archive/` are routed historical records, not the root binary archive problem.

## Unresolved Items

None for CP1. Future code-module splitting should be selected after CP1 verification.

## Destructive Change

No worktree deletion. Git index removal of a tracked binary.

## Branch

`ai/refactor-repo-hygiene-20260701-2042`

## Migration

Developers who need the old compressed legacy source can keep or place it locally under ignored `archive/`. Fresh clones are not expected to contain it.

## Critical Review Pass 1

Risk: This becomes docs-only cleanup and does not improve developer experience.

Correction: The checkpoint removes a 24MB tracked binary from Git history moving forward and stops tests from requiring it in fresh clones.

Risk: Removing tracked evidence makes migration history unverifiable.

Correction: Current docs should describe code/test/config proof and local ignored archive convention separately. Historical audit references remain in `docs/archive/`.

## Critical Review Pass 2

Risk: `.gitignore` root `archive/` rule accidentally affects `docs/archive/` or `plan/archive/`.

Correction: Use an anchored `/archive/` rule, not a broad `archive/` glob.

Risk: A local ignored zip makes test behavior depend on local files.

Correction: Test Git tracking state, not file existence. Local ignored files may exist without affecting fresh-clone correctness.

## Readiness

Implementation readiness: ready.
