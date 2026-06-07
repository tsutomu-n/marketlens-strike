<!--
作成日: 2026-05-30_21:32 JST
更新日: 2026-06-07_21:33 JST
-->

# Repository Guidelines

Last updated: 2026-06-07_21:33 Asia/Tokyo. Keep this guide concise; no fixed word limit.

## Codex Loading

Codex reads this file when a new run or TUI session starts. Restart Codex or start a fresh session after materially editing this file.

If `./.ai_memory/HANDOFF.md` exists, read it first for restart state before choosing the next action. Treat it as the restart artifact only; code, tests, schemas, config, lockfiles, CI, and CLI help remain the implementation source of truth.

## Source Of Truth

Code, tests, schemas, config, lockfiles, CI, and CLI help are authoritative. Prefer `src/`, `tests/`, `schemas/`, `pyproject.toml`, `.python-version`, `uv.lock`, `.github/workflows/ci.yml`, `scripts/check`, and `uv run sis --help` over README, docs, plans, or generated artifacts. Docs summarize current state; `plan/` and `docs/archive/` are context, not current proof. Do not copy changing pass counts, artifact snapshots, or phase-gate values into this file; record commands instead.

## Project Structure

`marketlens-strike` is a Python 3.13 CLI workspace for research, read-only evidence, Strategy Lab workflows, paper operations, and safety gates. Core code lives in `src/sis/`. `src/sis/cli.py` builds the Typer root app; command implementations live under `src/sis/commands/`. Domain code includes `venues/trade_xyz`, `backtest`, `research/strategy_lab`, `research_protocol`, `paper`, `execution`, `risk`, `tracking`, and `validation`.

Tests live in `tests/` with focused slices under `tests/backtest/` and `tests/strategy_authoring/`. Docs are in `docs/`, plans in `plan/`, schemas in `schemas/`, templates in `templates/`, and examples/config in `configs/`. `data/`, `logs/`, and `.tmp/` are runtime/generated state.

## Default Scope Bias

When the user does not specify a scope, prefer research/backtest-first and venue-neutral work. Use the NDX Layer 2.2 DAG foundation for NDX research tasks. Prefer Strategy Lab authoring or backtest-first workflows when a task does not explicitly require venue-specific work.

Trade[XYZ] remains implemented code and historical/read-only venue context, but it is no longer the default product axis, primary execution path, or primary next action. Do not introduce new Trade[XYZ] assumptions, collectors, readiness claims, or order-path work unless the user explicitly scopes the task to Trade[XYZ].

## Commands

- `uv sync --dev --locked`: install locked dependencies.
- `uv run python -V`: confirm Python 3.13.
- `uv run sis --help`: inspect the actual public CLI surface.
- `./scripts/check` or `just check`: run locked sync, Python version, Ruff lint/format check, current-docs check, Pyrefly, ty, and Pytest.
- `uv run python scripts/check_current_docs.py`: verify current-doc links, EOF, and legacy-root references.
- `uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx`: validate the local-only NDX Layer 2.2 DAG foundation.
- `uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx`: export Layer 2.2 DAG artifacts without fetching data.
- `uv run sis phase-gate-review`: review the read-only/paper gate.

CI also runs `bun install --frozen-lockfile` for lockfile integrity. Normal development is Python/uv-first; `package.json` is not the main app entrypoint.

## Coding And Workflow

Start with read-only inspection. Use `rg`, `rg --files`, CLI help, tests, schemas, and config before editing. Preserve local patterns and keep changes scoped.

Use 4-space Python indentation, explicit public type hints, and small modules aligned to domain boundaries. Keep reusable logic out of command wrappers when practical. New or heavily edited Python files should stay at 800 lines or fewer. Strategy Authoring enforces this with `tests/strategy_authoring/test_module_boundaries.py`.

Trade[XYZ] pure backtest v0.1 is a Python API surface, not a public CLI, and should be treated as an isolated venue-specific surface. `uv run sis build-backtest` is a separate legacy/bridge command. Micro-live code exists, but standard operator CLI live execution is not exposed. `READ_ONLY_GO` means read-only/paper gate only; it does not prove wallet, signing, exchange write, or production live trading readiness.

## Document Timestamps

For every documentation file created or edited by the agent, add or update a hidden metadata header near the top of the file.

For Markdown files, use exactly:

```markdown
<!--
作成日: YYYY-MM-DD_HH:mm JST
更新日: YYYY-MM-DD_HH:mm JST
-->
```

Use Tokyo time. `作成日` is the original document creation time and must not change after first creation. Update `更新日` whenever the document content is materially edited. Place the header at the top of the file, after shebang or frontmatter only if required. Do not add it to generated files, vendored files, lockfiles, binary files, or files where comments are invalid. If a format has no safe comment syntax, do not invent one; use the repository-specific rule.

## Testing And PRs

Add focused Pytest coverage near changed behavior. Prefer deterministic fixtures; avoid live market responses unless testing explicit read-only evidence flow.

PRs should state purpose, changed commands or artifacts, verification run, and any live-readiness boundary. Keep commits scoped and separate formatting from behavior changes.

Keep secrets out of git. Runtime settings come from `.env`; start from `configs/env.example` for normal repo settings and `.env.example` for the Alpaca runbook.
