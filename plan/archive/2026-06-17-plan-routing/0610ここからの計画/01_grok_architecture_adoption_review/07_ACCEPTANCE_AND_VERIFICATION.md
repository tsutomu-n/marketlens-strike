<!--
作成日: 2026-06-10_11:21 JST
更新日: 2026-06-10_11:31 JST
-->

# Acceptance And Verification

## Acceptance

This review is complete only when:

- the plan package exists under `plan/0610ここからの計画/01_grok_architecture_adoption_review/`
- the source Grok transcript is explicitly named
- each Grok architecture proposal is classified as `adopt`, `adapt`, `reject`,
  or `unknown`
- the decision rejects `src/strat_tool` creation in this repo slice
- the decision rejects VectorBT primary adoption in this repo slice
- the decision preserves `src/sis` and existing Strategy Lab / NDX / backtest
  boundaries
- `09_SOURCE_EVIDENCE_LEDGER.md` records local commands, local source files,
  external source URLs, and evidence limits
- `plan/README.md` links to the package
- no code, schema, dependency, or test files are changed

## Verification

Required commands:

```bash
git diff -- src schemas pyproject.toml uv.lock tests
uv run python scripts/check_current_docs.py
uv run python - <<'PY'
from pathlib import Path
root = Path("plan/0610ここからの計画/01_grok_architecture_adoption_review")
missing = []
for path in sorted(root.glob("*.md")):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("<!--\n作成日: "):
        missing.append(f"{path}: missing metadata")
    if not text.endswith("\n"):
        missing.append(f"{path}: missing final newline")
if missing:
    raise SystemExit("\n".join(missing))
print(f"checked {len(list(root.glob('*.md')))} review docs")
PY
```

Expected:

- `git diff -- src schemas pyproject.toml uv.lock tests` prints no output
- current-doc checker passes
- direct review-package metadata/final-newline check passes

Optional:

```bash
./scripts/check
```

Expected:

- full repository gate passes

## Stop Conditions

Stop and do not continue if:

- implementing the review requires code edits
- a proposed change touches schemas or dependencies
- a new package name is introduced
- a task attempts to move active research implementation out of `src/sis`
- the plan starts claiming Strategy Lab export, paper readiness, or live
  readiness
