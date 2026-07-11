<!--
作成日: 2026-07-11_11:40 JST
更新日: 2026-07-11_18:53 JST
-->

# Crypto Perp No-Cash Third-Party Explainer Plan

## チェックポイントID

`DOC-20260711-CRYPTO-PERP-NO-CASH-EXPLAINER`

## 現在の位置づけ

この計画は、第三者向け説明書を作成した時点の履歴です。現在の実装主計画ではありません。追加のprofit evidence auditにより、当初のartifact判断と経済評価は更新されました。

現在の主計画は[Crypto Perp Profit Evidence Hardening](CRYPTO_PERP_PROFIT_EVIDENCE_HARDENING_2026-07-11.md)です。fail-closed decision chain計画とbias guard warning semantics計画も、主計画へ至る履歴として扱います。

## 目的

Repoの概要だけを知る第三者が、Crypto Perp no-cash検証で何を行い、何が確認され、なぜPaper Observation計画へ進めないのかを、コード・artifact・テストに基づいて理解できるcurrent docを維持する。

## Current Artifact State

```text
bias guard         = BLOCKED
guard stop         = BIAS_GUARD_FAILED_sample_sufficient_for_pbo
pbo status         = NOT_ESTIMABLE
pbo computed       = false
candidate pack     = BACKTEST_REJECT
no-cash gate       = NO_CASH_BACKTEST_REJECT
kill report        = KILL_UPSTREAM_GATE_REJECTED
leaderboard        = KILL
human review packet= BLOCKED_BY_BIAS_GUARD
next action        = FIX_REVIEW_PACKET_BLOCKERS
artifact lineage   = PASS
input contract     = strict v2 / 12 inputs
```

default `fold_count=0`でguardがBLOCKEDです。PBO専用証跡producerがないため、`COMPUTED_PASS`文字列だけでもREADYへ進めません。

## Current Economics

| 項目 | 現在値 |
|---|---:|
| events / trades / wins | 30 / 14 / 10 |
| backtest / stress | 3.042366783076564551621614274 / 2.762366783076564551621614274 USD |
| peak concurrent positions | 6 |
| market episodes / wins | 5 / 3 |
| single-position total | -0.4618201695034107750204885438 USD |
| always-long total | 5.816219911337534249441041925 USD |
| score/result correlation | -0.2902937515082110915592253119 |
| short sleeve | 2 losses / -0.4939911498820537167728313263 USD |
| episode bootstrap 95% | -1.9182 to +9.2413 USD |

trade単位の見た目は改善しましたが、5 episode intervalは0を跨ぎます。30件中27件が同一UTC日、ticker eligibleは30ちょうど、50 bps slippageでは負です。aggregate正値だけでedgeを主張しません。

## 制約

- コード、テスト、schema、config、CLI help、current artifactを正本とする。
- Paper Observation、paper order、actual cash、wallet、signing、exchange write、live orderを許可しない。
- 利益証明やライブ準備完了を主張しない。
- 過去の固定pass countを現在値として扱わない。
- 第三者がRepo全体と今回のno-cash laneを混同しない構成にする。
- artifact lineage `PASS`を経済妥当性や将来利益の証明と誤読しない。
- operator labor `0 USD`を運用コストゼロの現実認定と誤読しない。

## 対象ファイル

- `docs/crypto_perp/CURRENT_NO_CASH_HUMAN_REVIEW_EXPLAINER_2026-07-11.md`
- `docs/crypto_perp/HUMAN_REVIEW_FOR_PAPER_OBSERVATION_PLAN_2026-07-09.md`
- `docs/CURRENT_DOCS_INDEX_2026-07-05.md`
- `docs/final-summary.md`
- `docs/plans/CRYPTO_PERP_NO_CASH_THIRD_PARTY_EXPLAINER_2026-07-11.md`

## 実装方針

第三者向け説明書をcurrent evidenceへ更新し、docs indexとfinal summaryから主計画へroutingする。本文では次を分離する。

1. Repo全体とno-cash laneの責任範囲。
2. 現在の判定チェーンと停止理由。
3. PBO status文字列と専用計算証跡の違い。
4. trade countと独立market episodeの違い。
5. aggregate profit、single-position profit、always-long比較の違い。
6. artifact lineageと経済妥当性の違い。
7. Paper/live safety boundary。
8. Git/merge状態。

## Critique反映

追加調査で、当初説明に残っていた次の誤謬リスクを修正対象へ追加した。

- event数とfold数だけでPBOを評価済みと扱う誤り。
- 14 tradesの時間重複を無視し、独立標本数を過大評価する誤り。
- position overlapとgross notionalを無視してprofitを足し上げる誤り。
- selectorをalways-longなどの単純基準と比較しない抜け。
- scoreがresultを順位付けできているか確認しない抜け。
- short sleeveの全敗をaggregate利益で隠す誤り。
- 既存derived rowsを再利用して内容改ざんを通せるinput integrity欠陥。
- packetへ異なるrunのartifactを混ぜられるlineage欠陥。
- operator laborゼロを現実の運用コストゼロと混同する誤り。

## 完了条件

- current docsが上記のREJECT/KILL/BLOCKED chainを一致して示す。
- `pbo_computed=false` / `pbo_evidence_verified=false`と専用PBO producer不在を明記する。
- 30 events / 14 trades / 10 winsと、5 episodes / single-position負 / episode intervalが0を跨ぐ実態を併記する。
- 最低10 episodesに対する不足を`INDEPENDENT_MARKET_EPISODE_SAMPLE_NOT_MET`として明記する。
- always-long比較、負のscore相関、short sleeve全敗を割愛しない。
- selectorの単純基準未達を`SELECTOR_DOES_NOT_BEAT_BEST_STATIC_ACTION`として明記する。
- artifact lineage `PASS`と利益proofを分離する。
- 全paper/cash/wallet/signing/exchange/live flagがfalseであることを示す。
- current docs indexがprofit evidence hardening計画を主計画としてrouteする。
- fail-closed/warning計画をhistoricalとしてrouteする。
- docs checker、CLI catalog checker、diff checkが通る。

## 失敗条件

- 現在のartifactを人間レビュー計画へ進める状態と記載する。
- `INPUT_THRESHOLD_MET`をPBO合格と記載する。
- 30 eventsを独立30局面として扱う。
- 同時保有を無視したaggregate totalだけを利益根拠にする。
- selectorが単純基準を下回る事実やshort sleeveの損失を隠す。
- lineage `PASS`を将来利益、実約定、運用準備の証明へ拡張する。
- safety flagのfalseを省略する。

## 影響範囲

文書ルーティングと説明のみ。コード、schema、依存関係、runtime artifact、外部サービスには影響しません。

## ロールバック方針

この文書更新とcurrent docsの説明差分を戻す。ただし、旧artifact判断はcurrent code/artifactと不一致なので、旧記述へ戻してcurrent proofとして使ってはいけません。

## 未解決事項

- production PBO engineと`COMPUTED_PASS`生成条件。
- position overlapを反映する資本・position limitモデル。
- selector候補のout-of-sample比較設計。
- 最低market episode数、期間分散、regime分散の閾値。
- books / trades / replayまたは同等の執行証拠。
- 非ゼロoperator laborの感応度。

## 破壊的変更の有無

この文書更新自体はなし。参照先のhardening実装は既存artifact semanticと判定挙動を変更するため、専用branch上で継続しています。

## Branch Status

Branch: `ai/human-review-packet-20260709-2200`

ブランチは未コミット差分を含み、merge holdです。commit、push、merge、cherry-pickは実施していません。runtime `data/`と`.ai-work/`はGit差分に含めません。
