<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Acceptance

The implementation is complete only when all conditions are true.

## Code Acceptance

- `src/sis/venues/read_only_probe.py` exists and has pure local builders.
- The generated probe summary includes `trade_xyz`, `bitget_demo`,
  `bitget_futures`, and `hyperliquid_perp`.
- Future venues are blocked by capability, not marked ready.
- `bitget_demo` remains demo-only.
- Trade[XYZ] remains separate from direct `hyperliquid_perp`.
- CLI command `venue-read-only-probe` writes JSON and Markdown artifacts.
- The default CLI path does not read credentials, call external APIs, sign
  requests, or perform exchange writes.
- Existing `execution-read-only-surfaces` and execution lineage reports are not
  widened in this slice.

## Schema Acceptance

- `schemas/venue_read_only_probe_summary.v1.schema.json` exists.
- Generated summary validates against the schema.
- Strategy Lab schemas remain unchanged.
- `src/sis/venues/ids.py` remains unchanged.
- `evaluation_plan.mls.v1` remains `target_venue=trade_xyz`.

## Documentation Acceptance

- `docs/venues/read_only_capability_probe.md` exists.
- `README.md`, `docs/CURRENT_STATE.md`, and `docs/CODE_STATUS.md` mention the
  probe without claiming readiness.
- `uv run python scripts/check_current_docs.py` passes.

## Verification Acceptance

Required commands:

```bash
git diff -- schemas/strategy_signal.v1.schema.json schemas/trade_candidate.v1.schema.json schemas/paper_intent_preview.v1.schema.json schemas/evaluation_plan.mls.v1.schema.json src/sis/venues/ids.py
uv run pytest -q tests/test_venue_read_only_probe.py tests/test_venue_read_only_probe_cli.py tests/test_venue_capabilities.py tests/test_venue_suitability.py tests/test_strategy_lab_schemas.py tests/test_bitget_demo_cli.py
uv run python scripts/check_current_docs.py
./scripts/check
```

Expected:

- first command has no output
- focused tests pass
- current-doc checker passes
- full gate passes
