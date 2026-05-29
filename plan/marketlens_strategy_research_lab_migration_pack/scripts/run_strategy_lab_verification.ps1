$ErrorActionPreference = "Stop"
uv run ruff check .
uv run pyrefly check
uv run pytest -q
./scripts/check
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
uv run sis bot-preview
