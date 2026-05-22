# 12. Go / No-Go Spec

## Decision types

```txt
GO
CONDITIONAL_GO
NO_GO
```

## GO criteria

```txt
- gTrade SPY/QQQ/XAU quote取得が安定
- Ostiumの対象symbolとprice/session取得が確定
- 4h〜3dのvenue-native backtestでコスト控除後に期待値が残る
- stale_rateが閾値以下
- tradable_rateが閾値以上
- spread_p90が閾値以下
- mark/index/bid/ask/oracle_tsを保存できる
- 短期スキャルなしで成立する
```

## Conditional GO

```txt
- gTradeはGOだがOstium未確定
- Ostiumはsymbol/priceは取れるがfee/liquidation未確定
- 24hログではOKだが14日ログが未完了
```

## NO-GO criteria

```txt
- quote取得が不安定
- price reference不明
- holding/borrowing/rollover costを再現できない
- market close/gapが致命的
- spreadが高すぎる
- 4h〜3dで期待値が残らない
- 短期スキャルでしか利益が出ない
```

## Report format

```md
# Go/No-Go Report

## Decision
CONDITIONAL_GO

## Summary
...

## Criteria
| Criterion | Result | Evidence |
|---|---|---|

## Venue Decisions
| Venue | Decision | Main Blocker |
|---|---|---|

## Blockers
...

## Next Actions
...
```
