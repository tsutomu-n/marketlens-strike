<!--
作成日: 2026-06-09_19:10 JST
更新日: 2026-06-09_19:10 JST
-->

# Test Plan

## Focused Tests

```bash
uv run pytest -q tests/test_venue_capabilities.py
uv run pytest -q tests/test_venue_suitability.py
uv run pytest -q tests/test_bitget_demo_adapter.py tests/test_bitget_demo_cli.py
uv run pytest -q tests/test_strategy_lab_schemas.py
uv run pytest -q tests/test_paper_from_intents.py
```

## Docs Check

```bash
uv run python scripts/check_current_docs.py
```

## Aggregate Gate

```bash
./scripts/check
```

## Required Test Scenarios

- `bitget_futures` is known to capabilities but not accepted by current schemas.
- `hyperliquid_perp` is known to capabilities but not accepted by current schemas.
- `bitget_demo` remains non-writing.
- Missing Bitget demo env remains blocked.
- Present Bitget demo env means local config only, not network readiness.
- NDX/QQQ family remains blocked from paper routing.
- No future venue is live-enabled by default.
- No external network call is made by default tests.
