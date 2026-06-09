<!--
作成日: 2026-06-09_15:07 JST
更新日: 2026-06-09_16:13 JST
-->

# Goal

Prevent NDX/QQQ research outputs from being promoted or routed to unsuitable
venues such as Bitget demo/futures or Hyperliquid direct perp.

The implementation must separate two concepts:

- `VenueId`: the current artifact enum, still only `trade_xyz` and
  `bitget_demo`.
- venue suitability: a fail-closed policy that states which venue can be used
  for which asset universe and stage.

The gate must preserve blocked candidate records. A blocked `TradeCandidate` is
evidence and must remain serializable. The gate should stop selection, paper
intent creation, raw paper intent execution, and legacy paper-step order
generation, not candidate recording or research/backtest artifacts.
