# Why Not Bot Preview Strategy Engine

bot-previewはHOLD専用の安全surfaceとして残す。

理由:

```text
- bot-previewを戦略エンジン化すると、Botが注文判断を始めたと誤読される
- read-only safety surfaceとstrategy research surfaceが混ざる
- wallet/signing/exchange writeなしを保証しにくくなる
```

戦略候補は別CLIで出す。

```text
strategy-preview
build-paper-candidate-pack
build-paper-intent-preview
```
