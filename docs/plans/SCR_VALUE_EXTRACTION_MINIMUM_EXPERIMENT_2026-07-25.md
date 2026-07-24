<!--
作成日: 2026-07-25_00:56 JST
更新日: 2026-07-25_01:10 JST
-->

# SCR論文の価値抽出判断と最小検証指示

## 結論

`Portfolio Reinforcement Learning with Scenario-Context Rollout`（arXiv:2602.24037v1）を、方式一式として `marketlens-strike` へ導入しない。

また、汎用の `SCR micro evaluator`、多arm shadow tournament基盤、regime embedding基盤も作らない。これらは「小さく試す」という名目でも研究基盤を増やし、利益仮説の検証より実装対象の維持を優先させる可能性が高い。

論文から検証対象として残すのは、次の1仮説だけとする。

> 現在時点に似た過去局面の、action別・費用後結果を使うと、現行selectorおよび過去時点だけで決めるbest static actionより、forward-collected data上の費用後損益を改善できるか。

検証名は `context_action_challenger_v0` とする。これは `tools/experiment_spikes/` 配下の使い捨てspikeであり、`src/`、公開CLI、schema、Candidate Pack、paper/live境界を変更しない。

必要なforward dataが不足している間の推奨判断は**現状維持**である。データ不足を埋めるためにSCR専用collector、daemon、feature storeを作らない。

## 前提修正

直前までの検討には、次の誤りがあった。

1. 「SCRを小分けにする」という方向へ同意した後、複数arm、汎用sidecar、promotion loopまで提案し、別の研究基盤を作る計画へ戻っていた。
2. 現行repoが継続的なリアルタイム検証loopを既に持つように扱った。実際にあるのはpublic RESTからのforward snapshot appendとlocal no-cash評価であり、連続ingestion、実約定、live PnL検証ではない。
3. OOD局面をsmall-bet探索へ回す案を出したが、現在はmark-to-market、liquidation、production executionを証明していないため、損失境界を裏付けられない。
4. 現在の独立episode数、true OOS、portfolio accountingの不足を解消せず、context modelの有効性を論じた。
5. 多数の比較armを置けば客観的になると仮定したが、arm数と調整箇所の増加自体がselection biasと保守コストを増やす。

この計画では、比較対象を3つ、context featureを3つ、アルゴリズムを1つに固定する。

## 判断材料

### 確認済みの事実

- 現行repoはbacktest-first / no-actual-cashのresearch and evidence workspaceであり、live order、wallet、signing、exchange writeを許可していない。正本はcode、tests、schemas、configs、scripts、CLI helpである。
- `strategy-idea-candidates-bitget-source-refresh --append-existing` により、現在時点のpublic ticker snapshotをforward保存できる。これはhistorical bid/ask取得でも、継続実行daemonでもない。
- `crypto-perp-real-market-no-cash-sample --require-ticker-coverage` は、signal cutoff以前に保存されたbid/ask rowを持つfuture eventだけを選べる。
- 2026-07-11更新のcurrent docに記録されたlocal sampleは、30 event、5 episode、ticker-covered eligibleに余裕なしである。これはcontext-conditioned modelの一般化を主張できる量ではない。実装判断時は固定値を信用せず、current artifactを再生成する。
- 現行Candidate Packは各eventについて `CONTINUATION_LONG`、`REVERSAL_SHORT`、`NO_TRADE` の反実仮想rowを持ち、費用前後の算術とartifact lineageをfail-closedで検証する。
- 現行のIssue #41は、canonical hypothesis PnL stream、真のtrain/validation/test、label interval purge/embargo、実strategy streamによるportfolio accountingが未完成であることを明記している。
- 論文の実験対象は米国株・ETFの日次portfolio rebalancingであり、Crypto Perpのfunding、liquidation、24時間市場、板、venue差を直接検証していない。

参照:

