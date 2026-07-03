<!--
作成日: 2026-07-03_10:10 JST
更新日: 2026-07-03_12:41 JST
-->

# Next Decision After Dogfood

## 結論

Reality Check Sprint の後にやることは、結果で決める。事前に Smart Prior、ML、Virtual Gate、Hyperliquid / GRVT を実装キューへ入れない。

最終判断は `next_single_blocker_to_fix` を1つだけ見て決める。

## Decision Table

| Reality check result | 次にやること | やらないこと |
|---|---|---|
| `SEARCH_LEDGER_MISSING` | candidate generation outputを修正 | bridge拡張、ML |
| `SUCCESS_ONLY_REPORTING_DETECTED` | full inventory / rejection ledgerを復旧 | selected候補の評価 |
| `SEALED_TEST_USED_FOR_SELECTION` | run破棄、split/leakage policy修正 | 成績の解釈 |
| `AUTHORING_BRIDGE_MISSING` | C9 bridgeを実行可能にする | Smart Prior新設 |
| `UNSUPPORTED_FAMILY_DOMINATES` | 1 familyだけC9 mappingを追加 | 全family対応 |
| `UNSUPPORTED_SIDE_BIAS_DOMINATES` | both/no_trade の橋渡し意味を定義 | 無理に売買spec化 |
| `NO_SYMBOL_DATA_DOMINATES` | source refresh / source root修正 | candidate family追加 |
| `BRIDGED_TECHNICAL_ONLY` | economic statusを明示、kill gateへ進む条件定義 | BRIDGEDを合格扱い |
| `BLOCKED_MISSING_EVENT_OR_OUTCOME` | truth-cycle event/outcome作成 | risk reviewやgate実行 |
| `ACTUAL_CASH_SOURCE_MISSING` | cash ledger / assignment handoff設計 | virtual/estimateで代用 |
| `NEEDS_ACTUAL_CASH` | actual cash rows handoff | strategyを勝ち扱い |
| `KILL` dominant | familyごと棄却またはmechanism修正 | parameter微調整で再挑戦 |
| no blocker | 次に小さなvirtual lifecycle fixture | demo/testnet本番接続 |

## Scenario A: Bridge blockers dominate

### 条件

```text
bridge_blocked_count > bridge_bridged_count
UNSUPPORTED_FAMILY_DOMINATES or UNSUPPORTED_SIDE_BIAS_DOMINATES
```

### 次PR

```text
PR: harden C9 bridge for one additional family
```

対象family:

```text
bridge manifest の blocked_by_family / blocked_reason_counts で支配的なfamilyを1つだけ選ぶ。
```

理由:

- 事前に都合のよい family を選ばない。
- 実dogfoodの詰まりを1つだけ直す。
- source不足、side bias不足、unsupported family を混ぜて成功扱いにしない。
- family-aware mapping は `BRIDGED` だけでなく、より正確な blocker への分解でもよい。

### 完了条件

- 対象familyが candidate-scoped authoring spec を生成できる、または source / side / product / symbol 不足を precise blocker として返す。
- unsupported family のまま放置しない。
- `BRIDGED` は technical-only のまま。
- `economic_gate_status=NOT_EVALUATED` をsummaryに出す。
- tests/strategy_idea_candidates/test_authoring_bridge.py にfocused testを追加する。

### やらないこと

- 全family対応。
- sourceに無い liquidation / OI を推定で埋める。
- production execution。
- actual cash claim。

## Scenario B: Source blockers dominate

### 条件

```text
NO_SYMBOL_DATA_DOMINATES
MISSING_SOURCE_COLUMNS_DOMINATES
SOURCE_ROOT_MISSING
CANDLES_5M_MISSING
```

### 次PR

```text
PR: fix prep-watchdeck compatible source adapter / source refresh assumptions
```

### 完了条件

- BTCUSDT / ETHUSDT 5m source rootがbridge inputとして読める。
- funding, spread, candles の欠損がmachine-readable blockerになる。
- source不足をestimateで黙って埋めない。
- `known_gaps` に不足を残す。

### やらないこと

- source不足のままcandidateを成功扱いする。
- generated fake dataでbridgeを通す。
- orderbook depthが無いのにdepth measured扱いする。

## Scenario C: Technical bridge works but economic evidence is missing

