<!--
作成日: 2026-06-14_18:28 JST
更新日: 2026-06-14_20:29 JST
-->

# Current Backtest Plan And Framework Roles

## 結論

現行の backtest 方針は **自前中核 + 外部 framework は責務別の補助** で固定する。

標準 engine は `strategy_authoring_native` である。`vectorbt`、`bt`、`empyrical-reloaded`、`quantstats` は採用済み optional extra だが、標準 engine を置き換えない。外部 framework は検証速度、比較、portfolio allocation、metrics、report、参考実装のために使う。

`OSS` という呼び方はこの文書では雑に使わない。`vectorbt` と `PyBroker` は `Apache 2.0 with Commons Clause` 系で、通常の permissive OSS と同じ扱いにしない。今後の候補は `OSS / source-available / external platform` に分けて読む。

backtest artifact は alpha、paper observation、live readiness の証明ではない。すべての backtest / framework / report surface は `paper_only`、no live order、no wallet、no signing、no exchange write の境界内で扱う。

この completion scope で実装しないが将来候補として残す項目は [BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md](BACKTEST_NON_GOALS_AND_FUTURE_SCOPE_2026-06-14.md) に分ける。Bitget / Hyperliquid direct schema widening、Coinalyze collector、live / wallet / signing / exchange write、NautilusTrader / HftBacktest / Tardis / PyBroker / Qlib / FinRL / skfolio の dependency adoption、replay-style simulation からの market impact claim、alpha / live readiness claim は、現在のゴールへ混ぜない。

2026-06-14_20:29 JST 時点で、completion artifact として `strategy-backtest-data-availability`、`strategy-backtest-baseline-compare`、`strategy-backtest-no-lookahead-diff`、`strategy-backtest-execution-sim`、`strategy-backtest-assumption-ledger`、`strategy-backtest-trial-ledger` を追加済みである。`strategy-backtest-data-availability` は local parquet の row count、timestamp range、gap / duplicate を実測する。`strategy-backtest-no-lookahead-diff` は spec が渡された場合、未来側 feature rows を一時 parquet で変異させて Strategy Authoring を再実行し、cutoff 以前の signals / executed backtest rows の不変性を検査する。`strategy-backtest-execution-sim` は native metrics から paper-only order intents / fill events を作る。`strategy-backtest-pack` はこれらを標準 chain で生成し、`strategy-backtest-pack-validate` は completion artifact の存在、hash、paper-only / no-live boundary を検査する。

## 追加調査で修正した判断

楽観的な読み替えを避けるため、次をこの文書の上書き判断とする。

| 論点 | 修正後の判断 |
|---|---|
| `Bitget + Hyperliquid + Coinalyze` 前提 | 現行 repo の既定前提ではない。`bitget_futures` と `hyperliquid_perp` は capability-known だが schema-disabled、paper-disabled、network-disabled、live-disabled。Coinalyze も現行実装 surface ではない |
| `bitget_demo` | production Bitget futures ではない。demo/local fixture surface として読む |
| `bt` | 不採用ではない。`bt==1.2.0` は portfolio allocation / rebalance comparison 用 optional extra として採用済み |
| `src/marketlens/...` 案 | この repo では使わない。既存 package は `src/sis/` であり、backtest 実装先は `src/sis/backtest/` |
| NautilusTrader / HftBacktest | 強いが、今すぐ依存採用しない。設計参考または隔離 POC であり、先に data availability ledger と source-hashed artifact が必要 |
| PyBroker | walk-forward / bootstrap / parallel indicator 計算は有用。ただし Commons Clause 付きで、標準依存や標準 engine にはしない |

現実的な結論は、`strategy_authoring_native` を正本にし、外部 framework は「同じ入力を別 surface で照合する補助」に留めることである。

## 追加資料から採用する学び

`資料/0614バックテストについて/資料１a.md` と `資料/0614バックテストについて/資料２.md` は、source of truth ではなく意見資料として読む。採用するのは narrative ではなく、現行 repo の境界に合う実務ルールだけである。

採用する学び:

