# Trade[XYZ] Implementation Status Audit 2026-05-28

コード、tests、設定、runtime artifact を正として、Trade[XYZ] 実装状態を current status として棚卸しする。2026-05-27 版は pre-P2 gate restore の historical audit として残し、現在状態の根拠にはしない。

## 結論

Trade[XYZ] の PR9a-PR12 read-only evidence chain と P2 gate restore は完了済み。現時点の repo は P2 へスムーズに進める状態で、最新 phase gate は `READ_ONLY_GO`、strict validation は `checked_files=12`, `issues=0`、full check は `294 passed`。

ただし、これは production live trading ready ではない。execution drift は live-readiness blocker として 6 件残っており、Alpaca credentials ありの API connectivity は確認済みだが fresh live `status=pass`、wallet/signing、exchange write integration、public micro live CLI はまだ未完了または意図的に未公開である。

Current snapshot:

```text
./scripts/check:
  294 passed

validate-artifacts --strict:
  checked_files: 12
  issues: 0

phase-gate-review:
  phase_gate_decision: READ_ONLY_GO
  phase2_entry_allowed: true
  blockers: []
  diagnostics_symbols: SP500, XYZ100, NVDA, AAPL, MSFT
  execution_drift_classification_counts:
    P2_BLOCKER: 0
    LIVE_READINESS_BLOCKER: 6

latest quote collection summary:
  venue: trade_xyz
  duration_minutes: 1
  interval_seconds: 60
  row_count: 11
  api_error_count: 0
  collected_symbols:
    SP500, XYZ100, NVDA, AAPL, MSFT, AMZN, GOOGL, META, TSLA, AMD, EWJ

PR12 fresh read-only smoke:
  observed_window_seconds: 3673.995702
  raw_row_count: 310
  per_symbol_raw_row_count:
    AAPL: 62
    MSFT: 62
    NVDA: 62
    SP500: 62
    XYZ100: 62
  final_decision: READ_ONLY_GO
  next_action: none
```

重要な読み替え:

- `fee_mode_unknown_rate=1.0` は current blocker ではない。latest diagnostics は target symbols で `fee_mode_unknown_rate=0.0`。
- Alpaca provider は silent stub ではない。credentials 未設定や empty response は `AlpacaProviderUnavailable` で明示失敗する。
- `READ_ONLY_GO` は read-only / P2 entry の成功であり、live trading ready ではない。
- latest 1-minute refresh と PR12 60-minute smoke evidence は別 artifact として読む。

## Status Table

| Slice | Current status | Evidence | 残る境界 |
|---|---|---|---|
| PR9a CLI / import recovery | DONE | `uv run sis --help`, command split under `src/sis/commands/` | 完全 lazy import までは目的にしない |
| PR9b HIP-3 mapping and contexts | DONE | `perpDexs` / `metaAndAssetCtxs`, `asset_id`, context enrichment, registry tests | 解決不能時は fail-closed |
| PR9c fresh quote window CLI | DONE | `collect-trade-xyz-quotes` with symbols / duration / interval / summary / report / normalize | short refresh と 60-minute smoke を混同しない |
| PR10 strict validation / diagnostics | DONE | `checked_files=12`, `issues=0`, diagnostics target symbols healthy | schema green は live readiness ではない |
| PR11 operations cutover | DONE | `phase-gate-review` consumes Trade[XYZ] artifacts and emits `READ_ONLY_GO` | execution drift は live-readiness blocker として別扱い |
| PR12 fresh read-only smoke | DONE | `observed_window_seconds=3673.995702`, `raw_row_count=310`, `READ_ONLY_GO` | latest artifact overwrite と混同しない |
| P2 fee mode resolution | DONE | registry / raw quote rows have `fee_mode=standard`, taker `9.0`, maker `3.0`; diagnostics fee unknown 0.0 | fee config drift は regression blocker |
| P2 tracking mark-only fix | DONE | `mark_real_diff_bps` uses `quote.mark_price` only; missing mark blocks | mid remains venue mid, not mark substitute |
| P2 Alpaca provider stub removal | DONE | `fetch_alpaca_bars`, `AlpacaProviderUnavailable`, `alpaca-smoke`, unit tests | credentials live API success is unverified |
| P2 execution drift classification | DONE | `P2_BLOCKER=0`, `LIVE_READINESS_BLOCKER=6` | live readiness requires blocker count 0 |
| Micro live safety code | PARTIAL / NOT PUBLIC | adapter / policy / canary tests exist | public CLI, signing, wallet, write smoke absent |
| Production live trading | NOT READY | no public live trading command surface | requires separate safety plan |

