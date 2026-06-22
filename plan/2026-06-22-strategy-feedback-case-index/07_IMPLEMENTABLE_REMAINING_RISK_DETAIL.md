<!--
作成日: 2026-06-22_19:21 JST
更新日: 2026-06-22_19:21 JST
-->

# Implementable Remaining Risk Detail

## 結論

今回の T0-T7 は完了しても、「実装できることがすべて終わった」わけではない。

正しい読み方は次の通り。

- 完了したもの: local / offline の Strategy Input Feedback、Strategy Case Index、Static Workbench Viewer case index 表示。
- 残っているもの: 実装可能なものは多い。ただし、多くは dogfood、外部 evidence、credential、network、外部副作用承認、運用設計が揃うまで着手しない方がよい。
- 着手してはいけないもの: live order、wallet、signing、exchange write、production live trading、自動売買 daemon は、現計画の完了だけでは前提を満たさない。

この文書は、残リスクを「実装不能」ではなく「実装前提がまだないもの」として分類するための判断材料である。詳細な D1-D21 の entry criteria は [06_DEFERRED_WORK_AND_ENTRY_CRITERIA.md](06_DEFERRED_WORK_AND_ENTRY_CRITERIA.md) を正とする。

## この文書の目的

目的:

- 「まだ着手しないもの」を曖昧な backlog ではなく、前提条件付きの残リスクとして整理する。
- coder が次計画を書く時に、false readiness を作りやすい領域を先に避けられるようにする。
- 実装できるが今やらないもの、承認が必要なもの、実データが必要なもの、運用設計が必要なものを分ける。

対象外:

- D1-D21 の全 task をここで再設計しない。
- credential、network、paper order、live order、wallet、signing、exchange write をこの文書作成で実行しない。
- profit、alpha、production readiness を主張しない。

## 大分類

| 分類 | 残る代表領域 | 実装可能性 | 今すぐ着手しない理由 |
|---|---|---:|---|
| A. Dogfood 待ち | D3 direct apply、D4 registry、D5 UI | 高い | 今回作った proposal / review / case index / viewer を実 artifact で読んだ痛みがまだ足りない |
| B. 外部 evidence 待ち | D1 paper bridge、D2 normal paper observation | 中から高 | 新しい trading day や paper chain の実 artifact が必要 |
| C. Credential / network 待ち | D6 Bitget、D7 Hyperliquid、D18 Alpaca | 中 | secret 管理、redaction、opt-in、no-write 境界が先に必要 |
| D. Order lifecycle 待ち | D8 demo order、D10 preview、D11 tiny live | 中 | submit / cancel / close / reconcile の失敗時対応と明示承認が必要 |
| E. Schema / venue 拡張待ち | D9 production venue schema widening | 中 | venue を1つに固定し、fee / funding / lot size / cost model を先に検証する必要がある |
| F. Production / live 待ち | D12 production live、D13 wallet / signing / write | 低から中 | 技術実装よりも、権限、運用、事故時停止、監査、法務・税務境界が不足 |
| G. 評価・採算証拠待ち | D14 optimizer、D15 profit claim、D17 replay expansion、D21 accounting | 中 | 評価設計、out-of-sample、cash reconciliation がないと見せかけの改善になる |
| H. 運用 gate 待ち | D16 CI network、D19 freshness、D20 operations drill | 中 | 通常 CI の安定性、外部 API flake、監視、事故対応が未整理 |

## A. Dogfood 待ちの実装可能領域

対象:

- D3 Strategy Input Contract Direct Apply
- D4 Strategy Case Full Registry
- D5 Svelte UI / Server UI / Productized Workbench

実装できること:

- review artifact から手動 patch 用 diff を生成する。
- Case Index を DB registry や search index に発展させる。
- Static Viewer を超えた UI、検索、フィルタ、操作導線を作る。

今すぐやらない理由:

- 今回追加した `strategy-input-feedback-proposal-build`、`strategy-input-feedback-proposal-review`、`strategy-case-index-build`、`strategy-workbench-viewer-build` を実 artifact で十分に dogfood していない。
- direct apply は、便利だが一気に source of truth を書き換える機能になる。
- registry / DB / server UI は、導入すると state と recovery の責務が増える。

