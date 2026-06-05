<!--
作成日: 2026-05-29_21:42 JST
更新日: 2026-06-05_08:11 JST
-->

# Currentness Source Notes

2026-05-29時点で、実装直前に公式情報へ戻るべき資料です。ここでは固定仕様として断定せず、確認入口として扱います。

## Official Sources

| topic | source | 実装前に見ること |
|---|---|---|
| Polars | https://docs.pola.rs/ | lazy/query plan、time-series、join/asof、rolling、null処理 |
| LightGBM Parameters | https://lightgbm.readthedocs.io/en/latest/Parameters.html | alias、default、互換性、seed/deterministic系 |
| LightGBM Tuning | https://lightgbm.readthedocs.io/en/latest/Parameters-Tuning.html | leaf-wise overfit、`num_leaves`、`max_depth`、`min_data_in_leaf` |
| scikit-learn TimeSeriesSplit | https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html | time split、gap、equal spacing assumptions |
| Solana Tokens | https://solana.com/docs/tokens | mint、token account、authority、Token Extensions |
| Solana Transactions | https://solana.com/docs/core/transactions | transaction制約、signature、blockhash |
| Solana Fees | https://solana.com/docs/core/fees | base fee、prioritization fee |
| Jito Low Latency Transaction Send | https://docs.jito.wtf/lowlatencytxnsend/ | bundle、tip、landing、uncled blocks、API仕様 |
| PyBotters | https://pybotters.readthedocs.io/ja/stable/index.html | v1/v2予定、supported exchanges、API互換性 |
| VectorBT | https://vectorbt.dev/ | vectorized backtestの範囲、実約定との差 |

## Currentness Rules

- Medium、YouTube、古いREADME由来の主張をそのまま実装しない。
- API、SDK、protocol、取引所仕様は実装直前に公式資料で再確認する。
- 「低遅延で有利」「高精度」「bundleなら安全」は検証対象であり結論ではない。
- secret、private key、seed phrase、wallet credentialの実値はdocsへ書かない。

## What Changed In The Plan

追加調査後、付録に次を入れることにした。

- LightGBMのparameter alias / leaf-wise overfit注意。
- 時系列splitでのgapとfuture data回避。
- Solana token authority / fee / transaction制約。
- Jito bundleのtip、landing、uncled block注意。
- PyBottersのcurrentnessリスク。
- VectorBTを一次スクリーニングに限定する注意。
