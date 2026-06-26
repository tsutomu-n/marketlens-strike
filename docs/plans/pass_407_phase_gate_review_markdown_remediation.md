<!--
作成日: 2026-06-26_21:59 JST
更新日: 2026-06-26_21:59 JST
-->

# Pass 407 Phase Gate Review Markdown Remediation Sections

## Purpose

Extract Phase Gate Review Markdown remediation section rendering from `src/sis/reports/phase_gate_review_markdown.py`.

## Scope

- Add `src/sis/reports/phase_gate_review_markdown_remediation.py`.
- Add direct tests in `tests/test_phase_gate_review_markdown_remediation.py`.
- Update `src/sis/reports/phase_gate_review_markdown.py` to delegate remediation order, success criteria, command flow, verification signals, signal snapshots, signal diffs, and recommendations sections.

## Out Of Scope

- Public CLI command names or options.
- Markdown heading names, line order, wording, or summary key names.
- Phase Gate decision logic.
- Diagnostics tables, venue decision tables, execution snapshot sections, next actions, stop conditions, schemas, dependencies, CI, auth, DB, or external-service behavior.
- Paper, live, account, wallet, signing, exchange-write, production trading, or profit readiness claims.

## RED

Run:

```bash
CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_markdown_remediation.py
```

Expected before implementation: import failure for `sis.reports.phase_gate_review_markdown_remediation`.

## GREEN

Move only the remediation Markdown section lines:

- `## Remediation Order`
- `## Remediation Success Criteria`
- `## Remediation Command Flow`
- `## Remediation Verification Signals`
- `## Remediation Signal Snapshots`
- `## Remediation Signal Diffs`
- `## Remediation Recommendations`

## Verification

- `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_markdown_remediation.py`
- `CI=true timeout 120 uv run pytest -q tests/test_phase_gate_review_markdown_remediation.py tests/test_phase_gate_review_markdown.py tests/test_phase_gate_review.py`
- `CI=true timeout 120 uv run pytest -q tests/test_cli_smoke.py -k 'phase_gate_review'`
- `uv run ruff format src/sis/reports/phase_gate_review_markdown.py src/sis/reports/phase_gate_review_markdown_remediation.py tests/test_phase_gate_review_markdown_remediation.py`
- `uv run ruff check src/sis/reports/phase_gate_review_markdown.py src/sis/reports/phase_gate_review_markdown_remediation.py tests/test_phase_gate_review_markdown_remediation.py`
- `uv run ty check src --python-version 3.13 --output-format concise`
- `uv run sis --help | wc -l`
- `git diff --check`
- `./scripts/check`

## Practical Review

- This is a renderer-only extraction with no decision logic or artifact loading.
- The main risk is changing Markdown text/order. Direct tests lock representative populated and empty remediation sections.
- Existing Phase Gate Markdown, Phase Gate builder, and CLI smoke tests remain in the verification path.
