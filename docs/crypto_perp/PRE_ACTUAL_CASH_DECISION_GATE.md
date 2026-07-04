<!--
作成日: 2026-07-04_16:00 JST
更新日: 2026-07-04_16:00 JST
-->

# Pre Actual Cash Decision Gate

## 結論

actual cash を当分実装しない前提では、pre-actual-cash 段階のゴールを利益証明に置かない。

この gate のゴールは、候補を次の4択に落とすことだけに限定する。

- `KILL`
- `REVISE_EVENT_DEFINITION`
- `COLLECT_MORE_SOURCES`
- `HOLD_FOR_FUTURE_ACTUAL_CASH`

この文書は新しい CLI、schema、artifact contract、actual cash source、cash ledger、live measurement、exchange write、wallet/signing、live order を追加しない。既存 artifact と人間レビューで、pre-actual-cash の判断境界を固定するための文書である。

## 範囲

扱うもの:

- candidate event / matured outcome
- public candle based outcome
- source availability
- replay / feature / edge / tournament rows v2 / bias guard
- existing profit-readiness docs の読み替え境界
- actual cash を先送りする時の人間 decision

扱わないもの:

- actual cash の実装
- actual cash rows の生成
- actual cash gate の追加
- cash ledger の設計
- tiny-live execution
- production live trading
- external exchange write
- wallet / signing
- profit proof

## 読み間違えてはいけない境界

次の状態は、利益証拠ではない。

| 状態 | 読んでよいこと | 読んではいけないこと |
|---|---|---|
| public candle only | 公開OHLCVだけで event / outcome の形を確認できた | fill、fee、funding、slippage、trade tape、order book、actual cash を確認できた |
| 1 event | pipeline の疎通と1件の事後 outcome を確認できた | 再現性、期待値、robustness、利益性を確認できた |
| `leader_action=NO_TRADE` | 同一 event set 上では見送りが最良または取引候補が弱い | NO_TRADE を無視して取引 action を選んでよい |
| `selected_action=UNKNOWN` | edge scorer が取引 action を選べる入力に達していない | UNKNOWN を弱いBUY/SELL signalとして読んでよい |
| bias guard sample insufficient | sample不足を guard が正しく止めた | bias / overfit risk を通過した |
| `pbo_status=NOT_ESTIMABLE` | PBO を推定しない正式結果が出た | PBO が良い、または問題なし |
| `actual_cash_result_usd=null` | actual cash evidence が接続されていない | cash PnL が0、または損益なし |

特に、`public 5m candles only`、`1 event`、`leader_action=NO_TRADE`、`selected_action=UNKNOWN`、`PBO_NOT_ESTIMABLE_SAMPLE_INSUFFICIENT` が同時に出ている場合、結論は「利益証明に近い」ではない。結論は「pre-actual-cash では候補判断をまだ限定する」である。

## 4択 decision

### `KILL`

候補を棄却する。

使う時:

- 複数 event で NO_TRADE に勝てない。
- cost-adjusted / stress estimate で取引 action が一貫して負ける。
- source を増やしても event definition が signal として機能しない。
- candidate を残す理由が「実装済みだから」「見た目がよいから」だけになっている。

意味:

- actual cash へ進まない。
- tiny-live の理由にしない。
- 同じ event definition で再試行しない。

### `REVISE_EVENT_DEFINITION`

event definition を作り直す。

使う時:

- event が広すぎる、遅すぎる、または情報 cutoff と outcome window が噛み合っていない。
- NO_TRADE leader が続くが、source不足だけでは説明できない。
- `selected_action=UNKNOWN` が、source不足ではなく feature / rule / event設計の曖昧さから出ている。
- 1 event の outcome を見てから都合よく action を選びたくなる構造になっている。

意味:

- 既存 candidate を利益候補として温存しない。
- event id、cutoff、feature baseline、outcome window、比較 action set を見直す。
- revised definition で別 candidate として再収集する。

### `COLLECT_MORE_SOURCES`

追加収集へ戻す。

使う時:

