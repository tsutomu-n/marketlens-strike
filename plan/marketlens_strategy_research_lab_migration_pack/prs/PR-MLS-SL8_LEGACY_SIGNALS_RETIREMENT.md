# PR-MLS-SL8 Legacy Signals Retirement

## Goal

signals.csv / ResearchSignalStrategy中心のactive pathを退役させる。

## Steps

```text
1. SignalPassthroughStrategyを作る
2. ResearchSignalStrategy aliasを一時的に残す
3. active importsをSignalPassthroughStrategyへ変更
4. paper main pathをPaperIntentPreviewへ変更
5. ResearchSignalStrategyをlegacy moduleへ移す
6. signals.csvをlegacy export扱いにする
7. active testsをnew pathへ移す
```

## Tests

```text
- active path does not require signals.csv
- strategy_signals.parquet/jsonl exists as source of truth
- legacy signals.csv export still possible if explicitly requested
- PaperIntentPreview path is primary
```

## Done

```text
- ResearchSignalStrategy not used in active paper path
- signals.csv not required for paper-operations-cycle when --intents-path is used
```
