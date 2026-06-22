<!--
作成日: 2026-06-22_18:06 JST
更新日: 2026-06-22_18:16 JST
-->

# Deferred Work And Entry Criteria

## 結論

この計画の T0-T7 を全部実行しても、未着手の大きい領域はまだ多い。

完了するのは、Strategy Input Feedback、Strategy Case Lite Index、Static Workbench Viewer の case index 表示まで。これは local/offline artifact workflow の整備であり、paper execution、live execution、venue enablement、profit proof、UI productization ではない。

この文書は「次に残るもの」と「着手できる絶対前提条件」を分ける。絶対前提条件を満たしていないものは、実装計画を書くだけでも誤読リスクが高い。

根拠として読む current docs:

- [docs/CURRENT_STATE.md](../../docs/CURRENT_STATE.md)
- [docs/NEXT_DIRECTION_CURRENT.md](../../docs/NEXT_DIRECTION_CURRENT.md)
- [docs/IMPLEMENTED_SURFACES.md](../../docs/IMPLEMENTED_SURFACES.md)
- [docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md](../../docs/REPO_CAPABILITIES_CURRENT_2026-06-16.md)
- [docs/venues/read_only_capability_probe.md](../../docs/venues/read_only_capability_probe.md)
- [docs/venues/bitget_hyperliquid_capability_gate.md](../../docs/venues/bitget_hyperliquid_capability_gate.md)

## 読み方

`entry criteria` は「あると望ましい条件」ではなく、着手前に必ず満たす条件。満たしていない場合は、設計・実装・検証のどこかで false readiness を作りやすい。

`blocked by approval` は、技術的に書けそうでも、承認なしに進めないという意味。

`blocked by evidence` は、コードを書くより先に実データ、生成 artifact、人間判断、または外部入力が必要という意味。

## 追加調査で修正した判断

- `crypto-perp-order-preview` と `crypto-perp-tiny-live-measurement` は CLI に存在する。ただし Crypto Perp 専用で、`tiny-live-measurement` は CLI help 上も mock-first / real network は別承認である。したがって「完全未実装」とは書かず、「標準 operator surface や real-network 実行は未着手」と読む。
- `hyperliquid_perp` は current capability code では `requires_credentials=false` だが、network は disabled。したがって Hyperliquid は「credentialed」と決め打ちせず、public / address-scoped / credentialed のどれかを設計前に分ける。
- `alpaca-smoke` は read-only command として実装済み。未着手なのは command 実装ではなく、credentials ありの fresh successful evidence と、その結果を live readiness と誤読しない運用である。
- `bitget-demo-smoke` は credentials presence を確認できるが、current runbook では network / account read / order submit / fill sync を証明しない。
- Python dependency 追加はこの文書更新には不要。future plan で追加する場合も、既存の `httpx` / `jsonschema` / `pyyaml` / `polars` / `duckdb` 等で足りないことを先に示す。

## 依存関係

計画上の依存関係は次の通り。ここを飛ばすと、実装は進んだように見えても false readiness を作る。

| Lane | 先に必要なもの | 後続候補 | 進めてはいけない条件 |
|---|---|---|---|
| Local artifact lane | この plan の T0-T7 完了と dogfood | D3, D4, D5 | proposal / case index を実 artifact で読んでいない |
| Paper evidence lane | D1 paper bridge validation、D2 normal paper evidence | D15 profit / readiness claim の一部 | smoke pass や same-day rerun を normal evidence として扱う |
| Venue read-only lane | D6 Bitget、D7 Hyperliquid の read-only probe設計 | D8, D9, D10 | credential / endpoint / no-write 境界が曖昧 |
| Venue schema lane | D9 target venue を1つに固定し、cost / fee / funding を paper-only で検証 | D10, D11 | `VenueId` だけ広げる |
| Live measurement lane | D10 preview、D13 write-secret管理、D19 data freshness、D20 operations drill、明示承認 | D11 | mock / preview / read-only を execution proof と読む |
| Production lane | D11 を複数回通し、D13 / D20 / D21 / monitoring / audit が揃う | D12 | T0-T7 完了や paper pass だけで production へ進む |
| UI lane | Static Viewer dogfoodで HTML では解けない痛みが具体化 | D5 | 見た目改善だけで Svelte / server / auth を入れる |
| Optimizer lane | D15 の評価設計と no-auto-apply 境界 | D14 | backtest metric だけで自動改善する |
| Accounting lane | D21 cash reconciliation / fee / funding / statement突合 | D15, D12 | unreconciled PnL を profit proof として扱う |

