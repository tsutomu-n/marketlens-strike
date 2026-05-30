# Repository Guidelines

## Project Structure & Module Organization

`marketlens-strike` is a Python 3.13 CLI workspace for Trade[XYZ] research, read-only evidence, strategy lab workflows, paper operations, and safety gates. Core code lives in `src/sis/`; Typer registration is in `src/sis/cli.py`, with commands under `src/sis/commands/`. Domain modules include `venues/trade_xyz`, `research/strategy_lab`, `paper`, `risk`, and `validation`.

Tests live in `tests/` and follow `test_*.py` naming. Docs are in `docs/`, plans in `plan/`, schemas in `schemas/`, templates in `templates/`, and examples in `configs/`. `data/`, `logs/`, and `.tmp/` are generated.

## Build, Test, and Development Commands

- `uv sync --dev --locked`: install locked dependencies.
- `uv run python -V`: confirm Python 3.13 is active.
- `uv run sis --help`: inspect the CLI surface.
- `./scripts/check` or `just check`: run sync, Ruff lint/format check, docs-current check, Pyrefly, and Pytest.
- `uv run pytest -q tests/test_strategy_authoring.py`: run one test file.
- `uv run sis phase-gate-review`: review the read-only gate.

## Coding Style & Naming Conventions

Use 4-space Python indentation, explicit public type hints, and small modules aligned to domain boundaries. Keep CLI code in `src/sis/commands/`; keep reusable logic outside command wrappers. Keep each Python file at 800 lines or fewer; split by responsibility before exceeding that limit. Ruff targets Python 3.13 with `line-length = 100`.

## Tooling & Agent Workflow

Start with read-only inspection. Use CLI commands actively for search, inventory, verification, and reads before editing; `rg`, `rg --files`, and `ls` are examples, not the only options. Use applicable Codex skills when they match the task, for workflow, review, planning, UI, or docs work.

## Testing Guidelines

The test stack is Pytest plus `pytest-httpx` for HTTP behavior. Add focused tests like `tests/test_trade_xyz_collector.py` or `tests/test_strategy_lab_commands.py`. Prefer deterministic fixtures; avoid live market responses unless testing an explicit read-only evidence flow.

## Commit & Pull Request Guidelines

Recent commits use imperative subjects such as `Add ...` or `Update ...`, often including changed capabilities and verification counts. Keep commits scoped to one logical change; separate formatting from behavior changes.

Pull requests should include purpose, changed commands or artifacts, verification run, and any live-readiness boundary. Link docs when changing strategy lab, Trade[XYZ], paper, or gate behavior. Do not claim live trading readiness from `READ_ONLY_GO`; wallet secrets, signing, and production live trading remain out of scope.

## Security & Configuration Tips

Start from `configs/env.example` and keep secrets out of git. Treat `bot-preview` and phase-gate outputs as read-only/paper artifacts unless code and docs explicitly say otherwise.