- `README.md`
- `docs/CURRENT_STATE.md`
- `docs/crypto_perp/REAL_MARKET_NO_CASH_SAMPLE_V1.md`
- `docs/crypto_perp/BACKTEST_CANDIDATE_PACK_V1.md`
- GitHub Issue #41

### 推論

- SCR一式を今入れると、既存のsample依存、portfolio accounting、true OOSの問題を解決せず、複雑なmodelで覆い隠す可能性が高い。
- 一方、「過去の似た局面によるaction別条件付き平均」に限れば、既存のall-action rowsとforward eventを利用でき、RL、critic、scenario state engineなしで価値を反証できる。
- eventごとの損益をそのまま足すと同時positionと資本制約を無視するため、v0はactionから独立に決めた非重複event subsetだけを評価対象にしなければならない。
- context challengerが取引を避けるだけで成績を作る可能性がある。したがって、損益だけでなくaction flip、abstention、missed winnerを分解しなければならない。

### 仮定

- 目的は論文再現ではなく、同じevent、同じ費用仮定、同じ情報cutoffでの**増分費用後損益**の有無を早く判定することである。
- 初回対象は `BTCUSDT`、5分bar、60分holdingに固定する。
- public forward dataを使うno-cash shadow評価で十分に反証可能であり、実注文は不要である。
- v0のfeature数、`k`、data floorは事前固定し、結果を見て変更しない。

### 未確認事項

- forward ticker appendが、今後も欠損なく必要頻度で運用されるか。
- 100件以上の非重複eventを、十分な日付分散とtimestamp-safe bid/ask付きで確保できるか。
- current selectorのdecisionをartifactから完全再現できるか。
- event-level改善がportfolio-level改善へ残るか。
- public REST proxyと実約定の差が、candidateとbaselineの順位を反転させないか。

これらは推測で埋めない。該当時点でartifactまたはblockerとして確定する。

## 選択肢比較

| 選択肢 | 速度 | 追加保守 | 得られる証拠 | 主な失敗 | 判断 |
|---|---:|---:|---|---|---|
| O0 現状維持 | 最速 | なし | 既存forward sampleとCandidate Pack | 論文由来の改善余地を試さない | data不足時の推奨 |
| O1 SCR一式 | 遅い | 非常に大 | 論文方式の再現結果 | 目的が研究基盤化、Cryptoへの外挿、現行gapの隠蔽 | 却下 |
| O2 汎用micro-experiment基盤 | 中〜遅 | 大 | 多数armの比較 | arm/tuning増加、selection bias、完成条件膨張 | 却下 |
| O3 単一の使い捨てchallenger | 速い | 小 | context条件付けの増分価値 | sample不足、過学習、event-level止まり | 条件付き推奨 |

## 実験契約: `context_action_challenger_v0`

### 仮説

過去にsettle済みの類似局面だけからaction別の費用後平均を計算し、最大のactionを選ぶchallengerは、次の両方をforward evaluationで上回る。

1. `current_selector`: 現行 `signal_rows.jsonl` の `selected_action`
2. `best_static_prior_only`: その時点までにsettle済みの全training eventで、平均費用後結果が最大の固定action

`best_static_prior_only`を上回れなければ、context conditioningを導入する理由はない。

### 比較対象

比較対象は次の3つだけとし、追加armを作らない。

- `current_selector`
- `best_static_prior_only`
- `context_action_challenger_v0`

### feature

featureはsignal cutoff時点で確定する次の3つだけとする。

1. `trailing_return_60m`: 直前60分のclose-to-close return
2. `realized_vol_60m`: 直前60分の5分return標準偏差
3. `spread_bps_at_cutoff`: timestamp-safeなbid/askから計算したspread bps

funding、OI、book depth、text、embedding、cross-asset featureはv0へ追加しない。feature欠損は0埋めせず、そのeventをmachine-readable reason付きで除外する。

### data floor

次は**実験開始の下限**であり、利益証明の基準ではない。

