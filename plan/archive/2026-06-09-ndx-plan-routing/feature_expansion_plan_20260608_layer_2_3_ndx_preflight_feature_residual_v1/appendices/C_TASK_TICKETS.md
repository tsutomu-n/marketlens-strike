<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# Appendix C: Task Tickets

## Ticket 2.3-0

Title:
```text
Add Layer 2.3 start-condition guard
```

Files:
```text
src/sis/research/ndx/start_conditions.py
tests/research/test_ndx_start_conditions.py
```

Done:
```text
2.3 cannot start without APPROVE_2_3 + freeze manifest + no second review required.
```

## Ticket 2.3-1

Title:
```text
Add NDX data source resolution artifact
```

Files:
```text
schemas/ndx_data_source_resolution.v1.schema.json
src/sis/research/ndx/source_resolution.py
tests/research/test_ndx_source_resolution.py
```

Done:
```text
required / optional / deferred sources are generated and reported without external API.
```

## Ticket 2.3-2

Title:
```text
Add fixture-first NDX feature panel builder
```

Files:
```text
src/sis/research/ndx/fixture_loader.py
src/sis/research/ndx/feature_panel.py
src/sis/research/ndx/feature_manifest.py
tests/research/test_ndx_fixture_loader.py
tests/research/test_ndx_feature_panel.py
```

Done:
```text
fixture input creates ndx_feature_panel.parquet and manifest.
```

## Ticket 2.3-3

Title:
```text
Add feature leakage checks
```

Files:
```text
src/sis/research/ndx/leakage.py
tests/research/test_ndx_feature_leakage.py
```

Done:
```text
future timestamps and outcome leakage are rejected.
```

## Ticket 2.3-4

Title:
```text
Add rolling OLS residual builder
```

Files:
```text
src/sis/research/ndx/residual_model.py
src/sis/research/ndx/residual_artifact.py
tests/research/test_ndx_residual_model.py
tests/research/test_ndx_residual_artifact.py
```

Done:
```text
expected_qqq_gap and open_gap_residual are generated without future leakage.
```

## Ticket 2.3-5

Title:
```text
Add diagnostics and counter-DAG refutation reports
```

Files:
```text
src/sis/research/ndx/diagnostics.py
src/sis/research/ndx/neutralization.py
src/sis/research/ndx/refutation.py
tests/research/test_ndx_diagnostics.py
tests/research/test_ndx_refutation.py
```

Done:
```text
reports are generated, but Strategy Lab export is not performed.
```

## Ticket 2.3-6

Title:
```text
Add CLI wrappers
```

Files:
```text
src/sis/commands/research.py
tests/research/test_ndx_commands.py
```

Done:
```text
research-ndx-source-resolve / feature-panel / residual / diagnostics commands work.
```
