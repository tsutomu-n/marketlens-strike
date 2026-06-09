<!--
作成日: 2026-06-08_20:18 JST
更新日: 2026-06-08_20:18 JST
-->

# 13_RISK_AND_STOP_CONDITIONS

## 主要リスク

| Risk | 内容 | 対策 |
|---|---|---|
| 2.2承認の過信 | APPROVE_2_3をデータ可用性の証明と誤解 | Start conditionとData Source Resolutionを挟む |
| QQQ/NDX混同 | QQQ ETF価格をNDXそのものと扱う | QQQはobserved ETF proxyとしてmanifestへ明記 |
| NQ混同 | NQをQQQ/NDXの正本にする | NQはdeferred futures price discovery proxy |
| 時刻リーク | same-day closeやsource_ts_max超過を使う | leakage.pyでfail |
| provider依存 | データ取得元が未決のまま実装 | fixture mode first |
| 早すぎるStrategy Lab接続 | residual生成後すぐsignal化 | Strategy Lab exportは別計画 |
| backtest沼 | residualができたら性能検証へ飛ぶ | Neutralization/Counter-DAG reportを先に通す |

## Stop conditions

```text
- 2.2 exit decision が APPROVE_2_3 でない
- freeze manifestがない
- second_review_required=true
- unresolved_human_decisionsが残る
- required sourceのfixture/local inputが用意できない
- DGS10/VIXのavailabilityを定義できない
- source_ts_max <= feature_ts を保証できない
- same-day closeをinputに使いたくなる
- external API / credentials / dependency追加が必要
- Strategy Lab model変更が必要
- paper/live/order path変更が必要
- NQ/VXN/SOX/optionsを初期requiredにしたくなる
```

## 止まった時に聞く質問

```text
1. このsourceはinitial requiredにするか、それともdeferredにするか？
2. DGS10/VIXの時刻availabilityはどの時点で固定するか？
3. QQQ ETF proxyの代替としてNDX index levelを使う必要があるか？
4. NQ futuresを2.3初期から入れるか、別PRに分けるか？
5. Strategy Lab exportへ進む前に必要な診断基準をどう置くか？
```
