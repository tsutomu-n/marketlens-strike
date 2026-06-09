<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_19:10 JST
-->

# Coder Handoff Prompt

Read this directory first. This is a venue design gate for future Bitget and
Hyperliquid support. It is not a live trading implementation task.

Start with:

```bash
git status --short --branch --untracked-files=all
sed -n '1,220p' .ai_memory/HANDOFF.md
```

Before editing, confirm:

```bash
sed -n '1,80p' src/sis/venues/ids.py
sed -n '1,220p' src/sis/venues/suitability.py
sed -n '1,80p' schemas/evaluation_plan.mls.v1.schema.json
```

Default implementation slice:

1. Add `src/sis/venues/capabilities.py`.
2. Add `tests/test_venue_capabilities.py`.
3. Add `docs/venues/bitget_hyperliquid_capability_gate.md`.
4. Do not widen `VenueId`.
5. Do not modify Strategy Lab schemas.
6. Do not call external APIs.
7. Do not add credentials or dependencies.
8. Do not implement live orders.

Finish with:

```bash
uv run pytest -q tests/test_venue_capabilities.py
uv run pytest -q tests/test_venue_suitability.py
uv run pytest -q tests/test_bitget_demo_adapter.py tests/test_bitget_demo_cli.py
uv run pytest -q tests/test_strategy_lab_schemas.py
uv run python scripts/check_current_docs.py
./scripts/check
```