## Dependency 追加ポリシー

package dependency を追加する前提条件:

- 標準 library と既存 dependency で足りない理由が1文で説明できる。
- 対象 package の Python 3.13 対応、license、maintenance 状態、lockfile 影響を確認している。
- `pyproject.toml` と `uv.lock` の更新、focused tests、`./scripts/check` を同じ task に含める。
- broker / exchange SDK の場合、secret redaction、retry、timeout、rate limit、no-write guard を tests に含める。
- UI dependency の場合、D5 の entry criteria を満たし、`bun` 側の install / lock / CI impact を別 plan にする。
- external API / broker / exchange を扱う plan は、その時点の公式 API docs と sandbox/demo仕様を確認してから task 化する。

現時点で追加しないもの:

- Bitget / Hyperliquid SDK。狭い read-only probe なら、まず既存 `httpx` と signed request helper の可否を評価する。
- Svelte / Vite / Playwright。Static Viewer dogfood の不足がまだ証拠化されていない。
- DB migration package。Case Lite Index で足りる段階では DB registry を作らない。

## D1: Paper Bridge Validation

残ること:

- backtest / strategy review / stage decision から paper observation へ進む bridge を validation する。
- paper smoke、normal paper observation、drift review、learning cycle の接続を、実際の strategy artifact chain で再確認する。

この計画後の状態:

- Strategy Input Feedback proposal と Case Index は作れる。
- それでも paper bridge validation は未着手のまま。

着手の絶対前提条件:

- 対象 strategy を1つに固定する。
- Strategy Input Contract、Strategy Idea、Strategy Authoring YAML、backtest result、backtest pack validation、Strategy Review record、Stage Decision、Paper Smoke Plan が揃っている。
- `PAPER_OBSERVATION_CANDIDATE` を paper execution permission と読まない方針が明文化されている。
- smoke threshold と normal threshold を分ける。
- `strategy-paper-observation-status` で current gap を再確認する。
- paper order を実行する場合は、別途 operator approval と paper-only execution preview がある。

着手不可の条件:

- backtest pass だけを根拠にする。
- normal threshold の不足を smoke pass で代替する。
- same-day rerun で trading days を増やした扱いにする。
- paper bridge を live readiness の証明として扱う。

## D2: Normal Paper Observation Continuation

残ること:

- 新しい trading day を含む通常 paper observation evidence を積む。
- smoke pass とは別に normal threshold の gap を埋める。

この計画後の状態:

- local feedback / index / viewer は整う。
- しかし新しい trading day の外部 evidence は増えない。

着手の絶対前提条件:

- 新しい trading day を含む paper observation evidence がある。
- `strategy-paper-observation-status` の `latest_normal_requirement_gaps` を再実行で確認している。
- 対象 session id、artifact dir、reports dir が明確。
- paper-only であり、live order へ変換しないことが明確。

着手不可の条件:

- 同じ trading day の artifact 再実行だけ。
- smoke session を normal session として数える。
- `normal_thresholds_met=false` のまま live / micro live plan へ進む。

## D3: Strategy Input Contract Direct Apply

残ること:

- Strategy Input Feedback proposal / review を、Strategy Input Contract の実ファイル更新へつなぐ。

この計画後の状態:

- proposal / review artifact は作れる。
- direct apply、auto patch、contract writer はまだない。

着手の絶対前提条件:

- Strategy Input Feedback proposal / review が実 artifact で複数回 dogfood されている。
- approved / rejected / hold の review sample が存在する。
- conflict handling、backup、rollback、diff format、human approval step が仕様化されている。
- 自動適用しない mode と、手動確認後にだけ patch する mode が分かれている。
- source contract の hash mismatch を必ず止める設計になっている。

着手不可の条件:

- review artifact なしで contract を直接編集する。
- stale source contract に patch する。
- proposal を承認済み変更として扱う。
- Strategy Authoring YAML まで同時に自動編集する。

## D4: Strategy Case Full Registry

残ること:

- Strategy Case Lite / Case Index を超えて、検索、merge policy、conflict handling、retention、DB storage を持つ full registry を作る。

この計画後の状態:

- Case Lite Index は再生成可能な派生 artifact として作れる。
- registry、DB、merge workflow は未着手。