- training候補: 100件以上の非重複matured event
- 日付分散: 14 UTC date以上
- 全eventに3 feature、3 action row、費用仮定、source hashが存在
- 各neighbor候補は `settled_at < current information_cutoff_at`
- evaluationはtraining floor到達後のforward eventだけ
- 結論を出す最低evaluation数: 60件の非重複event、7 UTC date以上

不足時は `COLLECT_MORE_DATA` とし、feature追加、synthetic data、重複window水増しで回避しない。

`100 / 14 / 60 / 7`、`k = 20`、後述の`50% / 80%`は最適値として確認済みの数ではない。結果後の閾値調整を防ぐためのv0事前登録値であり、変更する場合は別experiment IDと新しいforward期間を必要とする。

### event subset

evaluation対象は、actionやoutcomeを見る前にtimestampだけで決める。

1. eventを `entry_at` 昇順に並べる。
2. 最初のeligible eventを採用する。
3. 次は、直前採用eventの `settled_at` より後にentryする最初のeventを採用する。
4. baseline、static、challengerの全てを同じevent setで評価する。

これによりv0はsingle-position相当の比較に限定する。portfolio PnL、margin、liquidation改善は主張しない。

### algorithm

- `k = 20` 固定。
- featureの平均・標準偏差は、そのdecisionより前にsettle済みのtraining eventだけで計算する。
- 標準化後のEuclidean distanceで20近傍を取得する。
- 近傍eventの `CONTINUATION_LONG`、`REVERSAL_SHORT`、`NO_TRADE` それぞれの費用後USD resultを平均する。
- 平均が最大のactionを選ぶ。完全同値の場合だけ `current_selector` を採用する。
- `k`、feature、distance、tie rule、event floorをevaluation結果で変更しない。

### 出力

既定出力候補:

```text
data/research/experiment_spikes/context_action_challenger_v0/
  manifest.json
  decisions.jsonl
  summary.json
  report.md
```

最低限保存する項目:

- input path / SHA-256
- event set / source refs
- information cutoff / entry / settled timestamp
- 3 featureのraw値とpast-only標準化値
- neighbor event IDsとdistance
- action別neighbor mean
- 3 comparatorのactionと費用後結果
- action change reason
- exclusion reason
- deterministic semantic result hash

### 評価指標

- challenger minus current selectorのtotal after-cost USD
- challenger minus best staticのtotal after-cost USD
- UTC-date block bootstrapによるdeltaのp05 / p50 / p95
- action一致・long/short flip・trade-to-no-trade・no-trade-to-trade件数
- `gain_from_action_flip`
- `gain_from_abstention`
- `missed_winner_cost`
- `extra_loss_from_added_trade`
- trade count ratio
- largest loss
- top-1 / top-3 contribution share
- decision計算時間

block bootstrapはUTC date単位、1,000 iteration、seed `20260725`に固定する。

## 判定

このspikeからproduction、Paper Observation、liveへ直接昇格しない。

### `KILL`

60件以上のforward evaluation後、次のいずれかに当たる。

- current selectorとの差のtotal after-cost USDが0以下
- best staticとの差のtotal after-cost USDが0以下
- future outcome、未settle event、cutoff後sourceが1件でも混入
- input / action row / cost assumption / semantic hashを再現できない
- 結果を良くするためfeature、`k`、event setを変更する必要がある

### `INCONCLUSIVE`

- total deltaは両controlに対して正だが、UTC-date block bootstrapのp05が0以下
- top-1 eventが改善額の50%以上を占める
- evaluation dateまたはaction change数が少なく、mechanismを判別できない

この場合は同じ仕様のままforward dataを追加する。parameterを変更しない。

### `RISK_THROTTLE_ONLY`

次を同時に満たす場合、alpha selectorではなくrisk overlay候補としてのみ扱う。

- challengerのtrade countがcurrent selectorの50%未満
- 改善額の80%以上が `gain_from_abstention`

