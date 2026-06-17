<!--
作成日: 2026-06-10_11:21 JST
更新日: 2026-06-10_11:31 JST
-->

# Implementation Tasks

## Task 1: Add Plan Package

Goal: add this docs-only review package.

Target directory:

- `plan/0610ここからの計画/01_grok_architecture_adoption_review/`

Files:

- `README.md`
- `01_SOURCE_AND_SCOPE.md`
- `02_REPO_TRUTH_FINDINGS.md`
- `03_ADOPTION_MATRIX.md`
- `04_RISK_AND_NARRATIVE_AUDIT.md`
- `05_DECISION.md`
- `06_IMPLEMENTATION_TASKS.md`
- `07_ACCEPTANCE_AND_VERIFICATION.md`
- `08_CODER_HANDOFF_PROMPT.md`
- `09_SOURCE_EVIDENCE_LEDGER.md`

Acceptance:

- all files have metadata headers
- the source Grok transcript is named
- the package states that code/schema/dependency changes are out of scope
- the package records local and external evidence used for the adoption decision

## Task 2: Add Plan Index Link

Goal: make the package discoverable.

Target file:

- `plan/README.md`

Implementation details:

- update the metadata `更新日`
- add a new current 2026-06-10 section
- link to the package path
- state that this is a docs-only adoption review, not an implementation change

Acceptance:

- link resolves
- no legacy root path warning is introduced

## Task 3: Verify Docs-Only Boundary

Commands:

```bash
git diff -- src schemas pyproject.toml uv.lock tests
uv run python scripts/check_current_docs.py
```

Acceptance:

- the first command has no output
- current-doc checker passes

Optional full gate:

```bash
./scripts/check
```

Run the full gate if a final repo-wide confidence check is desired.
