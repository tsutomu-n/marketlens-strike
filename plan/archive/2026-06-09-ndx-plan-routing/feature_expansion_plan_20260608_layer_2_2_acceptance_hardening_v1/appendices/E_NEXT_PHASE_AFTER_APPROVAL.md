<!--
作成日: 2026-06-08_19:23 JST
更新日: 2026-06-08_19:23 JST
-->

# E_NEXT_PHASE_AFTER_APPROVAL

## APPROVE_2_3後の次フェーズ

このPRが終わり、`layer_2_2_exit_decision.json` が `APPROVE_2_3` になり、`second_review_required=false` かつfreeze manifestが存在する場合のみ、次フェーズ計画へ進む。

次フェーズは2.3であり、今回のPRには含めない。

## 2.3で初めて扱うもの

```text
NDX Feature Panel
Data Source Resolver
Open Gap Residual Builder
Expected Gap Model
source_ts_max <= feature_ts checks
neutralization planning
```

## 2.3でもまだ注意すること

```text
NQ/VXN/SOX direct sourceはoptional/deferredのまま始める。
初期はQQQ/SPY/SMH/VIX/DGS10/mega-cap basketの日足・寄り付き系から始める。
Strategy Lab exportはさらに後。
```