## Current Evidence

### Runtime / Test Evidence

Current verification:

```text
uv run python -V: Python 3.13.7
uv run ruff check .: pass
uv run pyrefly check: 0 errors
uv run pytest -q: 294 passed
./scripts/check: pass, 294 passed
```

The current acceptance command for repo health is:

```bash
./scripts/check
```

### Strict Validation

Current strict validation:

```text
checked_files: 12
issues: 0
```

Interpretation:

- Trade[XYZ] registry / raw quote / summary / normalized output / schema chain is valid.
- legacy-only artifact pass is not a current success condition.
- strict validation success does not prove execution readiness.

### Phase Gate

Current phase gate:

```text
phase_gate_decision: READ_ONLY_GO
phase2_entry_allowed: true
blockers: []
strict_validation_issue_count: 0
diagnostics_symbols: SP500, XYZ100, NVDA, AAPL, MSFT
execution_drift_classification_counts:
  P2_BLOCKER: 0
  LIVE_READINESS_BLOCKER: 6
```

Live-readiness blockers:

| signal | observed | expected | classification |
|---|---|---|---|
| `execution_drift_overview_status` | `degraded` | `ok` | `LIVE_READINESS_BLOCKER` |
| `execution_balance_gap_detected` | `true` | `false` | `LIVE_READINESS_BLOCKER` |
| `execution_fills_gap_detected` | `true` | `false` | `LIVE_READINESS_BLOCKER` |
| `execution_comparison_all_registries_present` | `false` | `true` | `LIVE_READINESS_BLOCKER` |
| `execution_state_comparison_mismatching_count` | `3` | `0` | `LIVE_READINESS_BLOCKER` |
| `execution_snapshot_drift_mismatching_snapshot_count` | `3` | `0` | `LIVE_READINESS_BLOCKER` |

Interpretation:

- P2 entry is not blocked.
- live execution readiness is blocked.
- phase gate remediation order is `none` for live-readiness-only drift, so it no longer loops on `refresh-operations-artifacts` as a P2 remediation.
- These two statements are not contradictory.

### Quote / Fee Evidence

Target symbols:

```text
SP500, XYZ100, NVDA, AAPL, MSFT
```

Latest quote diagnostics also include current registry symbols:

```text
AAPL, AMD, AMZN, EWJ, GOOGL, META, MSFT, NVDA, SP500, TSLA, XYZ100
```

Fee fields:

```text
fee_mode: standard
taker_fee_bps: 9.0
maker_fee_bps: 3.0
fee_mode_source: config
```

Interpretation:

- `fee_mode_unknown_rate=1.0` from the 2026-05-27 audit is stale.
- `fee_mode_unknown_rate != 0` is now a regression blocker.
- fee resolution is implemented for the current Trade[XYZ] registry and raw quote rows.

### Latest Refresh vs PR12 Smoke

Latest refresh:

```text
data/ops/trade_xyz_quote_collection_summary.json:
  duration_minutes: 1
  row_count: 11
  collected_symbols:
    SP500, XYZ100, NVDA, AAPL, MSFT, AMZN, GOOGL, META, TSLA, AMD, EWJ
```

PR12 60-minute evidence:

```text
data/ops/pr12_fresh_read_only_smoke_summary.json:
  observed_window_seconds: 3673.995702
  raw_row_count: 310
  per_symbol_raw_row_count:
    AAPL: 62
    MSFT: 62
    NVDA: 62
    SP500: 62
    XYZ100: 62
```

Interpretation:

- latest refresh is the current snapshot.
- PR12 smoke summary is the long-window evidence.
- Do not use the 11-row latest refresh as proof of 60-minute freshness.
- Do not treat the 310-row PR12 smoke as automatically current after a refresh.

## Resolved Former Caveats

| Former caveat in 2026-05-27 audit | 2026-05-28 status |
|---|---|
| `checked_files=11` | Resolved to `checked_files=12` |
| `fee_mode_unknown_rate=1.0` | Resolved; latest diagnostics show `0.0` |
| registry `fee_mode=unknown` | Resolved; registry rows use `standard`, taker `9.0`, maker `3.0` |
| Alpaca provider returns silent empty stub | Resolved; provider raises `AlpacaProviderUnavailable` and maps real bars |
| tracking mark diff can use mid substitute | Resolved; `mark_real_diff_bps` uses mark only |
| execution drift blocks P2 ambiguously | Resolved; drift is classified into `P2_BLOCKER` vs `LIVE_READINESS_BLOCKER` |