- public candle only で、ticker / trades / books / funding / replay / cost inputs が足りない。
- `can_compute_actual_cash=false` のまま、actual cash 以前の estimate すら荒い。
- `optional_feature_count=0` や `sets_entry_action=false` が残っている。
- `selected_action=UNKNOWN` の主因が source不足である。
- sample が 1 event だけで、bias guard が sample不足で止まっている。

意味:

- 利益証明ではなく、判断材料の不足を埋める。
- public network、credential、外部書き込みを使う場合は、既存 runbook の承認条件に従う。
- actual cash source の設計には進まない。

### `HOLD_FOR_FUTURE_ACTUAL_CASH`

将来の actual cash 検証まで保留する。

使う時:

- pre-actual-cash では追加収集しても決定できない論点が残る。
- fee / funding / slippage / fills / execution quality が判断の主因で、proxy では代替できない。
- 今は actual cash を実装しない方針で、候補を kill するほどの否定材料もない。
- future work として残す価値はあるが、当面の実装優先度は低い。

意味:

- actual cash を今すぐ実装する許可ではない。
- 候補を利益証明済みとして扱わない。
- 将来再開するなら、actual cash source / cash ledger / rows / gate の設計から再開する。

## Decision の選び方

まず、以下を読む。

- source availability の `can_compute_actual_cash`、`can_compute_cost_adjusted_estimate`、`can_compute_depth`
- feature pack の `optional_feature_count`、`sets_entry_action`
- edge score の `selected_action`
- tournament rows v2 の `leader_action`、`leader_beats_no_trade`
- bias guard の `guard_status`、`pbo_status`、known gaps
- event count と source の種類

次に、以下の順で落とす。

| 条件 | decision |
|---|---|
| 複数 event / source補強後も取引候補が NO_TRADE に勝てない | `KILL` |
| event / cutoff / outcome window / action set の定義が弱い | `REVISE_EVENT_DEFINITION` |
| source不足や sample不足で判断不能 | `COLLECT_MORE_SOURCES` |
| proxy では決められず、actual cash まで保留するのが最も正直 | `HOLD_FOR_FUTURE_ACTUAL_CASH` |

この gate には `READY_FOR_ACTUAL_CASH`、`READY_TO_DESIGN_ACTUAL_CASH_SOURCE`、`PROFIT_PROVEN`、`TRADE_APPROVED` を置かない。actual cash を当分実装しない前提では、pre-actual-cash の出口を「実資金へ進む」ではなく「候補をどう扱うか」に限定する。

## 現行 artifact への読み

現行の progress assessment で確認されている `public 5m candles only`、`1 event / 1 outcome`、`leader_action=NO_TRADE`、`leader_beats_no_trade=false`、`selected_action=UNKNOWN`、`pbo_status=NOT_ESTIMABLE`、`PBO_NOT_ESTIMABLE_SAMPLE_INSUFFICIENT` は、利益証拠ではない。

この状態の基本 decision は `COLLECT_MORE_SOURCES` である。ただし、追加 source を集めても event definition が信号として弱いと判断できる場合は `REVISE_EVENT_DEFINITION`、追加収集の価値が薄い場合は `KILL`、actual cash でしか決められないが当分実装しない場合は `HOLD_FOR_FUTURE_ACTUAL_CASH` にする。

## 禁止する読み替え

- public candle outcome を actual cash evidence と読む。
- 1 event の outcome を alpha proof と読む。
- NO_TRADE leader を「保守的に勝っている trade候補」と読む。
- `selected_action=UNKNOWN` を暗黙の entry signal と読む。
- bias guard の sample不足停止を robustness 通過と読む。
- `actual_cash_result_usd=null` を cash 0 と読む。
- estimate / preview / dogfood / status / viewer を profit proof と読む。
- この文書を新CLI追加、actual cash 実装、または live permission の根拠にする。

## 参照

- [PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md](PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md)
- [PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md](PROFIT_READINESS_SURFACE_INVENTORY_2026-06-27.md)
- [../runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](../runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md)
- [../READ_THIS_FIRST_PROGRESS_TO_90_2026-07-04/PRE_ACTUAL_CASH_PROGRESS_2026-07-04.md](../READ_THIS_FIRST_PROGRESS_TO_90_2026-07-04/PRE_ACTUAL_CASH_PROGRESS_2026-07-04.md)
