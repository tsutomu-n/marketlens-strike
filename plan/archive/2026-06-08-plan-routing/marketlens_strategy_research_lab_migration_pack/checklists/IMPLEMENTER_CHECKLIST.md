# Implementer Checklist

```text
[ ] production live tradingを実装していない
[ ] wallet/signingを実装していない
[ ] public micro live CLIを出していない
[ ] OrderIntentという名前をresearch/paper preview層で使っていない
[ ] signals.csvを正本にしていない
[ ] strategy_signals.parquet/jsonlを正本にしている
[ ] execution_symbol / real_market_symbolを分離している
[ ] QQQ -> XYZ100はSymbolBinding経由である
[ ] DataSnapshotManifestを生成している
[ ] FeatureSnapshotManifestを生成している
[ ] TrialLedgerに全trialを記録している
[ ] blocked/no_signal candidatesを保存している
[ ] claim flagsはfalseがdefault
[ ] PromotionDecisionなしでPaperIntentPreviewを作らない
[ ] PaperIntentPreviewはrequires_revalidation=true
[ ] PaperBrokerは最新データで再検査する
[ ] ./scripts/check pass
```