これは無価値ではないが、「contextが方向判断を改善した」とは結論しない。別の採用判断が必要である。

### `CONTINUE_LONGER_SHADOW`

次を全て満たす場合だけ、同一仕様で観測期間を延長する。

- 両controlに対するdeltaのUTC-date block bootstrap p05が0より大きい
- top-1 contribution shareが50%未満
- leakage、lineage、cost、timestamp違反なし
- 実装が後述のcomplexity budget内

このstatusも採用許可ではない。portfolio-level、別期間、別symbolの検証は別決定とする。

## complexity budget

実装を開始する場合も、次を超えた時点で停止して再判断する。

- 1 branch / 1 PR / 1 experiment directory
- `tools/experiment_spikes/context_action_challenger_v0/` とfocused testsだけ
- 新規dependencyなし
- `src/`、`schemas/`、公開CLI、current docs変更なし
- 汎用plugin interface、registry、feature store、scheduler、dashboardなし
- 実装とfocused verificationを2作業日以内で完了できない場合は中止

既存production code変更が必要になった場合、この計画の前提が崩れたものとして止める。

## 重大リスクと停止条件

- **疑似リアルタイムの誤認**: public RESTのforward snapshotは実約定ではない。実注文品質を示す表現は禁止する。
- **依存標本の水増し**: 5分ごとの重複60分windowを独立eventとして数えない。
- **outcome availability leakage**: 類似過去eventでも、current cutoff時点で未settleならneighborに使わない。
- **静的action未達**: best staticを上回らなければ即終了する。
- **保守化による見かけ改善**: abstention寄与とmissed winnerを分解し、risk throttleとalphaを区別する。
- **portfolio外挿**: event-level結果をportfolio、margin、liquidation、live readinessへ外挿しない。
- **scope creep**: feature追加、モデル学習、embedding、RL、複数symbolへ進みたくなった時点で停止する。
- **collector拡張依存**: data floorを満たすため専用daemonやWebSocket基盤が必要なら、このspikeは中止し、collector投資を別件で判断する。

## 次に取る行動

1. 既存のpublic source refreshを `--append-existing` で継続し、raw forward dataを増やす。

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis strategy-idea-candidates-bitget-source-refresh \
  --symbol BTCUSDT \
  --product-type USDT-FUTURES \
  --granularity 5m \
  --limit 200 \
  --out data/strategy_idea_candidates/btc-perp/bitget_public_source \
  --append-existing
```

2. current artifactを再生成し、非重複event数、UTC date数、3 feature coverageを数える。data floor未達なら `COLLECT_MORE_DATA` で終了する。command既定の30 eventではfloor判定が不可能なため、抽出要求は `--target-event-count 200` を明示する。200件は非重複160件を保証する値ではなく、headroomを持たせた抽出要求であり、生成後に非重複件数を別途数える。

```bash
uv run sis crypto-perp-real-market-no-cash-sample \
  --source-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --require-ticker-coverage \
  --ticker-max-staleness-seconds 900 \
  --target-event-count 200 \
  --out data/crypto_perp/real_market_no_cash/latest

uv run sis crypto-perp-backtest-candidate-pack \
  --data-dir data/crypto_perp/real_market_no_cash/latest \
  --out data/crypto_perp/real_market_no_cash/backtest_candidate_pack/latest
```

3. data floorを満たした時点でのみ、上記contractをそのまま実装するchild Issueを1件作る。data floor未達の間はSCR関連コードを追加しない。

## 完了条件

このplanning recordの完了は、SCR導入ではない。次のいずれかがmachine-readableに確定した時点で完了とする。

- `COLLECT_MORE_DATA`
- `KILL`
- `INCONCLUSIVE`
- `RISK_THROTTLE_ONLY`
- `CONTINUE_LONGER_SHADOW`

正の収益、paper/live permission、production adoptionはこの計画の完了条件ではない。