着手の絶対前提条件:

- Case Lite Index を実運用で使い、artifact 探索だけでは足りない具体的な痛みが記録されている。
- registry の責務が `index`、`case history`、`review workflow`、`permission gate` のどれかに分解されている。
- merge policy と conflict resolution が決まっている。
- storage を file artifact で続けるか DB にするかの判断理由がある。
- migration / backfill / corruption recovery / schema versioning の方針がある。

着手不可の条件:

- index で足りる段階で DB を導入する。
- latest status を permission gate として扱う。
- case merge で source artifact hash を失う。

## D5: Svelte UI / Server UI / Productized Workbench

残ること:

- Static Workbench Viewer を超えて、検索、フィルタ、操作導線、状態管理を持つ UI を作る。

この計画後の状態:

- Static HTML viewer は case index を見やすくする。
- Svelte UI、server、DB、auth、hidden mutable state はまだない。

着手の絶対前提条件:

- Static Workbench Viewer を dogfood し、HTML では解けない具体的な workflow が3つ以上ある。
- UI が編集するものと、閲覧するだけのものが分かれている。
- source of truth が artifact / schema / CLI のままか、server state へ移すか決まっている。
- auth、local-only、file access、artifact write permission の方針がある。
- Playwright E2E と fixture artifact dataset が用意できる。

着手不可の条件:

- 「見た目を良くする」だけで server UI を始める。
- viewer を source of truth にする。
- permission artifact を UI のボタン表示だけで判断する。

## D6: Credentialed Bitget Read-only Network Probe

残ること:

- Bitget production / demo の credentialed read-only network connectivity を明示 opt-in で確認する。

この計画後の状態:

- Venue capability は fixture-first / local boundary のまま。
- credentialed network readiness は未証明。

着手の絶対前提条件:

- credentialed read-only network probe の別 plan がある。
- demo と production を同じ task にしない。最初は demo read-only network smoke に限定する。
- `BITGET_DEMO_API_KEY`、`BITGET_DEMO_API_SECRET`、`BITGET_DEMO_PASSPHRASE` など必要 credential の種類と保管場所が明確。
- key は withdrawal disabled、IP restriction あり、read-only または demo-only に限定されている。
- credential redaction、log redaction、artifact redaction の tests がある。
- normal CI では network を使わない。
- timeout、rate limit、retry、stop condition が明確。
- `bitget-demo-smoke` の `status=configured` を network pass と読まない。

着手不可の条件:

- tracked file に secret を置く。
- read-only smoke を production trading readiness と読む。
- demo credential を production Bitget futures 対応として扱う。
- CI で暗黙に外部 API を叩く。

## D7: Hyperliquid Read-only Network Probe

残ること:

- direct Hyperliquid perp の read-only network probe を設計・実装する。

この計画後の状態:

- `hyperliquid_perp` は known future venue / schema-disabled のまま。
- Trade[XYZ] proxy と direct Hyperliquid は分離されたまま。

着手の絶対前提条件:

- Trade[XYZ] proxy と direct Hyperliquid の責務分離が plan で明確。
- public endpoint、address-scoped read、credentialed read のどれを扱うか決める。current capability code は `hyperliquid_perp.requires_credentials=false` なので、credentialed と決め打ちしない。
- read-only の account / open order / fill query だけに限定する。
- secret redaction と no-write guard の tests がある。
- address-scoped read の場合、public address は secret ではなくても privacy-sensitive として扱い、tracked docs や sample artifact に固定しない。
- `hyperliquid_perp` を current `VenueId` に入れないまま probe するか、schema widening と同時にやるかを決めている。

着手不可の条件:

- Trade[XYZ] を generic Hyperliquid として扱う。
- credentialed read を live permission と読む。
- schema widening と network probe を1つの曖昧な作業に混ぜる。

## D8: Bitget Demo Order Lifecycle

残ること:

- demo 環境で order submit / cancel / close / reconciliation の lifecycle を確認する。

この計画後の状態:

- `bitget_demo` は demo/local fixture surface のまま。
- demo order lifecycle completion は未証明。

着手の絶対前提条件:

- Bitget demo read-only smoke が通っている。
- demo-only credential と demo-only account が確認済み。
- production endpoint へ絶対に向かわない guard がある。
- max notional、max open positions、cancel / close / reconcile の stop condition が決まっている。
- order idempotency、client id、query-before-resubmit、flat reconciliation が fixture と demo で検証できる。
- failed submit / partial fill / cancel rejected / close rejected の handling plan がある。