### 条件

```text
bridge_bridged_count > 0
actual_cash_available_count = 0
BRIDGED_TECHNICAL_ONLY
```

### 次PR

```text
PR: economic-readiness summary for bridged candidates
```

または既存 `risk_taker_review` / `profit_readiness` のsource refsへ bridge output をつなぐ。

### 完了条件

- technical bridgeとeconomic readinessが分離される。
- `min_trade_count=0`、`pass_thresholds={}` のspecは economic passにならない。
- rows-v2 / source availability / bias guard が無い場合は `INCONCLUSIVE_DATA`。

### やらないこと

- backtest pack validation PASSを利益証拠にする。
- total_returnだけでshortlistする。

## Scenario D: Candidate generation is the bottleneck

### 条件

```text
candidate_count_total is too low
candidate_count_shortlisted = 0
bridge has little to process
rejection reasons show family/grid too narrow
```

### 次PR

```text
PR: expand deterministic candidate family or parameter grid minimally
```

### 完了条件

- 新familyまたはparameterは1回に少数だけ。
- search ledgerに全candidate / rejected rowsが残る。
- duplicate / cap rejectionが残る。
- sealed testは使わない。

### やらないこと

- Smart Prior Generator新設。
- GA/ML。
- 大量indicator catalog。

## Scenario E: Actual cash input is the bottleneck

### 条件

```text
NEEDS_ACTUAL_CASH
ACTUAL_CASH_SOURCE_MISSING
ACTUAL_CASH_ROWS_MISSING
```

### 次PR

```text
PR: actual cash rows handoff hardening
```

### 完了条件

- ledger + assignment の必要条件が明確。
- trade actionのmissing ledger entryは失敗。
- NO_TRADEだけcash 0を許可。
- virtual / estimate / preview からactual cash rowsを作れない。

### やらないこと

- actual cashなしのgate実行。
- virtual PnLの昇格。
- tiny live実行。

## Scenario F: Virtual lifecycle is the bottleneck

### 条件

```text
bridge and risk review can produce candidates
actual cash before execution risk check is too risky
Bitget demo order lifecycle is still unproven
```

### 次PR

```text
PR: fixture virtual execution lifecycle artifact
```

### 完了条件

- fixtureでorder accepted / rejectedを表現できる。
- partial fill、cancel、reduce-only close、flat reconciliationを表現できる。
- duplicate clientOidを検出できる。
- virtual resultは profit evidence ではない。

### やらないこと

- Bitget demo network接続。
- Hyperliquid / GRVT testnet対応。
- virtual PnL評価。

## Scenario G: Everything dies as KILL

### 条件

```text
risk_review_status_counts.KILL dominates
NO_TRADE leader dominates
after-cost edge negative
stress edge negative
profit concentration too high
```

### 次PR

基本的に実装PRではなく、candidate family rejection / learning記録です。

```text
PR: record family-level rejection and stop condition notes
```

### 完了条件

- そのfamilyを無理に救わない。
- parameter微調整で同じfamilyを再提出しない。
- kill reasonをcandidate review / learning ledgerに残す。

### やらないこと

- しきい値を緩めて通す。
- NO_TRADEを失敗扱いする。
- LLMに救済説明を書かせる。

## Reality Check Sprint後の最短推奨

最もあり得る順番:

```text
1. profit-core-reality-check 実装
2. dogfood BTCUSDT / ETHUSDT
3. C9 bridge blocker top1 を修正
4. もう一度 dogfood
5. それでも必要なら fixture virtual lifecycle
6. actual cash handoff
```

## Decision anti-patterns

やってはいけない判断:

1. `BRIDGED` が増えたから成功とする。
2. `candidate_count_total` が増えたから前進とする。
3. `backtest_pack_validation` が通ったから攻める。
4. risk reviewが `NEEDS_ACTUAL_CASH` なのにvirtualで代替する。
5. `KILL` をparameter調整で救う。
6. blocker分布を見ずにSmart Priorを作る。
7. dogfood前にHyperliquid / GRVTへ広げる。

## Final rule

次に直すのは、最大の理想機能ではなく、`next_single_blocker_to_fix` で最上位に出た1つだけです。

このルールを破ると、また「研究基盤を作る研究」に戻る。