## Remaining Gaps

### Live Readiness

Status: not ready.

Reasons:

- `LIVE_READINESS_BLOCKER=6`
- no production live order smoke
- no signing / wallet / exchange write integration
- no public micro live execution CLI
- execution comparison / state / snapshot drift remains degraded

Done condition:

- `execution_drift_classification_counts.LIVE_READINESS_BLOCKER=0`
- exchange write path is reviewed separately
- cancel / close / reduce-only safety is verified against the intended live surface

### Alpaca Live Provider Confidence

Status: partially proven.

Proven:

- credentials missing fails explicitly
- request failure fails explicitly
- empty response fails explicitly
- valid response maps to `RealMarketBar`
- operator entry exists: `uv run sis alpaca-smoke --symbol NVDA --timeframe 15m --limit 1 --feed iex`
- smoke writes `data/ops/alpaca_live_smoke_summary.json` and `data/reports/alpaca_live_smoke.md` on success and failure

Not proven:

- credentials ありの live Alpaca API success smoke

Done condition:

- credentials-present smoke passes without writing secrets to repo
- provider source confidence is reflected in tracking / paper-to-live decisions

### Micro Live Surface

Status: code/test surface only.

Proven:

- adapter / policy / canary tests exist.
- policy checks are dry-run / fake-exchange oriented.

Not public:

- operator CLI for live micro order execution.
- production write integration.
- wallet / signing path.

Done condition:

- separate PR / plan defines public command, env contract, safety limits, dry-run default, kill switch, cancel/close proof, and audit bundle.

### Session / Underlying Market Boundary

Status: guarded, not fully modeled in quote row.

Current behavior:

- quote row can have `session_type=unknown` while venue book is present.
- tracking and micro live layers own underlying-session blocks.

Done condition:

- any live or paper-to-live decision requires known acceptable underlying session.
- `session_type=unknown` is not treated as live-ready.

## What To Read

Current docs:

1. `docs/CURRENT_STATE.md`
2. `docs/CODE_STATUS.md`
3. `docs/OPERATIONS_RUNBOOK.md`
4. `docs/FAILURE_MODE_RESPONSIBILITY_MAP_2026-05-28.md`
5. `docs/DOCUMENT_AUDIT_2026-05-30.md`
6. this document

Historical docs:

- `docs/archive/2026-05-30-doc-audit/TRADE_XYZ_IMPLEMENTATION_STATUS_AUDIT_2026-05-27.md`
- `docs/archive/2026-05-30-doc-audit/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md`
- `docs/archive/2026-05-30-doc-audit/DOCUMENT_AUDIT_2026-05-27.md`

## Recheck Commands

Fast current check:

```bash
./scripts/check
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

Trade[XYZ] fresh short refresh:

```bash
uv run sis collect-trade-xyz-quotes \
  --symbols SP500,XYZ100,NVDA,AAPL,MSFT \
  --duration-minutes 1 \
  --interval-seconds 60 \
  --replace \
  --write-summary \
  --write-report
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

PR12-style long-window evidence refresh:

```bash
uv run sis collect-trade-xyz-quotes \
  --symbols SP500,XYZ100,NVDA,AAPL,MSFT \
  --duration-minutes 60 \
  --interval-seconds 60 \
  --normalize \
  --replace \
  --write-summary \
  --write-report
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

Targeted tests:

```bash
uv run pytest \
  tests/test_trade_xyz_registry.py \
  tests/test_trade_xyz_collector.py \
  tests/test_trade_xyz_normalizer.py \
  tests/test_validate_artifacts_trade_xyz.py \
  tests/test_quote_diagnostics.py \
  tests/test_phase_gate_review.py \
  tests/test_alpaca_provider.py \
  tests/test_real_vs_venue_tracking.py \
  -q
```

## Completion Criteria

This audit is current if all are true:

- `./scripts/check` passes.
- `validate-artifacts --strict` reports `checked_files=12`, `issues=0`.
- `phase-gate-review` reports `READ_ONLY_GO`, `P2_BLOCKER=0`.
- docs do not treat `fee_mode_unknown_rate=1.0` as current.
- docs do not describe Alpaca provider as a silent stub.
- docs do not describe `READ_ONLY_GO` as live trading ready.
- latest refresh and PR12 long-window evidence are not mixed.