着手できる絶対前提:

- proposal / review / case index / viewer を実 artifact で複数回使い、失敗例、保留例、却下例、承認例がある。
- static artifact だけでは解けない具体的な痛みが記録されている。
- direct apply の場合、backup、rollback、diff review、stale source detection、human approval step がある。
- DB / registry の場合、migration、backfill、corruption recovery、schema versioning 方針がある。
- UI の場合、閲覧専用と編集可能操作の境界が決まっている。

誤謬リスク:

- 「便利そう」だけで DB や server UI を入れる。
- proposal を承認済み変更として扱う。
- viewer を source of truth にする。
- UI のボタン表示を permission gate として扱う。

現実的な次手:

1. 実 artifact で proposal / review を 3 件以上作る。
2. approved / rejected / hold / needs_fix の sample を残す。
3. Case Index と Viewer で、探しにくい箇所を具体的にメモする。
4. direct apply、registry、UI のどれが本当に必要かを別計画に分ける。

## B. 外部 evidence 待ちの実装可能領域

対象:

- D1 Paper Bridge Validation
- D2 Normal Paper Observation Continuation

実装できること:

- backtest / review / stage decision / paper smoke plan / observation status を chain として検証する。
- 新しい normal paper observation evidence を読み、status / drift / learning へつなぐ。
- paper bridge の validation report を作る。

今すぐやらない理由:

- 新しい trading day を含む paper observation evidence はコードだけでは作れない。
- smoke threshold と normal threshold を混同すると、paper readiness を過大評価する。
- same-day artifact rerun では `trading_days` の不足を埋められない。

着手できる絶対前提:

- 対象 strategy が1つに固定されている。
- Strategy Input Contract、Strategy Idea、Authoring YAML、backtest result、review record、stage decision、paper smoke plan が揃っている。
- `strategy-paper-observation-status` の current gap を再実行で確認している。
- paper execution を伴う場合は、paper-only preview と operator approval がある。

誤謬リスク:

- `PAPER_OBSERVATION_CANDIDATE` を paper 実行許可と読む。
- smoke pass を normal pass と読む。
- normal threshold が未達のまま micro live や profit claim に進む。

現実的な次手:

1. `strategy-paper-observation-status` を再実行する。
2. 対象 strategy と session id を固定する。
3. 新しい trading day の evidence がある時だけ D2 を進める。
4. bridge validation は report-only に止め、paper / live permission を出さない。

## C. Credential / Network 待ちの実装可能領域

対象:

- D6 Credentialed Bitget Read-only Network Probe
- D7 Hyperliquid Read-only Probe
- D18 Alpaca / Other External Broker Connectivity

実装できること:

- 明示 opt-in の read-only probe を作る。
- credential presence、endpoint reachability、account snapshot、open orders / positions の read-only read を検証する。
- redacted artifact と probe report を出す。

今すぐやらない理由:

- credential と network は、失敗時の副作用、secret leak、rate limit、外部 API flake を伴う。
- normal CI に入れると、外部状態で CI が壊れる。
- read-only success は live readiness ではない。

着手できる絶対前提:

- demo / production / public / address-scoped / credentialed のどれを扱うか決めている。
- credential scope、保管場所、redaction、artifact 出力禁止項目が明確。
- opt-in flag があり、通常実行では外部 API を叩かない。
- timeout、retry、rate limit、no-write guard の tests がある。
- normal CI では実行しない。

誤謬リスク:

- credential なしの stale artifact を fresh connectivity と読む。
- read-only probe pass を order permission と読む。
- demo success を production readiness と読む。
- secret を logs、reports、tracked artifact に出す。

現実的な次手:

1. まず demo-only / read-only / no-write の範囲で設計する。
2. secret redaction test を最初に書く。
3. probe output は readiness ではなく observation として schema 化する。
4. normal CI には入れず、manual opt-in command にする。

## D. Order Lifecycle 待ちの実装可能領域

対象:

- D8 Bitget Demo Order Lifecycle
- D10 Live Order Preview Formal Command Surface
- D11 Tiny Live Measurement / Micro Live Execution

実装できること:

