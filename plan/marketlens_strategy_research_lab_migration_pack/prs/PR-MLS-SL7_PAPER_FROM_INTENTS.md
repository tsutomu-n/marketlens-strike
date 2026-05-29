# PR-MLS-SL7 paper-from-intents

## Goal

PaperIntentPreviewをpaper実行入力にする。ただしPaperBrokerはintentを信じず、最新データで再検査する。

## Files To Change

```text
src/sis/paper/runner.py
src/sis/paper/broker.py
src/sis/commands/paper.py
```

## New CLI

```bash
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

or:

```bash
uv run sis paper-operations-cycle --intents-path data/bot/paper_intent_preview.json
```

## Revalidation

PaperBroker must check:

```text
- latest quote freshness
- latest tracking status
- fee mode
- spread/depth
- session
- risk gate
- valid_until
```

## Artifacts

```text
data/paper/paper_observation_ledger.jsonl
data/paper/orders.parquet
data/paper/fills.parquet
data/paper/positions.parquet
```

## Tests

```text
- stale intent blocks
- latest quote missing blocks
- tracking disallowed blocks
- successful intent creates paper order/fill only
- exchange_write_used remains false
```
