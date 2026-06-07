<!--
作成日: 2026-06-07_20:21 JST
更新日: 2026-06-07_20:21 JST
-->

# NDX Data Source Contract

## 結論

Layer 2.2 ではデータ取得を実装しない。`data_sources.yaml` は、将来 feature panel を作る時に NDX / QQQ / NQ を混同しないための source tier と proxy 責務の contract である。

## Source Tier

```text
defined:
  初期研究 artifact で proxy として使う候補。今回 fetch はしない。

optional_provider_dependent:
  provider 決定後に使える可能性がある候補。初期必須 source にはしない。

deferred:
  index methodology など、今回の Layer 2.2 DAG foundation では参照名だけを残す候補。
```

## 責務分離

```text
QQQ:
  初期 observed ETF proxy。actual_open_gap と open_to_close_outcome の proxy。

NDX:
  Nasdaq-100 index concept と methodology の参照先。初期の売買可能価格 proxy ではない。

NQ:
  optional futures price discovery proxy。QQQ ETF price と同じ node にはしない。
```

## Safety Boundary

この contract は provider 名や候補 proxy を記録するだけである。

```text
しない:
  - external API call
  - credentials read
  - provider fetch implementation
  - Strategy Lab export
  - backtest readiness claim
  - paper/live order path mutation
```