- demo account で submit / cancel / close / reconcile の lifecycle を検証する。
- live order を出さない standard preview command を作る。
- 5-25 USD 程度の tiny live measurement flow を、承認付きで実行可能にする。

今すぐやらない理由:

- order path は demo でも失敗時の処理が複雑で、partial fill、cancel reject、close reject、network timeout、idempotency が必要。
- preview と submit-ready payload を混同すると、review gate が実行許可に見える。
- tiny live は実資金と実約定を伴うため、明示承認なしに進めない。

着手できる絶対前提:

- D6 / D7 の read-only probe が先に成立している。
- D10 preview と D13 secret 管理方針が揃っている。
- D19 data freshness と D20 operations drill が揃っている。
- isolated margin、withdrawal disabled key、IP restriction、max notional、max open positions、no existing position / open order が確認済み。
- reduce-only close と flat reconciliation がある。
- explicit approval、kill switch、rollback plan、monitoring plan がある。

誤謬リスク:

- preview を submit payload として扱う。
- demo lifecycle success を production readiness と読む。
- mock tiny live を real network measurement と読む。
- close / reconcile なしで measurement 完了扱いにする。

現実的な次手:

1. order preview は human-review preview で止める。
2. demo order lifecycle は production endpoint へ向かわない guard を先に置く。
3. tiny live は別承認があるまで実装計画だけでも進めすぎない。

## E. Schema / Venue 拡張待ちの実装可能領域

対象:

- D9 Production Venue Schema Widening

実装できること:

- `bitget_futures` または `hyperliquid_perp` を Strategy Lab / execution venue schema に正式追加する。
- venue capability、symbol mapping、cost model、paper evaluation を整える。

今すぐやらない理由:

- `VenueId` だけ広げると、見た目は対応済みでも fee、funding、lot size、min notional、session、cost model が空になる。
- schema widening と live enablement を同時にやると、どの gate が何を許可したか不明になる。

着手できる絶対前提:

- target venue を1つに固定している。
- fee、funding、lot size、min notional、symbol mapping、session handling、cost model が paper-only で検証済み。
- Strategy Lab models、strategy signal、trade candidate、paper intent preview、evaluation plan への影響範囲が明確。
- schema tests と venue capability tests を先に書ける。

誤謬リスク:

- `catalog known` を `venue enabled` と読む。
- schema widening を paper readiness や live readiness と読む。
- cost / fee / funding 未定のまま backtest result を比較する。

現実的な次手:

1. target venue を1つに絞る。
2. paper-only cost model fixture を作る。
3. venue id 追加より先に capability tests を書く。

## F. Production / Live 待ちの実装可能領域

対象:

- D12 Production Live Trading / Automatic Trading Daemon
- D13 Wallet / Signing / Exchange Write Integration

実装できること:

- exchange write credential 管理、signing、submit / cancel / close / reconcile path を作る。
- production live trading daemon を作る。

今すぐやらない理由:

- 技術的に書けても、事故時停止、権限、監査、復旧、資金管理、法務・税務境界が揃っていない。
- tiny live を複数回通していない状態で production daemon に進むと、失敗時の損失と原因追跡ができない。

着手できる絶対前提:

- D11 tiny live measurement が複数回、fill / cancel / close / reconciliation の観点で合格している。
- secret storage、rotation、redaction、access control が決まっている。
- withdrawal disabled、least privilege、IP restriction が証明済み。
- daily loss limit、position limit、emergency stop、monitoring、alerting、audit log がある。
- manual approval gate と emergency revoke procedure がある。

誤謬リスク:

- read-only credential と write credential を混同する。
- tracked file、logs、runtime artifact に secret を出す。
- paper pass や backtest pass だけで production readiness と読む。
- daemon failure mode を未検証のまま常駐化する。

現実的な次手:

1. 今は着手しない。
2. D11、D13、D19、D20、D21 を先に別々に満たす。
3. production daemon は最後の統合計画にする。

## G. 評価・採算証拠待ちの実装可能領域

対象:

- D14 Strategy Optimizer / ML / LLM Auto-improvement
- D15 Profit / Alpha / Production Readiness Claims
- D17 Optional Backtest Framework / Market Replay Expansion
- D21 Cash Reconciliation / Accounting / Statement Evidence