着手不可の条件:

- production credential を使う。
- read-only smoke なしに submit path を作る。
- demo success を production readiness と扱う。

## D9: Production Venue Schema Widening

残ること:

- `bitget_futures` または `hyperliquid_perp` を Strategy Lab / execution venue schema に正式追加する。

この計画後の状態:

- current `VenueId` は `trade_xyz` と `bitget_demo` のまま。
- future venues は catalog-only / disabled のまま。

着手の絶対前提条件:

- target venue を1つに絞る。
- `src/sis/venues/ids.py`、Strategy Lab Pydantic models、`strategy_signal`、`trade_candidate`、`paper_intent_preview`、`evaluation_plan.mls.v1` の schema 更新範囲が明確。
- fee、funding、lot size、min notional、symbol mapping、session handling、cost model が paper-only で検証できる。
- venue capability tests と schema tests が先に書ける。
- paper execution を有効化するか、schema-only widening に止めるかを決めている。

着手不可の条件:

- `VenueId` だけを広げる。
- evaluation plan の target venue を放置する。
- schema widening と live enablement を同時に行う。
- cost / fee / funding 未定のまま paper readiness を主張する。

## D10: Live Order Preview Formal Command Surface

残ること:

- live order を出さない正式な order preview / candidate generation command を、標準 operator surface として作るか判断する。

この計画後の状態:

- Crypto Perp 側には `crypto-perp-order-preview` がある。
- しかしこれは Crypto Perp 専用であり、venue-neutral / standard operator の正式 live order preview surface ではない。

着手の絶対前提条件:

- 対象を Crypto Perp 専用 preview の改善にするのか、venue-neutral standard preview にするのかを先に決める。
- preview が live order ではないことを schema / CLI stdout / docs で固定する。
- input artifact、risk limit、account state read、venue id、client id、idempotency、query-before-resubmit の設計がある。
- output が submit-ready ではなく human-review preview で止まる。
- credentialed read-only state が必要な場合、その prerequisite を満たしている。

着手不可の条件:

- preview output をそのまま submit payload として使える形にする。
- wallet / signing / exchange write と同じ task にする。
- preview pass を order permission と読む。

## D11: Tiny Live Measurement / Micro Live Execution

残ること:

- 実ネットワークで 5-25 USD 程度の tiny live measurement を実行し、実約定・close・flat reconciliation を測る。

この計画後の状態:

- Micro Live Plan / Live Observation / Scale Decision artifact は存在する。
- `crypto-perp-tiny-live-measurement` は存在するが、CLI help 上は mock mode のみが実装済みで、real network は別承認が必要。
- 実 tiny live execution は未実行。

着手の絶対前提条件:

- D10 の preview と D13 の write-secret 管理方針が先に揃っている。
- D19 の data freshness / venue quality gate と D20 の operations drill が先に揃っている。
- 対象 venue の read-only account snapshot / open order / position probe が実行前に通っている。
- separate explicit approval がある。
- `SIS_ENABLE_TINY_LIVE_MEASUREMENT=1`、`--confirm-live`、confirmation phrase が揃っている。
- isolated margin account を使う。
- withdrawal disabled API key を使う。
- IP restriction がある。
- max notional 25 USD 以下。
- max open positions 1。
- 開始前に existing position / open order がない。
- reduce-only close path がある。
- flat reconciliation を必ず実施する。
- kill switch と operator stop procedure が書かれている。
- preview、read-only account snapshot、risk limit、monitoring plan、rollback plan が揃っている。

着手不可の条件:

- approval なし。
- production account の通常資金で試す。
- existing position / open order がある。
- close / reconcile の検証なし。
- mock M09 を実測済みとして扱う。

## D12: Production Live Trading / Automatic Trading Daemon

残ること:

- production live trading と自動売買 daemon。

この計画後の状態:

- まったく着手しない。
- 現行 docs でも production live trading ready ではない。

着手の絶対前提条件:

- 複数回の tiny live measurement と scale decision が損失・fill・cancel・reconciliation の観点で合格している。
- risk governance、position limits、daily loss limits、emergency stop、audit log、monitoring、alerting が実装済み。
- wallet / signing / exchange write credential の管理方針が別途承認済み。
- legal / tax / operational risk を user が明示的に受け入れている。
- daemon failure mode と recovery test がある。

