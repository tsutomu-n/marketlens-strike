<!--
作成日: 2026-06-09_15:07 JST
更新日: 2026-06-09_15:07 JST
-->

# Test Plan

Run focused tests first:

```bash
uv run pytest -q tests/test_venue_suitability.py
uv run pytest -q tests/test_strategy_lab_candidate_pack.py tests/test_strategy_lab_paper_intent_preview.py tests/test_paper_from_intents.py
uv run pytest -q tests/test_strategy_lab_commands.py
uv run pytest -q tests/strategy_authoring/test_cli_bundle.py
uv run pytest -q tests/test_strategy_lab_schemas.py
uv run python scripts/check_current_docs.py
```

Then run the aggregate gate:

```bash
./scripts/check
```

Required test scenarios:

- future catalog venues exist but are not in `VENUE_IDS`
- NDX/QQQ blocks `bitget_demo` paper candidate and paper intent
- NDX/QQQ blocks `hyperliquid_perp` and `bitget_futures`
- BTCUSDT `bitget_demo` fixture remains allowed
- `trade_xyz` NDX proxy is blocked at paper candidate / paper intent stages
- blocked candidates can still be recorded
- selected candidates cannot be venue-unsuitable
- CLI candidate pack writes suitability-blocked NDX/QQQ rows as rejected
- Strategy Authoring paper preview remains paper-only and emits no intents