実装できること:

- optimizer / model loop を拡張する。
- optional backtest framework や market replay を追加する。
- cash、fees、funding、deposits、withdrawals、statements を突合する。
- profit / alpha claim 用の evidence report を作る。

今すぐやらない理由:

- 評価設計なしの optimizer は overfit を増やす。
- before-cost proxy rows は actual cash ではない。
- broker / exchange statement なしの profit report は運用上の損益証拠にならない。
- framework 追加は、現行 engine で解けない具体的 gap がないと保守負債になる。

着手できる絶対前提:

- metric、baseline、validation split、cost model、stop condition が明確。
- transaction cost、slippage、funding、fees、latency、operator time を含む。
- out-of-sample、walk-forward、forward paper、actual cash のどれを証拠にするか決めている。
- account、venue、期間、currency が固定されている。
- raw statement を tracked git に入れない方針がある。

誤謬リスク:

- Sharpe や backtest pass だけを目的関数にする。
- LLM 出力を検証なしに strategy truth とする。
- NO_TRADE baseline を見ずに勝ち筋を主張する。
- fees / funding / deposits / withdrawals を損益から分けない。

現実的な次手:

1. optimizer より先に evaluation design を書く。
2. cash reconciliation の source と保存境界を決める。
3. optional framework は1つに絞り、既存 result と fixture 比較できる時だけ採用する。

## H. 運用 Gate 待ちの実装可能領域

対象:

- D16 Normal CI Network Tests
- D19 Data Freshness / Venue Quality / Time Sync Gate
- D20 Operations Drill / Incident Response / Reconciliation

実装できること:

- opt-in network CI job を作る。
- data freshness、venue quality、clock skew、funding / fee / spread gate を作る。
- operations drill、kill switch、cancel / close / reconcile、incident response、audit bundle を整備する。

今すぐやらない理由:

- default CI で外部 API を叩くと flake と rate limit が通常開発を止める。
- stale / empty / low-confidence data を pass と読むと、live や profit proof の前提が崩れる。
- operations drill なしの live measurement は、失敗時に止められない。

着手できる絶対前提:

- network test は opt-in job に分離されている。
- secrets scope、environment protection、redaction、timeout、rate limit がある。
- 対象 venue と symbol が固定されている。
- latest bars、order book、ticker、funding、fees、spread、min notional、lot size の取得元と hash が残る。
- local clock と exchange timestamp のズレを検出する。
- kill switch、cancel、reduce-only close、flat reconciliation の手順が written runbook と dry-run で確認済み。

誤謬リスク:

- default CI で external API を叩く。
- stale data を fresh と読む。
- read-only probe だけで tiny live へ進む。
- monitoring owner が曖昧なまま実行する。

現実的な次手:

1. data freshness gate を local artifact として先に設計する。
2. operations drill は fixture / dry-run で先に通す。
3. network CI は最後まで optional にする。

## 次計画を作る時の優先順位

推奨順:

1. 今回の T0-T7 artifact を dogfood する。
2. D1 または D2 を、外部 evidence がある時だけ別計画にする。
3. dogfood で痛みが出た場合だけ、D3 / D4 / D5 を分けて計画する。
4. D6 / D7 / D18 は secret redaction と opt-in no-write boundary から始める。
5. D8-D13、D19-D21 は承認、運用、freshness、accounting が揃うまで実装計画を狭く保つ。

非推奨順:

- UI から始める。
- DB registry から始める。
- production venue schema widening から始める。
- tiny live / live order から始める。
- optimizer / ML / LLM 自動改善から始める。

## 完了条件

この文書は次を満たせば十分:

- T0-T7 完了後も残る実装可能領域を、dogfood、evidence、credential / network、order lifecycle、schema / venue、production / live、評価・採算、運用 gate に分けている。
- それぞれについて、なぜ今すぐ着手しないか、絶対前提、誤謬リスク、現実的な次手を明記している。
- live readiness、paper readiness、venue readiness、profit proof を主張していない。
- 具体的な implementation task は [06_DEFERRED_WORK_AND_ENTRY_CRITERIA.md](06_DEFERRED_WORK_AND_ENTRY_CRITERIA.md) を正として参照している。
