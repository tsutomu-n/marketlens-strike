<!--
作成日: 2026-05-29_22:07 JST
更新日: 2026-06-05_08:11 JST
-->

# Strategy Backlog Table

戦略候補の台帳です。新しい候補は、`SIGNAL_CANDIDATE_TEMPLATE.md` を埋めてからここに追加します。

## Backlog

| signal_id | name | archetype | status | pre_score | next_gate | duplicate_key | evidence | blocker | reject_code | last_review | note |
|---|---|---|---|---:|---|---|---|---|---|---|---|
| SIG-001 | Trend Pullback Resume | pullback | specified | 15 | data-ready | pullback:liquid-major:4h:ma-pullback | source docs | data source not fixed | | pending | 最初の実装候補 |
| SIG-002 | Breakout With Retest | breakout | idea | 13 | specified | breakout:liquid-major:1h:range-retest | source docs | candidate sheet incomplete | | pending | false breakout削減候補 |
| SIG-003 | Mean Reversion In Range | mean-reversion | idea | 12 | specified | mean-reversion:liquid-major:1h:zscore-range | source docs | regime definition needed | | pending | regime条件が先 |
| SIG-004 | Volatility Compression Breakout | volatility | idea | 12 | specified | volatility:liquid-major:1h:compression-break | source docs | slippage model needed | | pending | slippage stress必須 |
| SIG-005 | Regime Filtered Base Signal | regime | idea | 14 | specified | regime:base-signal:4h:allowed-regime | source docs | base signal needed | | pending | skip PnL記録必須 |
| SIG-006 | Cross-asset Confirmation | cross-asset | idea | 10 | specified | cross-asset:target-related:4h:confirmation | source docs | timestamp alignment needed | | pending | timestamp alignmentが課題 |
| SIG-007 | Event Reaction | event | idea | 9 | specified | event:macro-news:1h:first-seen | source docs | first_seen_ts source needed | | pending | first_seen_tsが必要 |

## Status Definitions

| status | meaning |
|---|---|
| `idea` | まだ1枚シート未完成 |
| `specified` | signal contractがある |
| `data-ready` | 必須データの取得可能性が確認済み |
| `backtest-ready` | leakage/cost/baselineが揃った |
| `backtested` | backtest済み |
| `paper-observing` | paper観測中 |
| `rejected` | taxonomy code付きで棄却 |
| `archived` | 重複、保留、古い候補 |

## Batch Review Checklist

- `pre_score < 10` は原則、specifiedへ進めない。
- `reject_code` がある候補は、再開条件がない限り触らない。
- `duplicate_key` が近い候補は統合する。
- `blocker` が残っている候補は次gateへ進めない。
- `evidence` が空の候補はpromotion不可。
- `SIG-001` より複雑な候補は、`SIG-001` の検査観点を再利用する。
