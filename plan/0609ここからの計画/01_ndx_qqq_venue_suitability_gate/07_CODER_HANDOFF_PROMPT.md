<!--
作成日: 2026-06-09_15:07 JST
更新日: 2026-06-09_16:13 JST
-->

# Coder Handoff Prompt

Read this directory first. Implement or verify the NDX/QQQ venue suitability
gate exactly as specified.

Start with:

```bash
git status --short --branch --untracked-files=all
```

Do not add Bitget futures or Hyperliquid direct perp to `VenueId` or Strategy
Lab schemas. Do not call external APIs, use credentials, update
`strategy_signals.parquet`, run backtests, or create paper/live orders.

Implement the pure suitability module, selected-candidate guard,
paper-intent guard, Strategy Authoring propagation, CLI candidate-pack
propagation, raw `paper-from-intents` revalidation, legacy `paper-step`
blocking metrics, tests, and README boundary text.

Finish with:

```bash
uv run pytest -q tests/test_venue_suitability.py
uv run pytest -q tests/test_strategy_lab_candidate_pack.py tests/test_strategy_lab_paper_intent_preview.py tests/test_paper_from_intents.py
uv run pytest -q tests/test_strategy_lab_commands.py
uv run pytest -q tests/test_paper_runner.py
uv run pytest -q tests/strategy_authoring/test_cli_bundle.py
uv run pytest -q tests/test_strategy_lab_schemas.py
uv run python scripts/check_current_docs.py
./scripts/check
```