| 学び | この repo での扱い |
|---|---|
| backtest は採用装置ではなく棄却装置 | report / comparison / pack validation は「勝てる証明」ではなく、落とした理由、弱い bucket、過剰適合リスク、残仮定を残す |
| `available_at_ts` が最重要 | feature / quote / external series / future data ledger では `available_at <= decision_ts` を不変条件にする |
| signal と order を混ぜない | Strategy Authoring は signal / target / candidate を出し、fill / portfolio accounting は backtest 側で別責務にする |
| fill と slippage を二重控除しない | `fill_price` に spread / slippage を含めた場合、PnL から同じ slippage を再控除しない。slippage は attribution metric として別に残す |
| fee / funding の単位を推測しない | 不明 fee は entry block、funding rate は単位 / interval / sign / price basis が不明なら `unknown_or_null` として artifact に残す |
| baseline / negative control が必要 | cash/no-trade、buy-and-hold、単純 momentum、単純 funding carry、random throttle、単純 leverage を比較候補にする |
| trial ledger が必要 | parameter sweep、framework comparison、PyBroker / vectorbt 補助検証は、試した条件と失敗理由を残す。良い結果だけを report に残さない |
| scenario layer が必要 | base / conservative / severe cost stress だけでなく、将来は optimistic / standard / conservative の約定仮定差も artifact 化する |
| capacity / liquidity stress が必要 | turnover、fee drag、slippage drag、fill ratio、partial fill ratio、capacity を採用判断に入れる |
| implementation risk も backtest risk | 同じ入力で native と external framework の差分を説明できない場合、external result を採用根拠にしない |

そのまま採用しない点:

| 資料内の主張 | 修正 |
|---|---|
| このプロジェクトは Bitget / Hyperliquid / MEXC / GRVT 前提 | 現行 repo の venue schema は `trade_xyz` と `bitget_demo` のみ。直接 venue は future scope |
| perp 手数料を片道 0.04% と固定 | hardcode しない。venue cost matrix / config / row-level fee を正にする。不明なら block する |
| NautilusTrader を finalist validation に置く | 今は採用しない。data ledger と自前 artifact が揃った後の隔離 POC |
| Qlib / FinRL を研究基盤候補にする | 今回の主経路では不要。ML / RL platform 移植ではなく、point-in-time / validation 思想だけを参考にする |
| 汎用 `BacktestCore` package を新設する | package root は `src/sis/` のまま。既存 `strategy_authoring_native` / `src/sis/backtest/` 境界へ翻訳する |

追加資料で一番価値があるのは、OSS選定ではなく、**Data Availability Ledger -> source-hashed BacktestCore behavior -> ExecutionSimulator** の順序を再確認できた点である。

## 追加調査でさらに補強する点

2026-06-14_19:25 JST の追加調査では、前回まだ薄かった点を補強した。

| 論点 | 補強後の判断 |
|---|---|
| point-in-time feature | `available_at <= decision_ts` だけでなく、`event_ts`, `exchange_ts`, `ingested_at`, `available_at`, `decision_ts`, `fill_ts` を混同しない。Feast の point-in-time join と NautilusTrader の `ts_event` / `ts_init` は設計参考になる |
| lookahead 検査 | Freqtrade の `lookahead-analysis` は、baseline run と signal 別 run を比較して未来参照を検出する発想が有用。MarketLens Strike では「未来 feature row を変えても過去 decision / executed row が変わらない」差分検査を artifact 化する |
| HftBacktest の限界 | HftBacktest は L2 / latency / queue realism には有用だが、market replay 型なので自分の注文が市場を変える効果は表現しにくい。大きい liquidity-taking order の fill は非現実的になり得る |
| queue position | 多くの crypto venue は Market-By-Price で、正確な自分の queue position は直接分からない。HftBacktest を使う場合も queue model は仮定として ledger に残す |
| CPCV / PBO / DSR / SPA | 多数の parameter / strategy を試す段階では有用。ただし現行 v0 の合格条件にはしない。まず trial count、candidate universe、同一データで試した全履歴を残す |
| dynamic universe / survivorship | 将来 multi-symbol 化するなら universe snapshot、inception / delisting / expiry / halted / shortable を固定する。現行 single fixture では未実装でよいが、将来の抜けにしない |
| Tardis | データ取得 / historical market data provider / Nautilus integration の候補であり、backtest OSS ではない。料金・ライセンス・データ取得条件を確認するまで標準入力にしない |
| Qlib / FinRL | ML / RL 研究 platform として参考にはなるが、現行 Python 3.13 / uv lock / Strategy Authoring 境界に混ぜない。feature pipeline と RL reward design の失敗モードだけ参考にする |

この補強により、外部 framework の扱いはさらに明確になる。`vectorbt` / `PyBroker` は探索補助、`bt` は portfolio comparison、`quantstats` / `empyrical-reloaded` は analytics、`NautilusTrader` / `HftBacktest` は後段 POC、`Freqtrade` は lookahead / bot UX / exchange notes の参考、`skfolio` / PBO 系は将来の validation methodology 参考である。

## いまの標準 Backtest