着手不可の条件:

- 現行 plan の T0-T7 完了だけ。
- paper pass だけ。
- backtest / tournament だけ。
- read-only probe だけ。

## D13: Wallet / Signing / Exchange Write Integration

残ること:

- real wallet secret、signing、exchange write integration。

この計画後の状態:

- 完全に対象外。
- 現行 operator path では許可しない。

着手の絶対前提条件:

- secret storage、rotation、redaction、access control が決まっている。
- key scope、IP restriction、withdrawal disabled、least privilege が証明できる。
- no-secret-in-artifact の tests がある。
- submit / cancel / close / reconcile の integration test plan がある。
- manual approval gate と emergency revoke procedure がある。

着手不可の条件:

- tracked file、logs、runtime artifact に secret が出る可能性がある。
- read-only credential と write credential を混同している。
- cancel / close / flat reconciliation がない。

## D14: Strategy Optimizer / ML / LLM Auto-improvement

残ること:

- model / optimizer / LLM が戦略を自動改善する loop。

この計画後の状態:

- Strategy Model Loop first slice と AI Review support はある。
- optimizer execution、自動採用、Strategy Authoring YAML 自動編集はない。

着手の絶対前提条件:

- optimize 対象の metric、baseline、validation split、cost model、stop condition が明確。
- overfit detection と out-of-sample 評価がある。
- generated proposal は人間レビューで止める。
- auto-apply をしない boundary が schema と tests にある。
- compute cost と runtime limit が決まっている。

着手不可の条件:

- Sharpe / backtest pass だけを目的関数にする。
- Strategy Authoring YAML を自動編集して即採用する。
- LLM 出力を検証なしに strategy truth として扱う。

## D15: Profit / Alpha / Production Readiness Claims

残ること:

- この repo が実際に儲かる、alpha がある、本番運用できる、という主張の証明。

この計画後の状態:

- artifact workflow は進む。
- profit proof は増えない。

着手の絶対前提条件:

- transaction cost、slippage、funding、fees、latency、operator time を含めた評価設計がある。
- out-of-sample、walk-forward、forward paper、actual cash のどれを証拠にするか決めている。
- D21 の cash reconciliation が、少なくとも評価対象期間について成立している。
- loss concentration、drawdown、largest loss、profit concentration、NO_TRADE baseline を見る。
- insufficient data を `INCONCLUSIVE_DATA` として止める運用がある。
- profit claim と implementation readiness を別文書に分ける。

着手不可の条件:

- backtest pass だけ。
- before-cost proxy rows だけ。
- small sample tournament だけ。
- viewer がきれいに見えるだけ。

## D16: Normal CI Network Tests

残ること:

- GitHub Actions / normal CI で external API や credentialed network smoke を走らせる。

この計画後の状態:

- normal CI は local/offline gate のまま。

着手の絶対前提条件:

- network test は opt-in job に分離されている。
- secrets scope、environment protection、redaction、timeout、rate limit がある。
- failure が通常開発の blocking flake にならない設計がある。
- no-write と no-secret-log の tests がある。

着手不可の条件:

- default CI で外部 API を叩く。
- developer fork / PR から secret が読める。
- rate limit failure を app failure と混同する。

## D17: Optional Backtest Framework / Market Replay Expansion

残ること:

- HftBacktest、qstrader、PyBroker、skfolio、Riskfolio-Lib などの追加採用や market replay / impact proof。

この計画後の状態:

- optional framework surface は一部あるが、追加 engine 採用や market impact proof は進まない。

着手の絶対前提条件:

- 現行 backtest engine では解けない具体的な gap がある。
- 採用候補1つに絞り、fixtureで current result と比較できる。
- dependency、license、runtime cost、maintenance cost を確認している。
- live / paper permission と切り離した evaluation-only plan がある。

着手不可の条件:

- 「有名ライブラリだから」で採用する。
- framework adoption と strategy improvement を同じ成功条件にする。
- market replay を market impact proof と言い換える。

## D18: Alpaca / Other External Broker Connectivity

残ること:

- Alpaca credentials ありの fresh API connectivity smoke や、他 broker の external connectivity。

この計画後の状態:

- `alpaca-smoke` command は read-only surface として実装済み。
- ただし credentials ありの fresh successful artifact と、その結果を live readiness と誤読しない運用は未証明。

