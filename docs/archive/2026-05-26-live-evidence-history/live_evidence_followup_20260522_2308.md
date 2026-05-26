# Live Evidence Follow-up

## Current State

- run_status: `failed`
- decision: `CONDITIONAL_GO_NEEDS_LIVE_WINDOW`
- markdown_report: `docs/live_evidence_reports/live_evidence_report_20260522_2308.md`
- html_report: `docs/live_evidence_reports/live_evidence_report_20260522_2308.html`

## Immediate Next Work

- inspect the failure point in the log tail and fix the first blocking error before rerunning

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
