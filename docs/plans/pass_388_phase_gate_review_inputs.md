<!--
作成日: 2026-06-26_19:05 JST
更新日: 2026-06-26_19:05 JST
-->

# Pass 388: Phase Gate Review Execution Inputs

## Purpose

Reduce `src/sis/reports/phase_gate_review.py` by extracting execution summary loading and flat-field assembly into a focused helper module.

## Restart Basis

- Branch: `refactor/backtest-primitives`
- HEAD: `30e43d1`
- Preserve: Pass 377, Pass 378, Pass 379, Pass 380, Pass 381, Pass 382, Pass 383, Pass 384, Pass 385, Pass 386, and Pass 387 uncommitted changes.
- Latest broad verification before this pass: Pass 387 `./scripts/check` passed with `2694 passed in 79.39s`.

## Target Files

- `src/sis/reports/phase_gate_review.py`
- `src/sis/reports/phase_gate_review_inputs.py`
- `tests/test_phase_gate_review_inputs.py`

## Scope

- Add a helper module that reads the execution snapshot, comparison, diagnostics, gap history, state comparison, snapshot drift, and drift overview summary payloads.
- Return the loaded payloads plus the flat fields currently expanded into the phase gate review summary.
- Keep `build_phase_gate_review()` output keys, Markdown text/order, CLI behavior, artifact paths, and remediation logic unchanged.

## Out Of Scope

- Public CLI names/options.
- Summary key names or artifact key names.
- Markdown/report wording or ordering.
- Schema, auth, DB, CI, dependencies, paper/live safety boundaries.
- Trade[XYZ] decision logic changes.
- Remediation order/recommendation logic changes.

## Red-Green-Refactor

1. RED: Add direct tests for the new execution input helper module.
2. GREEN: Move only execution summary loading and flat-field assembly from `phase_gate_review.py`.
3. REFACTOR: Run focused tests, related phase gate review tests, lint/type/CLI checks, `git diff --check`, and `./scripts/check`.

## Verification Plan

- `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_inputs.py`
- `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_inputs.py tests/test_phase_gate_review.py tests/test_phase_gate_review_paths.py tests/test_phase_gate_review_decisions.py`
- `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'phase_gate_review'`
- `uv run ruff format src/sis/reports/phase_gate_review.py src/sis/reports/phase_gate_review_inputs.py tests/test_phase_gate_review_inputs.py`
- `uv run ruff check src/sis/reports/phase_gate_review.py src/sis/reports/phase_gate_review_inputs.py tests/test_phase_gate_review_inputs.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help | wc -l`
- `git diff --check`
- `./scripts/check`

## Practical Review

- Best next target: `phase_gate_review.py` is currently 490 lines and mixes input collection with gate decisions and summary rendering.
- Safer boundary: execution input loading is deterministic and already indirectly covered by phase gate review tests.
- Main risk: losing or renaming flat execution keys. Mitigation: direct helper tests assert payload and flat-field outputs; existing phase gate tests assert persisted summary keys.
- Stop condition: if the helper requires changing summary shape or report text, stop and pick a smaller boundary.

## Branch Decision

Continue on `refactor/backtest-primitives`. This is the existing dedicated refactor branch, and this pass is a small behavior-preserving split.