着手の絶対前提条件:

- credential source、scope、redaction、opt-in flag が明確。
- 対象 command と endpoint が read-only に限定されている。
- market hours / stale data / session calendar の判定方針がある。
- normal CI では実行しない。

着手不可の条件:

- credential なしで fresh pass を主張する。
- stale market data を live connectivity と読む。
- broker connectivity を live trading readiness と扱う。

## D19: Data Freshness / Venue Quality / Time Sync Gate

残ること:

- live measurement や profit claim の前に、データ鮮度、取引時間、venue quality、clock / exchange time、funding / fee / spread の前提を gate 化する。

この計画後の状態:

- Case Index と Viewer は artifact を見やすくする。
- しかし source freshness や venue quality の新しい証拠は増えない。

着手の絶対前提条件:

- 対象 venue と symbol が1つに固定されている。
- market session / funding window / exchange maintenance / stale data 判定が明確。
- latest bars、order book、ticker、funding、fees、spread、min notional、lot size の取得元と hash が残る。
- local clock と exchange timestamp のズレを検出する。
- stale / empty / low confidence を pass と読まない。
- normal CI では external API を叩かない。

着手不可の条件:

- old artifact の再利用だけで fresh と主張する。
- free feed の empty bars を provider failure と短絡する。
- data freshness gate なしに tiny live や profit proof へ進む。

## D20: Operations Drill / Incident Response / Reconciliation

残ること:

- tiny live や production に進む前の、operator drill、kill switch、cancel / close / reconcile、incident response、audit bundle の実運用確認。

この計画後の状態:

- operations / audit / remediation surface は多数ある。
- しかし live measurement で必要な実運用 drill は未完了。

着手の絶対前提条件:

- kill switch、schedule cancel、reduce-only close、flat reconciliation の手順が written runbook と fixture / dry-run で確認されている。
- monitoring owner、monitoring cadence、alert path、manual stop procedure が決まっている。
- open order / position / fill / balance の read-only snapshot を、実行前後で比較できる。
- failed submit、partial fill、cancel reject、close reject、network timeout の対応が書かれている。
- `export-state` / `restore-state` 相当の recovery path を dry-run で確認している。
- `operations-bundle` / audit pack / relevant reports を保存する場所が決まっている。

着手不可の条件:

- emergency close や reconciliation が手順化されていない。
- monitoring owner が曖昧。
- execution artifact はあるが、operator が何を見るかが決まっていない。

## D21: Cash Reconciliation / Accounting / Statement Evidence

残ること:

- actual cash、fees、funding、入出金、残高、実現損益、未実現損益、exchange statement を突合し、profit / loss を運用上読める形にする。

この計画後の状態:

- Crypto Perp や Strategy artifact は actual cash 風の値や tournament report を扱える。
- しかし broker / exchange statement と口座残高まで含む accounting proof は未着手。

着手の絶対前提条件:

- 対象 account、対象 venue、対象期間、対象 currency が1つに固定されている。
- exchange / broker statement、fills、fees、funding、deposits、withdrawals、cash balance を入手できる。
- realized PnL、unrealized PnL、fees、funding、cash movement を分ける。
- raw statement をそのまま tracked git に入れない方針がある。
- 税務・会計判断は repo の自動判定ではなく、人間確認に回す境界がある。

着手不可の条件:

- before-cost proxy rows を actual cash として扱う。
- exchange statement なしに profit proof を作る。
- fees / funding / deposits / withdrawals を損益から分けない。
- tax-ready report と operational PnL report を同じものとして扱う。

## 実務上の優先順位

次に実装へ進むなら、今回の T0-T7 の後にすぐ大きな UI / DB / live へ飛ばない。

現実的な順番:

1. T0-T7 を完了する。
2. 生成した proposal / review / case index / viewer を実 artifact で dogfood する。
3. D1 / D2 の paper bridge と normal paper observation を、外部 evidence がある時だけ進める。
4. D3 / D4 / D5 は、dogfood で不足が見えてから分けて計画する。
5. D6 以降の credential / network / order / live 系は、承認、D19、D20、D13、D21 が揃うまで計画だけでも先走らない。

最初に選ぶなら D1 または D2。理由は、現行主軸が backtest-first / venue-neutral で、local artifact workflow の次に必要なのは live ではなく paper / evidence の再確認だから。
