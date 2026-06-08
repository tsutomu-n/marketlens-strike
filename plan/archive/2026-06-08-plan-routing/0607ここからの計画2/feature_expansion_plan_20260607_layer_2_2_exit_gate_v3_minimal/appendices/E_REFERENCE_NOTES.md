<!--
作成日: 2026-06-07_21:35 JST
更新日: 2026-06-07_21:35 JST
-->

# E_REFERENCE_NOTES

## Repo context

- `data/research/strategy_signals.parquet` is the Strategy Lab canonical signal artifact.
- `data/research/signals.csv` is legacy export.
- `PaperIntentPreview` is paper-only and must not be converted to live orders.
- Runtime validation is in Pydantic models; tracked JSON Schema files are thin guards.
- Wallet secrets, signing, exchange writes, and production live trading remain out of scope.
- Current verification should run commands, not copy old pass counts.

## Official market structure references

### Nasdaq-100 methodology

Reference URL:

```text
https://indexes.nasdaq.com/docs/Methodology_NDX.pdf
```

Relevant facts:

```text
- Nasdaq-100 is designed to measure 100 of the largest Nasdaq-listed non-financial companies.
- It uses modified market capitalization weighting.
- It defines Fast Entry, annual reconstitution, quarterly rebalance, special rebalance, and weighting constraints.
```

### Invesco QQQ ETF

Reference URL:

```text
https://www.invesco.com/qqq-etf/en/home.html
```

Relevant facts:

```text
- QQQ tracks the Nasdaq-100 Index.
- ETF market price is affected by NAV, marketplace supply/demand, bid-ask spread, and premium/discount to NAV.
```

### CME E-mini Nasdaq-100 futures

Reference URL:

```text
https://www.cmegroup.com/markets/equities/nasdaq/e-mini-nasdaq-100.html
```

Relevant facts:

```text
- NQ futures provide Nasdaq-100 exposure.
- Nearly 24-hour access makes them relevant for off-hour news and overseas events.
```

### OpenAI Structured Outputs

Reference URL:

```text
https://developers.openai.com/api/docs/guides/structured-outputs
```

Relevant facts:

```text
- Strict JSON schema output is supported via json_schema / strict true.
- This is relevant for a future API mode, not for the initial manual mode.
```

### GitHub Security Lab Taskflow Agent

Reference URL:

```text
https://github.blog/security/ai-supported-vulnerability-triage-with-the-github-security-lab-taskflow-agent/
```

Relevant facts:

```text
- LLMs are useful for triage when tasks are broken into stages.
- Information collection and auditing are separated.
- Human review remains part of the workflow.
```
