# Failure Mode Map For Strategy Research Lab

## FD-SL-01 Data Provenance Failure

壊れ方:

```text
古いquote、新しいfeature、別runのtrackingを混ぜる
```

防止:

```text
DataSnapshotManifest
FeatureSnapshotManifest
hash / generated_at / min_ts / max_ts
```

## FD-SL-02 Signal Symbol Binding Failure

壊れ方:

```text
QQQ signalをそのままXYZ100 candidateへ流す
```

防止:

```text
SymbolBinding
execution_symbol / real_market_symbol mandatory
```

## FD-SL-03 Trial Overfitting Failure

壊れ方:

```text
多数試行からbestだけ採用
```

防止:

```text
TrialLedger
trial_group_id
trial_index
parameter_space_hash
```

## FD-SL-04 Claim Inflation Failure

壊れ方:

```text
paper_ready / live_readyを過剰主張
```

防止:

```text
claim flags default false
PromotionDecision required
```

## FD-SL-05 Paper Intent Staleness Failure

壊れ方:

```text
古いPaperIntentPreviewをpaper実行する
```

防止:

```text
valid_until
requires_revalidation=true
PaperBroker latest quote/tracking recheck
```
