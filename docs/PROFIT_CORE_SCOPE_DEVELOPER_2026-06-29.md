<!--
作成日: 2026-06-29_21:02 JST
更新日: 2026-06-29_21:02 JST
-->

# Profit Core Scope For Developers

## 結論

Profit Core は、candidate を増やす仕組みではなく、利益っぽく見える候補を actual cash evidence、cost-stress survival、kill decision で早く落とすための最小中核です。

この repo で Core と呼んでよいのは次だけです。

```text
candidate
-> cost/stress check
-> paper or tiny-live evidence
-> actual_cash / no actual_cash
-> keep / kill / wait
```

この流れを短くしないもの、証拠を強くしないもの、候補を棄却しやすくしないものは Core ではありません。

## Source Boundary

実装の正本は code、tests、schemas、config、CLI help、runtime artifact です。この文書は scope-control であり、schema や CLI の代替正本ではありません。

既存の実務メモとして [AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md](AGENT_ASSESSMENT_PRACTICAL_DECISION_NOTE_2026-06-20.md) も読む。ただし、この文書も正本ではありません。

Crypto Perp の `actual_cash_result_usd` は、`cash_metric_basis=actual_cash` と actual cash source がそろう時だけ actual cash evidence として扱います。preview、replay、simulation、operator estimate、`cost_adjusted_cash_estimate_usd`、`stress_cash_estimate_usd` は actual cash proof ではありません。

## Core KPIs

Core KPI は次に限定します。

| KPI | 読み方 |
|---|---|
| actual cash evidence | 実 fill、実 fee、funding、cash ledger、または明示された tiny-live measurement artifact に接続しているか |
| NO_TRADE over trade | 同じ event set で trade action が `NO_TRADE` を費用後、stress 後に上回るか |
| kill / wait / run decision | 今日の判断が keep / kill / wait / run のどれかに落ちているか |
| stress-cost survival | spread、slippage、fee、funding、operator time、追加摩擦後にまだ残るか |
| operator burden | 必要な手作業、確認時間、認知負荷が利益幅を食わないか |

この 5 つに直接つながらない metric は Core KPI ではありません。

## Anti-KPIs

次は進捗ではありません。

- `PASS`
- `READY_FOR_HUMAN_REVIEW`
- `READY_FOR_HUMAN_RISK_REVIEW`
- `READ_ONLY_GO`
- viewer 完成
- dashboard 完成
- docs 量
- CLI 数
- artifact 数
- local-only review packet
- audit/remediation の件数
- paper fill 数だけの増加
- same-day rerun の成功
- estimate/proxy の positive result

これらは配線、検査、表示、観察の状態です。actual cash evidence、cost-stress survival、kill / wait / run decision に変換できない限り、利益進捗として数えません。

## Add-on Rule

Strategy Lab、NDX、Trade[XYZ]、Workbench、AI Review、audit/remediation は Add-on です。Core ではありません。

Add-on として触ってよい条件は、次のどれかを改善する時だけです。

- Core の入力品質を上げる。
- actual cash / no actual cash の証拠品質を上げる。
- keep / kill / wait / run の判断を速くする。
- `NO_TRADE` を含む候補棄却力を上げる。
- operator burden を減らす。

この条件に当たらない Add-on は触りません。特に viewer、AI review、audit result は、候補を殺すか待つか実測へ進めるかを明確にしないなら、Core の外です。

## Surface Acceptance

新しい surface、CLI、artifact、schema、doc、viewer を足す時は、実装計画または PR 説明に必ず次を書く。

```text
Core decision shortened:
What the operator no longer needs to inspect:
What can now be killed earlier:
What actual_cash / no_actual_cash boundary is preserved:
Why NO_TRADE remains a first-class outcome:
```

書けない場合、その surface は Profit Core の作業ではありません。

## Decision States

Core の出力は、派手な readiness 名ではなく次の判断へ寄せます。

| state | meaning |
|---|---|
| keep | 次の証拠を集める価値がある |
| kill | これ以上時間を使わない |
| wait | 日数、実測、source、外部入力、または市場状態が足りない |
| run | 明示的な許可、上限、分離、flat reconciliation などの条件を満たした範囲で実測する |

`run` は live order permission と同義ではありません。実測の種類、notional、credential、network、venue、jurisdiction、rollback、stop condition が別途固定されていない限り、run とは呼びません。

## Must Not Break

- `NO_TRADE` を失敗扱いしない。
- estimate positive を actual cash proof と読まない。
- local/manual review を alpha proof と読まない。
- `READ_ONLY_GO` を wallet、signing、exchange write、production live readiness と読まない。
- Trade[XYZ] を default product axis に戻さない。
- NDX Layer 2.2 review harness を alpha、feature-panel readiness、paper readiness、live readiness と読まない。
- Workbench / viewer を判断そのものと読まない。
- paper fill 数を独立した利益機会の数として読まない。

## Implementation Bias

Core に近い変更は、基本的に「追加」より「削る」です。

- 見なくてよい artifact を増やす。
- stop condition を早く出す。
- same-day rerun や proxy gain を落とす。
- `NO_TRADE` leader を trade action へすり替えない。
- actual cash が無いなら `NEEDS_ACTUAL_CASH` または wait に止める。
- operator が読む画面を増やす前に、読まなくてよい理由を artifact に出す。

Profit Core は楽観的な story を守る場所ではありません。候補を早く殺す場所です。