標準入口は Strategy Authoring の local fixture / YAML flow である。

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-pack --benchmark-series-path docs/strategy_research_lab/examples/external_benchmark_series.csv
uv run sis strategy-backtest-pack-validate
uv run sis strategy-backtest-artifact-summary
```

標準 pack は外部 framework を必須にしない。`strategy-backtest-pack` は単発 Strategy Authoring backtest、5手法 suite、bundle result、adapter spike、external result、portfolio comparison、metric extension、report extension、stress、regime split、rolling stability、benchmark relative、comparison、pack manifest を作る。

標準 completion は `complete_without_locked_external_dependency` である。採用済み optional extra が入っている環境では追加比較が実行され、通常環境で未インストールなら `not_installed_in_current_env` として artifact に残る。これは失敗ではなく、依存を標準環境へ混入させないための境界である。

## 現在できる Backtest 手法

現行の自前 surface でできること:

| Surface | Entry | 役割 |
|---|---|---|
| single Strategy Authoring backtest | `strategy-author-run --through backtest` | YAML 戦略を signal 生成から fixed-horizon backtest metrics まで通す |
| multi-method suite | `strategy-backtest-suite` | `single_window`、`walk_forward`、`purged_walk_forward`、return bootstrap、block bootstrap を同じ suite で実行する |
| acceptance gate | `strategy-backtest-acceptance` | backtest artifact の pass/fail と no-live boundary を固定する |
| comparison | `strategy-backtest-compare` | native metrics、suite、framework result、portfolio、metrics、report、robustness artifact を比較用 artifact に正規化する |
| stress | `strategy-backtest-stress` | executed signal return に追加 cost / slippage bps を掛けた耐性を見る |
| regime split | `strategy-backtest-regime-split` | side、timeframe、exit reason、timestamp bucket などで弱い bucket を見る |
| rolling stability | `strategy-backtest-rolling-stability` | rolling window ごとの return / drawdown の弱さを見る |
| benchmark relative | `strategy-backtest-benchmark-relative` | strategy return と benchmark return の active return / tracking error / information ratio を見る |
| pack validation | `strategy-backtest-pack-validate` | pack manifest、artifact hash、5手法、paper-only境界を検査する |

現行の Strategy Authoring は long / short / hold / close / reduce / add / rebalance signal、fixed horizon exit、stop loss、take profit、trailing stop、partial take profit、entry constraint、time-in-force marker、spread / depth / latency / queue / borrow / tax / turnover / capacity / crowding / fee-edge gate、volatility target、target weight、inverse vol、dollar neutral、beta neutral、group neutral、multi-leg metrics、parameter sweep、era metrics、strategy scorecard などを扱える。

現在できない、または標準 backtest の範囲外に置くこと:

- live order
- wallet / signing / exchange write
- broker queue replay
- full L2 order book event replay
- production slippage calibration
- true live book としての multi-strategy accounting
- arbitrary Python strategy execution
- profitability guarantee

## 採用済み Optional Framework

採用済み optional extra は4つだけである。

| Extra | Package | 役割 | 標準扱い |
|---|---|---|---|
| `vectorbt` | `vectorbt==1.0.0` | 高速 signal runner / vectorized comparison / sweep 補助 | optional。標準 engine ではない |
| `bt` | `bt==1.2.0` | portfolio allocation / rebalance comparison | optional。portfolio比較面 |
| `metrics` | `empyrical-reloaded==0.5.12` | risk / performance metrics normalization | optional。engineではない |
| `reports` | `quantstats==0.0.81` | tear sheet / HTML report | optional。engineではない |

選択実行の入口:

```bash
uv run --extra vectorbt sis strategy-backtest-framework-run --framework vectorbt
uv run --extra bt sis strategy-backtest-framework-run --framework bt
uv run --extra metrics sis strategy-backtest-framework-run --framework metrics
uv run --extra reports sis strategy-backtest-framework-run --framework reports
uv run --extra vectorbt --extra bt --extra metrics --extra reports sis strategy-backtest-framework-run --framework vectorbt --framework bt --framework metrics --framework reports
```

`strategy-backtest-framework-run` の `surface_type` は重要である。4件をすべて「backtest engine」と読まない。

| Framework selector | `surface_type` | 読み方 |
|---|---|---|
| `vectorbt` | `backtest_engine` | signals / quotes から外部 engine result を作る |
| `bt` | `portfolio_backtest_engine` | portfolio allocation / rebalance の比較 |
| `metrics` | `metrics_analytics` | return series の分析 |
| `reports` | `report_analytics` | report / tear sheet 生成 |

## 現行 Repo の Venue / Data 境界

現行 code / schema 上、Strategy Lab と paper preview が受け付ける execution venue は `trade_xyz` と `bitget_demo` だけである。`src/sis/venues/ids.py` の `VenueId` もこの2つに限られる。

`docs/venues/bitget_hyperliquid_capability_gate.md` の判断では、`bitget_futures` と `hyperliquid_perp` は capability-known だが schema-disabled である。つまり、将来の調査対象として記録できても、現行 backtest / paper artifact の正式 venue としては扱わない。

実務上の読み方:

- `trade_xyz`: 実装済み proxy / research / read-only surface。
- `bitget_demo`: demo fixture / paper-only surface。production Bitget futures ではない。
- `bitget_futures`: 将来の直接 Bitget futures venue。現時点では schema / paper / network / live 無効。
- `hyperliquid_perp`: 将来の直接 Hyperliquid perp venue。現時点では schema / paper / network / live 無効。
- `Coinalyze`: OI / funding / liquidation / long-short 系 data provider 候補。現時点では repo 実装 surface ではない。

したがって、「Bitget / Hyperliquid / Coinalyze で検証する」という話は、新しい data / venue scope の候補であり、現行 repo の既定機能として書かない。進めるなら、まず data availability ledger に `candidate_provider` / `schema_disabled_venue` として記録し、schema widening や collector 実装とは分ける。

## 外部 Framework の責務分担

外部 framework は「どれが一番よいか」ではなく、責務で分ける。

| 責務 | 第一候補 | 状態 | 使い方 |
|---|---|---|---|
| 高速 signal / parameter sweep | `vectorbt` | optional extra 採用済み | native result の補助比較、広い候補探索 |
| portfolio allocation / rebalance | `bt` | optional extra 採用済み | bundle / target weight / rebalance 比較 |
| metrics normalization | `empyrical-reloaded` | optional extra 採用済み | Sharpe、drawdown、annual return などの補助 |
| report / tear sheet | `quantstats` | optional extra 採用済み | HTML report、operator-readable report |
| feature / ML風候補検証 | `PyBroker` | 未採用。候補整理のみ | 一時 `uv --with lib-pybroker` で検証補助 |
| schedule-driven equities | `qstrader` | 未採用。明示 smoke 後は isolated runner contract 候補 | local input runner の設計後に再評価 |
| simple OHLC prototype | `backtesting.py` | 未採用 | AGPL review 後の参考候補 |
| event-driven comparison | `backtrader` | 未採用 | GPL / live surface 分離が重い |
| large equity event-driven | `zipline-reloaded` / `zipline-refresh` | 未採用 | 現環境 build failure。別環境 spike 候補 |
| L2 / latency / queue realism | `HftBacktest` | 未採用 | L2/L3板、feed/order latency、queue position が損益を左右する後段で検証 |
| factor analysis | `alphalens-reloaded` | 未採用 | backtest engine ではなく factor research 候補 |
| portfolio report | `pyfolio-reloaded` | 未採用 | report 補助。quantstats後に再評価 |

## PyBroker の判断

`PyBroker` は入れる価値があるが、標準 engine ではない。位置付けは `feature_validation_runner_candidate` が妥当である。

確認済み事実:

- package 名は `lib-pybroker`、import 名は `pybroker`。
- 2026-06-14_18:28 JST の local smoke では `lib-pybroker==1.2.12` を Python 3.13 環境で import できた。
- package metadata の license は `Apache License 2.0 with Commons Clause`、classifier は `License :: Free for non-commercial use`。
- package metadata の `Requires-Python` は空だった。
- 主な依存に `akshare`, `alpaca-py`, `diskcache`, `joblib`, `numba`, `numpy`, `pandas`, `yahooquery`, `yfinance` がある。
- `Strategy.backtest(..., calc_bootstrap=False, disable_parallel=False, train_size=0, ...)` と `Strategy.walkforward(windows, train_size=0.5, calc_bootstrap=False, disable_parallel=False, ...)` の API を確認した。
- local DataFrame 入力だけで最小 `backtest` と `walkforward` は実行できた。

現実的な用途:

- ML風の特徴量候補を粗く検証する。
- walk-forward の別実装として sanity check する。
- bootstrap metrics を候補評価の補助に使う。
- cache / parallel を使った検証速度改善を調べる。
- `vectorbt` で広く拾った候補を別 surface で軽く再確認する。

やらないこと:

- `strategy_authoring_native` の置換。
- `pyproject.toml` / `uv.lock` への即時追加。
- external data fetch を暗黙に使う runner 化。
- Alpaca / Yahoo / AkShare など外部データ取得 surface を backtest 標準に混ぜる。
- PyBroker の bootstrap 結果だけで alpha / paper / live readiness を主張する。

次に PyBroker を進めるなら、まず docs / metadata candidate に留める。その次に local DataFrame input 専用の isolated runner spike を作る。正式 optional extra 化は Commons Clause / non-commercial classifier / transitive dependency / CI load を確認してからである。

## 大型 Platform / 参考実装

現行候補表に入っていなかったが、調査対象としては明記しておく。

| 候補 | 位置付け | 判断 |
|---|---|---|
| `NautilusTrader` | production-grade / event-driven / Rust-native 寄りの大型 trading platform | 強力だが、この repo の optional extra に混ぜる対象ではない。別環境検証または設計参考に留める |
| `LEAN` | QuantConnect の大型 backtesting / live trading engine | Apache-2.0 だが C# core + Python algorithm の別プラットフォーム。repo中核とは混ぜない |
| `Freqtrade` | crypto bot platform with backtesting | bot運用寄りで GPLv3。現 repo の no-live / venue-neutral backtest には参考止まり |
| `HftBacktest` | full order book / latency / queue position 対応の HFT backtesting tool | L2/L3やlatency dataが揃うまで後段保留。先に入れると data infra が未熟なまま実装だけ重くなる |
| `Zipline` | calendar / bundle / blotter / stream 型 backtest の設計参考 | 現環境 build risk があるため依存採用ではなく、calendar / bundle / no-lookahead discipline の参考に留める |

これらは「漏らさない」が「採用しない」。現行 repo の Strategy Authoring artifact、source hash、paper-only boundary、pack validation に直接収めるには重すぎる。

学ぶべき点は次である。

| 参考元 | 学ぶ対象 | repo への翻訳先 |
|---|---|---|
| `NautilusTrader` | event-driven engine boundary、deterministic run、venue / data / execution / matching / funding の分離 | `src/sis/backtest/engine/` と将来の execution simulation contract |
| `HftBacktest` | L2/L3 order book replay、feed/order latency、queue position、partial fill realism | L2 raw data recorder と後段 execution-aware simulation |
| `vectorbt` | 大規模 signal / parameter sweep、結果比較 | optional `vectorbt` runner と comparison artifact |
| `PyBroker` | walk-forward、bootstrap、feature / model validation workflow | feature validation runner candidate |
| `LEAN` | fee / fill / slippage / buying power / settlement などの pluggable reality modeling | 自前 fee / slippage / fill model の責務分離 |
| `Zipline` | calendar、data bundle、stream処理、blotter discipline | data availability ledger、calendar-aware input、no-lookahead validation |
| `Freqtrade` | bot platform と exchange-specific operational notes | 外部 benchmark / dry-run comparison。repo中核には入れない |

backtest framework ではないが、設計参考として分けて読むもの:

| 参考元 | 学ぶ対象 | 判断 |
|---|---|---|
| `Feast` | point-in-time feature retrieval、TTL、feature availability | feature store を入れるのではなく、`available_at` と historical retrieval discipline だけを学ぶ |
| `skfolio` | walk-forward、Combinatorial Purged CV、portfolio model selection | dependency 採用ではなく、将来の validation design 参考 |
| Bailey et al. PBO / CSCV | 多数試行から生じる backtest overfitting | まず trial ledger を作る。PBO 指標は十分な試行履歴が残ってから |
| `Qlib` | ML quant pipeline、data processing / model training / backtesting の分離 | current scope では採用しない。ML platform 移植はしない |
| `FinRL` | RL environment / reward design の参考 | current scope では採用しない。reward / cost / slippage を固める前の RL は危険 |
| `Tardis` | historical market data source / Nautilus integration | data vendor / integration 候補。OSS backtest framework として扱わない |

## Data Availability Ledger を先に作る理由

次の実装で最も壊れにくい順序は、PyBroker runner より先に data availability ledger を作ることだ。

理由は単純で、backtest engine を増やしても、過去データの期間・粒度・欠損・取得制限が不明なら結果は信用できないからである。

ledger の最初の目的は「データを増やすこと」ではなく、「今どの入力で何を検証できるかを嘘なく固定すること」である。既定では外部 API を叩かず、既存 raw / normalized artifact を読む。将来の Bitget / Hyperliquid / Coinalyze は、取得済みデータがない限り `unavailable` または `candidate_only` として記録する。

まず ledger に残すべき最小情報:

- venue / provider
- symbol / instrument
- timeframe / data type
- available start / end
- expected row count / actual row count
- gap count / duplicate count
- source API endpoint
- request limit / response max rows / historical range limit
- raw file path / hash
- normalized file path / hash
- unusable reason
- capture mode: `fixture`, `local_raw`, `local_normalized`, `external_candidate`
- current repo status: `enabled`, `schema_disabled`, `provider_candidate`, `not_implemented`
- no-lookahead guard note
- timezone / calendar assumption
- event timestamp / exchange timestamp / local ingest timestamp / initialization timestamp の区別
- `available_at` / `decision_ts` の関係
- trial / run id
- accepted / rejected reason code
- assumption level: `measured`, `configured`, `assumed`, `unknown`
- universe snapshot id、inception / expiry / delisting / halted status。multi-symbol 化する場合のみ必須

優先 source:

| Source | 確認すべき制約 | 判断 |
|---|---|---|
| current Strategy Authoring fixture | source path / hash、row count、timestamp range、feature / quote alignment | まずここを `enabled` として ledger 化する |
| Trade[XYZ] local historical archive | local raw / normalized path、coverage、gap、duplicate、hash | 既存 surface の可用性を明確化する |
| Bitget historical candles | response max rows、query range、rate limit | future candidate。raw recorder と pagination ledger が無い限り正式評価に使わない |
| Hyperliquid | market order 非対応、historical candle limit、order modify / batchModify / scheduleCancel / expiresAfter | future candidate。ordinary OHLCV backtest だけでは execution-aware 評価に不足 |
| Coinalyze | call limit、intraday retention、古い intraday data の欠落 | future provider candidate。OI / funding / liquidation 系の利用可能期間を ledger 化するまで正本にしない |
| Freqtrade data notes | exchange別の historical data caveat | 外部 bot benchmark の入力制約として読む |
| Freqtrade lookahead-analysis | baseline run と sliced run の差分で lookahead bias を探す発想 | 将来の no-lookahead differential test 参考 |
| HftBacktest data / order fill docs | feed/order latency、queue model、market replay の限界 | 後段 POC の assumption ledger に使う |

この ledger がない段階では、`HftBacktest` や NautilusTrader POC より、raw recorder / gap ledger / source hash を優先する。

最初の実装単位は小さくする。

```text
src/sis/backtest/data_availability.py
schemas/backtest_data_availability_ledger.v1.schema.json
tests/backtest/test_data_availability_ledger.py
```

CLI を作る場合も最初は local artifact 読み取りだけにする。外部 API fetch、credential、network collector、schema widening は別タスクに分ける。

## Hyperliquid Execution-Aware Simulation の境界

Hyperliquid を対象に execution-aware backtest を考えるなら、通常の OHLCV backtest や vectorized runner では足りない。

最低限、次を自前 execution simulator 側で扱う。

- market order が実質的に使えない前提
- cancel -> new を乱発しない modify / batchModify 前提
- partial fill
- cancel 中 fill
- stale `expiresAfter` の扱い
- rate limit 逼迫時の degrade
- unknown order state
- `scheduleCancel` を dead man's switch として扱う
- reduce-only / post-only / time-in-force の venue constraint

これは `vectorbt`, `PyBroker`, `backtesting.py` の責務ではない。NautilusTrader や HftBacktest から設計を学ぶ価値はあるが、MarketLens Strike の artifact / safety boundary へ合わせるには自前 model が必要である。

## 実装順

次の backtest 改善は、小さく進める。

1. 現行 docs を整理する。
   - この文書と `docs/backtest/README.md` で、標準 engine、採用済み optional extra、未採用候補、source-available license risk を読めるようにする。

2. data availability ledger を作る。
   - まず現行 Strategy Authoring fixture と Trade[XYZ] local archive の期間、粒度、欠損、重複、source hash、取得制約を artifact 化する。
   - Bitget / Hyperliquid / Coinalyze は `candidate_provider` または `schema_disabled_venue` として記録し、取得済みデータがない限り有効 coverage と書かない。
   - backtest engine 評価より先に、どの期間を検証に使えるかを固定する。

3. PyBroker を候補 inventory に追加する。
   - `framework_id=pybroker`
   - `distribution=lib-pybroker`
   - `module=pybroker`
   - `adapter_role=feature_validation_runner_candidate`
   - ただし dependency 採用や runner 実装はしない。

4. PyBroker smoke を artifact 化する。
   - `uv --with lib-pybroker` で import / version / license / dependencies / API signature を記録する。
   - Commons Clause / non-commercial classifier を adoption blocker として残す。

5. qstrader isolated runner contract を必要なら設計する。
   - local CSV / parquet input に限定する。
   - `BacktestTradingSession` に必要な universe、alpha model、risk model、data handler、rebalance、fee model の変換責務を明記する。
   - import smoke 成功を runner 完成と読まない。

6. vectorbt の sweep 補助を拡張する。
   - Strategy Authoring artifact から安全に parameter / signal variation を作る。
   - result は既存 `strategy_backtest_external_result.v1` または comparison artifact に収める。

7. report / analytics を operator-readable にする。
   - `empyrical-reloaded` と `quantstats` は engine ではなく analytics / report として見せる。
   - metrics / reports が alpha 証明に読まれないように文言を固定する。

8. negative control / baseline comparison を増やす。
   - cash/no-trade、buy-and-hold、単純 momentum、単純 funding carry、random throttle、単純 leverage を比較する。
   - 高機能な strategy が、単純 baseline や取引削減だけの random throttle に負けるなら棄却する。

9. assumption ledger / reason code を report に出す。
   - `measured`, `configured`, `assumed`, `unknown` を分ける。
   - 採用理由よりも、棄却理由、未確認仮定、データ欠損を先に読める report にする。

10. no-lookahead differential harness を作る。
   - baseline run と、未来側 feature rows を変異させた run を比較する。
   - 過去 decision / fill / metrics が動くなら、lookahead または global aggregation leak として棄却する。
   - 将来は signal rows / quote rows mutation replay にも広げる。

11. 多数試行向け validation を後段に設計する。
   - `CPCV`, `PBO`, `Deflated Sharpe Ratio`, `White Reality Check`, `Hansen SPA` は、trial ledger と candidate universe が揃ってから検討する。
   - 今は metric 名だけを先に入れて採用判定を複雑にしない。

## Stop Conditions

次の場合は進めない。

- 外部 framework が通常 dependency に混入する。
- source path / source hash / dependency source / runner mode を artifact に残せない。
- live order、wallet、signing、exchange write へ接続しそうになる。
- license が repo 利用形態と衝突する。
- Python 3.13 / uv lock / CI が不安定。
- native result と external result の差分を説明できず、report が誤解を生む。
- external framework の便利機能を理由に、現行 Strategy Authoring DSL / lifecycle / pack validation を迂回する。
- `bitget_futures` / `hyperliquid_perp` を、schema widening 無しに artifact の正式 venue として扱う。
- `src/marketlens/` など新 package root を作って既存 `src/sis/` 境界を迂回する。
- `available_at` がない特徴量や外部 benchmark series を正式評価に使う。
- random throttle / simple leverage / cash/no-trade などの単純 baseline に負けた結果を、複雑な narrative で採用扱いにする。
- 試した parameter / framework / feature 候補の失敗履歴を捨てる。
- HftBacktest の market replay 結果を、market impact まで再現した証拠として扱う。
- Tardis を「無料 OSS framework」として扱う。
- Qlib / FinRL / skfolio を、現行 backtest core の dependency として混ぜる。
- CPCV / PBO / DSR などの高度 validation 名を、trial ledger 無しに飾りとして report に出す。

## 抜け・漏れ・誤謬リスク

- PyPI metadata は package author が提供する情報であり、法務判断そのものではない。
- `vectorbt` と `PyBroker` は Commons Clause 付きで、通常の Apache-2.0 単体ではない。
- `PyBroker` は local import と最小実行は通るが、依存が重く、外部 data source package も引く。標準依存に入れると repo の軽さと境界が悪化する可能性がある。
- `qstrader` は MIT signal があり local import も通るが、Python classifier は 3.12 までで、runner contract は未設計である。
- `zipline-reloaded` / `zipline-refresh` の local build failure は現環境の Python headers 不足を含む可能性があり、package自体の不可とは断定しない。
- `NautilusTrader`, `LEAN`, `Freqtrade` は backtest能力を持つが、別プラットフォーム級であり、この repo の optional adapter と同列に扱うと設計が大きくなる。
- `HftBacktest` は L2/L3、latency、queue position が必要な段階では有力だが、raw order book / latency data がない段階では過剰である。
- データ可用性 ledger が無い状態で framework だけ増やすと、検証速度は上がっても判断品質は上がらない。
- `backtesting.py` と `backtrader` は技術参考にはなるが、AGPL / GPL の扱いが重い。
- `empyrical-reloaded`, `quantstats`, `pyfolio-reloaded`, `alphalens-reloaded` は backtest engine ではない。
- 現行 generated artifact は runtime state であり、fresh checkout では再生成が必要である。
- `Bitget + Hyperliquid + Coinalyze` を「現行 repo の対応済み前提」と読むのは誤りである。現行 schema venue は `trade_xyz` と `bitget_demo` のみ。
- `bitget_demo` は production Bitget futures の代替ではない。
- 外部 API docs の rate limit、historical data limit、endpoint behavior は変わり得る。collector / ledger 実装時に必ず再確認する。
- Freqtrade の Hyperliquid notes は外部 bot platform の制約メモであり、MarketLens Strike の直接実装事実ではない。
- NautilusTrader と HftBacktest は execution realism の参考価値が高いが、データが薄い段階で導入しても判断品質は上がらない。
- PyBroker の walk-forward / bootstrap / parallel は魅力的だが、local input only と source hash を強制しないと、外部 data source 依存が混ざる。
- LEAN / Zipline から学ぶべきなのは platform 移植ではなく、reality model、bundle、calendar、reproducibility の責務分離である。
- 追加資料には有用な一般論が多いが、`Bitget / Hyperliquid / MEXC / GRVT` 前提や固定 fee 前提は現行 repo の source of truth ではない。
- `available_at` を artifact に持たずに walk-forward / bootstrap / PyBroker 検証をしても、ML風の結果は未来リークを否定できない。
- Freqtrade の lookahead-analysis は有用な設計参考だが、MarketLens Strike の Strategy Authoring DSL にそのまま移植できるわけではない。
- HftBacktest は queue / latency 仮定を明示できるが、market replay 型の限界により、自分の注文が板や将来 trade を変える影響までは保証しない。
- PBO / CPCV / DSR / SPA は、多数試行の過剰適合に対する高度な検査候補であり、現在の local fixture smoke を「統計的に強い」とする根拠ではない。
- multi-symbol / cross-sectional へ進める場合、dynamic universe と survivorship bias が新しい主リスクになる。現行 single fixture の結果からこのリスクを消せない。

## Sources

Repo:

- `pyproject.toml`
- `src/sis/backtest/`
- `src/sis/venues/ids.py`
- `schemas/strategy_backtest_*.schema.json`
- `docs/backtest/README.md`
- `docs/backtest/CURRENT_BACKTEST_DETAIL_AND_FRAMEWORK_OPTIONS_2026-06-13.md`
- `docs/backtest/OPTIONAL_BACKTEST_FRAMEWORK_ADOPTION_REVIEW_2026-06-13.md`
- `docs/backtest/VECTORBT_LICENSE_DECISION_MEMO_2026-06-13.md`
- `docs/venues/bitget_hyperliquid_capability_gate.md`
- `uv run sis --help`
- `資料/0614バックテストについて/資料１a.md`
- `資料/0614バックテストについて/資料２.md`

External:

- https://pypi.org/project/lib-pybroker/
- https://www.pybroker.com/en/latest/license.html
- https://www.pybroker.com/en/latest/notebooks/6.%20Training%20a%20Model.html
- https://www.pybroker.com/en/latest/reference/pybroker.strategy.html
- https://docs.feast.dev/getting-started/concepts/point-in-time-joins
- https://pypi.org/project/vectorbt/
- https://vectorbt.dev/terms/license/
- https://pypi.org/project/bt/
- https://pypi.org/project/empyrical-reloaded/
- https://pypi.org/project/quantstats/
- https://pypi.org/project/qstrader/
- https://pypi.org/project/backtesting/
- https://pypi.org/project/backtrader/
- https://pypi.org/project/zipline-reloaded/
- https://nautilustrader.io/docs/latest/concepts/backtesting/
- https://nautilustrader.io/docs/latest/concepts/data/
- https://nautilustrader.io/docs/latest/getting_started/installation/
- https://nautilustrader.io/docs/latest/integrations/tardis/
- https://hftbacktest.readthedocs.io/
- https://hftbacktest.readthedocs.io/en/latest/order_fill.html
- https://hftbacktest.readthedocs.io/en/latest/data.html
- https://www.quantconnect.com/docs/v2/lean-engine/getting-started
- https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/key-concepts
- https://raw.githubusercontent.com/QuantConnect/Lean/master/LICENSE
- https://zipline.ml4trading.io/beginner-tutorial.html
- https://zipline.ml4trading.io/bundles.html
- https://www.freqtrade.io/en/stable/backtesting/
- https://www.freqtrade.io/en/stable/lookahead-analysis/
- https://www.freqtrade.io/en/stable/exchanges/
- https://raw.githubusercontent.com/freqtrade/freqtrade/develop/LICENSE
- https://skfolio.org/user_guide/model_selection.html
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf
- https://papers.ssrn.com/sol3/papers.cfm?abstract_id=1343896
- https://github.com/microsoft/qlib
- https://github.com/AI4Finance-Foundation/FinRL
- https://www.bitget.com/api-doc/contract/market/Get-History-Candle-Data
- https://api.coinalyze.net/v1/doc/
- https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint
