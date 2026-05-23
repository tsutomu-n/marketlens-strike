# Live Evidence Detailed Report

## Status

- run_status: `failed`
- started_at_utc: `2026-05-22T14:08:00Z`
- finished_at_utc: `None`
- decision: `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`
- log_path: `logs/live_evidence/live_evidence_20260522_2308.log`

## Artifact Summary

- sidecar_metadata_rows: `64`
- sidecar_pricing_rows: `138667`
- raw_quote_rows: `192`
- normalized_quotes: `data/normalized/quotes.parquet`
- cost_matrix: `data/research/venue_cost_matrix.csv`
- backtest_metrics: `data/research/backtest_metrics.json`
- go_no_go_report: `data/research/go_no_go_report.md`
- evidence_card: `data/evidence/evidence_card_20260522_210613.json`

## Venue Decisions

| Venue | Decision | Main Blocker |
|---|---|---|
| gtrade | CONDITIONAL_GO_NEEDS_LIVE_WINDOW | stale_rate at or below threshold |
| ostium | GO |  |

## GTrade Diagnostics

| Symbol | Rows | Open Rows | Tradable Rate | Stale Rate | Missing Mark | Missing Index | Oracle p90 ms | Spread p90 bps |
|---|---|---|---|---|---|---|---|---|
| QQQ | 65 | 60 | 0.9231 | 0.9692 | 0.0769 | 0.0769 | 96108 | 2.0 |
| SPY | 65 | 60 | 0.9231 | 0.9692 | 0.0769 | 0.0769 | 96108 | 2.0 |
| XAU | 65 | 65 | 1.0000 | 0.9692 | 0.0769 | 0.0769 | 96108 | 0.0 |

## Cost Matrix Snapshot

| Venue | Symbol | Stale Rate | Tradable Rate | Spread p90 bps | Holding 4h bps | Notes |
|---|---|---|---|---|---|---|
| gtrade | SPY | 0.9692307692307692 | 0.9230769230769231 | 2.0 | 0.0 | gTrade sidecar=data/raw/sidecar/gtrade/2026-05-22.jsonl; fee_index=5; holding cost uses max active collateral borrowing/funding rate from trading-variables |
| gtrade | QQQ | 0.9692307692307692 | 0.9230769230769231 | 2.0 | 0.0 | gTrade sidecar=data/raw/sidecar/gtrade/2026-05-22.jsonl; fee_index=5; holding cost uses max active collateral borrowing/funding rate from trading-variables |
| gtrade | XAU | 0.9692307692307692 | 1.0 | 0.0 | 22.497049733184 | gTrade sidecar=data/raw/sidecar/gtrade/2026-05-22.jsonl; fee_index=13; holding cost uses max active collateral borrowing/funding rate from trading-variables |
| ostium | SPX_EQUIV | 0.0 | 1.0 | 1.0034440433904563 | 0.255967561152 | ostium registry=data/registry/ostium_instrument_registry.json; rollover_fee_per_block=2.85388127e-10; rollover_rate_long=-0.00511935122304; rollover_rate_short=0.0014559912230400001; holding cost uses conservative max(abs(long), abs(short)) 8hr percent conversion |
| ostium | NDX_EQUIV | 0.0 | 1.0 | 0.4745310165324132 | 0.255967561152 | ostium registry=data/registry/ostium_instrument_registry.json; rollover_fee_per_block=2.85388127e-10; rollover_rate_long=-0.00511935122304; rollover_rate_short=0.0014559912230400001; holding cost uses conservative max(abs(long), abs(short)) 8hr percent conversion |
| ostium | XAU | 0.0 | 1.0 | 2.1890039037231457 | 0.23463989856 | ostium registry=data/registry/ostium_instrument_registry.json; rollover_fee_per_block=1.69360935e-10; rollover_rate_long=-0.0046927979712; rollover_rate_short=-0.0007907220288; holding cost uses conservative max(abs(long), abs(short)) 8hr percent conversion |

## Backtest Snapshot

| Venue | Symbol | Trade Count | Avg Trade Return | Cost Drag bps | Stale Rejected | Halt Rejected |
|---|---|---|---|---|---|---|
| gtrade | SPY | 59 | -0.0011621644928994977 | 708.0 | 1 | 5 |
| gtrade | QQQ | 59 | -0.001127547378643834 | 708.0 | 1 | 5 |
| gtrade | XAU | 59 | -0.003764898852638281 | 2250.1002166625613 | 6 | 0 |
| ostium | SPX_EQUIV | 3 | -0.00012028247940723445 | 12.578700858865947 | 0 | 0 |
| ostium | NDX_EQUIV | 3 | 0.00018143923732168748 | 11.171893724123382 | 0 | 0 |
| ostium | XAU | 3 | -0.0007125387607483172 | 15.55411774059705 | 0 | 0 |

## Validation

- checked_files: `7`
- issue_count: `0`

## Blockers

- stale_rate at or below threshold
- tradable_rate at or above threshold

## Next Actions

- Collect quote rows with fresh venue timestamps so stale_rate is at or below threshold
- Collect a sufficient gTrade/Ostium quote window during tradable sessions
- Provide data/research/signals.csv to run signal-driven backtests instead of quote-only fallback

## Log Tail

```text
│                                                                              │
│ /home/tn/projects/marketlens-strike/.venv/lib/python3.14/site-packages/polar │
│ s/_utils/construction/dataframe.py:457 in sequence_to_pydf                   │
│                                                                              │
│    454 │   if not data:                                                      │
│    455 │   │   return dict_to_pydf({}, schema=schema,                        │
│        schema_overrides=schema_overrides)                                    │
│    456 │                                                                     │
│ ❱  457 │   return _sequence_to_pydf_dispatcher(                              │
│    458 │   │   get_first_non_none(data),                                     │
│    459 │   │   data=data,                                                    │
│    460 │   │   schema=schema,                                                │
│                                                                              │
│ /home/tn/.local/share/uv/python/cpython-3.14.3-linux-x86_64-gnu/lib/python3. │
│ 14/functools.py:982 in wrapper                                               │
│                                                                              │
│    979 │   │   if not args:                                                  │
│    980 │   │   │   raise TypeError(f'{funcname} requires at least '          │
│    981 │   │   │   │   │   │   │   '1 positional argument')                  │
│ ❱  982 │   │   return dispatch(args[0].__class__)(*args, **kw)               │
│    983 │                                                                     │
│    984 │   funcname = getattr(func, '__name__', 'singledispatch function')   │
│    985 │   registry[object] = func                                           │
│                                                                              │
│ /home/tn/projects/marketlens-strike/.venv/lib/python3.14/site-packages/polar │
│ s/_utils/construction/dataframe.py:713 in _sequence_of_dict_to_pydf          │
│                                                                              │
│    710 │   │   else None                                                     │
│    711 │   )                                                                 │
│    712 │                                                                     │
│ ❱  713 │   pydf = PyDataFrame.from_dicts(                                    │
│    714 │   │   data,                                                         │
│    715 │   │   dicts_schema,                                                 │
│    716 │   │   schema_overrides,                                             │
╰──────────────────────────────────────────────────────────────────────────────╯
ComputeError: could not append value: 7464.63333 of type: f64 to the builder; 
make sure that all rows have the same schema or consider increasing 
`infer_schema_length`

it might also be that a value overflows the data-type's capacity
```
