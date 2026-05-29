# Stop Conditions

Stop implementation and ask for review if any condition occurs.

```text
- Any artifact claims live_ready=true
- PaperIntentPreview can be passed to live adapter
- bot-preview starts generating executable order candidates
- Strategy trial runs without DataSnapshotManifest
- Feature timestamp can exceed signal timestamp
- SymbolBinding missing for XYZ100 / SP500 proxy
- PaperBroker accepts intent without revalidation
- signals.csv becomes source of truth again
```
