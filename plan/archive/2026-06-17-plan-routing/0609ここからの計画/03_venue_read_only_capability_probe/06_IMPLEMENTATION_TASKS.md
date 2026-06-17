<!--
作成日: 2026-06-09_21:11 JST
更新日: 2026-06-09_21:11 JST
-->

# Implementation Tasks

## Task 1: Add Pure Probe Builder

Goal: create a local-only read-only probe builder.

Target files:

- add `src/sis/venues/read_only_probe.py`
- add `tests/test_venue_read_only_probe.py`

Implementation details:

- Define frozen dataclasses or typed dict builders for probe rows.
- Build rows from `VENUE_CAPABILITY_CATALOG` and `VENUE_SUITABILITY_CATALOG`.
- Fail closed if a venue exists in one catalog but not the other.
- Never read env values.
- Never import network clients.
- Never call adapter methods.
- Add a pure function, suggested:
  - `build_venue_read_only_probe_summary(*, generated_at: str | None = None) -> dict[str, object]`
  - `build_venue_read_only_probe_report(summary: Mapping[str, object]) -> str`

Acceptance:

- generated summary includes all four current catalog venues
- future venues are blocked by capability
- top-level false fields are all false
- no secret-like values can appear because no env is read

Verification:

- `uv run pytest -q tests/test_venue_read_only_probe.py`

Destructive level: none.

## Task 2: Add JSON Schema

Goal: make the probe artifact machine-checkable.

Target files:

- add `schemas/venue_read_only_probe_summary.v1.schema.json`
- modify `tests/test_venue_read_only_probe.py`
- modify `tests/test_strategy_lab_schemas.py` if schema inventory tests need the new schema listed

Implementation details:

- Add schema with const false guards for:
  - `external_api_used`
  - `credentials_used`
  - `wallet_used`
  - `exchange_write_used`
  - `live_order_submitted`
- Validate generated summary in tests using the repo's existing schema test
  pattern.
- Do not add a schema that permits live/order/write fields to be true.

Acceptance:

- generated summary validates against the new schema
- schema file parses in existing schema inventory tests

Verification:

- `uv run pytest -q tests/test_venue_read_only_probe.py tests/test_strategy_lab_schemas.py`

Destructive level: none.

## Task 3: Add Minimal CLI

Goal: expose the local probe as an operator-visible command without network use.

Target files:

- modify `src/sis/commands/execution.py`
- add `tests/test_venue_read_only_probe_cli.py`

Implementation details:

- Add command:
  - `uv run sis venue-read-only-probe`
- Command writes:
  - `data/ops/venue_read_only_probe_summary.json`
  - `data/reports/venue_read_only_probe.md`
- Command echoes:
  - `status=<status>`
  - `venue_count=<count>`
  - `external_api_used=False`
  - `credentials_used=False`
  - `exchange_write_used=False`
  - `summary_path=<path>`
  - `report_path=<path>`
- Command must exit `0` when it successfully writes fixture-only blocked
  status. A blocked future venue is expected, not a CLI failure.
- Do not add options for live network mode in this slice.

Acceptance:

- CLI runs with empty env
- CLI writes both artifacts
- stdout contains no secret values
- summary includes `bitget_futures` and `hyperliquid_perp` as blocked

Verification:

- `uv run pytest -q tests/test_venue_read_only_probe_cli.py`
- `uv run sis venue-read-only-probe`

Destructive level: low local writes under `data/ops` and `data/reports`.

## Task 4: Update Docs

Goal: make the new artifact discoverable and prevent operator misread.

Target files:

- add `docs/venues/read_only_capability_probe.md`
- modify `README.md`
- modify `docs/CURRENT_STATE.md`
- modify `docs/CODE_STATUS.md`

Required wording:

- fixture-first
- no external API used
- no credentials used
- no exchange write used
- no schema widening
- no paper/live readiness

Acceptance:

- current-doc checker passes
- docs do not say `bitget_futures` or `hyperliquid_perp` are ready

Verification:

- `uv run python scripts/check_current_docs.py`

Destructive level: docs only.

## Task 5: Final Guard Verification

Goal: prove this slice did not widen trading scope.

Commands:

```bash
git diff -- schemas/strategy_signal.v1.schema.json schemas/trade_candidate.v1.schema.json schemas/paper_intent_preview.v1.schema.json schemas/evaluation_plan.mls.v1.schema.json src/sis/venues/ids.py
uv run pytest -q tests/test_venue_read_only_probe.py tests/test_venue_read_only_probe_cli.py tests/test_venue_capabilities.py tests/test_venue_suitability.py tests/test_strategy_lab_schemas.py tests/test_bitget_demo_cli.py
uv run python scripts/check_current_docs.py
./scripts/check
```

Acceptance:

- schema/`VenueId` diff command has no output
- all focused tests pass
- `./scripts/check` passes

Destructive level: none, except local generated reports if CLI was run.
