<!--
作成日: 2026-06-07_20:25 JST
更新日: 2026-06-07_20:25 JST
-->

# Appendix G: Reference Notes

この計画は、Repo内の既存設計と外部一次情報の両方を前提にする。

## Repo references to inspect

```text
AGENTS.md
README.md
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
docs/strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md
docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md
src/sis/research/strategy_lab/
src/sis/research_protocol/
src/sis/commands/research.py
schemas/strategy_signal.v1.schema.json
schemas/data_snapshot_manifest.v1.schema.json
schemas/feature_snapshot_manifest.v1.schema.json
```

## External references for later Phase C

Phase A/Bでは外部APIを使わない。以下は設計理解用。

```text
Nasdaq-100 Methodology:
  Nasdaq official methodology PDF.
  Use for modified capitalization weighting, Fast Entry, reconstitution, rebalance, special rebalance, weight cap concepts.

Invesco QQQ official pages:
  Use for ETF/NAV/market price/premium-discount distinction.

CME E-mini Nasdaq-100 futures official page:
  Use for NQ as futures price discovery proxy.

Cboe VXN official dashboard:
  Use for Nasdaq-100 volatility regime concept.

Numerai docs:
  Use later for neutralization / residual alpha design.

DoWhy graph refutation docs:
  Use later after feature panel exists.

causal-learn docs:
  Use later for causal discovery challenge, not initial DAG generation.
```

## Current interpretation

```text
- Nasdaq-100 methodology parts belong in mechanism_parts and counter_dags, not initial feature computation.
- QQQ is the initial observable proxy, not the same as NDX theoretical index.
- NQ is optional price discovery proxy, not required for Phase A/B.
- VXN is optional provider-dependent; VIX is default proxy for initial contract.
- SMH is default semiconductor proxy; SOX direct source is optional.
```
