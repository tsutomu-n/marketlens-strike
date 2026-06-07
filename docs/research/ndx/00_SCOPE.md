<!--
作成日: 2026-06-07_19:37 JST
更新日: 2026-06-07_19:37 JST
-->

# NDX Research Scope

Layer 2.2 の初期対象は Nasdaq-100 / NDX と QQQ に限定する。NQ futures は将来候補だが、この実装では取得も検証もしない。

Included:
- NDX
- QQQ
- SPY / SMH / VIX / DGS10 / mega-cap basket as known factors

Excluded:
- Trade[XYZ] order execution
- Bitget demo network
- paper/live order
- wallet, signing, exchange write
- NQ futures ingestion
- options chain, gamma, 0DTE

正本 config は `configs/research_layer_2_2/ndx/scope.yaml`。
