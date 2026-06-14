バックテストについて。

## 1
## 結論

バックテストは、**「過去で勝った物語を作る装置」ではなく、戦略・Alpha・執行ロジックを現実条件で壊すための検査装置**として設計するべきです。

汎用的な定義はこれです。

```txt
Backtest System
= point-in-timeで再現可能なデータ
+ 現実的なコスト・約定・資金制約
+ OOS検証
+ 失敗理由の記録
+ 実運用との差分監視
```

このプロジェクトでは、特に **perp / funding / OI / liquidation / 片道0.04%手数料 / Bitget・Hyperliquid・MEXC・GRVT** を前提にします。
他プロジェクトへ転用する場合も、まず「市場固有のコスト・時刻・約定制約」を定義してからバックテストを作るのが基本です。

---

# 1. バックテストの目的

バックテストの目的は、次を判定することです。

```txt
1. この戦略は未来情報なしで成立するか
2. 手数料・スリッページ・funding等を入れても期待値が残るか
3. OOSでも崩れないか
4. 単純なベースラインより良いか
5. 実運用に近い約定条件でも成立するか
6. なぜ失敗したか記録できるか
```

特にAlphaFactoryでは、バックテストは **Alphaを採用するための道具ではなく、Alphaを棄却するための道具**です。バックテストを大量に試すほど、良い結果だけを選ぶ過剰適合リスクが増えます。Baileyらの “Probability of Backtest Overfitting” は、戦略探索で最良結果を選ぶ行為そのものが過剰適合を生む問題を扱っています。

---

# 2. バックテストの種類

## A. Bar-based backtest

OHLCV足で検証する最も軽い方式です。

```txt
日足 / 4時間足 / 1時間足 / 5分足
↓
特徴量
↓
シグナル
↓
仮想約定
↓
PnL
```

向いているもの：

```txt
momentum
mean reversion
funding carry
trend filter
volatility strategy
長期・中期Alpha探索
```

弱点：

```txt
約定順序が曖昧
高値・安値到達順が不明
指値約定が甘くなりやすい
板薄銘柄のslippageを過小評価しやすい
```

v0ではこれでよいですが、最終判断にはコスト・slippage stressが必要です。

---

## B. Event-driven backtest

市場データ、注文、約定、キャンセル、資金移動などをイベントとして処理します。

```txt
MarketEvent
OrderEvent
AckEvent
FillEvent
FundingEvent
RiskEvent
```

NautilusTraderのバックテストは、`BacktestEngine` がhistorical data streamを処理し、engine / cache / message bus / portfolio / strategies / execution algorithmsなどを含むシステム実装をシミュレートする設計です。低レベルAPIでは複数venue、複数actor、複数execution algorithm、手動設定を扱えます。([NautilusTrader][1])

向いているもの：

```txt
複数venue
partial fill
cancel/replace
funding settlement
latency
live/paperとの整合
```

本格運用に近づくほど、bar-basedからevent-drivenへ寄せるべきです。

---

## C. Order book replay backtest

L1/L2/L3の板データを再生して、発注と約定を検証します。

NautilusTraderはデータ粒度を、L3 order book、L2 order book、L1 quote、trade tick、barの順に整理し、L2/L3を使う場合は対応するorder book deltaが必要で、barやquoteから高粒度のL2/L3を生成できないと明記しています。([NautilusTrader][1])

向いているもの：

```txt
order flow imbalance
liquidity-taking
maker/post-only
partial fill
queue model
薄い板のperp
```

弱点：

```txt
データ取得・保存が重い
venueごとの仕様差が大きい
再構築が難しい
fill modelの仮定が結果に強く効く
```

このプロジェクトでは、v0で入れず、v2以降の現実約定検証で扱うのが現実的です。

---

## D. Portfolio / factor backtest

銘柄群に対して、factor scoreやrankでポートフォリオを組む方式です。

```txt
universe
↓
factor score
↓
rank / weight
↓
rebalance
↓
PnL / IC / turnover
```

Qlibは、data processing、model training、back-testingを含むML pipelineを持ち、alpha seeking、risk modeling、portfolio optimization、order executionまでを対象にすると説明されています。([GitHub][2])

向いているもの：

```txt
株式factor
銘柄選択
rank IC
cross-sectional momentum
ML Alpha研究
```

perp中心のこのプロジェクトでは、Qlibをそのまま本体にするより、研究ワークフローの参考にするのが妥当です。

---

## E. RL environment backtest

PPO/SAC/TD3などのRL agentに環境を与えて学習・評価する方式です。

FinRLは金融RLのOSSで、教育・研究向けに複数DRLアルゴリズムを扱えます。([GitHub][3])
ただし、RL環境では報酬関数、コスト、slippage、funding、実行遅延の入れ方で結果が大きく変わります。RLを使う場合も、売買判断の本体ではなく、allocator / timing / confidence / consensus の補助に使う方が現実的です。

---

# 3. 必須データ契約

バックテストで最初に決めるべきは、戦略ではなく **データ契約** です。

## 最低限の時刻

```txt
event_ts          市場でイベントが発生した時刻
exchange_ts       取引所が付与した時刻
ingested_at_ts    自分のシステムが取得した時刻
available_at_ts   戦略が実際に使えるようになった時刻
decision_ts       Botが判断した時刻
sent_ts           注文を送信した時刻
ack_ts            取引所が受理した時刻
fill_ts           約定した時刻
```

最重要は `available_at_ts` です。
Feastのpoint-in-time joinは、過去の特定時点で利用可能だった特徴量状態を再現する考え方で、entity timestampから過去方向にTTL範囲内で特徴量を結合します。([Feast][4])

## 最低限の市場データ

```txt
OHLCV
trades
best bid / ask
funding_rate
open_interest
liquidations
instrument metadata
fee schedule
mark price
index price
```

perpでは `funding_rate` を **特徴量** と **PnL上の資金移動** の両方で扱います。NautilusTraderのdocsでも、perp fundingは `FundingRateUpdate` の境界に基づいてsettlementされ、positive funding rateではlongがdebit、shortがcreditされると説明されています。([NautilusTrader][1])

---

# 4. コストモデル

コストを入れないバックテストは、基本的に信用しない方がよいです。

## 汎用コスト

```txt
fee
spread
slippage
market impact
borrow cost
tax friction
latency cost
opportunity cost
```

## perp固有コスト

```txt
funding
mark/index乖離
liquidation risk
maintenance margin
leverage cap
contract spec change
```

このプロジェクトでは、perp手数料を **片道0.04%** として評価します。

```txt
片道 0.04% = 4bps
往復 0.08% = 8bps
```

したがって、短期Alphaは少なくとも往復8bpsを超えるgross edgeが必要です。実際には、spread、slippage、funding、失敗約定を入れるため、必要edgeはさらに大きくなります。

最小式はこれです。

```txt
net_edge_bps
= gross_edge_bps
- entry_fee_bps
- exit_fee_bps
- spread_bps
- slippage_bps
- funding_bps
- impact_bps
```

---

# 5. 約定モデル

約定モデルはバックテスト結果を大きく変えます。

## レベル0: Close約定

```txt
signal at close
fill at next close / next open
```

簡単ですが、現実性は低い。

## レベル1: OHLC内約定

```txt
limit / stop が高値安値に触れたら約定
```

高値・安値の到達順が分からないため、楽観的になりやすい。

## レベル2: Bid/Ask約定

```txt
buy market = ask
sell market = bid
spreadを明示
```

v0では最低ここを目指す。

## レベル3: Trade tick約定

```txt
実際の約定価格列で判定
```

短期Alphaの検証に必要。

## レベル4: L2/L3 replay

```txt
order book delta
queue
partial fill
liquidity consumption
latency
```

NautilusTraderのbacktesting loopでは、market data処理、strategy callback、venue command settlingが明確に分かれており、LatencyModelがある場合はvenueのinflight queueに将来timestampでコマンドが置かれます。また、fill modelはhistorical order book / trade dataをimmutableとして扱い、必要ならliquidity consumptionを追跡します。([NautilusTrader][1])

---

# 6. 検証プロトコル

## 基本順序

```txt
1. データ品質検査
2. PIT feature generation
3. in-sample sanity check
4. walk-forward
5. purged / embargoed CV
6. CPCV
7. cost stress
8. baseline comparison
9. shadow / paper
10. micro-live
```

## Walk-forward

時系列順に、学習期間と検証期間をずらして評価します。

```txt
train 2024-01〜2024-06 → test 2024-07
train 2024-02〜2024-07 → test 2024-08
```

金融時系列の基本です。
ただし、単一の歴史経路に依存しやすいという限界があります。

## Purged / embargoed CV

通常のKFoldは、金融ラベルが未来リターンを含む場合にリークしやすいです。skfolioの `CombinatorialPurgedCV` は、通常KFoldと違って複数test foldを組み合わせ、複数test pathを再構成できます。また、data leakage回避のため、test labelと時間的に重なるtraining observationを除くpurgingと、test直後のtraining observationを除くembargoingを持ちます。([skfolio][5])

## Lookahead検査

Freqtradeのlookahead-analysisは、backtestingが全timestampを読み込んだ状態でindicatorを一括計算すると、未来candleを参照してしまう危険があると説明しています。`shift(-10)`、全期間の`.mean()`や`.max()`、rollingなしの集計などは典型的なlookahead bias例です。([Freqtrade][6])

---

# 7. ベースライン比較

バックテストでは、戦略単体の成績だけ見てはいけません。

必ず比較するもの：

```txt
buy and hold
cash / no trade
単純momentum
単純mean reversion
単純vol filter
単純funding carry
random throttle
単純leverage
volatility targeting
既存戦略
```

特に重要なのはこの2つです。

```txt
random throttle
単純leverage
```

理由は、成績改善が「取引を減らしただけ」「リスクを増やしただけ」かもしれないからです。

---

# 8. 評価指標

## 収益系

```txt
gross return
net return
CAGR
average trade return
expected_net_edge_bps
profit factor
payoff ratio
hit rate
```

## リスク系

```txt
volatility
max drawdown
worst 5% period
tail loss
VaR / CVaR
time under water
drawdown duration
```

## 効率系

```txt
Sharpe
Sortino
Calmar
information ratio
return / maxDD
```

## 執行系

```txt
turnover
fee drag
slippage drag
funding drag
fill ratio
partial fill ratio
cancel ratio
latency
capacity
```

## AlphaFactory用

```txt
IC
Rank IC
ICIR
decay half-life
feature stability
regime別成績
existing alpha correlation
novelty score
accepted / rejected reason
```

---

# 9. 合格条件・棄却条件

## 合格条件

```txt
1. cost後net edgeが正
2. OOSで残る
3. baselineより良い
4. random throttleより良い
5. 単純leverageより良い
6. turnover増加を利益で上回る
7. slippage stressで即死しない
8. 既存Alphaとの相関が低い
9. regime別に弱点が説明できる
10. paper / shadowで劣化が許容範囲
```

## 即棄却

```txt
1. feeを入れると消える
2. fundingを入れると消える
3. slippageを少し増やすと消える
4. OOSで符号が反転する
5. 特定期間だけ勝つ
6. パラメータを少し変えると壊れる
7. 仮説と式が対応していない
8. 全期間正規化を使っている
9. available_at_tsがない
10. 説明不能だがバックテストだけ良い
```

---

# 10. よくある誤謬

## A. Lookahead bias

未来情報を使うこと。

例：

```txt
全期間平均でz-score
shift(-1)
rollingではないmean/max/min
当時未公開のfunding/OI/ニュースを使う
```

## B. Survivorship bias

生き残った銘柄だけで検証すること。

## C. Selection bias

大量に試して、良かったものだけ採用すること。

## D. Data snooping

同じデータで何度も調整して、たまたま効く形を見つけること。

## E. Cost omission

手数料・spread・slippage・fundingを抜くこと。

## F. Fill optimism

指値が都合よく約定したことにすること。

## G. Regime overfit

特定の相場だけに合った戦略を一般化すること。

## H. Capacity illusion

小さいロットなら勝てるが、少し増やすとedgeが消えること。

---

# 11. バックテストシステムの標準アーキテクチャ

汎用形はこれです。

```txt
raw_data/
  ↓
data_normalizer
  ↓
point_in_time_store
  ↓
feature_builder
  ↓
signal_generator
  ↓
execution_simulator
  ↓
portfolio_accounting
  ↓
validator
  ↓
reporter
  ↓
accepted/rejected registry
```

## 責務分解

| モジュール                 | 役割                              |
| --------------------- | ------------------------------- |
| `DataIngestor`        | raw data取得                      |
| `DataNormalizer`      | symbol, timestamp, schema統一     |
| `PITStore`            | available_at_ts付き保存             |
| `FeatureBuilder`      | rolling特徴量生成                    |
| `SignalGenerator`     | Alpha signal生成                  |
| `ExecutionSimulator`  | 約定・latency・partial fill         |
| `CostModel`           | fee, spread, slippage, funding  |
| `PortfolioAccounting` | position, cash, margin, PnL     |
| `Validator`           | walk-forward, CPCV, stress      |
| `Reporter`            | metrics, plots, failure reasons |
| `Registry`            | accepted / rejected保存           |

---

# 12. 保存設計

汎用的には、Parquet + DuckDB / Polars が扱いやすいです。Parquetは列指向フォーマットで、効率的な保存・取得を目的としています。([Parquet][7])

## 推奨パーティション

```txt
data/
  raw/
    venue=bitget/
      data_type=ohlcv/
        date=2026-06-14/
          part-000.parquet

  features/
    feature_set=v1/
      horizon=1h/
        date=2026-06-14/
          part-000.parquet

  backtests/
    run_id=...
      config.json
      metrics.json
      trades.parquet
      equity_curve.parquet
      validation_report.json

  registry/
    accepted_alpha.parquet
    rejected_alpha.parquet
```

## 必須バージョン

```txt
data_version
schema_version
feature_version
alpha_version
cost_model_version
simulator_version
validator_version
run_id
git_commit
```

---

# 13. OSSの使い分け

## NautilusTrader

event-driven、order book、fill model、latency、funding settlementの設計参考として最重要です。v0で全面採用するより、v2以降で現実約定PoCに使うのが現実的です。NautilusTraderはbarからorder bookまで複数粒度を扱い、book_typeとデータ粒度の整合が必要です。([NautilusTrader][1])

## vectorbt

高速なbar-based探索・parameter sweepの思想が参考になります。vectorbtはNumPy/Pandasの上に構築され、Numbaで高速化し、大量のstrategy instanceを高速にテストする方向のツールです。([VectorBT][8])
ただし、partial fill、funding settlement、order book replayの最終判定には向きません。

## Qlib

ML Alpha研究、factor workflow、model training / backtesting / report構造の参考になります。([GitHub][2])
perp固有のfunding、OI、liquidation、venue executionをそのまま扱うには距離があります。

## skfolio

CPCVやportfolio validation部品として有用です。特にAlphaFactoryで大量候補を検証する場合、purging / embargoing / multiple test pathsの考え方は重要です。([skfolio][5])

## Freqtrade

crypto botのCLI、dry-run、lookahead-analysis、運用UXの参考になります。lookahead-analysisの説明は、未来情報バグを実務的に見つける観点で有用です。([Freqtrade][6])

## LEAN

event-driven trading platform設計の参考になります。LEANはPython/C#対応のalgorithmic trading engineです。([GitHub][9])
ただし、このプロジェクトでは重く、perp固有要件に合わせるには遠回りです。

---

# 14. このプロジェクト向けの最小仕様

## v0

```txt
目的:
  perp Alpha候補をPIT・コスト後・OOSで殺す

対象:
  funding_extreme
  crowding_squeeze
  liquidation_shock
  order_flow_imbalance
  momentum_with_carry_penalty
```

## v0の技術構成

```txt
Python 3.13
uv
Polars
DuckDB
Parquet
Pydantic
Typer
Loguru
skfolio
```

## v0の必須機能

```txt
1. available_at_ts付きデータ保存
2. OHLCV / funding / OI / liquidation集計
3. 片道0.04% fee
4. funding PnL
5. slippage stress
6. walk-forward
7. CPCV adapter
8. baseline comparison
9. accepted / rejected registry
10. validation_report
```

## v0でやらないこと

```txt
L2 replay
live trading
RL training
LLM Alpha自動生成
NautilusTrader全面統合
Qlib全面統合
```

---

# 15. 汎用チェックリスト

バックテストシステムを作る前に、必ずこれを埋める。

```txt
市場:
  株 / 先物 / perp / FX / CFD / 競馬 / その他

時間軸:
  日足 / 4h / 1h / 5m / tick / book

データ:
  何がいつ使えたか
  available_at_tsはあるか

コスト:
  fee
  spread
  slippage
  funding / borrow / tax

約定:
  close約定か
  bid/askか
  tickか
  book replayか

検証:
  train/test分離
  walk-forward
  purging
  embargo
  CPCV

比較:
  baseline
  random throttle
  simple leverage

成果物:
  metrics
  trades
  equity curve
  failure reason
  accepted/rejected registry
```

---

# 16. 最終まとめ

バックテストを作るときの原則はこれです。

```txt
1. まずPITデータ契約を決める
2. 次にコストモデルを決める
3. その後に約定モデルを決める
4. その上で戦略を検証する
5. 最後にOOS・CPCV・paperで壊す
```

このプロジェクトでは、最初に作るべきものは高機能なOSS統合ではありません。

```txt
PIT-first Edge Validation Line
```

です。

OSSは以下のように使います。

```txt
NautilusTrader → 現実約定設計の先生
vectorbt → 高速探索の先生
Qlib → ML研究ワークフローの先生
skfolio → 検証プロトコルの部品
Freqtrade → lookahead検査・運用UXの参考
FinRL → RL比較の参考
```

最も重要な姿勢は、**「勝つ結果を探す」ではなく「壊れない結果だけ残す」** です。

18:41:02.(06/14)

[1]: https://nautilustrader.io/docs/latest/concepts/backtesting/ "Backtesting | NautilusTrader"
[2]: https://github.com/microsoft/qlib "GitHub - microsoft/qlib: Qlib is an AI-oriented Quant investment platform that aims to use AI tech to empower Quant Research, from exploring ideas to implementing productions. Qlib supports diverse ML modeling paradigms, including supervised learning, market dynamics modeling, and RL, and is now equipped with https://github.com/microsoft/RD-Agent to automate R&D process. · GitHub"
[3]: https://github.com/AI4Finance-Foundation/FinRL "GitHub - AI4Finance-Foundation/FinRL: FinRL®:  Financial Reinforcement Learning.  · GitHub"
[4]: https://docs.feast.dev/getting-started/concepts/point-in-time-joins "Point-in-time joins | Feast: the Open Source Feature Store"
[5]: https://skfolio.org/generated/skfolio.model_selection.CombinatorialPurgedCV.html "skfolio.model_selection.CombinatorialPurgedCV - skfolio"
[6]: https://www.freqtrade.io/en/stable/lookahead-analysis/ "Lookahead analysis - Freqtrade"
[7]: https://parquet.apache.org/docs/ "Documentation | Parquet"
[8]: https://vectorbt.dev/ "Getting started - VectorBT"
[9]: https://github.com/QuantConnect/Lean "GitHub - QuantConnect/Lean: Lean Algorithmic Trading Engine by QuantConnect (Python, C#) · GitHub"

## 2

結論：**バックテストは「勝てる証明」ではなく、「壊れる戦略を早く落とす検査工程」として設計するのが実務的です。**
どのプロジェクトでも再利用できる基本形は、次です。

```text
raw data保存
  ↓
正規化
  ↓
特徴量・ラベル生成
  ↓
軽量バックテスト
  ↓
保守的な約定・コストモデル
  ↓
event-driven / replay型バックテスト
  ↓
paper trading
  ↓
小額本番
```

最初からNautilusTraderなどの本格エンジンに寄せるより、**まず自前の軽量検証で「シグナルに説明力があるか」を見る**。その後、約定・板・funding・latencyが重要になったら、NautilusTrader、hftbacktest、Tardisなどを使う、という順序が現実的です。

---

# 1. バックテストの目的

バックテストの目的は、主に5つです。

| 目的    | 内容                                         |
| ----- | ------------------------------------------ |
| 仮説検証  | 特徴量・ルールが将来リターンと関係するかを見る                    |
| 期待値確認 | fee、slippage、funding、borrow、税前コスト後でも残るかを見る |
| 破綻検出  | DD、連敗、流動性不足、片寄り銘柄依存を見つける                   |
| 実装検査  | liveと同じロジックで再現できるか確認する                     |
| 承認材料  | 実弾投入前の根拠・監査ログを残す                           |

重要なのは、**バックテスト成績そのものを信じすぎないこと**です。2026年の実装リスクに関する研究でも、同じ論理戦略でもエンジンや取引コスト実装の違いだけで結果がズレる問題が指摘されています。つまり、バックテスト結果は「真実」ではなく「特定のデータ・仮定・エンジンでのシミュレーション結果」です。([arXiv][1])

---

# 2. バックテストの段階設計

## L0：データ監査

最初にやるべきは売買検証ではなく、**データが使えるかの検査**です。

見るべきものはこれです。

```text
- 欠損
- 重複
- timestampずれ
- timezoneずれ
- symbol変更
- 上場廃止
- split / adjustment
- contract rollover
- API取得遅延
- event_ts と recv_ts の乖離
- データ定義変更
```

暗号資産perpでは、OI、funding、liquidation、long/short ratioの定義が取引所・集約サービスごとに違うため、価格OHLCVだけの検証よりデータ監査が重要です。

## L1：特徴量の説明力検証

この段階では売買しません。
特徴量が将来リターンと関係するかだけ見ます。

```text
features at t
  ↓
fwd_ret_5m
fwd_ret_15m
fwd_ret_1h
fwd_volatility
adverse_excursion
favorable_excursion
```

見る指標は以下です。

| 指標                  | 意味                       |
| ------------------- | ------------------------ |
| 分位別forward return   | signalが強いほど将来returnが変わるか |
| Rank IC             | signal順位と将来return順位の相関   |
| long/short別平均return | 上下両方向で効くか                |
| decay               | 5分、15分、1時間でedgeが消える速度    |
| 銘柄別安定性              | 特定銘柄だけで効いていないか           |
| 時間帯別安定性             | 特定時間だけで効いていないか           |
| regime別安定性          | 上昇相場・下落相場・レンジで違うか        |

ここで反応がなければ、約定シミュレーションを精密化しても意味が薄いです。

## L2：軽量バー・バックテスト

次に、1分足・5分足・日足などのbarで売買形式にします。

```text
signal確定
  ↓
次barでentry
  ↓
固定時間exit / 逆signal / stop
  ↓
fee + spread + slippage + funding
  ↓
PnL
```

最初は**保守的なtaker約定**でよいです。
makerで都合よく約定した前提にすると、実弾で崩れやすくなります。

## L3：event-drivenバックテスト

ここから、注文、約定、position、cash、margin、funding、latencyをイベント順で処理します。

NautilusTraderは、historical data streamを`BacktestEngine`で処理し、複数venue、actor、strategy、execution algorithmを扱える設計です。また、order book、quote tick、trade tick、barなど複数粒度のデータを扱い、barからL2/L3のような高粒度データを生成することはできないと明記しています。([NautilusTrader][2])

## L4：market replay / 板バックテスト

板、約定tick、latency、queue positionを使う段階です。
market making、scalping、裁定、短期perp戦略ではここが必要になることがあります。

hftbacktestは、market replay型のHFT/market making向けバックテストで、order latency、feed latency、queue position、L2/L3板再構築などを扱います。一方で、historical market data replayでは自分の注文が市場を変えないため、大きなliquidity-taking orderのfillは非現実的になり得ると公式ドキュメントも警告しています。([HftBacktest][3])

## L5：paper trading / shadow trading

最後に、liveと同じcollector、同じfeature、同じsignalでpaper運用します。

見るべきものはバックテスト成績ではなく、以下です。

```text
- live data lag
- order decision lag
- signal発生頻度
- 約定可能性
- slippage
- funding PnL
- API failure
- 再接続
- 状態復旧
- 証拠金不足
- 銘柄停止・メンテナンス
```

---

# 3. バックテストで必ず持つべき時刻

これは最重要です。

```text
event_ts      : 取引所・データ元でイベントが発生した時刻
source_ts     : データ元payload内の時刻
recv_ts       : 自分のcollectorが受信した時刻
available_ts : 戦略がそのデータを利用可能になった時刻
decision_ts   : 売買判断を出した時刻
order_ts      : 注文を送った時刻
fill_ts       : 約定した時刻
```

バックテストでは、**available_ts以前の情報を使ってはいけません**。
特に外部APIの履歴endpoint、ニュース、決算、清算履歴、Long/Short履歴、funding履歴は、barの時刻ではなく「その情報を実際に取得・利用できた時刻」で管理する必要があります。

Coinalyzeのような集約APIでは、履歴データは昇順で返りますが、1分〜12時間足のintraday履歴は1500〜2000 datapoints程度しか保持されず、古いintradayデータは毎日削除されます。API制限も40 calls/min/API keyで、429時は`Retry-After`が返ります。つまり、バックテストに使うなら取得時刻とraw保存が必須です。([Coinalyze][4])

---

# 4. データ層の設計

## raw layer

最初に保存すべきは正規化済みデータではなく、**生payload**です。

```text
raw_event:
- id
- source
- channel_or_endpoint
- symbol_raw
- recv_ts
- event_ts
- available_ts
- payload_hash
- raw_payload
- parse_status
- error_message
- collector_version
```

rawを保存しないと、あとから定義変更、parser bug、単位ミス、時刻ズレを検証できません。

## normalized layer

rawを戦略で使える共通形式に落とします。

```text
trades:
- venue
- symbol
- trade_id
- event_ts
- recv_ts
- price
- size
- side_raw
- notional
- aggressor_side_normalized
- raw_ref

bars:
- venue
- symbol
- interval
- open_ts
- close_ts
- open
- high
- low
- close
- vwap
- volume
- buy_volume
- sell_volume
- trade_count

book_top:
- venue
- symbol
- event_ts
- bid_px_1..N
- bid_sz_1..N
- ask_px_1..N
- ask_sz_1..N
- checksum_status
- raw_ref

funding:
- venue
- symbol
- event_ts
- funding_rate
- funding_interval_hours
- next_funding_ts
- raw_ref

open_interest:
- venue
- symbol
- event_ts
- oi_raw
- oi_unit
- oi_usd_optional
- raw_ref
```

## feature layer

特徴量は「再計算可能」にします。
feature tableには、元データ参照、計算バージョン、パラメータも残します。

```text
feature_bar:
- symbol
- venue
- interval
- ts
- feature_set_version
- ret_1m
- ret_5m
- volume_z
- taker_imbalance
- spread_bps
- book_imbalance
- oi_delta
- funding_z
- basis_bps
- raw_refs
```

## decision / order / fill layer

バックテストでも本番でも同じ形式にします。

```text
signal:
- ts
- strategy_id
- symbol
- side
- score
- reason
- feature_snapshot_id

order:
- order_id
- ts
- symbol
- side
- order_type
- qty
- limit_price
- reduce_only
- time_in_force
- intended_venue

fill:
- fill_id
- order_id
- ts
- price
- qty
- fee
- liquidity_side
- slippage_estimate
```

---

# 5. 約定モデル

バックテストの品質は、シグナルよりも約定モデルで崩れることがあります。

## 成行/takerモデル

最初はこれでよいです。

```text
long entry:
  next_mid + half_spread + slippage

short entry:
  next_mid - half_spread - slippage
```

保守的には、以下を全部差し引きます。

```text
- taker fee
- half spread
- slippage bps
- funding
- borrow / margin interest
- price impact
- minimum lot / tick size
```

## limit/makerモデル

maker前提にすると、難易度が一気に上がります。

必要な要素はこれです。

```text
- queue position
- partial fill
- cancel latency
- amend latency
- post-only reject
- stale quote
- price crossing
- maker rebate
- adverse selection
```

hftbacktestはqueue position modelを持ちますが、Market-By-Priceしかない多くの暗号資産取引所では、自分の正確なqueue positionは推定になります。公式ドキュメントでも、Market-By-Orderがない場合はqueue positionをmodelingする必要があると説明されています。([HftBacktest][5])

## stop / take profit

barバックテストで特に危険なのがstopとtake profitです。
同一bar内でhighとlowのどちらが先に起きたかはOHLCVだけでは分かりません。

実務では以下のどれかに固定します。

| 方法               | 判断                         |
| ---------------- | -------------------------- |
| 保守的順序            | longならstopを先、shortならstopを先 |
| 次bar約定           | signal確定後、次barでのみ約定        |
| detail timeframe | 5分戦略でも1分足でstop判定           |
| tick replay      | 重要ならtick/板で再現              |

Freqtradeのbacktestingも、candle内の詳細がないため、entryはopen価格、high/low範囲内なら指定価格で全約定、slippageなし、exit signalは次candle openなどの仮定を置くと明記しています。これは便利ですが、短期戦略では楽観的になりやすいです。([Freqtrade][6])

---

# 6. コストモデル

最低限、以下をすべて別列で持つべきです。

```text
gross_pnl
- fee
- spread_cost
- slippage
- funding
- borrow_cost
- liquidation_penalty
- currency_conversion
= net_pnl
```

## 暗号資産perpのfunding

perpではfundingを無視するとバックテストが歪みます。

```text
funding_pnl = position_notional * funding_rate * side_sign
```

ただし、取引所ごとにfunding interval、settlement時刻、rate上限下限、predicted fundingの定義が違います。NautilusTraderは`FundingRateUpdate`からfunding boundaryで`FundingSettlement`を発生させ、positive funding rateならlongが支払い、shortが受け取る設計を持っています。([NautilusTrader][2])

## Fee

Freqtradeはbacktest利益計算にfeeを含め、exchange default feeを使うと説明しています。ただし、実務では実際のVIP tier、maker/taker、rebate、紹介手数料、キャンペーンを別管理したほうがよいです。([Freqtrade][6])

---

# 7. バックテストの主要な誤謬リスク

## 1. look-ahead bias

未来情報を使うバグです。

例：

```text
- bar close前にclose価格を使ってentry
- Coinalyze履歴barをそのbar時刻で即利用
- 決算発表時刻ではなく決算対象日で使う
- stop/take profitの順序を都合よく解釈する
```

vectorbtのドキュメントにも、stop signalの処理例で、シグナルロジックはbarの最後で発生するようにしないとlook-ahead biasに晒されると注意されています。([VectorBT][7])

## 2. survivorship bias

生き残った銘柄だけで検証する問題です。

暗号資産では特に深刻です。

```text
- 上場廃止銘柄を除外
- 取引停止銘柄を除外
- 流動性が枯れた銘柄を除外
- 現在人気の銘柄だけで過去検証
```

対策は、当時のuniverseを保存することです。

```text
instrument_universe:
- date
- symbol
- venue
- listed
- delisted
- tradable
- min_qty
- tick_size
- fee_tier
- status
```

## 3. selection bias / multiple testing

多数のパラメータを試して一番良いものだけ採用すると、ほぼ過剰適合します。

対策：

```text
- 試行回数を記録する
- train/validation/testを分ける
- walk-forwardする
- regime別に見る
- パラメータを単純にする
- 説明不能な最適値を捨てる
```

Deflated Sharpe RatioやProbability of Backtest Overfittingのような考え方は、この「多数試行後の見かけのSharpe」を補正するためのものです。([ウィキペディア][8])

## 4. dynamic universe bias

その時点では選べなかった銘柄を、過去に戻って選んでしまう問題です。

Freqtradeもdynamic pairlistについて、backtestでは現在の市場条件に依存するため過去状態を反映せず、再現性が保証されない場合があると説明しています。([Freqtrade][6])

## 5. implementation risk

同じ戦略でも、engineの実装差で結果がズレます。

```text
- fee計算
- slippage計算
- 同一bar内の処理順序
- order fill順序
- partial fill
- rounding
- timezone
- cash/margin処理
- funding処理
```

このため、重要戦略は**2系統で検算**する価値があります。
たとえば、まず自前Polars/DuckDBで検算し、その後NautilusTraderでevent-driven検算します。

---

# 8. 評価指標

## 最低限見るもの

| 指標                         | 意味            |
| -------------------------- | ------------- |
| net profit                 | コスト後利益        |
| CAGR / annual return       | 年率換算          |
| max drawdown               | 最大DD          |
| profit factor              | 粗利 / 粗損       |
| expectancy per trade       | 1取引あたり期待値     |
| win rate                   | 勝率。ただし単独では弱い  |
| average win / average loss | 勝ち負けの非対称性     |
| turnover                   | 回転率           |
| exposure                   | 市場に晒されていた時間   |
| Sharpe                     | 平均超過収益 / 標準偏差 |
| Sortino                    | 下方偏差で調整       |
| Calmar                     | 年率収益 / 最大DD   |
| hit by symbol              | 銘柄別の偏り        |
| hit by regime              | 相場局面別の偏り      |
| capacity                   | どれくらいの資金まで入るか |

Sharpeだけで判断しないほうがよいです。短期戦略では、tail loss、流動性、手数料、約定不能、取引停止リスクのほうが重要なことがあります。

## 実務で重視する追加指標

```text
- worst day
- worst week
- max consecutive losses
- time to recovery
- average holding time
- PnL by hour of day
- PnL by venue
- PnL by symbol
- PnL by volatility regime
- PnL before/after funding
- slippage sensitivity
- fee sensitivity
- latency sensitivity
```

## 必ずやる感度分析

```text
fee x 1.0 / 1.5 / 2.0
slippage 0 / 2 / 5 / 10 bps
entry delay 0 / 1 / 2 bars
exit delay 0 / 1 bars
volume cap 1% / 5% / 10%
funding included / excluded
top N symbols only / all symbols
```

感度分析で簡単に死ぬ戦略は、本番で死ぬ可能性が高いです。

---

# 9. フレームワーク比較

## まず結論

| 用途                      | 第一候補                    |
| ----------------------- | ----------------------- |
| 独自特徴量の粗検証               | **自前 Polars / DuckDB**  |
| 大量パラメータ探索               | **vectorbt**            |
| OHLCV中心のcrypto bot      | **Freqtrade**           |
| event-driven本格バックテスト    | **NautilusTrader**      |
| 板・market making・queue検証 | **hftbacktest**         |
| 米株・ETF・複数資産・クラウド運用      | **QuantConnect / LEAN** |
| 古典的なPython裁量風検証         | **Backtrader**          |
| 米株日次・ファクター研究            | **Zipline Reloaded**    |
| 暗号資産tick/板履歴            | **Tardis 有料データ**        |

## 自前 Polars / DuckDB

最初に作るべき基盤です。

向いているもの：

```text
- feature検証
- forward return検証
- bar backtest
- cross-sectional ranking
- custom dataのavailable_ts管理
- 低コストな実験
```

向かないもの：

```text
- 複雑なorder state
- partial fill
- maker queue
- 複数venue同時約定
- latency simulation
```

このプロジェクトでは、最初は自前で十分です。

## vectorbt

vectorbtはNumPy、Numba、オプションでRust kernelsを使った高速なpandas拡張・シグナル検証に向いています。`Portfolio.from_signals`ではentry/exit signal、fees、stop loss/take profit、long/short方向などを扱えます。([VectorBT][9])

向いているもの：

```text
- 大量パラメータ探索
- signal matrix検証
- portfolio ranking
- 日足〜分足の探索
```

注意点：

```text
- 約定再現は自分で厳しめに設定する
- 板・queue・latencyには向かない
- look-ahead biasを作りやすい
```

## Freqtrade

Freqtradeはcrypto trading botとして、OHLCVデータを前提にbacktesting、fee計算、結果exportなどを提供します。BitgetやHyperliquidのfutures対応もありますが、backtestは主にcandleベースです。([Freqtrade][6])

向いているもの：

```text
- crypto OHLCV戦略
- dry-run bot運用
- 既存bot形式での検証
- simple indicator strategy
```

注意点：

```text
- candle内の約定仮定が強い
- slippageなし仮定になりやすい
- 独自OI/funding/liquidation featureを厳密に扱うには不向き
```

## NautilusTrader

NautilusTraderはevent-drivenの本格エンジンです。order book、quote tick、trade tick、bar、custom dataを扱え、funding settlementも扱えます。custom dataはPython/Rustで定義でき、Arrow/Parquet、actor/strategyのsubscription flowに乗せられます。([NautilusTrader][2])

向いているもの：

```text
- 本格event-driven backtest
- live/paperと同じstrategy code
- funding込みperp検証
- custom data統合
- Hyperliquid運用
- Tardis履歴の取り込み
```

Hyperliquid adapterはRust実装＋Python bindingsで、REST/WebSocket APIへ直接接続します。([NautilusTrader][10])
Tardis integrationもあり、Tardis CSV、Tardis Machine、HTTP client、Parquet catalog pipelineなどが用意されています。([NautilusTrader][11])

注意点：

```text
- 学習コストが高い
- 最初のfeature検証には重い
- 標準adapterがない取引所は自前変換・adapterが必要
- データ形式・instrument定義・venue設定が重要
```

## hftbacktest

hftbacktestはHFT、market making、板replay向けです。
queue positionやpartial fillを扱えますが、replay型なので市場インパクトは表現しきれません。大きなtaker orderは非現実的なfillになり得ると公式ドキュメントも説明しています。([HftBacktest][3])

向いているもの：

```text
- maker strategy
- scalping
- queue position
- latency sensitivity
- L2/L3 order book replay
```

向かないもの：

```text
- 最初のsignal検証
- 日足・スイング
- 大きなmarket impactがある戦略
```

## QuantConnect / LEAN

QuantConnectのLEANは、複数資産、brokerage model、fee、slippage、fill modelなどのreality modelingを持つ汎用エンジンです。公式ドキュメントでは、slippage、fee、brokerage、settlementなどのreality modelingが体系化されています。([QuantConnect][12])

向いているもの：

```text
- 米株
- ETF
- futures
- options
- multi-asset portfolio
- クラウド/研究一体運用
```

注意点：

```text
- 独自crypto perp venueには制約がある
- データ利用・クラウド前提の設計を確認する必要がある
```

## Backtrader

Backtraderは古典的なPythonバックテストフレームワークで、broker、commission、slippageなどの設定が可能です。公式ドキュメントでもbrokerのslippage設定が説明されています。([Backtrader][13])

向いているもの：

```text
- 日足・分足の古典的戦略
- 裁量ロジック風の検証
- Pythonで軽く試す
```

注意点：

```text
- 開発活発度や現代的データ基盤は要確認
- tick/板/HFT向けではない
```

## Zipline Reloaded

Zipline ReloadedはZipline 3.0 docsとして提供され、pandas、exchange calendars、bcolz、SQLAlchemyなどに依存するPythonバックテスト基盤です。([Zipline][14])

向いているもの：

```text
- 米株日足
- factor research
- pipeline-style equity research
```

注意点：

```text
- crypto perpやtick/板には不向き
- asset masterやcalendar管理が前提
```

## Tardis

Tardisはフレームワークというより、暗号資産の履歴tick/板データ源です。Bitget Futuresは2024-11-08から、Hyperliquidは2024-10-29から履歴データがあり、Bitgetではtrade、books15、books1、ticker、Hyperliquidではtrades、l2Book、bbo、activeAssetCtxなどが確認できます。([Tardis.dev][15])

このプロジェクトで過去検証を急ぐなら、Tardisは最も効果が大きい改善です。無料収集だけだと、まともなtick/板履歴は「今日からしか」貯まりません。

---

# 10. プロジェクト別の推奨構成

## A. このプロジェクト：Bitget + Hyperliquid + Coinalyze

最初はこれです。

```text
自前:
- Polars
- DuckDB
- PyArrow
- Parquet
- raw JSONL.zst

collector:
- pybotters for Bitget/Hyperliquid WS
- httpx for REST/Coinalyze

backtest:
- L1 feature検証
- L2 conservative market-order backtest
- L5 paper

後で:
- Tardis履歴
- NautilusTrader
- hftbacktest
```

このプロジェクトで最初に見るべき仮説は1つです。

```text
Bitget taker imbalance
+ Bitget / Hyperliquid OI delta
+ funding / predicted funding
+ Bitget-Hyperliquid basis
が、5分〜60分後returnに説明力を持つか
```

この仮説が効かないなら、フレームワークを増やす前にfeature設計を見直します。

## B. Crypto OHLCV bot

```text
初期:
- Freqtrade
- vectorbt
- 自前Polars

本格:
- NautilusTrader
```

OHLCVだけならFreqtradeでよいです。
ただし板、funding、liquidation、basis、custom alternative dataを厳密に扱うなら自前かNautilusTrader寄りです。

## C. 株式・ETF・日足/分足

```text
初期:
- vectorbt
- Zipline Reloaded
- Backtrader

本格:
- QuantConnect / LEAN
```

米株・ETFのportfolio運用では、survivorship bias、corporate action、dividend、split、delisting、borrow、short availabilityが重要です。

## D. Futures / options / multi-asset

```text
候補:
- QuantConnect / LEAN
- NautilusTrader
- 自前event-driven
```

期限、roll、margin、settlement、calendar、contract multiplierを正しく扱う必要があります。

## E. HFT / market making

```text
初期:
- 自前データ監査
- hftbacktest

本格:
- hftbacktest + 自前live engine
- NautilusTrader
```

bar backtestはほぼ意味がありません。
L2/L3、latency、queue、partial fill、cancel raceを扱う必要があります。

## F. ML / ranking strategy

```text
初期:
- 自前Polars/DuckDB
- sklearn / lightgbm / xgboost
- vectorbt補助

重要:
- walk-forward
- purged CV
- embargo
- feature availability
- label leakage防止
```

MLではbacktestより前に、**ラベル設計とリーク防止**が重要です。

---

# 11. バックテストシステムの最小ディレクトリ

汎用テンプレートとしては、これで十分です。

```text
backtest-system/
  pyproject.toml
  .env.example

  src/
    config/
      settings.py
      instruments.py
      calendars.py
      fees.py

    data/
      raw_writer.py
      raw_reader.py
      normalizer.py
      schema.py
      quality.py

    features/
      build_bars.py
      build_features.py
      labels.py
      availability.py

    strategy/
      signal.py
      sizing.py
      risk.py

    execution/
      cost_model.py
      fill_model.py
      funding_model.py
      slippage_model.py

    backtest/
      engine_vector.py
      engine_event.py
      portfolio.py
      accounting.py
      report.py

    validation/
      walk_forward.py
      sensitivity.py
      leakage_check.py
      universe_check.py

    adapters/
      nautilus_export.py
      tardis_import.py
      freqtrade_export.py

  data/
    raw/
    normalized/
    features/
    reports/
```

---

# 12. 最初に実装すべき軽量バックテスター

実務上は、まずこの仕様で十分です。

## 入力

```text
feature_bars:
- ts
- symbol
- close
- signal_score
- volatility
- spread_bps
- funding_rate
- volume
```

## ルール

```text
- signalはbar確定後にしか使えない
- entryは次bar
- feeを必ず控除
- slippageを必ず控除
- funding時刻を跨いだらfunding PnLを反映
- 同一bar内の都合よいentry/exitは禁止
- position sizeは出来高capを超えない
```

## 例：保守的な約定価格

```text
long_entry_price  = next_open * (1 + half_spread_bps / 10000 + slippage_bps / 10000)
long_exit_price   = next_open * (1 - half_spread_bps / 10000 - slippage_bps / 10000)

short_entry_price = next_open * (1 - half_spread_bps / 10000 - slippage_bps / 10000)
short_exit_price  = next_open * (1 + half_spread_bps / 10000 + slippage_bps / 10000)
```

## レポート

```text
- gross PnL
- net PnL
- fee
- slippage
- funding
- max DD
- profit factor
- expectancy
- trade count
- turnover
- exposure
- symbol split
- time split
- regime split
- parameter sensitivity
```

---

# 13. 採用判断の基準

バックテスト結果は、以下を満たすまで信用しないほうがよいです。

```text
- raw dataから再現できる
- feature生成が再現できる
- signal生成が再現できる
- 同じcommitで同じ結果になる
- fee/slippage/funding込みで正
- 銘柄別に偏りすぎていない
- 時間帯別に偏りすぎていない
- 期間分割しても大崩れしない
- パラメータを少し変えても死なない
- entry delayを入れても死なない
- slippageを増やしても即死しない
- paper tradingと大きく乖離しない
```

---

# 14. 最終的な実務方針

この資料を他プロジェクトでも使うなら、原則はこれです。

```text
1. いきなり本格フレームワークに入らない
2. raw保存を最初に作る
3. available_tsを必ず持つ
4. feature説明力を先に見る
5. 保守的なコスト・約定で見る
6. 良さそうなものだけevent-drivenへ進める
7. 板・maker戦略だけmarket replayへ進める
8. paper tradingでlive差分を見る
9. 実弾前に必ず感度分析をする
10. バックテストは「採用理由」ではなく「不採用判定装置」として使う
```

このプロジェクトでは、**自前Polars/DuckDB → 必要ならTardis → NautilusTrader** の順が最も現実的です。
他プロジェクトでも、最初の判断軸は同じです。**データ粒度・約定現実性・コスト・時刻管理・再現性**を満たさないバックテストは、見かけの成績が良くても採用材料にしないほうがよいです。

18:40:41.(06/14)

[1]: https://arxiv.org/abs/2603.20319?utm_source=chatgpt.com "Implementation Risk in Portfolio Backtesting: A Previously Unquantified Source of Error"
[2]: https://nautilustrader.io/docs/latest/concepts/backtesting/ "Backtesting | NautilusTrader"
[3]: https://hftbacktest.readthedocs.io/en/latest/ "HftBacktest — hftbacktest"
[4]: https://api.coinalyze.net/v1/doc/ "Coinalyze API documentation. Free crypto data API."
[5]: https://hftbacktest.readthedocs.io/en/latest/order_fill.html "Order Fill — hftbacktest"
[6]: https://www.freqtrade.io/en/stable/backtesting/ "Backtesting - Freqtrade"
[7]: https://vectorbt.dev/api/portfolio/base/ "base - VectorBT"
[8]: https://en.wikipedia.org/wiki/Deflated_Sharpe_ratio?utm_source=chatgpt.com "Deflated Sharpe ratio"
[9]: https://vectorbt.dev/getting-started/features/ "Features - VectorBT"
[10]: https://nautilustrader.io/docs/latest/integrations/hyperliquid/ "Hyperliquid | NautilusTrader"
[11]: https://nautilustrader.io/docs/latest/integrations/tardis/ "Tardis | NautilusTrader"
[12]: https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/key-concepts "Key Concepts - QuantConnect.com"
[13]: https://www.backtrader.com/docu/slippage/slippage/ "Broker - Slippage - Backtrader"
[14]: https://zipline.ml4trading.io/ "Zipline — Zipline 3.0 docs"
[15]: https://docs.tardis.dev/historical-data-details/bitget-futures "Bitget Futures | Tardis.dev Documentation"

## 3

以下は、**MarketLens Strikeだけでなく、他プロジェクトでも使えるバックテスト設計資料**として読めるように整理したものです。
結論から言うと、バックテストシステムは「利益を証明する装置」ではなく、**仮説・データ・約定・コスト・評価を分解し、壊れる条件を見つけるための検査装置**として作るべきです。

---

# 0. 最重要結論

バックテストで最初に作るべきものは、華やかな戦略評価ではありません。

最初に作るべき順番はこれです。

```text
1. データ契約
2. 時刻・利用可能性ルール
3. signal生成
4. order生成
5. fill model
6. cost model
7. portfolio accounting
8. artifact出力
9. no-lookahead test
10. baseline比較
11. walk-forward / stress test
12. paper観測への接続
```

逆に、最初にやってはいけないことはこれです。

```text
- いきなり高性能な戦略を探す
- パラメータ最適化から始める
- 勝率・利益率だけを見る
- close価格で約定した前提にする
- 手数料・slippage・fundingを後回しにする
- live実行とbacktestを混ぜる
- paperで良いからliveへ進む
```

MarketLens Strikeでも、Trade[XYZ] pure backtest v0.1 は「利益を出す戦略」ではなく、まず accounting / no-lookahead / artifact correctness を固定する correctness harness として扱う方針になっています。現Repoでは、Trade[XYZ] pure backtest は Python API surfaceで、public CLIではなく、live order・wallet・signing・exchange writeとは切り離されています。

---

# 1. バックテストとは何か

バックテストとは、過去データ上で戦略を再生して、

```text
このルールは、当時利用可能だった情報だけで判断したら、
どのような注文・約定・損益・リスクになったか
```

を検査する仕組みです。

ただし、バックテストで分かるのは、

```text
過去の特定条件で破綻したか
過去の特定条件では一応動いたか
どの条件で弱いか
どの仮定に依存しているか
```

までです。

分からないものはこれです。

```text
未来でも勝てるか
実運用で同じ約定になるか
API障害時に安全か
流動性が変わっても耐えるか
大きな資金でも同じ結果になるか
```

つまり、バックテストは **証明装置ではなく、反証装置**です。

---

# 2. バックテストの種類

## 2.1 ベクトル型バックテスト

pandas / NumPy / Polars などで、価格列・signal列・position列をまとめて計算する方式です。

向いている用途：

```text
- 大量のパラメータ比較
- 多銘柄の粗い比較
- signalの早期スクリーニング
- IC / rank IC / threshold sweep
- 研究段階の高速検証
```

弱点：

```text
- 注文状態や約定イベントを細かく扱いにくい
- partial fill / cancel race / latencyを表現しにくい
- 同じbar内の順序問題が曖昧になりやすい
```

OSS例では vectorbt がこの方向に強く、pandas/NumPyをNumbaやRustで高速化し、多数の戦略設定・銘柄・期間をまとめて比較する設計です。vectorbt公式は、多数のstrategy configurations・time periods・instrumentsを高速にsweepできることを特徴として説明しています。([VectorBT][1])

---

## 2.2 イベント駆動型バックテスト

時系列イベントを順番に処理します。

```text
MarketDataEvent
SignalEvent
OrderEvent
FillEvent
PositionEvent
RiskEvent
```

のように、実際の運用に近い流れを再現します。

向いている用途：

```text
- order / fill / positionの整合性確認
- multi-timeframe
- intraday
- live実行との整合性
- venue adapter設計
```

弱点：

```text
- 実装が重い
- 遅い
- デバッグが難しい
- artifact設計がないと再現性が落ちる
```

NautilusTraderは、research、deterministic simulation、live executionを単一のevent-driven architectureで扱い、同じexecution semanticsとdeterministic time modelをresearch/liveで共有する設計を掲げています。これは、MarketLens Strikeが将来 Bitget / Hyperliquid 対応を進める際の設計参考になります。([NautilusTrader][2])

---

## 2.3 約定リアリティ重視型バックテスト

注文板、best bid/ask、depth、latency、maker/taker、partial fill、cancel、fundingなどを細かく入れる方式です。

向いている用途：

```text
- crypto perp
- 板が薄い銘柄
- 短期売買
- maker/taker差が重要な戦略
- Hyperliquid / Bitgetのようなvenue実行評価
```

弱点：

```text
- データ量が大きい
- L2/L3データが必要
- 実装ミスが多い
- 取引所仕様依存が強い
```

この方式は、最初から作ると重すぎます。まずは「market-like taker fill」「next-row fill」「fee/slippage/funding v0」程度の小さいモデルから始めるのが実務的です。MarketLens StrikeのTrade[XYZ] pure backtest v0.1も、single-symbol / long-only / market-like taker fill / next-row fill / fixed notional sizing という小さい範囲に絞っています。

---

## 2.4 Portfolio / allocation型バックテスト

複数戦略・複数銘柄・資金配分を検証する方式です。

向いている用途：

```text
- strategy basket
- risk parity
- equal weight
- inverse volatility
- capital allocation
- strategy correlation
```

弱点：

```text
- 約定モデルが粗くなりやすい
- individual tradeの挙動が見えにくい
- 配分最適化が過学習しやすい
```

ここでは、単独戦略の勝ち負けよりも、

```text
複数戦略を組み合わせた時にDDが下がるか
相関が急上昇した時に壊れないか
turnoverが増えすぎないか
```

を見るべきです。

---

# 3. バックテストシステムの基本構成

汎用的には、この構成が安全です。

```text
Data Layer
  ↓
Feature Layer
  ↓
Signal Layer
  ↓
Candidate / Order Intent Layer
  ↓
Execution Simulation Layer
  ↓
Portfolio Accounting Layer
  ↓
Metrics Layer
  ↓
Artifact / Report Layer
  ↓
Promotion / Paper Decision Layer
```

MarketLens Strikeでは、`strategy_signals.parquet`、`trial_ledger.jsonl`、`paper_candidate_pack.json`、`promotion_decision.json`、`paper_intent_preview.json` という流れが既に定義されています。`strategy_signals.parquet` がStrategy Labの正本で、`signals.csv` はlegacy thin exportです。また、`PaperIntentPreview` はpaper-onlyであり、live orderではありません。

---

# 4. Data Layer

## 4.1 データ契約

バックテストで最初に固定すべきものは、戦略ではなくデータ契約です。

最低限必要な列：

```text
symbol
timestamp
open
high
low
close
volume
source
source_timestamp
received_timestamp
session
is_tradable
```

crypto / perpなら追加：

```text
bid
ask
mid
spread_bps
mark_price
index_price
funding_rate
open_interest
liquidity_depth
venue_status
```

## 4.2 データの時刻

重要なのは、価格そのものより **いつ利用可能だったか** です。

分けるべき時刻：

```text
event_ts:
  市場イベントの時刻

source_ts:
  データ提供元が持つ原時刻

recv_ts:
  自分のシステムが受け取った時刻

feature_ts:
  特徴量として使える時刻

decision_ts:
  signal判断時刻

order_ts:
  注文を出した時刻

fill_ts:
  約定した時刻
```

この区別が曖昧だと、すぐ未来情報を使います。

---

## 4.3 データ品質

見るべき項目：

```text
欠損率
重複
時刻逆転
異常値
stale価格
bid > ask
spread異常
volume欠損
symbol mapping不一致
session不一致
source切替
```

バックテストは、入力データが壊れていると、正しい実装でも壊れた結果を出します。

---

# 5. Feature Layer

Featureは、signalより前に作る「判断材料」です。

例：

```text
return_1d
rolling_volatility
moving_average
vix_change
spread_bps
funding_delta
orderbook_imbalance
calendar_flag
event_window_flag
```

重要ルール：

```text
feature_ts <= decision_ts
```

この条件を満たさないfeatureは使ってはいけません。

特に危険なもの：

```text
same-day close
future high/low
翌日の出来高
後から確定するindex membership
後から修正されるfundamental data
確定後のevent label
```

---

# 6. Signal Layer

Signalは「売買する」ではありません。
Signalは、あくまで **候補を出す研究上の観測結果** です。

よいsignalの条件：

```text
入力featureが明確
利用可能時刻が明確
出力時刻が明確
sideが明確
confidenceがある
block reasonがある
lineageがある
```

悪いsignal：

```text
なんとなく強そう
AIがそう言った
過去成績が良かった
どの価格で判断したか不明
どの時点で使えた情報か不明
```

MarketLens Strikeでは、Strategy Labの正本signal artifactは `data/research/strategy_signals.parquet` であり、`trial_ledger.jsonl` はbestだけではなく全trialを記録する設計です。

---

# 7. Order / Candidate Layer

Signalから直接注文してはいけません。

分けるべきです。

```text
Signal:
  市場上の候補・兆候

TradeCandidate:
  売買候補

PaperCandidate:
  paper観測候補

PaperIntentPreview:
  paper-onlyの仮注文意図

Order:
  実際の注文
```

この分離がないと、

```text
研究signalがそのままlive orderになる
paper評価がlive-ready扱いになる
candidateのreject理由が残らない
```

という事故が起きます。

MarketLens Strikeでは、`PaperIntentPreview` は `live_conversion_allowed=false`、`wallet_used=false`、`exchange_write_used=false` を守るpaper-only artifactとして扱う方針です。

---

# 8. Execution Simulation Layer

## 8.1 約定モデルの段階

約定モデルは段階的に作るべきです。

```text
Level 0:
  close-to-close仮想評価

Level 1:
  next-bar open / next-row fill

Level 2:
  bid/askを使ったtaker fill

Level 3:
  maker/taker区別

Level 4:
  partial fill

Level 5:
  L2 depth / queue position

Level 6:
  latency / cancel race / order lifecycle replay
```

最初からLevel 5や6を作る必要はありません。
まずLevel 1〜2で十分です。

## 8.2 避けるべき約定仮定

```text
signalを出した同じcloseで約定
high/lowの都合の良い価格で約定
spreadなし
手数料なし
slippageなし
常に全量約定
cancelは必ず成功
market orderは常に安全
```

## 8.3 推奨される最小約定モデル

最小構成はこれです。

```text
decision row:
  signalを出す

next row:
  fillする

fill price:
  long entryなら ask / conservative mid + slippage
  long exitなら bid / conservative mid - slippage

cost:
  taker fee + slippage + funding
```

MarketLens StrikeのTrade[XYZ] pure backtestでも、runnerがnext-row fillを強制し、`close/high/low` を暗黙のfill priceにしない、fee未解決ならblockする、という方針が明記されています。

---

# 9. Cost Model

バックテストで最も軽視されやすいのがcostです。

最低限入れるもの：

```text
commission
maker fee
taker fee
spread
slippage
funding
borrow cost
tax / financing cost
market impact
failed fill penalty
```

crypto perpなら特に重要：

```text
funding
mark/index乖離
liquidation risk
leverage
margin mode
position mode
maker/taker差
```

cost modelは、単一値ではなくstressをかけます。

```text
base cost
2x cost
3x cost
wide spread condition
low liquidity condition
high volatility condition
```

戦略がcost 2倍で消えるなら、実運用ではかなり危ないです。

---

# 10. Portfolio Accounting

正しい会計がないバックテストは信用できません。

必要な状態：

```text
cash
position_qty
average_entry_price
realized_pnl
unrealized_pnl
equity
fees_paid
funding_paid
exposure
leverage
drawdown
```

検査すべきこと：

```text
cashがマイナスにならないか
positionが二重計上されないか
partial fill後の平均単価が正しいか
feeがentry/exit両方にかかるか
fundingが保有時間に応じて入るか
end-of-runでpositionをどう扱うか
```

MarketLens Strikeのpure backtest v0.1でも、Order / Fill / BlockedEvent / Position / Portfolioがあり、accounting testsとno-lookahead testsを重視する方針になっています。

---

# 11. Metrics Layer

利益率だけでは足りません。

## 11.1 収益系

```text
total return
CAGR
average trade return
expectancy
profit factor
win rate
payoff ratio
```

## 11.2 リスク系

```text
max drawdown
drawdown duration
volatility
downside volatility
VaR
expected shortfall
tail loss
worst trade
consecutive losses
```

## 11.3 安定性

```text
era別return
月別return
年別return
regime別return
symbol別return
parameter sensitivity
walk-forward stability
```

## 11.4 実行系

```text
trade count
turnover
average holding period
fee ratio
slippage ratio
fill rate
blocked rate
capacity
market impact estimate
```

## 11.5 baseline比較

最低限比較するもの：

```text
buy and hold
flat / no-trade
random entry
simple momentum
simple mean reversion
previous version
cost-stressed version
```

戦略単体の成績ではなく、**baseline差分**で見ます。

---

# 12. Validation

## 12.1 Train / Test

同じ期間でパラメータを探して、その期間の成績を見るのは危険です。

最低限：

```text
train
validation
test
```

を分けます。

## 12.2 Walk-forward

時間を前に進めながら、

```text
過去で学習
次の期間で評価
```

を繰り返します。

PyBrokerはwalkforward analysisをサポートしており、strategyが実際の取引中にどう振る舞ったかを模擬する用途として説明されています。NumPy/Numbaによる高速backtesting、複数instrument、bootstrap metrics、cachingも特徴です。([PyBroker][3])

## 12.3 Purged / Embargo

ラベル期間が重なるとリークします。

例：

```text
今日のsignalで5日後returnを予測
```

なら、train/testの境界周辺でラベルが重なる可能性があります。

対策：

```text
purge:
  重なるサンプルを除去

embargo:
  境界後の一定期間を使わない
```

## 12.4 Parameter Sensitivity

最適値だけを見るのは危険です。

見るべきもの：

```text
少し変えても成績が残るか
近傍が広いか
一点だけ異常に良いだけではないか
```

## 12.5 Stress Test

```text
fee 2倍
slippage 2倍
latency追加
spread悪化
低流動性期間
急落期間
高ボラ期間
データ欠損
symbol除外
```

で壊れるかを見ます。

---

# 13. Artifact Layer

バックテスト結果は、画面表示だけでは不十分です。

最低限出すべきartifact：

```text
backtest_run.json
data_manifest.json
feature_manifest.json
orders.parquet
fills.parquet
trades.parquet
positions.parquet
equity_curve.parquet
metrics.json
data_quality.json
candidate_result.json
backtest_report.md
backtest_report.html
```

MarketLens StrikeのTrade[XYZ] pure backtestでも、`backtest_run.json`、`orders.parquet`、`fills.parquet`、`trades.parquet`、`equity_curve.parquet`、`metrics.json`、`data_quality.json`、`data_manifest.json`、`candidate_result.json`、`backtest_report.md/html` が主なartifactとして整理されています。

重要なのは、artifactに次を必ず含めることです。

```text
strategy_id
strategy_version
data_hash
feature_hash
parameter_hash
code_version
run_id
created_at
input_paths
cost_model_version
fill_model_version
no_live_order=true
wallet_used=false
exchange_write_used=false
```

---

# 14. Test Plan

バックテストシステムには通常の単体テスト以上に、金融特有のテストが必要です。

## 14.1 Accounting test

```text
entry後のcash減少
exit後のcash増加
fee控除
PnL計算
position更新
平均単価
```

## 14.2 No-lookahead test

```text
future closeを使っていない
same-bar high/lowを都合よく使っていない
feature_ts <= decision_ts
fill_ts > decision_ts
```

## 14.3 Fill test

```text
next-row fill
bid/ask fill
slippage適用
fee適用
partial fill
blocked fill
```

## 14.4 Data quality test

```text
欠損
重複
時刻逆転
stale
bid/ask異常
fee未解決
```

## 14.5 Artifact test

```text
全artifactが出る
schemaが合う
hashが入る
no_live_order=true
wallet_used=false
exchange_write_used=false
```

## 14.6 Regression test

```text
小さいfixtureで結果固定
既知のorders/fills/metricsを比較
```

MarketLens Strikeでは、Trade[XYZ] pure backtestの受入コマンドとして `tests/backtest`、bridge、fixed horizon、normalizer、registryのテストを通す方針があり、最初の指示は「performanceではなくaccountingとno-lookaheadから始める」です。

---

# 15. よくある失敗

## 15.1 closeで買ってcloseで売る

一番多い失敗です。

```text
close価格を見てsignalを出したのに、
同じcloseで約定したことにする
```

これは未来情報です。

## 15.2 high/lowを都合よく使う

同じbarのhigh/lowのどちらが先に来たか分からないのに、

```text
先にtarget到達
その後stop未達
```

のように都合よく解釈する。

## 15.3 手数料なし

特に短期戦略では、手数料なしの成績はほぼ使えません。

## 15.4 survivorship bias

生き残った銘柄だけで検証する。

## 15.5 selection bias

良かった条件だけ残す。

## 15.6 parameter overfit

最適パラメータを探しすぎる。

## 15.7 data revision

後から修正されたデータを当時使えたように扱う。

## 15.8 live-ready誤認

paperやbacktestの成功をlive可能と読む。

MarketLens Strikeでも、known gapsとして production live trading、wallet secrets、exchange write credentials、public micro-live CLI、Bitget credentialed read-only network smoke、Bitget demo order lifecycle などは未完了として整理されています。

---

# 16. OSSの使い方

OSSバックテストは、**中核置換ではなく補助部品**として使うのが現実的です。

## vectorbt

役割：

```text
高速sweep
threshold比較
parameter grid
多銘柄比較
可視化
```

向いている用途：

```text
研究初期
candidateを早く捨てる
IC / threshold / z-score検証
```

注意：

```text
正本artifactにはしない
約定リアリティは別途検証する
```

vectorbtはpandas/NumPy上で動き、Numba/Rustで高速化され、多数の戦略をまとめて検証できる設計です。([VectorBT][1])

---

## PyBroker

役割：

```text
walk-forward
ML model validation
bootstrap metrics
複数instrumentへのrule/model適用
```

向いている用途：

```text
ML補助
walk-forward検証
モデル比較
```

注意：

```text
データ取得機能はそのまま使わず、自前artifactを入力する
```

PyBrokerはNumPy/Numbaベースの高速backtesting engine、複数instrumentへのrule/model適用、walkforward analysis、bootstrap metrics、caching、parallelized computationを特徴として説明されています。([PyBroker][3])

---

## NautilusTrader

役割：

```text
event-driven architectureの設計参考
research/live parityの設計参考
venue adapter設計
deterministic simulation
```

向いている用途：

```text
Bitget / Hyperliquid正式対応の設計参考
order lifecycle設計
live parity設計
```

注意：

```text
中核置換は重い
MarketLensのartifact-first設計とは役割を分ける
```

NautilusTraderは、multi-asset/multi-venue trading systems向けのopen-source production-grade engineで、research、deterministic simulation、live executionを単一event-driven architectureで扱う設計です。([NautilusTrader][2])

---

## LEAN

役割：

```text
大規模engine設計参考
brokerage abstraction
data provider abstraction
local backtest workflow
optimization workflow
```

注意：

```text
Docker / LEAN形式 / C#-Python混在などが重い
設計参考に留める方が現実的
```

QuantConnect Lean CLIは、historical dataでalgorithmをテストするbacktestingをlocalまたはcloudで実行でき、local backtestはLEAN engineのDocker imageで実行され、結果はJSONとして保存される設計です。([QuantConnect][4])

---

## Backtrader

役割：

```text
古典的なStrategy / Data Feed / Broker / Order / Commission / Analyzer設計の参考
```

向いている用途：

```text
order model
broker model
commission scheme
analyzer設計
multi-timeframe
```

Backtraderは、Data Feeds、Indicators、Strategies、Orders、Broker、Commission Schemes、Analyzers、Sizers、Live Tradingなどの概念を持つ古典的なバックテストフレームワークです。([Backtrader][5])

---

## backtesting.py

役割：

```text
小さい戦略のsanity check
教育用
小型fixture検証
```

backtesting.pyは、historical candlestick data上で戦略viabilityを推定する軽量・高速なPython frameworkで、vectorizedまたはevent-based backtestingに対応すると説明されています。([Kernc][6])

---

## Zipline-reloaded

役割：

```text
米株日足
event-driven research
market calendar
pipeline/data bundle設計
```

ZiplineはPythonicなevent-driven backtesting systemで、Pandas DataFrameとの統合、移動平均や線形回帰などの統計、scikit-learn等の利用を前提にしたresearch環境です。Zipline 3.0ではpandas 2.0以降、SQLAlchemy 2.0以降へ更新されています。([Zipline][7])

---

# 17. OSS使い分け表

| OSS            | 主用途               | 使い方                            | 中核置換 |
| -------------- | ----------------- | ------------------------------ | ---- |
| vectorbt       | 高速sweep           | threshold / parameter / 多銘柄比較  | しない  |
| PyBroker       | walk-forward / ML | model validation / bootstrap   | しない  |
| NautilusTrader | event-driven設計    | live parity / venue adapter参考  | しない  |
| LEAN           | 大規模engine設計       | brokerage / data abstraction参考 | しない  |
| Backtrader     | 古典的概念設計           | broker / order / commission参考  | しない  |
| backtesting.py | 小型検証              | 教育用 / sanity check             | しない  |
| Zipline        | 米株日足research      | calendar / pipeline参考          | しない  |

---

# 18. MarketLens Strikeへの適用

MarketLens Strikeでは、バックテスト面は3系統に分かれています。

```text
1. Trade[XYZ] pure backtest v0.1
2. Strategy Authoring fixed-horizon backtest
3. legacy backtest bridge
```

Trade[XYZ] pure backtestは `sis.backtest.engine.runner.run_backtest()` が入口で、CLI未公開。Strategy Authoring fixed-horizon backtestは `strategy-author-run --through backtest` が入口。`uv run sis build-backtest` はlegacy bridgeであり、pure backtestの入口ではありません。

## 現実的な拡張方針

最初にやるべきこと：

```text
OSS adapter policyを作る
```

たとえば：

```text
src/sis/research/backtest_adapters/
  vectorbt_adapter.py
  pybroker_adapter.py
  result_normalizer.py

docs/backtest/OSS_BACKTEST_ADAPTER_POLICY.md
tests/research/test_backtest_adapter_contract.py
```

ただし、最初はdependency追加しなくてよいです。
まずは「どんなDataFrameを渡し、どんな結果を戻すか」のcontractだけ作るのが安全です。

---

# 19. 他プロジェクトで使えるMVP設計

汎用MVPはこれで十分です。

```text
backtest/
  contracts.py
  data.py
  strategy.py
  signal.py
  order.py
  fill.py
  portfolio.py
  costs.py
  metrics.py
  artifacts.py
  runner.py

tests/
  test_accounting.py
  test_no_lookahead.py
  test_fill_model.py
  test_cost_model.py
  test_artifacts.py
  test_data_quality.py
```

最初の仕様：

```text
single-symbol
long-only
fixed notional
next-bar fill
fee + slippage
no leverage
no partial fill
no live connection
```

この小さい範囲で正しく作る方が、最初からmulti-venue / L2 / ML / portfolio最適化を入れるより安全です。

---

# 20. バックテスト設計チェックリスト

## Data

```text
[ ] timestampが明確
[ ] source_ts / recv_ts / decision_tsが分かれている
[ ] 欠損・重複・時刻逆転を検査
[ ] symbol mappingが固定
[ ] session / tradable flagがある
```

## Feature

```text
[ ] feature_ts <= decision_ts
[ ] same-day closeをsignal側に使っていない
[ ] future high/lowを使っていない
[ ] データrevisionを考慮
```

## Signal

```text
[ ] signal_idがある
[ ] strategy_versionがある
[ ] input feature lineageがある
[ ] block reasonがある
```

## Fill

```text
[ ] fill_ts > decision_ts
[ ] fill_price_sourceが残る
[ ] bid/askまたはconservative priceを使う
[ ] fee/slippageが入る
[ ] unresolved feeをblockする
```

## Accounting

```text
[ ] cash
[ ] position
[ ] realized/unrealized PnL
[ ] fee
[ ] funding
[ ] equity curve
```

## Metrics

```text
[ ] return
[ ] drawdown
[ ] trade count
[ ] turnover
[ ] cost ratio
[ ] baseline delta
[ ] era stability
```

## Artifacts

```text
[ ] data_manifest
[ ] feature_manifest
[ ] backtest_run
[ ] orders
[ ] fills
[ ] trades
[ ] equity_curve
[ ] metrics
[ ] report
```

## Safety

```text
[ ] no_live_order=true
[ ] wallet_used=false
[ ] exchange_write_used=false
[ ] paper/liveと接続しない
```

---

# 21. 最終的な実務方針

バックテストシステムを作る時の最善手は、次です。

```text
1. 最初は小さく作る
2. accountingとno-lookaheadを最優先する
3. cost/slippageを初期から入れる
4. artifactを必ず残す
5. baseline比較を必須にする
6. 最適化よりstress testを優先する
7. OSSは中核置換ではなく検証加速器として使う
8. paper/liveとは明確に分離する
```

MarketLens Strikeでも、最初のbacktest実装者への指示は「strategy performanceから始めない。accountingとno-lookaheadから始める。live/wallet/exchange境界を越えられないようにする。最初の動く結果はprofitabilityではなくcorrectness harnessとして扱う」です。

---

# 一文でまとめる

**バックテストは、儲かる戦略を証明する装置ではなく、データ・時刻・約定・コスト・会計・評価の仮定を明示し、その仮定が壊れる条件を見つけるための検査基盤です。**

18:27:18.(06/14)

[1]: https://vectorbt.dev/ "Getting started - VectorBT"
[2]: https://nautilustrader.io/docs/latest/ "NautilusTrader Documentation | NautilusTrader"
[3]: https://www.pybroker.com/ "Algorithmic Trading in Python with Machine Learning — PyBroker"
[4]: https://www.quantconnect.com/docs/v2/lean-cli/backtesting/deployment "Deployment - QuantConnect.com"
[5]: https://www.backtrader.com/docu/quickstart/quickstart/ "Quickstart Guide - Backtrader"
[6]: https://kernc.github.io/backtesting.py/ "Backtesting.py - Backtest trading strategies in Python"
[7]: https://zipline.ml4trading.io/ "Zipline — Zipline 3.0 docs"


## 4

According to a document from 2026-06-08, **MarketLens Strike は backtest-first / venue-neutral の戦略研究ワークスペースであり、Strategy Lab・paper運用・安全gateを持つ一方、production live trading / wallet / signing / exchange write は範囲外**です。したがって、この資料も「実弾売買の作り方」ではなく、**戦略を安全に検証し、棄却し、paper運用へ進めるためのバックテスト設計資料**として整理します。

# 結論

**バックテストシステムは、“儲かりそうな成績を出す装置”ではなく、“戦略仮説を壊すための検証装置”として作るべきです。**

他プロジェクトにも使い回すなら、最初にこの原則で設計するとよいです。

```text
1. raw data を保存する
2. 正規化データを作る
3. 特徴量を作る
4. シグナルを作る
5. 約定・手数料・slippage・fundingを模擬する
6. 損益・drawdown・riskを計算する
7. train/testやwalk-forwardで検証する
8. 全試行を台帳に残す
9. 採用・棄却理由を残す
10. paper/liveへ直結させない
```

MarketLens Strikeでは、既に `StrategyExperimentSpec -> StrategySignalRecord -> EvaluationPlan -> TrialRecord / TrialLedger -> TradeCandidate -> PaperCandidatePack -> PromotionDecision -> PaperIntentPreview -> paper-from-intents` という流れが整理されており、`PaperIntentPreview` は paper-only の仮注文意図で live order ではありません。

---

# 1. バックテストとは何か

## 悪い定義

```text
過去データで儲かったかを見ること
```

この定義だと、過去に合うパラメータを探すだけになります。

## よい定義

```text
戦略仮説が、データ品質・時間順序・コスト・約定・リスク・過学習に耐えるかを検査すること
```

つまり、バックテストは「成功を証明する道具」ではなく、**失敗条件を見つける道具**です。

---

# 2. バックテストの種類

## 2.1 ベクトル型バックテスト

価格やシグナルを配列で一気に計算する方式です。

```text
向く:
  - 大量のパラメータ探索
  - signal候補の粗いスクリーニング
  - indicator比較
  - cross-sectional ranking

向かない:
  - 複雑な約定
  - order book再現
  - partial fill
  - latency
  - exchange固有仕様
```

代表例は `vectorbt` です。vectorbtは多数の戦略構成をNumPy配列に詰め、Numba/Rustで高速化して大量探索を行う思想のライブラリです。ただしライセンスはApache 2.0 with Commons Clauseで、商用・製品利用には注意が必要です。([PyPI][1])

## 2.2 イベント駆動型バックテスト

時間順にイベントを処理する方式です。

```text
例:
  price update
  signal event
  order submitted
  order filled
  funding event
  risk halt
```

```text
向く:
  - no-lookahead検査
  - session/calendar管理
  - order/fill/accounting分離
  - 複数assetの状態管理

向かない:
  - 大量パラメータ探索を雑に回す用途
```

zipline-reloadedはevent-driven系の教材として有用です。公式docsでも、data、calendars、metricsなどの領域を持つbacktesting systemとして整理されています。([Zipline][2])

## 2.3 イベントスタディ型バックテスト

今回の小型alt perp戦略のように、「あるイベントが起きた後にどう動くか」を見る方式です。

```text
例:
  pump発生
    -> 1h後return
    -> 4h後return
    -> 12h後return
    -> MAE
    -> MFE
    -> slippage後net return
```

```text
向く:
  - 急騰後ショート
  - earnings event
  - listing event
  - liquidation event
  - macro event
  - opening gap
```

MarketLens Strikeの小型perp戦略では、これが最初の中核です。

## 2.4 order book / microstructure型バックテスト

板、queue、latency、tick dataを使う方式です。

```text
向く:
  - market making
  - scalping
  - passive limit order
  - thin bookの約定検証
  - slippage / impact検証
```

hftbacktestは、limit order、queue position、latency、full tick data、Level-2/Level-3 order bookを扱う高頻度向けツールです。PyPI上でも、feed/order latencyやqueue positionを考慮し、full order bookとtrade tick feedに基づくmarket replayを目指すと説明されています。([PyPI][3])

## 2.5 paper / shadow test

実際に注文を出さず、リアルタイムデータで仮想注文を記録する段階です。

```text
目的:
  - live dataの欠損を見る
  - signal遅延を見る
  - 実際のspread/depthを見る
  - paper fillと実板を比較する
```

これはバックテストとliveの間の重要な段階です。

---

# 3. バックテストシステムの基本構造

汎用的には、こう分けるとよいです。

```text
Raw Data Layer
  ↓
Normalized Data Layer
  ↓
Feature Layer
  ↓
Signal Layer
  ↓
Execution Simulation Layer
  ↓
Portfolio / Accounting Layer
  ↓
Metrics Layer
  ↓
Validation Layer
  ↓
Report / Artifact Layer
```

## 3.1 Raw Data Layer

取引所やデータ提供元から取得した生データを、そのまま保存します。

```text
保存する:
  - raw response
  - source
  - fetched_at
  - request params
  - status code
  - rate limit metadata
  - schema version
```

なぜ必要か。

```text
後から正規化ロジックを直せる
API仕様変更を検出できる
データ欠損の責任を追える
同じ実験を再現できる
```

やってはいけないこと。

```text
rawを上書きする
必要列だけ抜いてrawを捨てる
取得時刻を残さない
API errorを空データとして扱う
```

## 3.2 Normalized Data Layer

rawを、戦略が使える共通形式に変換します。

今回のBitget + Hyperliquidなら、最低限これです。

```text
funding_8h_equiv
oi_usd
premium_bps
spread_bps
depth_1pct_usd
taker_imbalance
```

Bitgetのopen interest APIは、特定ペアのplatform上のtotal positionを返し、responseの`size`は特定coin単位のopen interestとして説明されています。つまり、そのままHyperliquidと比較せず、USD notionalへ変換する必要があります。([Bitget][4])

Bitgetのcurrent funding APIは`fundingRateInterval`を返し、1/2/4/8時間などのsettlement periodがあり得るため、8時間換算などへ揃える必要があります。([Bitget][5])

Hyperliquidの`metaAndAssetCtxs`はmark price、current funding、open interestなどを含むasset contextを返し、`fundingHistory`、`predictedFundings`、OI cap関連のinfo endpointも用意されています。([Hyperliquid Docs][6])

## 3.3 Feature Layer

正規化データから、戦略用の特徴量を作ります。

```text
例:
  return_z
  volume_z
  funding_percentile
  oi_delta
  oi_to_mcap
  premium_drop_from_peak
  taker_imbalance_rollover
  spread_p90
  depth_1pct_usd
```

原則はこれです。

```text
特徴量は「その時点で見えていたデータ」だけで作る
未来の高値・安値・volumeを混ぜない
銘柄ごと・取引所ごとの定義差を残す
```

## 3.4 Signal Layer

特徴量からシグナルを作ります。

```text
signal:
  取引候補の方向・強さ・理由

candidate:
  実際にpaper検証へ進める候補

order:
  実際の注文
```

この3つは混ぜない。
MarketLens Strikeでも、`TradeCandidate`は売買候補であってpaper/live orderではなく、`PaperIntentPreview`はpaper-onlyの仮注文意図でlive orderへ変換しない設計です。

---

# 4. 時間設計：no-lookaheadが最重要

## no-lookaheadとは

**未来の情報を見ないこと**です。

悪い例。

```text
今日の終値でシグナルを出し、同じ今日の終値で約定したことにする
```

良い例。

```text
bar close後にシグナルを出す
次bar openまたは次barのbid/askで約定したことにする
```

## 必ず分ける時刻

```text
source_ts:
  取引所側でデータが発生した時刻

recv_ts:
  自分のcollectorが受け取った時刻

feature_ts:
  特徴量として利用可能になった時刻

signal_ts:
  シグナルを判定した時刻

order_ts:
  注文した時刻

fill_ts:
  約定した時刻
```

## 時間リークの典型例

```text
当日高値/安値を使って当日中に判断する
未来のfunding確定値をentry時点の特徴量に使う
後から補正されたmarket capを過去時点の特徴量に使う
銘柄の生存者だけをuniverseにする
欠損した銘柄を後から除外して成績を良くする
```

---

# 5. データスナップショットと特徴量スナップショット

バックテストごとに、何のデータを使ったかを固定します。

```text
DataSnapshotManifest:
  どのraw / normalized dataを使ったか

FeatureSnapshotManifest:
  どの特徴量定義・期間・欠損処理を使ったか

EvaluationPlan:
  train/test、horizon、metric、cost stressを定義

TrialLedger:
  全試行を記録
```

MarketLens Strikeでは、Strategy Research Labの構造として `DataSnapshotManifest -> FeatureSnapshotManifest -> StrategyExperimentSpec -> StrategySignalArtifact -> EvaluationPlan -> TrialLedger -> TradeCandidate -> PaperCandidatePack -> PromotionDecision -> PaperIntentPreview` という流れが既に設計されています。

---

# 6. 約定モデル

バックテストで一番成績を盛りやすいのがここです。

## Level 0：close約定

```text
約定価格 = close
```

最も簡単。
ただし、現実性は低い。

使ってよい場面。

```text
粗い仮説検証
長期足
流動性が厚い市場
```

使ってはいけない場面。

```text
小型alt
薄い板
急騰急落
scalping
perpショート
```

## Level 1：next bar約定

```text
signal at bar t
fill at bar t+1 open
```

Level 0より安全。
ただし、spread/slippageは別途必要。

## Level 2：bid/ask約定

```text
long entry:
  best_ask

short entry:
  best_bid

short exit:
  best_ask
```

小型perpなら最低ここからです。

## Level 3：spread + slippage

```text
fill_price = side_price + slippage_bps
```

```text
cost = fee + half_spread + estimated_impact + slippage_buffer
```

## Level 4：depth / impact

板の厚さを使います。

```text
depth_1pct_usd
depth_2pct_usd
expected_impact_bps(order_size)
```

小型altショートでは重要です。
損切り時は買い戻すので、ask側depthが重要です。

## Level 5：order book replay

tick / L2 / L3で板を再現します。

```text
- queue position
- latency
- partial fill
- cancel
- modify
- book disappearance
```

hftbacktestのようなツールはこの領域の教材・検証sidecarとして有用です。hftbacktestはtick-by-tick simulation、L2/L3 order book reconstruction、latency、queue positionを扱います。([PyPI][3])

---

# 7. コストモデル

バックテストでは、以下を必ず分けます。

```text
fee
spread
slippage
market impact
funding
borrow cost
tax / borrow / funding carry
failed order
partial fill
```

## perpで特に重要なもの

```text
funding
mark/index/premium
OI
position cap
market status
```

Bitgetならfunding intervalが1/2/4/8時間で返るため、8時間換算や時間按分が必要です。([Bitget][5])

Hyperliquidなら`metaAndAssetCtxs`からmark、funding、OI等を取れ、`fundingHistory`や`predictedFundings`もあります。([Hyperliquid Docs][6])

---

# 8. Portfolio / Accounting

最低限これを持ちます。

```text
cash
position_qty
position_value
realized_pnl
unrealized_pnl
fees_paid
funding_paid
slippage_cost
equity
margin_used
available_cash
```

## よくあるバグ

```text
ショートのPnL符号が逆
手数料を片道しか入れていない
fundingの支払い方向が逆
open positionを最終日に都合よく消す
unrealized PnLをrealizedとして扱う
複数positionの平均建値が壊れる
```

## 終了時ポジション

バックテスト終了時にポジションが残っている場合、ポリシーを明記します。

```text
close_at_end:
  最終barで強制決済

mark_to_market:
  評価損益のみ反映

reject_result:
  戦略評価には使わない
```

MarketLens Strikeの既存テスト群でも、backtest reportはScope、Data Manifest、Data Quality、Scenario Sensitivity、Split Validation、Parameter Sweep、Blocked Events、Cost Breakdownなどのsectionを要求しています。

---

# 9. 指標設計

## 基本指標

```text
net_return_after_cost
gross_return
trade_count
win_rate
profit_factor
avg_win
avg_loss
expectancy
max_drawdown
MAE
MFE
turnover
fee_impact
slippage_impact
funding_impact
```

## Sharpeの注意

Sharpeは便利ですが、万能ではありません。

```text
弱点:
  - fat tailに弱い
  - 少数取引に弱い
  - 多数パラメータ探索に弱い
  - 非正規returnに弱い
  - path riskを隠す
```

Deflated Sharpe Ratioは、Sharpeの選択バイアス、バックテスト過学習、サンプル長、非正規性を補正する目的の指標として知られています。([ウィキペディア][7])

## drawdown

```text
running_peak_t = max(equity_0..equity_t)
drawdown_t = equity_t / running_peak_t - 1
max_drawdown = min(drawdown_t)
```

## MAE / MFE

```text
MAE:
  entry後、どれだけ逆行したか

MFE:
  entry後、どれだけ有利に動いたか
```

小型altショートでは、MAEが特に重要です。
良いforward returnがあっても、先に踏み上げでstopされるなら使えません。

---

# 10. 検証方法

## 10.1 train / test split

```text
train:
  閾値・モデルを決める期間

test:
  触らない検証期間
```

## 10.2 walk-forward

時間を進めながら、学習・検証を繰り返します。

PyBrokerはwalkforward analysisを機能として持ち、公式docsではtrain/testを複数windowで進める例が示されています。PyBroker自体はML寄りの戦略検証sidecarとして使えますが、中核依存にはしない方針が安全です。([PyBroker][8])

## 10.3 purged / embargo

ラベルが未来期間を使う場合、trainとtestが重なるとリークします。

```text
例:
  24h forward returnをlabelにする
  すると、近接するサンプル同士の未来区間が重なる
  その重なりをtrainから除く
```

## 10.4 bootstrap

結果のばらつきを見る方法です。

PyBrokerのbootstrap metricsは、randomized bootstrapでProfit FactorやSharpe Ratioのconfidence interval、drawdown confidenceを出す例を示しています。公式例では、通常のmax drawdownよりbootstrap上の99.9% drawdownが悪化し、単純成績より保守的な評価になります。([PyBroker][9])

## 10.5 多重検定対策

パラメータをたくさん試すほど、偶然良いものが出ます。

```text
危険:
  thresholdを20個試す
  lookbackを10個試す
  exitを10個試す
  その中のbestだけ採用
```

この問題に対し、WhiteのReality Check、HansenのSPA test、Deflated Sharpe Ratio、Probability of Backtest Overfittingなどが使われます。実装は後段でよいですが、少なくとも全試行を台帳に残すことが必須です。Lopez de Pradoらも、backtestで複数設定を試すことがbacktest overfittingに寄与すると指摘しています。([arXiv][10])

MarketLens StrikeのTrialRecordは、`profitability_claimed`, `paper_ready_claimed`, `tiny_live_ready_claimed`, `live_ready_claimed` をfalseに保つvalidationを持っており、TrialLedgerに全試行を残す構造になっています。

---

# 11. レポート設計

バックテストレポートには、最低限これを入れます。

```text
1. Run Summary
2. Scope / Non-Scope
3. Data Manifest
4. Feature Manifest
5. Strategy Definition
6. Signal Summary
7. Fill Model
8. Cost Model
9. Funding Model
10. Portfolio Accounting
11. Metrics
12. Benchmark Comparison
13. Scenario Sensitivity
14. Split / Walk-forward Validation
15. Parameter Sweep
16. Blocked Events
17. Trade List
18. Failure Cases
19. Known Limitations
20. Artifact Paths
```

MarketLens Strikeの既存backtest reportテストでも、Run Summary、Data Manifest、Data Quality、Benchmark Comparison、Scenario Sensitivity、Split Validation、Parameter Sweep、Blocked Events、Cost Breakdown、Warnings / Known Limitationsなどのsectionを要求しています。

---

# 12. バックテストで必ず比較するbaseline

1つの戦略だけを見ると、良いか悪いか分かりません。

## 最低限のbaseline

```text
cash only
buy and hold
random entry
naive momentum
naive mean reversion
cost-only model
immediate entry
delayed entry
```

## 小型altショートなら

```text
Immediate Fade:
  pump直後にショート

Funding Only:
  funding高位だけでショート

Failure Confirmation:
  高値失敗 / VWAP割れ後にショート

Full Score:
  Pump + Crowd + Exhaustion + ExecutionRisk

No ExecutionRisk:
  ExecutionRiskを外したモデル
```

見たいこと。

```text
Full Score は Funding Only より良いか
ExecutionRiskを入れるとnetが改善するか
Failure Confirmationだけで十分ではないか
Immediate Fadeは危険か
```

---

# 13. データ品質ポリシー

## 欠損時の扱い

```text
price missing:
  event不可

funding missing:
  CrowdScore不可

OI missing:
  CrowdScore不可

depth missing:
  ExecutionRisk blocked

market_status unknown:
  blocked

fee unknown:
  scenario fallbackまたはblocked
```

## 補完してよいもの

```text
短いmissingで、分析対象外の補助列
明示的にflagを立てたforward fill
report用途の表示値
```

## 補完してはいけないもの

```text
fill price
funding event
OI
market status
depth
source timestamp
```

---

# 14. バックテストシステムのテスト

バックテストエンジン自体にもテストが必要です。

## 必須テスト

```text
test_no_lookahead
test_cost_model
test_fee_applied_both_sides
test_short_pnl_sign
test_funding_payment_direction
test_slippage_worsens_fill
test_depth_block
test_market_status_block
test_data_missing_block
test_train_test_split
test_parameter_sweep_records_all_trials
test_report_contains_known_limitations
```

## 小fixtureの例

```text
価格:
  100 -> 110 -> 105

ショート:
  110でentry
  105でexit
  gross profit = 5

手数料:
  entry fee
  exit fee

slippage:
  entry worse
  exit worse

期待:
  net profit < gross profit
```

---

# 15. OSSの使い方

## 中核にするべきもの

このプロジェクトの場合、最初は既存スタックのPolars / DuckDB / PyArrowで十分です。MarketLens Strikeは既にPython 3.13のCLI workspaceで、Strategy Lab、backtest、paper、venue-neutral execution contractを持っています。

```text
Polars:
  高速なDataFrame処理

DuckDB:
  Parquet / SQL / event window抽出

PyArrow:
  Parquet保存
```

## PyBroker

```text
使いどころ:
  - ML風特徴量検証
  - walk-forward
  - bootstrap
  - custom data source
  - sidecar実験
```

PyBrokerはNumPy/Numbaによるbacktesting、複数instrument、custom provider、walkforward、bootstrap、cache、parallelized computationsを掲げています。([PyPI][11])

```text
使わない:
  - Bitget / Hyperliquidの精密執行再現
  - order book replay
  - exchange API制約
  - MarketLens中核依存
```

注意として、PyBrokerのライセンスはApache 2.0 with Commons Clauseで、PyPI上でもFree for non-commercial useとされています。([PyPI][11])

## vectorbt

```text
使いどころ:
  - parameter sweep
  - 近傍安定性
  - 大量候補の粗い棄却
```

```text
使わない:
  - 正式会計
  - thin bookの約定
  - venue-specific execution
```

## hftbacktest

```text
使いどころ:
  - L2 / L3
  - latency
  - queue position
  - limit order fill
  - execution stress
```

P2以降の執行品質検証に向きます。hftbacktestはMIT License、Python 3.13 classifierを持ち、tick data・order book・queue・latencyを扱うと説明されています。([PyPI][3])

## NautilusTrader

```text
使いどころ:
  - research-to-live parityの設計教材
  - event-driven multi-venue architectureの教材
```

NautilusTraderは、高性能なalgorithmic trading platformで、backtestingとlive tradingに共通のevent-driven architectureを掲げています。([NautilusTrader][12])

ただし、MarketLens Strikeではlive orderやwallet/signingが範囲外なので、今すぐ依存しない。

---

# 16. 他プロジェクトでも使える設計テンプレート

```text
project/
  data/
    raw/
    normalized/
    features/
    events/
    backtests/
  configs/
    strategy.yaml
    cost_model.yaml
    venue_registry.yaml
    evaluation_plan.yaml
  schemas/
    data_snapshot.schema.json
    feature_snapshot.schema.json
    trial_record.schema.json
  src/
    data/
      collectors.py
      normalizers.py
      quality.py
    research/
      features.py
      signals.py
      event_study.py
    backtest/
      engine.py
      fill.py
      portfolio.py
      costs.py
      metrics.py
      validation.py
      reports.py
  tests/
    test_no_lookahead.py
    test_fill_model.py
    test_cost_model.py
    test_metrics.py
    test_split_validation.py
    test_report_artifacts.py
```

---

# 17. バックテスト実行フロー

```text
1. collect raw data
2. normalize data
3. validate data quality
4. freeze data snapshot
5. compute features
6. freeze feature snapshot
7. generate signals
8. run evaluation plan
9. simulate fills / costs / portfolio
10. compute metrics
11. run baselines
12. run scenarios
13. run train/test or walk-forward
14. write TrialLedger
15. generate report
16. decide reject / hold / paper candidate
```

---

# 18. 最小実装の順番

## PR-1：Metrics Contract

```text
docs/reference/METRICS_CONTRACT.md
tests/backtest/test_metrics_contract.py
```

固定する。

```text
return定義
drawdown定義
Sharpe定義
fee/slippage/fundingの含有
annualization
```

## PR-2：DataSnapshot / FeatureSnapshot

```text
data snapshot
feature snapshot
schema
hash
source paths
time range
```

## PR-3：Event Study

```text
event_candidates.parquet
forward returns
MAE / MFE
baseline comparison
```

## PR-4：Fill / Cost Model

```text
bid/ask
spread
slippage
fee
funding
depth block
```

## PR-5：TrialLedger

```text
全試行を保存
bestだけを残さない
rejection理由を残す
```

## PR-6：Report

```text
metrics
baseline
scenario
split
known limitations
blocked events
artifact paths
```

---

# 19. バックテストの失敗モード一覧

```text
未来データを見る
survivorship bias
lookahead bias
selection bias
overfitting
parameter mining
APIデータ欠損
venue定義差
funding interval差
OI単位差
spread無視
slippage無視
fee片道漏れ
funding漏れ
short PnL符号ミス
薄板の約定過信
partial fill無視
market halt無視
取引停止銘柄の除外漏れ
上場直後銘柄混入
勝ち事例だけレビュー
試したパラメータを記録しない
```

---

# 20. 採用判断のルール

バックテスト結果を見て、次を満たさないなら採用しません。

```text
- netで勝っている
- cost 2xでも壊れない
- slippage 2xでも壊れない
- trainだけでなくtestでも崩れない
- 特定1銘柄だけに依存しない
- 特定1週間だけに依存しない
- trade countが十分ある
- 最大損失が許容内
- paperで再現する
- 入らなかったイベントも記録している
```

---

# 21. MarketLens Strikeへの適用

今回の小型alt perp戦略では、こう作るのがよいです。

```text
src/sis/research/alt_perp/
  universe.py
  normalization.py
  features.py
  scores.py
  event_study.py
  execution_profiles.py
  trial_ledger.py
  reports.py
```

```text
data/research/
  alt_perp_event_candidates.parquet
  alt_perp_short_candidates.parquet
  alt_perp_trial_ledger.jsonl
  alt_perp_execution_profiles.parquet
```

```text
data/reports/
  alt_perp_event_study_report.md
  alt_perp_execution_venue_scorecard.md
```

中核は、汎用OSSではなく、MarketLens Strikeの既存思想に合わせた **event-study / execution-profile backtest** です。外部OSSはPyBrokerやvectorbtをsidecarにし、hftbacktestはL2データが溜まった後の執行検証に使うのが現実的です。

---

# 最終まとめ

バックテストシステムを作るときは、次の順番で考えれば大きく外しません。

```text
1. 仮説を1文で書く
2. 使うデータと使わないデータを決める
3. rawを保存する
4. 正規化する
5. 時点利用可能性を固定する
6. 特徴量を作る
7. シグナルと注文を分ける
8. 約定モデルを保守的にする
9. 手数料・slippage・fundingを入れる
10. train/testを分ける
11. 全試行をTrialLedgerに残す
12. baselineと比較する
13. scenario stressをかける
14. レポートに限界を書く
15. paperで再現するまでliveに進まない
```

この考え方を使うと、MarketLens Strikeだけでなく、株式、先物、FX、暗号資産、RWA perp、イベント戦略、ML戦略のどれにも応用できます。

18:35:52.(06/14)

[1]: https://pypi.org/project/vectorbt/ "vectorbt · PyPI"
[2]: https://zipline.ml4trading.io/ "Zipline — Zipline 3.0 docs"
[3]: https://pypi.org/project/hftbacktest/ "hftbacktest · PyPI"
[4]: https://www.bitget.com/api-doc/contract/market/Get-Open-Interest "Get Open Interest | Bitget API"
[5]: https://www.bitget.com/api-doc/contract/market/Get-Current-Funding-Rate "Get Current Funding Rate | Bitget API"
[6]: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals "Perpetuals | Hyperliquid Docs"
[7]: https://en.wikipedia.org/wiki/Deflated_Sharpe_ratio?utm_source=chatgpt.com "Deflated Sharpe ratio"
[8]: https://www.pybroker.com/ "Algorithmic Trading in Python with Machine Learning — PyBroker"
[9]: https://www.pybroker.com/en/latest/notebooks/3.%20Evaluating%20with%20Bootstrap%20Metrics.html "Evaluating with Bootstrap Metrics — PyBroker"
[10]: https://arxiv.org/abs/1408.1159?utm_source=chatgpt.com "Determining Optimal Trading Rules without Backtesting"
[11]: https://pypi.org/project/lib-pybroker/ "lib-pybroker · PyPI"
[12]: https://nautilustrader.io/docs/latest/ "NautilusTrader Documentation | NautilusTrader"


## 5

結論：**バックテストは「過去データで儲かったか」を見る道具ではなく、仮説・データ・執行・コスト・検証手順のどこが壊れるかを発見するための実験装置**として設計するのがよいです。
特に複数プロジェクトで再利用するなら、最初から **「研究用バックテスト」「イベント検証」「約定シミュレーション」「paper運用」「live差分検証」** を分けて考えるべきです。

---

# バックテスト設計リファレンス

## 1. バックテストの目的

バックテストの目的は、単に過去損益を見ることではありません。

本来の目的は以下です。

```text
1. 仮説が観測可能か確認する
2. シグナルが未来情報を使っていないか確認する
3. 取引コスト後も残るか確認する
4. パラメータ変更に対して壊れにくいか確認する
5. 市場環境・銘柄群・期間を変えても残るか確認する
6. 実運用との差分を見積もる
7. いつ停止すべきか決める
```

WhiteのReality Checkは、同じデータを何度も使ってモデル選択すると、良い結果が「モデルの実力」ではなく偶然である可能性がある、という問題を明示的に扱っています。バックテストでは「良い結果が出た」より先に、「何回試した結果なのか」を記録する必要があります。([Social Science Computing Core][1])

---

# 2. バックテストの種類

## 2.1 ベクトル型バックテスト

pandas / NumPy の配列上で、シグナルと価格系列をまとめて計算する方式です。

向いているもの：

```text
- 大量パラメータの初期検証
- 複数銘柄の横断比較
- forward return 分析
- factor / feature の一次評価
- 低頻度・単純なentry/exit
```

弱いもの：

```text
- 複雑な約定
- 注文変更
- 部分約定
- 板消失
- venue固有ルール
- 状態遷移が複雑な戦略
```

vectorbtはpandas / NumPy上で動き、Numbaなどで高速化され、多数の戦略・パラメータ・銘柄をまとめて検証する用途に強い設計です。特に「たくさん試せる」ことは利点ですが、同時に過剰最適化を加速する点に注意が必要です。([VectorBT][2])

## 2.2 イベント駆動型バックテスト

時系列イベントを1つずつ処理する方式です。

```text
market_data_event
signal_event
order_event
fill_event
position_event
risk_event
```

向いているもの：

```text
- 注文・約定・ポジション管理
- 複数venue
- stop / trailing / OCO
- 板・約定ログ
- live運用に近い検証
```

弱いもの：

```text
- 大量パラメータ探索
- 初期仮説の高速検証
- 実装コスト
```

NautilusTraderは、Rustネイティブのイベント駆動型エンジンで、研究・決定論的シミュレーション・live executionを同じアーキテクチャで扱うことを掲げています。quote tick、trade tick、bar、order book、custom dataを使えるため、約定や複数venueを真面目に扱う段階の参考になります。([GitHub][3])

## 2.3 イベント研究型バックテスト

特定のイベント発生後に、将来リターン・MAE・MFE・約定可能性を見る方式です。

今回の小型perps急騰後ショートのような戦略は、通常の連続売買よりこちらが向いています。

```text
event:
  24h急騰
  出来高急増
  funding高位
  OI増加
  premium縮小
  VWAP割れ

label:
  forward_return_1h
  forward_return_4h
  forward_return_24h
  MAE
  MFE
  funding_cost
  slippage_estimate
```

この方式の利点は、売買ロジックを作る前に「そもそもイベント後に偏りがあるか」を見られることです。

## 2.4 約定シミュレーション型

板、spread、注文方式、部分約定、cancel / replace、rate limit、latencyを扱う方式です。

```text
input:
  order book
  trades
  order intent
  latency model
  fee model

output:
  fill price
  fill ratio
  realized slippage
  queue risk
  cancel failure
```

低流動性・高頻度・perps・板薄銘柄では、ここが本体になります。

Freqtradeの公式ドキュメントでも、通常のローソク足バックテストには「ローソク足内の詳細がないため、価格がhigh/low内にあれば要求価格で全約定、slippageなし」などの仮定があると明示されています。この種の仮定は低流動性戦略では致命的になりやすいです。([Freqtrade][4])

---

# 3. バックテストシステムの基本アーキテクチャ

再利用可能なバックテスト基盤を作るなら、以下のレイヤーに分けるのがよいです。

```text
Data Layer
Feature Layer
Signal Layer
Portfolio / Position Layer
Execution Simulator
Cost Model
Risk Layer
Validation Layer
Reporting Layer
Experiment Registry
```

## 3.1 Data Layer

役割：

```text
- raw data保存
- point-in-time保証
- データ取得元の記録
- 欠損・stale判定
- corporate action / delisting / symbol変更処理
- timezone統一
- version管理
```

重要なのは、**加工済みデータだけ保存しない**ことです。

最低限、以下を分けます。

```text
raw_data
cleaned_data
feature_data
signal_data
trade_log
backtest_result
```

Numeraiのドキュメントでは、特徴量はその時点で既知の属性として設計され、ターゲットは未来リターンであり、era単位で扱うことが推奨されています。また、forward-lookingなターゲットが重なるため、cross validationには注意が必要とされています。この考え方は通常の金融バックテストにもそのまま使えます。([Numerai Docs][5])

## 3.2 Feature Layer

役割：

```text
- 指標計算
- rolling統計
- z-score
- percentile
- lag処理
- neutralization
- feature exposure測定
```

ここでの鉄則は、**全特徴量を「いつの時点で利用可能だったか」で管理すること**です。

```text
feature_timestamp <= decision_timestamp
```

を満たさないものは未来情報です。

## 3.3 Signal Layer

役割：

```text
- entry候補
- exit候補
- no-trade判定
- score計算
- 状態遷移
```

ここでは、売買判断だけでなく **no-trade理由** を残すべきです。

```yaml
signal:
  timestamp:
  symbol:
  state:
  action_candidate:
  score:
  no_trade_reason:
  feature_snapshot:
```

no-trade理由が残らないシステムは、後から改善できません。

## 3.4 Execution Simulator

役割：

```text
- 成行/指値/stopの仮定
- fill price
- fill ratio
- partial fill
- slippage
- spread
- latency
- queue position
- maker/taker fee
```

一般のOHLCVバックテストではここが粗くなりがちです。短期・小型・低流動性・perpでは、ここを粗くすると結果はほぼ使えません。

## 3.5 Cost Model

最低限、以下を分けます。

```text
gross_pnl
fee
slippage
spread_cost
market_impact
borrow_cost
funding_pnl
tax_estimate_optional
net_pnl
```

perpetual futuresではfundingを必ず損益に入れます。Freqtradeのfutures説明でも、futuresでは価格変化に加えてfunding feeが損益に加減されること、また過去funding rateが欠損している場合の代替値設定はバックテスト結果を不正確にし得ることが説明されています。([Freqtrade][6])

---

# 4. データ設計の原則

## 4.1 Point-in-Time

未来情報を使わないための原則です。

悪い例：

```text
今日時点の時価総額ランキングで、過去の銘柄ユニバースを作る
現在残っている銘柄だけで過去検証する
後で修正されたOHLCVだけ使う
発表後にしか分からないデータを発表前に使う
```

良い例：

```text
その日その時点で取引可能だった銘柄だけ使う
上場日・廃止日を持つ
データ取得時刻・更新時刻を記録する
修正前後のバージョンを区別する
```

## 4.2 Survivorship Bias

生き残った銘柄だけで検証すると、成績が良く見えます。

株式なら倒産・上場廃止銘柄、暗号資産ならdelist・流動性消滅・rug・取引停止銘柄が抜けます。

対策：

```text
- symbol masterに listing_start / listing_end を持つ
- delisted symbolも保存
- 検証時点で取引可能だった銘柄だけ使う
- 流動性フィルターを過去時点で評価する
```

## 4.3 Timestamp Alignment

複数データを結合する時は、必ず「利用可能時刻」で合わせます。

```text
bar close time
funding timestamp
OI timestamp
orderbook timestamp
news timestamp
feature available timestamp
decision timestamp
```

`event_time` と `available_time` を分けると事故が減ります。

```yaml
data_record:
  event_time:
  received_time:
  available_time:
  source:
  value:
```

## 4.4 欠損とstale data

欠損を0で埋めると、だいたい壊れます。

```yaml
data_quality:
  missing:
    action: no_trade
  stale:
    action: no_trade
  outlier:
    action: clip_and_flag
  source_disagreement:
    action: downgrade_confidence
```

Numeraiも、特徴量やターゲットの一部がNaNになる場合があり、偽データを作るのではなく利用者に処理を委ねていると説明しています。欠損は「補完すればよい」ではなく、戦略側の状態として扱うべきです。([Numerai Docs][5])

---

# 5. 検証データの分割

## 5.1 基本分割

最低限は以下です。

```text
train:
  ルール・特徴量・閾値の探索

validation:
  閾値・モデル選択

test:
  触らない最終確認

paper/live:
  本当のOOS
```

最も危険なのは、testを見ながら改善することです。
一度でも見て改善したら、それはもうtestではなくvalidationです。

## 5.2 Walk-Forward

時系列に沿って、過去で学習し、未来で評価する方式です。

PyBrokerはwalk-forward analysisを主要機能として掲げており、モデルを学習してバックテストし、実際の取引に近い形で評価する機能を提供しています。ML風の特徴量評価には、単純な1回分割より使いやすいです。([PyBroker][7])

基本形：

```text
Window 1:
  train: 2024-01〜2024-03
  test : 2024-04

Window 2:
  train: 2024-01〜2024-04
  test : 2024-05

Window 3:
  train: 2024-01〜2024-05
  test : 2024-06
```

注意：

```text
- ラベル期間が重なるサンプルを混ぜない
- イベントクラスタを跨いでtrain/testに分けない
- 未来の銘柄ユニバースを使わない
```

## 5.3 Purged / Embargoed Split

金融時系列では、未来リターンをラベルにするとサンプル期間が重なります。

例：

```text
2026-01-01 の24h forward return
2026-01-01 12:00 の24h forward return
```

この2つはラベル期間が重なります。
通常のcross validationだと情報漏洩になります。

対策：

```text
purge:
  testラベル期間と重なるtrainサンプルを削除

embargo:
  test期間の前後に空白期間を置く
```

Kaggle型のleaderboardでも、同じholdoutに繰り返し提出するとholdout自体へ過適合します。Blum and HardtのLadder論文は、繰り返し評価されるleaderboardが過適合される問題を扱っています。これはバックテストのvalidationを何度も見て調整する状況と同じです。([arXiv][8])

---

# 6. 代表的なバイアスと対策

## 6.1 Look-Ahead Bias

未来情報を使うことです。

典型例：

```text
当日終値を使って当日終値で約定
翌日の高値安値を見てentry判定
後から確定するfundingを事前に使う
出来高確定前に出来高条件を使う
```

対策：

```text
- 全featureにavailable_timeを持つ
- entryは次bar以降に遅らせる
- bar close後にしか使えない情報を明示する
- unit testでfeature_timestamp <= decision_timestampを検査
```

## 6.2 Data Snooping

良い結果が出るまで何度も試すことです。

Whiteは、同じデータを何度も使って推論・モデル選択する時、良い結果が偶然である可能性が避けられないと説明しています。これは戦略量産・LLM仮説生成・パラメータ総当たりで特に重要です。([Social Science Computing Core][1])

対策：

```text
- test budgetを決める
- 試行回数を記録する
- benchmarkを先に決める
- holdoutをロックする
- 良い結果が出た後に仮説を書き換えない
```

## 6.3 Overfitting

過去に合わせすぎることです。

危険な兆候：

```text
- パラメータが細かすぎる
- 特定期間だけ強い
- 特定銘柄だけ強い
- 特定exit条件だけで成績が成立
- 少数の大勝ちだけでPFが高い
- costを入れると消える
```

BaileyとLópez de PradoのDeflated Sharpe Ratioは、選択バイアス・バックテスト過剰適合・非正規性を補正する発想です。多数の戦略・パラメータを試す場合、通常のSharpeだけで判断するのは危険です。

## 6.4 Implementation Risk

同じ戦略ロジックでも、バックテストエンジンの実装差で結果が変わるリスクです。

2026年の研究では、複数のOSSエンジンで同じ戦略を走らせた際、コストが入るとエンジン間の結果差が構造的に現れ、特に高回転戦略では差が大きくなることが報告されています。これは「エンジンを変えても同じ結果になる」と思ってはいけない、という実務上かなり重要な指摘です。([arXiv][9])

対策：

```text
- 自作paper traderとOSS結果を照合する
- trade-level logを比較する
- fill price / fee / slippageを分解する
- 最低2系統でsanity checkする
```

---

# 7. コスト・約定モデル

## 7.1 コストの基本式

```text
net_pnl
= price_pnl
+ funding_pnl
+ borrow_or_lending_pnl
- taker_fee
- maker_fee
- spread_cost
- slippage
- market_impact
- transfer_or_gas_cost
```

暗号資産perpsでは最低限これです。

```text
net_pnl = price_pnl + funding_pnl - fee - slippage
```

## 7.2 Slippage Model

単純モデル：

```text
slippage_bps = fixed_bps
```

少し現実的：

```text
slippage_bps = spread_bps / 2 + impact_bps(order_size)
```

板を使うモデル：

```text
market_sell_fill_price:
  order_sizeをbid ladderにぶつけてVWAP算出

market_buy_fill_price:
  order_sizeをask ladderにぶつけてVWAP算出
```

低流動性では、固定bpsより板ベースが望ましいです。

## 7.3 Partial Fill

指値注文では、約定するかどうかが重要です。

```yaml
limit_order:
  price:
  size:
  queue_ahead_estimate:
  traded_volume_after_order:
  fill_ratio:
```

OHLCVだけではqueueは分かりません。
そのため、指値約定を楽観的に扱うと成績が過大評価されます。

## 7.4 Candle内順序問題

1本のローソク足の中で、

```text
open
high
low
close
```

の順序は分かりません。

そのため、

```text
同じ足で利確も損切りも到達
```

した場合の扱いが問題になります。

保守的にするなら、

```text
ロング:
  lowが先
ショート:
  highが先
```

と置くのが安全です。

Freqtradeも、ローソク足内情報不足によりbacktestでは複数の仮定を置いており、StoplossとROIの順序なども仮定されています。こうした仮定は戦略結果に直接影響します。([Freqtrade][4])

---

# 8. 評価指標

## 8.1 Trade-level Metrics

```text
trade_count
win_rate
avg_win
avg_loss
profit_factor
expectancy
median_pnl
tail_loss
max_loss
MAE
MFE
avg_holding_time
time_to_MFE
time_to_MAE
```

短期イベント戦略では、Sharpeよりtrade-level指標が重要なことがあります。

## 8.2 Return-series Metrics

```text
CAGR
annualized_return
annualized_volatility
Sharpe
Sortino
Calmar
max_drawdown
drawdown_duration
VaR
CVaR / expected shortfall
tail ratio
skew
kurtosis
```

QuantStatsはreturn seriesを入力として、Sharpe、win rate、volatility、drawdown、HTMLレポートなどを作れるツールです。ただし、QuantStats自身も「return seriesを分析するもので、離散的なtrade dataとは異なる」と明記しており、trade-level分析の代替ではありません。([GitHub][10])

## 8.3 Event-level Metrics

イベント戦略ではこれが重要です。

```text
event_count
event_to_trade_rate
blocked_rate
no_trade_reason_distribution
forward_return_by_bucket
MAE_by_score_bucket
MFE_by_score_bucket
net_expectancy_by_event_type
slippage_by_liquidity_bucket
```

特に `blocked_rate` と `no_trade_reason_distribution` は、良いシステムほど価値があります。

## 8.4 Robustness Metrics

```text
train_vs_test_decay
walk_forward_stability
parameter_sensitivity
subsample_stability
cross_asset_stability
cost_sensitivity
slippage_sensitivity
regime_sensitivity
```

バックテストで見るべきは、最高成績ではなく **壊れ方** です。

---

# 9. 統計的検証

## 9.1 Bootstrap

結果の不確実性を見る方法です。

PyBrokerはbootstrap metricsを機能として持ち、Profit FactorやSharpe Ratioなどの信頼区間を出す例を提供しています。bootstrap後に下限が悪い場合、見かけ上良い戦略でも信頼できない可能性があります。([PyBroker][11])

注意点：

```text
通常bootstrap:
  return seriesを再標本化

block bootstrap:
  時系列の連続性を少し保つ

event cluster bootstrap:
  イベント群単位で再標本化
```

イベント型・清算カスケード型・低頻度戦略では、通常bootstrapだけでは不十分なことがあります。

## 9.2 White Reality Check

多数のモデルを試した後、「一番良かったモデル」が本当にbenchmarkを上回るかを検定する発想です。

使う場面：

```text
- パラメータを大量に試した
- LLMで仮説を大量生成した
- 複数シグナルを比較した
- 過去データで最良モデルを選んだ
```

Whiteは、十分に多く探せば、実力がないモデルでも良く見えるものが見つかると説明しています。([Social Science Computing Core][1])

## 9.3 Hansen SPA

White Reality Checkに近いが、劣った候補が多い場合の検出力を改善する発想です。

使う場面：

```text
- 複数モデルの中から有望候補を比較
- benchmark比で本当に優越しているか確認
```

## 9.4 Deflated Sharpe Ratio

多数の試行、非正規性、サンプル数不足を考慮してSharpeを補正する発想です。

暗号資産・小型銘柄・ショート戦略は、リターン分布が太い尾を持ちやすく、通常のSharpeが過信されやすいです。Deflated Sharpe Ratioの論文は、選択バイアス・バックテスト過剰適合・非正規性を補正することを目的としています。

## 9.5 Probability of Backtest Overfitting

バックテストが過剰適合している確率を評価する発想です。

BaileyらのPBO論文は、バックテスト過剰適合を確率として扱い、研究プロセスそのものを疑うための枠組みです。戦略シード量産やパラメータ探索を行う場合は、この発想を設計に入れる価値があります。

---

# 10. バックテスト結果を見る順番

いきなり総損益を見ないほうがいいです。

順番はこれです。

```text
1. データ品質
2. イベント数
3. シグナル頻度
4. no-trade理由
5. gross PnL
6. cost控除
7. net PnL
8. MAE / MFE
9. worst cases
10. regime別成績
11. 銘柄別成績
12. 期間別成績
13. パラメータ感度
14. holdout
15. paper/live差分
```

最初に総損益を見ると、都合の良い説明を作りがちです。

---

# 11. よくある誤謬

## 11.1 「バックテストが良いから勝てる」

違います。

正しくは、

```text
バックテストが良い
= その条件では過去に機能したように見える
```

です。

## 11.2 「取引回数が少なくてもPFが高いから良い」

少数の大勝ちに依存している可能性があります。

見るべき：

```text
median_pnl
bootstrap lower bound
worst 5 trades
trade_count
event_count
MFE capture
```

## 11.3 「手数料だけ入れれば十分」

低流動性では不十分です。

必要：

```text
spread
slippage
market impact
partial fill
funding
liquidation fee
borrow
gas / transfer
latency
```

## 11.4 「MLで精度が高いからよい」

分類精度より、損益分布が重要です。

```text
accuracy 55%
でも
負けが大きければ破綻

accuracy 45%
でも
勝ちが大きく負けが小さければ成立
```

## 11.5 「ツールを使えば正しい」

違います。

エンジンごとの実装差が成績に影響します。2026年のimplementation risk研究は、取引コストが入るとバックテストエンジン間で結果差が生じることを示しており、エンジン差そのものをリスクとして扱う必要があります。([arXiv][9])

---

# 12. OSS・ツールの使い分け

## 12.1 役割別の分類

| ツール            | 主用途                         | 強み                                    | 注意                    |
| -------------- | --------------------------- | ------------------------------------- | --------------------- |
| vectorbt       | 高速検証                        | 大量パラメータ・銘柄を高速処理                       | 過剰最適化を加速しやすい          |
| PyBroker       | ML風検証・walk-forward          | walk-forward、bootstrap、cache、並列       | 執行再現は弱い               |
| backtesting.py | 小型ロジック検証                    | シンプルで理解しやすい                           | 複雑なperpsには弱い          |
| Backtrader     | 古典的event-driven設計学習         | broker / commission / analyzer構造      | やや古い                  |
| QuantStats     | 成績レポート                      | return series分析、HTMLレポート              | trade-level分析ではない     |
| CCXT           | データ取得・取引所接続                 | 100以上の取引所を統一API                       | バックテスターではない           |
| Freqtrade      | crypto bot / dry-run参考      | bot運用、dry-run、WebUI                   | 標準backtest仮定に注意       |
| Jesse          | crypto strategy framework参考 | backtest / optimize / live構造          | P1中核には重い              |
| Hummingbot     | execution / connector参考     | CEX/DEX connector、market making       | 研究基盤ではなく実行寄り          |
| NautilusTrader | 本格event-driven              | research-to-live parity、板・custom data | P1には重い                |
| LEAN           | 重厚な汎用エンジン                   | 複数市場、backtest/live/optimize           | crypto低流動性perps専用ではない |

CCXTは100以上の暗号資産取引所を統一APIで扱えるライブラリで、market data、注文、残高などを統一的に扱う目的に向いています。ただし、バックテストエンジンではなく、主にデータ取得・取引所接続レイヤーとして使うべきです。([CCXTドキュメント][12])

LEANはイベント駆動型のプロ向けアルゴリズム取引プラットフォームで、CLIからresearch、backtest、optimize、liveを実行できる構成を持ちます。複数プロジェクトの設計参考にはなりますが、軽量なP1検証には重めです。([GitHub][13])

## 12.2 このプロジェクトなら

今回の低流動性perpsプロジェクトでは、こうです。

```text
P1:
  自作event scanner + paper trader + structured log

P1.5:
  PyBroker: walk-forward / bootstrap / feature検証
  vectorbt: 大量閾値・イベント検証
  QuantStats: return report
  自作: event replay / no-trade分析

P2:
  PyBroker / vectorbt: 仮説カードの初期検証
  ただしtest budget必須

P3:
  Freqtrade / Jesse / Hummingbotを運用設計の参考

P4以降:
  NautilusTraderやHummingbotをexecution候補として比較
```

---

# 13. 最小バックテストシステム仕様

汎用的に作るなら、最小構成は以下です。

## 13.1 データテーブル

```sql
asset_master
  asset_id
  symbol
  venue
  listing_start
  listing_end
  asset_type
  quote_currency

market_bar
  ts
  asset_id
  open
  high
  low
  close
  volume
  source
  received_at

feature_snapshot
  ts
  asset_id
  feature_name
  value
  available_at
  source
  quality_flag

signal_log
  ts
  asset_id
  strategy_id
  state
  action_candidate
  score
  no_trade_reason
  feature_hash

paper_trade_log
  trade_id
  strategy_id
  asset_id
  side
  entry_ts
  entry_price
  exit_ts
  exit_price
  gross_pnl
  fee
  slippage
  funding_pnl
  net_pnl
  mae
  mfe
  exit_reason

experiment_log
  experiment_id
  strategy_id
  code_version
  data_version
  parameter_set
  train_period
  validation_period
  test_period
  created_at
```

## 13.2 最小ロジック

```text
1. raw data取得
2. feature計算
3. feature available_time確認
4. signal生成
5. no-trade判定
6. 仮想約定
7. cost控除
8. MAE/MFE計算
9. 結果保存
10. report生成
```

## 13.3 実験の再現性

最低限保存：

```text
- code commit hash
- data version
- parameter version
- universe definition
- cost model version
- random seed
- generated_at
```

Freqtradeもbacktest出力にreport、market change data、strategy file、config fileなどを含めて再現性を担保する設計を持っています。ただし「同じデータが利用可能である」という前提がある点には注意が必要です。([Freqtrade][4])

---

# 14. バックテスト開発のPhase

## P0：仕様固定

```text
- 戦略仮説を書く
- データ項目を定義する
- available_timeを決める
- cost modelを決める
- no-trade理由を決める
- benchmarkを決める
- test budgetを決める
```

成果物：

```text
DATA_CONTRACT.md
BACKTEST_ASSUMPTIONS.md
COST_MODEL.md
VALIDATION_PLAN.md
```

## P1：最小バックテスト

```text
- 単一戦略
- 単一データソース
- 単純なentry/exit
- gross/net分離
- trade log保存
```

合格条件：

```text
- 同じ入力で同じ結果
- trade-levelで説明可能
- no-tradeも記録
- cost込みnetが出る
```

## P1.5：検証強化

```text
- walk-forward
- bootstrap
- feature exposure
- cost sensitivity
- parameter sensitivity
- event replay
```

## P2：仮説量産

```text
- Hypothesis Card
- LLMによる仮説候補
- test budget
- holdout locked
- PBO/DSR的チェック
```

## P3：Paper運用

```text
- live dataでpaper
- alert
- stale data handling
- manual review
- paper/live差分の準備
```

## P4：Micro-live

```text
- 最小サイズ
- 実約定差分
- slippage検証
- kill switch
```

## P5：Live運用

```text
- サイズ管理
- strategy retirement
- monthly degradation check
- tax/log management
```

---

# 15. バックテスト前チェックリスト

```text
□ 仮説は反証可能か
□ benchmarkはあるか
□ データはpoint-in-timeか
□ 銘柄ユニバースは過去時点で再現可能か
□ delisted / dead assetを含めたか
□ feature available_timeを持つか
□ entryは次bar以降か
□ 手数料を入れたか
□ slippageを入れたか
□ spreadを入れたか
□ funding / borrowを入れたか
□ 最低取引単位・取引所制限を入れたか
□ no-trade理由を保存するか
□ 試行回数を記録するか
□ holdoutを触らない設計か
□ walk-forwardか
□ bootstrapやsubsampleで不確実性を見たか
□ worst casesを確認したか
□ strategy retirement ruleがあるか
```

---

# 16. バックテスト後チェックリスト

```text
□ grossとnetの差はどれくらいか
□ netでまだ正か
□ 少数の大勝ちに依存していないか
□ worst 5 tradesで破綻しないか
□ 期間別に偏りすぎていないか
□ 銘柄別に偏りすぎていないか
□ 特定market regimeだけか
□ パラメータを少し変えても残るか
□ 取引回数は十分か
□ MAEが許容できるか
□ MFEを取り逃がしていないか
□ no-trade理由は妥当か
□ costを2倍にしても残るか
□ slippageを2倍にしても残るか
□ liveで取得できないデータを使っていないか
□ paper運用へ進む価値があるか
```

---

# 17. このプロジェクトへの具体適用

低流動性perpsのモメンタムショートでは、通常のOHLCVバックテストを中核にしないほうがいいです。

中核はこれです。

```text
event scanner
+ paper trader
+ structured log
+ execution risk gate
```

検証対象：

```text
pump:
  return_z
  volume_z

crowding:
  funding_percentile
  funding_slope
  OI_delta
  OI_to_volume
  perp_premium

exhaustion:
  failed_high
  VWAP_loss
  taker_buy_rollover
  premium_contracting
  volume_peakout

execution:
  spread_bps
  depth_1pct
  depth_2pct
  size_to_depth
  stale_data
```

entryではなくexitに寄せる指標：

```text
long_liquidation_spike
OI_drop
funding_normalization
```

理由は、清算やOI急減は「これから崩れる」より「もう崩れた」を示すことが多いからです。

---

# 18. 推奨スタック

## 汎用バックテスト研究基盤

```text
Python
pandas / polars
numpy
duckdb or sqlite
pyarrow / parquet
vectorbt
PyBroker
QuantStats
pytest
```

## 暗号資産データ取得

```text
CCXT
venue native APIs
websocket collector
parquet raw store
```

## event-driven / execution研究

```text
NautilusTrader
Hummingbot
Freqtrade
Jesse
```

## レポート

```text
QuantStats
自作event report
Jupyter
Markdown
```

---

# 19. 最終原則

バックテストシステムは、以下の順序で強くなります。

```text
1. 儲かったか
2. なぜ儲かったか
3. コスト後も残るか
4. 他期間でも残るか
5. 他銘柄でも残るか
6. 少し条件を変えても残るか
7. 実運用でも再現できるか
8. 壊れた時に止められるか
```

最初から目指すべきは、最高のバックテスト結果ではありません。

```text
再現可能で、
疑いやすく、
壊れ方が分かり、
paper/live差分まで追える
バックテスト基盤
```

です。

この方針なら、今回の低流動性perps戦略だけでなく、株式、FX、先物、暗号資産spot、market making、イベントドリブン戦略にも流用できます。

23:17:35.(06/14)

[1]: https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf "270econ.p"
[2]: https://vectorbt.dev/ "Getting started - VectorBT"
[3]: https://github.com/nautechsystems/nautilus_trader "GitHub - nautechsystems/nautilus_trader: Production-grade Rust-native trading engine with deterministic event-driven architecture · GitHub"
[4]: https://www.freqtrade.io/en/stable/backtesting/ "Backtesting - Freqtrade"
[5]: https://docs.numer.ai/numerai-tournament/data "Data | Numerai Docs"
[6]: https://www.freqtrade.io/en/stable/leverage/ "Short / Leverage - Freqtrade"
[7]: https://www.pybroker.com/ "Algorithmic Trading in Python with Machine Learning — PyBroker"
[8]: https://arxiv.org/abs/1502.04585?utm_source=chatgpt.com "The Ladder: A Reliable Leaderboard for Machine Learning Competitions"
[9]: https://arxiv.org/abs/2603.20319?utm_source=chatgpt.com "Implementation Risk in Portfolio Backtesting: A Previously Unquantified Source of Error"
[10]: https://github.com/ranaroussi/quantstats "GitHub - ranaroussi/quantstats: Portfolio analytics for quants, written in Python · GitHub"
[11]: https://www.pybroker.com/en/latest/notebooks/3.%20Evaluating%20with%20Bootstrap%20Metrics.html "Evaluating with Bootstrap Metrics — PyBroker"
[12]: https://docs.ccxt.com/ "CCXT — Unified Crypto Trading API for 100+ Exchanges"
[13]: https://github.com/QuantConnect/Lean "GitHub - QuantConnect/Lean: Lean Algorithmic Trading Engine by QuantConnect (Python, C#) · GitHub"


## 6

結論：**バックテストは「1つのエンジンで過去損益を見るもの」ではなく、複数段階の検証システムとして設計するべきです。**
他プロジェクトでも使える参照資料として、Markdownファイルにまとめました。

[バックテスト設計リファレンスをダウンロード](sandbox:/mnt/data/backtesting_system_reference_2026-06-14.md)

一部の過去添付ファイルは期限切れで再読込できませんでした。ただし、今回のまとめは最新の公式情報と、これまでの議論で固まった StateStrike の方針をもとに整理しています。

## 全体像

バックテストは、最低でも次の4層に分けるのが実務的です。

```text
1. Screening Backtest
   大量候補を高速にふるい落とす

2. Finalist Backtest
   残った候補を会計・注文・funding込みで検証する

3. Mechanical / Latency Backtest
   時刻・遅延・板順序・fill仮定を検査する

4. Paper / Tiny-live Gap Analysis
   backtest と paper/live の差を分解する
```

この分け方をしないと、**速いが雑な検証**と、**遅いが現実に近い検証**が混ざります。結果として、「バックテストでは勝つが本番では負ける」状態を作りやすくなります。

## 役割別のOSS判断

| 役割                 | OSS候補             | 採用判断                       |
| ------------------ | ----------------- | -------------------------- |
| 高速スクリーニング          | vectorbt          | 有力。大量候補のふるい落とし用            |
| 本命検証               | Nautilus Trader   | 採用継続。finalist validation 用 |
| 時刻・遅延・fill検査       | hftbacktest       | 採用継続。ただし補助検査用              |
| 運用Bot設計の参考         | Freqtrade         | 中核採用せず、思想だけ借りる             |
| reality modeling参考 | QuantConnect LEAN | 中核採用せず、設計思想だけ借りる           |
| 簡易検証               | Backtesting.py    | notebook / toy / sanity 用  |
| event-driven旧来系    | Backtrader        | 優先度低。Nautilusと重複しやすい       |

Nautilus Trader は historical data stream を `BacktestEngine` が処理し、結果と performance metrics を出す設計で、高レベルAPIとして `BacktestNode` を提供しています。大きなデータや production workflow では `BacktestNode` と `ParquetDataCatalog` が向くため、StateStrike では finalist validation 側に置くのが妥当です。([NautilusTrader][1])

一方、vectorbt は pandas / NumPy オブジェクト上で動き、Numba や Rust kernels で高速化し、多数の戦略を短時間で検証する思想です。これは finalist 検証ではなく、**大量候補を落とす Screening Backtest** に向きます。([VectorBT][2])

hftbacktest は `exch_ts` と `local_ts` を明確に扱い、local timestamp と exchange timestamp の整合、positive feed latency、event order の検査に強いです。したがって、戦略edgeの主証明ではなく、**時刻・遅延・fill realism の検査装置**として使うべきです。([HftBacktest][3])

## バックテストで最も危険な誤謬

### 1. lookahead bias

未来情報を使うことです。Freqtrade の公式資料でも、backtesting は最初に全 dataframe を読み込むため、indicator や entry/exit signal が未来 candle を見ると結果が歪むと説明されています。典型例として、`shift(-10)`、rolling なしの全期間平均、`iloc[]` の不適切使用などが挙げられています。([Freqtrade][4])

StateStrike 型の設計では、**意思決定に使えるかは `exchange_ts` ではなく `recv_ts_ns <= decision_ts_ns` で判定**するべきです。取引所時刻が過去でも、自分のシステムにまだ届いていないデータは使えません。

### 2. execution cost の過小評価

低流動性銘柄では、fee だけ差し引いても意味が薄いです。最低でも、

```text
fee
spread
slippage
funding
missed trade cost
partial fill
reject
latency
```

を分けます。

QuantConnect LEAN の reality modeling でも、デフォルトモデルは高流動性資産を前提にしており、高出来高取引や低流動性資産では custom reality model が必要だと説明されています。これは StateStrike のように低流動性 perp を狙う場合、特に重要です。([QuantConnect][5])

### 3. Screening と Finalist の混同

高速スクリーニングの結果をそのまま live 判断に使ってはいけません。
vectorbt / pandas で候補を落とし、残ったものだけ Nautilus で event-driven に検証する、という分担が現実的です。

### 4. 未約定の無視

指値が刺さらなかった注文を損益ゼロ扱いすると、maker 系や低流動性銘柄で過大評価になります。
Execution Reality では、未約定後の価格移動を `missed_chase_cost_bps` のように記録すべきです。

## StateStrike への具体的な適用

StateStrike では、こう分けるのが最も現実的です。

```text
P5A: Pre-Compare
  自前
  target universe / feature / cost / eligibility

P5B: Fast Sweep
  vectorbt or pandas fallback
  戦略候補を高速ふるい分け

P5C: Finalist Validation
  Nautilus
  accounting / funding / order lifecycle

P5D: Paper-close-enough
  自前
  intent ledger / fill model / gate

P6: Tiny-live Experimental
  自前
  experimental capital only
  max 1 → 2 → 3 positions

P6.5: Mechanical Calibration
  hftbacktest
  live latency / fill realism calibration
```

Nautilus は `ts_event` と `ts_init` を分け、`ts_init - ts_event` を latency 分析に使える思想を持っています。backtest では `ts_init` で安定ソートされ、live では到着順に処理されるため、StateStrike の `recv_ts_ns / recv_seq` 方針と相性が良いです。([NautilusTrader][6])

## 実装時のチェックリスト

最低限、これを満たすと他プロジェクトでも再利用しやすくなります。

```text
データ:
- truth と derived/corrected を分離
- event time と receipt time を分離
- universe history を保存
- data availability time を持つ

特徴量:
- rolling window のみ使用
- 履歴不足を0埋めしない
- feature provenance を持つ

コスト:
- maker/taker fee を分ける
- funding を別建て
- spread / slippage / missed cost を分ける

検証:
- screening と finalist を分ける
- finalist は event-driven
- latency / fill realism は別検査

本番移行:
- paper ledger を持つ
- decision_id を持つ
- expected / actual / market を結合可能にする
- non-claim を毎回明記する
```

## 最終判断

このプロジェクトでも、他のシストレ開発でも、バックテストは次の順番に分けるのが最も現実的です。

```text
自前 Pre-Compare
  ↓
vectorbt / pandas fast screening
  ↓
Nautilus finalist validation
  ↓
Paper-close-enough
  ↓
Tiny-live experimental
  ↓
Execution Reality
  ↓
hftbacktest latency/fill calibration
```

**OSSは中核を置き換えるものではなく、検証速度・会計・時刻/遅延検査を強化する部品**として使うのが実務的です。

18:26:42.(06/14)

[1]: https://nautilustrader.io/docs/latest/concepts/backtesting/ "Backtesting | NautilusTrader"
[2]: https://vectorbt.dev/ "Getting started - VectorBT"
[3]: https://hftbacktest.readthedocs.io/en/latest/data.html "Data — hftbacktest"
[4]: https://www.freqtrade.io/en/stable/lookahead-analysis/ "Lookahead analysis - Freqtrade"
[5]: https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/key-concepts "Key Concepts - QuantConnect.com"
[6]: https://nautilustrader.io/docs/latest/concepts/data/ "Data | NautilusTrader"


## 7

結論：バックテストは「過去データで利益曲線を作る機能」ではなく、**戦略仮説・データ品質・執行可能性・過剰最適化リスクを段階的に落とす検査装置**として設計すべきです。
汎用プロジェクトでも、MarketLens Strikeでも、実務上の主案は同じです。

```text
Raw Data
  ↓
正規化・検証済みデータ
  ↓
特徴量・シグナル生成
  ↓
Pure Backtest
  ↓
Walk-forward / Out-of-sample / Robustness
  ↓
Execution-aware Backtest
  ↓
Paper / Read-only / Micro-live
  ↓
Live
```

一番重要なのは、**「戦略が正しいか」と「注文したら壊れないか」を分けること**です。
この2つを混ぜると、バックテスト結果はきれいでも、本番では手数料、スリッページ、部分約定、レート制限、状態ズレ、未来情報混入で崩れます。

調査日は **2026-06-14 JST** です。OSSや取引所API仕様は変わるため、採用前に再確認が必要です。

---

# 1. バックテストの定義

バックテストは、過去データ上で取引アルゴリズムをシミュレーションし、過去にどう振る舞ったかを測る手法です。QuantConnectの公式docsも、backtestingを「historical data上でtrading algorithmをsimulationすること」と説明しつつ、過去成績は将来を保証しないと明記しています。([QuantConnect][1])

ただし、実務ではこの定義だけでは不足です。

正しくはこうです。

```text
バックテスト =
  過去データを使って、
  その時点で利用可能だった情報だけで、
  戦略判断・注文・約定・会計・リスク制御を再現し、
  結果の再現性・頑健性・執行可能性を検証する仕組み
```

したがって、単に

```text
シグナル発生
↓
終値で約定
↓
損益計算
```

だけでは不十分です。

---

# 2. 良いバックテストの条件

良いバックテストは、以下を満たします。

| 条件        | 意味                                   |
| --------- | ------------------------------------ |
| 再現可能      | 同じ入力・同じコード・同じ設定で同じ結果になる              |
| 監査可能      | どのデータ、どのパラメータ、どの実験か追跡できる             |
| 未来情報を使わない | その時点で観測不能なデータを使わない                   |
| コスト込み     | 手数料、スプレッド、スリッページ、funding、borrow等を含める |
| 約定不能を表現   | 注文したら必ず約定、にしない                       |
| 過剰最適化を抑制  | 試行回数、パラメータ探索、選抜バイアスを管理する             |
| 本番との接続を意識 | バックテストの注文単位をlive実装へ接続できる             |
| 落とすために使う  | 勝つ戦略を証明するより、弱い仮説を落とす                 |

特に最後が重要です。
バックテストは「勝てる証明」ではなく、**失敗候補を早く安く落とすフィルター**です。

---

# 3. バックテストは4層に分ける

実務では、バックテストを1つの巨大機能として作らないほうがよいです。

## 第1層：Pure Strategy Backtest

戦略そのものに期待値があるかを見る層です。

対象：

```text
エントリー条件
イグジット条件
ポジションサイズ
保有期間
損切り
利確
銘柄選択
リバランス
```

ここでは、執行制約を過剰に入れすぎない。
目的は、まず「この仮説は検証する価値があるか」を判定することです。

ただし最低限、以下は最初から入れるべきです。

```text
手数料
スプレッドまたは簡易スリッページ
funding / borrow
取引サイズ制限
最小注文額
銘柄の上場・廃止
```

## 第2層：Portfolio / Accounting Backtest

ポートフォリオ、資金管理、会計を正しく扱う層です。

対象：

```text
現金
証拠金
レバレッジ
実現損益
未実現損益
手数料
funding
税引前損益
ポジション
エクスポージャー
リスク上限
```

この層が弱いと、戦略は勝っているように見えても、実際には資金制約、証拠金、手数料、ポジション上限で成立しません。

## 第3層：Execution-aware Backtest

実際に注文した場合に壊れないかを見る層です。

対象：

```text
約定遅延
部分約定
約定拒否
板の厚み
スリッページ
limit orderの未約定
cancel中の約定
modify中の約定
API rate limit
取引所ごとのtick size / lot size
```

この層は、OHLCVだけでは不十分になることがあります。
板や約定履歴が必要になる戦略もあります。

## 第4層：Paper / Read-only / Micro-live

これは厳密にはバックテストではありません。
現在の実データ流で運用システムが壊れないかを見る工程です。

| 段階                       | 目的            | 実注文 |
| ------------------------ | ------------- | --- |
| Backtest                 | 過去データで戦略検証    | なし  |
| Execution-aware Backtest | 執行制約を過去データで検証 | なし  |
| Paper                    | 現在データで状態管理を検証 | なし  |
| Micro-live               | 極小額で実約定を検証    | あり  |
| Live                     | 本番            | あり  |

Paperをバックテストの代替にしてはいけません。
Paperは「現在の通信・状態管理・API制限」の検査です。

---

# 4. 推奨アーキテクチャ

汎用的には、以下の構造が安全です。

```text
backtest/
  data/
    raw_store
    normalized_store
    feature_store
    data_quality
    symbol_master

  core/
    engine
    clock
    event_bus
    portfolio
    accounting
    broker_sim
    venue_sim
    order_book_sim
    fill_model
    cost_model
    risk_model

  strategy/
    signal
    sizing
    portfolio_construction
    exit_rules

  validation/
    walk_forward
    out_of_sample
    robustness
    bootstrap
    trial_ledger
    promotion_gate

  reports/
    metrics
    trade_log
    equity_curve
    drawdown
    diagnostics
```

実装上の中心概念はこれです。

```text
DataEvent
Signal
TargetPosition
OrderIntent
Order
Fill
Position
PortfolioSnapshot
BacktestRun
TrialRecord
```

重要なのは、**SignalとOrderを分けること**です。

悪い設計：

```text
Strategyが直接 buy() / sell() を呼ぶ
```

良い設計：

```text
Strategy
  ↓
Signal
  ↓
TargetPosition
  ↓
OrderPlanner
  ↓
OrderIntent
  ↓
BrokerSim / VenueAdapter
```

これにより、同じ戦略を

```text
バックテスト
paper
Bitget
Hyperliquid
他取引所
```

に展開しやすくなります。

---

# 5. データ設計

バックテストの品質は、ほぼデータ品質で決まります。

## データの層

```text
raw
  取得したまま。絶対に上書きしない。

normalized
  時刻、銘柄、型、単位、欠損、重複を整理したもの。

features
  その時点で利用可能な情報だけから作った特徴量。

signals
  戦略が使う売買判断。

results
  backtest runの出力。
```

## 最低限持つべき時刻

金融データでは、単一の`timestamp`だけでは足りません。

| 列              | 意味             |
| -------------- | -------------- |
| `event_ts`     | 市場でイベントが発生した時刻 |
| `exchange_ts`  | 取引所が付与した時刻     |
| `received_ts`  | 自システムが受信した時刻   |
| `available_at` | 戦略が使えるようになった時刻 |
| `bar_open_ts`  | ローソク足開始時刻      |
| `bar_close_ts` | ローソク足終了時刻      |

バックテストでは、**`available_at`より前にそのデータを使ってはいけません**。

## データ品質チェック

最低限これを検査します。

```text
欠損
重複
時刻逆転
異常値
ゼロ出来高
スプレッド異常
価格ジャンプ
銘柄名変更
上場・廃止
取引停止
タイムゾーン
粒度の混在
API取得制限
```

仮想通貨ではさらに以下が必要です。

```text
funding rate
open interest
liquidation
long/short ratio
mark price
index price
oracle price
上場直後の薄い板
取引所ごとのシンボル差
```

---

# 6. 未来情報混入を防ぐ

バックテストで最も危険なのは、lookahead biasです。

Freqtradeの公式docsでも、backtestingでは全timestampを読み込み、indicatorを一括計算するため、未来のローソク足を参照すると結果が falsify されると説明されています。([Freqtrade][2])

典型例：

```python
# 悪い例：未来を見ている
df["future_return"] = df["close"].shift(-1) / df["close"] - 1
df["signal"] = df["future_return"] > 0
```

より微妙な例：

```python
# 悪い例：当日終値を使って、同じ終値で約定した扱い
df["ma"] = df["close"].rolling(20).mean()
df["signal"] = df["close"] > df["ma"]
# 同じbarのcloseでentry
```

実務ルール：

```text
1. signalはbar close後に確定
2. 注文は次bar以降で発生
3. 特徴量は必ずlagを明示
4. available_at列を持つ
5. 未来方向のshift(-n)は禁止。ただしlabel生成時だけ隔離する
6. label列とfeature列を同じテーブルで不用意に混ぜない
```

ML系では特に、label生成とfeature生成を完全に分けるべきです。

---

# 7. バックテスト方式の種類

## 1. ベクトル型バックテスト

pandas / NumPy / Polarsなどで一括計算する方式です。

向くもの：

```text
大量パラメータ探索
日足・時間足の戦略
単純なentry/exit
ランキング戦略
ポートフォリオ検証
```

弱いもの：

```text
部分約定
注文状態
cancel race
latency
板のqueue position
複雑な注文管理
```

vectorbtはこの領域に強く、公式docsではpandas / NumPy上で動き、NumbaやRustで高速化し、多数の戦略を高速に検証できると説明されています。([VectorBT][3])

## 2. イベント駆動型バックテスト

市場イベント、注文、約定、ポートフォリオ更新を時系列に処理する方式です。

向くもの：

```text
複雑な注文
複数銘柄
ポートフォリオ管理
実運用と近い検証
```

弱いもの：

```text
実装コストが高い
遅くなりやすい
デバッグが難しい
```

NautilusTraderはこの方向に強く、公式docsではBacktestEngineがhistorical data streamを処理し、Cache、MessageBus、Portfolio、Strategies、Execution Algorithmsなどのシステム実装を使ってsimulationすると説明されています。([NautilusTrader][4])

## 3. Market replay / Order book replay

実際の板・約定履歴を時系列に再生し、注文がどう約定したかを近似する方式です。

向くもの：

```text
market making
短期売買
板厚依存の戦略
maker注文
queue positionが重要な戦略
```

弱いもの：

```text
データ量が大きい
実装が重い
完全再現は難しい
```

HftBacktestはこの領域に特化しており、公式docsではfeed latency、order latency、queue position、L2/L3 order book、trade tickを考慮すると説明されています。([HftBacktest][5])

## 4. ハイブリッド型

最初はベクトル型で候補を絞り、残った戦略だけイベント駆動・execution-awareで検証します。

実務ではこれが最も現実的です。

```text
高速スクリーニング
  vectorized

正式評価
  自前BacktestCore

執行検証
  event-driven / execution-aware

HFT検証
  order book replay
```

---

# 8. 約定モデル

バックテストの損益は、約定モデルで大きく変わります。

## OHLCVだけの場合

OHLCVでは、bar内の価格順序が分かりません。

同じローソク足で

```text
highに到達
lowに到達
```

していても、どちらが先かは分かりません。

したがって、保守的に扱う必要があります。

| 注文                             | 保守的な扱い                             |
| ------------------------------ | ---------------------------------- |
| market                         | 次bar open、または次bar VWAP近似           |
| limit buy                      | low <= limit だけでは即約定にしない。条件を厳しめにする |
| limit sell                     | high >= limit だけでは即約定にしない          |
| stop loss / take profitが同一bar内 | 不利な順序で処理                           |
| closeでsignal                   | 同じcloseでは約定させない                    |

## Tradesがある場合

約定履歴があれば、OHLCVより現実に近くできます。

```text
自分の注文価格に市場取引が当たったか
その時刻の出来高は十分か
自分の注文サイズが市場出来高に対して大きすぎないか
```

ただし、tradesだけでは板に並んだ自分のqueue positionは分かりません。

## L2 / L3板がある場合

板があれば、より精密なfill simulationが可能です。

見るもの：

```text
best bid / ask
spread
depth
queue position
order latency
cancel latency
trade-through
板消失
```

maker系、HFT系、短期スキャル系ではここが重要です。

---

# 9. コストモデル

コストを甘く見ると、ほぼ確実に過大評価になります。

最低限入れるもの：

```text
maker fee
taker fee
spread cost
slippage
funding
borrow cost
withdrawal / transfer cost
税引前・税引後の区別
```

仮想通貨perpでは特にこれが必要です。

```text
funding受払い
mark priceとlast priceの差
index price
oracle制約
liquidation price
maintenance margin
レバレッジ変更
```

短期売買では、少しのコスト差で結果が反転します。

例：

```text
1回あたり期待値: +4 bps
往復手数料: -6 bps
スリッページ: -3 bps

実質期待値: -5 bps
```

手数料前の勝ち戦略は評価対象外にすべきです。
最低ラインは、**手数料・funding・保守的スリッページ後に残ること**です。

---

# 10. レート制限・API制約もバックテスト対象にする

多くのバックテストは、注文を無制限に出せる前提になっています。
実運用ではこれは誤りです。

取引所ごとに以下があります。

```text
rate limit
最小注文額
tick size
lot size
最大注文数
最大ポジション
reduceOnly制約
post-only拒否
market order制約
cancel制約
nonce制約
WebSocket断
REST遅延
```

Hyperliquidでは、`expiresAfter`がstaleになってcancelされると通常の5倍のaddress-based rate limitを消費します。また、`modify`、`batchModify`、`scheduleCancel`、`reserveRequestWeight`などの取引所固有機能があります。([Hyperliquid Docs][6])

さらに、Hyperliquidのnonceはsigner単位で管理され、100個の高いnonceを保持する仕様です。公式docsでは、自動戦略でAPI walletをプロセスごとに分け、0.1秒ごとにbatchし、ALOとIOC/GTCを分けることが推奨されています。([Hyperliquid Docs][7])

これは、バックテストでも以下を再現すべきという意味です。

```text
注文頻度上限
cancel頻度上限
modify頻度上限
rate limit逼迫時の新規注文停止
stale expiresAfterのペナルティ
nonce衝突時のUNKNOWN状態
WebSocket欠落後のreconcile
```

---

# 11. 過剰最適化とデータスヌーピング

バックテストの最大の統計的リスクは、過剰最適化です。

WhiteのReality Check論文では、同じデータを推論やモデル選択に何度も使うと、良い結果が偶然出る可能性があると説明されています。([Social Science Computing Core][8])

BaileyらのDeflated Sharpe Ratio論文でも、多数の戦略・パラメータを探索する場合、試行回数を管理しないバックテストは評価不能に近い、という問題が指摘されています。

さらに、Probability of Backtest Overfittingの研究では、通常のhold-outが投資バックテストでは不安定になり得るため、PBOやCSCVのような枠組みが提案されています。

実務で必要な対策：

```text
1. Trial Ledgerを残す
2. 試した全パラメータを記録する
3. 最良結果だけを報告しない
4. walk-forwardを使う
5. out-of-sampleを固定する
6. parameter stabilityを見る
7. ランダム期間でも崩れないか確認する
8. 銘柄入れ替えでも崩れないか確認する
9. Deflated Sharpe / Reality Check / PBOを必要に応じて使う
```

特に重要なのは **Trial Ledger** です。

```text
run_id
strategy_id
git_commit
data_version
universe
time_range
parameters
fees
slippage_model
fill_model
random_seed
metrics
notes
decision
```

これがないと、「何回試したうちの勝ち結果か」が分からず、結果を信用できません。

---

# 12. Walk-forward設計

単純なtrain/test分割だけでは弱いです。
時系列では、未来から過去に戻れません。

代表的な分割：

```text
固定OOS
  例: 2021-2024で開発、2025で検証

rolling walk-forward
  train 180日 → test 30日
  30日ずつ前進

anchored walk-forward
  train開始日は固定
  testだけ前進

purged / embargo
  label期間が重なるML戦略で、情報漏洩を避ける
```

実務での推奨：

```text
短期売買:
  rolling walk-forward

長期ポートフォリオ:
  anchored + regime別評価

ML:
  purged / embargo + OOS固定

仮想通貨:
  bull / bear / crash / sideways / low liquidity を分ける
```

見るべきは、最良パラメータではなく、**周辺パラメータでも利益が残るか**です。

悪い例：

```text
window=17だけ勝つ
window=16,18は負ける
```

良い例：

```text
window=14〜24の範囲で概ね残る
```

---

# 13. 指標

損益だけでは不足です。

## 基本指標

```text
総損益
年率リターン
最大ドローダウン
Sharpe
Sortino
Calmar
Profit Factor
勝率
平均利益
平均損失
期待値
取引回数
平均保有時間
```

## 実務で重要な指標

```text
手数料合計
slippage合計
funding損益
turnover
exposure
capacity
最大連敗
日次損失最大
月次損失最大
tail loss
急落時損益
約定率
部分約定率
cancel失敗率
注文拒否率
```

## 戦略評価で見るべきもの

| 指標                  | 見る理由               |
| ------------------- | ------------------ |
| Net PnL             | コスト後に残るか           |
| Max DD              | 生き残れるか             |
| Profit Factor       | 利益と損失の比率           |
| Trade count         | 統計的に少なすぎないか        |
| Turnover            | 手数料で死なないか          |
| Exposure            | 常時リスクを取っているだけではないか |
| Tail loss           | 一撃死しないか            |
| Parameter stability | 過剰最適化ではないか         |
| OOS performance     | 未知期間でも残るか          |
| Capacity            | サイズを上げても成立するか      |

Sharpeだけで判断しないほうがよいです。
非正規分布、fat tail、少数トレード、過剰最適化で簡単に歪みます。

---

# 14. よくある失敗

## 1. 同じ終値で判断して同じ終値で約定

非常に多いミスです。

```text
closeでMAを計算
closeでsignal発生
同じcloseでentry
```

これは未来情報に近い扱いになります。
実務では、少なくとも次bar以降で約定させるべきです。

## 2. 手数料なし

短期売買では致命的です。

```text
手数料前 +20%
手数料後 -15%
```

は珍しくありません。

## 3. スリッページなし

market注文、薄い板、小型銘柄、急変時では結果が激変します。

## 4. survivorship bias

現在残っている銘柄だけで過去検証すると、上場廃止・無価値化・流動性消滅を無視します。

株式では特に危険です。
仮想通貨でも、上場廃止銘柄、小型銘柄、取引停止、極端な流動性低下があります。

## 5. dynamic universeの未来情報

例：

```text
今の時価総額トップ100で、3年前から検証する
```

これは未来の勝者だけを選んでいます。

## 6. パラメータ探索の記録なし

```text
1000回試して一番良い結果だけ採用
```

これは研究ではなく、結果の選別です。

## 7. 約定を楽観的に置く

```text
limit priceにタッチしたら全約定
```

実際には、自分より前に並んでいる注文があります。
maker戦略では特に危険です。

## 8. API制約を無視

```text
毎秒100回cancelできる前提
```

実取引所では通りません。

---

# 15. OSS選定

OSSは使えますが、**中核を丸ごと委ねるか、部品として使うか**を分けるべきです。

## 現実的な分類

| OSS            | 強み                                     | 弱み                       | 実務での扱い        |
| -------------- | -------------------------------------- | ------------------------ | ------------- |
| vectorbt       | 高速探索、大量パラメータ、pandas/NumPy              | 複雑な注文状態やpartial fillには弱い | research補助    |
| PyBroker       | walk-forward、bootstrap、ML寄り            | 取引所固有制約は薄い               | ML/特徴量検証補助    |
| Freqtrade      | crypto bot、backtest、dry-run、exchange実装 | 独自bot設計に寄る               | 外部ベンチマーク      |
| NautilusTrader | event-driven、backtest/live近似           | 重い、学習コスト高い               | execution POC |
| HftBacktest    | L2/L3、latency、queue position           | データ要求が重い                 | HFT/maker後段   |
| Backtrader     | 古典的で情報量が多い                             | 現代crypto perp固有制約には弱い    | 非主力           |
| Backtesting.py | 軽量で使いやすい                               | 本格評価には不足                 | 小実験用          |
| LEAN           | 大規模・多資産・live接続                         | 重い、C#中心                  | 大規模案件候補       |

vectorbtは高速な検証に向きますが、GitHub上ではApache 2.0 with Commons Clauseと記載されているため、商用配布やSaaS化を考えるならライセンス確認が必要です。([GitHub][9])

PyBrokerはwalk-forward、bootstrap、cache、parallel computationを公式に掲げています。([PyBroker][10])

Freqtradeはbacktesting機能を持ち、backtestingにはhistorical dataが必要で、profit calculationにはfeesを含むと公式docsで説明されています。([GitHub][11])
ただし、FreqtradeのHyperliquid notesでは、historic Hyperliquid dataについて制約が明記されています。([Freqtrade][12])

LEANはopen-source algorithmic trading engineで、research、backtesting、live trading向けと説明されています。([cdn.quantconnect.com][13])
Backtraderはbacktesting and trading向けのPython frameworkです。([Backtrader][14])
Backtesting.pyはhistorical candlestick dataで戦略のviabilityを推定する軽量frameworkです。([Kernc][15])

## OSS採用の実務判断

主案：

```text
自前BacktestCoreを正本にする
OSSは補助・比較・検証加速に使う
```

理由：

```text
1. データ契約を自分で管理できる
2. Trial Ledgerを自分の形式で残せる
3. live executionとの接続を設計できる
4. 取引所固有制約を入れられる
5. OSSの都合に戦略設計を寄せなくて済む
```

---

# 16. MarketLens Strikeへの適用

このプロジェクトでは、以下が現実的です。

```text
src/marketlens/backtest/
  core/
    engine.py
    data_contract.py
    portfolio.py
    accounting.py
    fills.py
    fees.py
    funding.py
    slippage.py
    metrics.py
    walk_forward.py
    trial_ledger.py

  adapters/
    vectorbt_adapter.py
    pybroker_adapter.py
    freqtrade_export.py

src/marketlens/execution_sim/
  order_intent.py
  venue_constraints.py
  fill_model.py
  cancel_race.py
  rate_limit_model.py
  hyperliquid_constraints.py
  bitget_constraints.py
```

## MarketLens Strikeで特に重要なこと

```text
1. StrategyはOrderを出さない
2. StrategyはSignalまたはTargetPositionを出す
3. OrderIntentに変換するのはOrderPlanner
4. BacktestとLiveでOrderIntentを共有する
5. Hyperliquid/Bitget固有制約はVenueConstraintに閉じ込める
```

推奨フロー：

```text
P0: Raw data recorder
P1: Data quality ledger
P2: Pure Backtest
P3: Walk-forward
P4: Execution-aware Backtest
P5: PaperHyperliquidAdapter
P6: Read-only live observation
P7: Micro-live
```

特にデータ面では、Bitgetのhistorical candlestick APIは最大200件返却、最大query range 90日という制約があります。([Bitget][16])
CoinalyzeはAPI keyあたり40 calls/minで、intradayは1500〜2000 datapointsのみ保持し、古いintraday dataは日次で削除されます。([Coinalyze][17])

つまり、MarketLens Strikeでは、OSS導入より先に

```text
データを継続保存する
データ可用性ledgerを作る
欠損期間を明示する
```

ことが重要です。

---

# 17. 実装時のデータ契約

最低限のBarデータ：

```text
symbol_id
venue
open_ts
close_ts
available_at
open
high
low
close
volume
quote_volume
trade_count
source
data_version
```

perp用：

```text
funding_rate
funding_time
open_interest
mark_price
index_price
liquidation_buy
liquidation_sell
long_short_ratio
```

注文用：

```text
order_id
client_order_id
strategy_id
symbol_id
side
order_type
time_in_force
price
size
reduce_only
created_at
sent_at
accepted_at
status
```

約定用：

```text
fill_id
order_id
symbol_id
side
price
size
fee
fee_currency
liquidity
exchange_ts
received_ts
```

BacktestRun用：

```text
run_id
strategy_id
git_commit
data_version
start_ts
end_ts
universe
parameters
fee_model
slippage_model
fill_model
risk_model
random_seed
created_at
```

---

# 18. バックテストエンジンの最小責務

BacktestCoreは、最低限これを保証します。

```text
1. 時刻順にイベントを処理する
2. 未来情報を読ませない
3. シグナルと注文を分離する
4. 約定モデルを差し替え可能にする
5. コストモデルを差し替え可能にする
6. ポートフォリオ会計を一元化する
7. 全取引ログを出す
8. 全runを記録する
9. 同じrunを再現できる
```

やってはいけないこと：

```text
戦略内でcashやpositionを勝手に更新する
戦略内で手数料を個別計算する
シグナル生成と約定処理を同じ関数に混ぜる
結果だけ保存してtrade logを保存しない
```

---

# 19. レポートに必ず含めるもの

バックテスト結果には、損益グラフだけでなく、以下を含めるべきです。

```text
run metadata
data coverage
data gaps
universe definition
cost assumptions
fill assumptions
parameter set
trade list
equity curve
drawdown curve
monthly returns
fee summary
slippage summary
funding summary
position exposure
risk breaches
OOS result
walk-forward result
robustness result
decision
```

特に、レポートには必ずこう書くべきです。

```text
この結果は、どのデータ、どのコスト、どの約定仮定、どの試行回数のもとで出たものか。
```

これがないバックテストは、意思決定資料として弱いです。

---

# 20. 戦略を昇格させる基準

Promotion Gateを作ります。

例：

```text
Gate 1:
  手数料後で利益がある

Gate 2:
  funding / slippage後でも利益がある

Gate 3:
  OOSで利益がある

Gate 4:
  walk-forwardで崩れない

Gate 5:
  パラメータ周辺で安定

Gate 6:
  最大DDが許容内

Gate 7:
  trade countが十分

Gate 8:
  execution-awareで利益が残る

Gate 9:
  paperで状態不一致がない

Gate 10:
  micro-liveで想定外挙動がない
```

Gateに落ちた戦略は、原則として本番に進めない。
例外を認める場合は、理由をTrial Ledgerに残す。

---

# 21. バックテスト設計の主案

汎用プロジェクトでも、MarketLens Strikeでも、主案はこれです。

```text
自前BacktestCore
  ↓
vectorbt / PyBrokerで探索補助
  ↓
ExecutionSimulator自前実装
  ↓
必要に応じてNautilusTrader / HftBacktestでPOC
  ↓
Paper
  ↓
Micro-live
```

## 自前BacktestCoreに入れるもの

```text
データ契約
時刻管理
会計
手数料
funding
slippage
注文・約定ログ
walk-forward
trial ledger
metrics
report
```

## OSSに任せるもの

```text
大量パラメータ探索
可視化
比較用ベンチマーク
研究用ノートブック
外部bot挙動確認
```

## 自前で持つべきもの

```text
データ可用性ledger
取引所制約
OrderIntent
ExecutionSimulator
Promotion Gate
Trial Ledger
Live接続前提の状態管理
```

---

# 22. 代替案

## 代替案A：Freqtrade中心

メリット：

```text
crypto botとしてすぐ使える
backtest / dry-run / liveが揃っている
exchange実装がある
```

デメリット：

```text
Freqtrade流のstrategy構造に寄る
独自OrderRouterと競合する
Hyperliquidなどの取引所固有制約を深く扱うには逃げ道が必要
データ制約は解決しない
```

判断：

```text
本体中核ではなく、外部ベンチマーク用
```

## 代替案B：NautilusTrader中心

メリット：

```text
event-driven
backtest/liveの差を縮めやすい
注文・会計・venueの概念が強い
```

デメリット：

```text
学習コストが高い
既存プロジェクト構造との接続が重い
最初の仮説検証には過剰
```

判断：

```text
execution-aware POCとして採用候補
```

## 代替案C：vectorbt中心

メリット：

```text
高速
パラメータ探索に強い
研究が速い
```

デメリット：

```text
注文状態やpartial fillには弱い
本番執行制約の再現には不十分
ライセンス確認が必要
```

判断：

```text
研究補助として採用
```

## 代替案D：完全自前

メリット：

```text
要件に完全一致
取引所制約を正確に入れられる
監査性を作りやすい
```

デメリット：

```text
実装コストが高い
バグを自分で抱える
検証に時間がかかる
```

判断：

```text
Coreは自前、探索・可視化はOSS補助
```

---

# 23. トレードオフ

| 選択               | 速度 | コスト | リスク |     効果 |
| ---------------- | -: | --: | --: | -----: |
| 自前BacktestCore   |  中 |   中 | 低〜中 |      高 |
| vectorbt補助       |  高 |   低 |   中 |    中〜高 |
| PyBroker補助       |  中 | 低〜中 |   中 |      中 |
| Freqtrade外部比較    |  高 |   低 |   中 |      中 |
| NautilusTrader中核 |  低 |   高 |   中 |      高 |
| HftBacktest      |  低 |   高 |   中 | HFTでは高 |
| Backtesting.py   |  高 |   低 |   中 |  小実験向け |
| LEAN             |  低 |   高 |   中 | 大規模では高 |

実務的には、

```text
早く落とす:
  vectorbt / PyBroker

正式評価:
  自前BacktestCore

執行事故を潰す:
  自前ExecutionSimulator

本格event-driven:
  NautilusTrader POC

板・latency:
  HftBacktest
```

です。

---

# 24. 最小実装順

次の3つから始めるのが最も現実的です。

## 1. Data Availability Ledger

目的：

```text
どの銘柄、どの期間、どの粒度、どの特徴量が使えるかを記録する
```

これがないと、バックテスト結果は信用できません。

## 2. BacktestCore v0

対象：

```text
OHLCV
fees
funding
basic slippage
position accounting
trade log
metrics
walk-forward
trial ledger
```

ここでまず、手数料後・funding後に利益が残るかを確認します。

## 3. ExecutionSimulator v0

対象：

```text
tick size
lot size
min notional
partial fill
limit non-fill
latency
rate limit
cancel race
modify race
```

HyperliquidやBitgetなど、実取引所に進む前の安全層です。

---

# 25. 最終まとめ

バックテストシステムの核心はこれです。

```text
1. データを疑う
2. 未来情報を遮断する
3. 手数料・スリッページ・fundingを入れる
4. 約定不能を表現する
5. 試行回数を記録する
6. OOS / walk-forwardで落とす
7. execution-awareでさらに落とす
8. paperとmicro-liveを別工程として扱う
```

MarketLens Strikeでは、以下の方針が最も壊れにくいです。

```text
自前BacktestCoreを正本にする
vectorbt / PyBrokerは探索補助
Freqtradeは外部ベンチマーク
NautilusTrader / HftBacktestは後段POC
Hyperliquid / Bitget制約はExecutionSimulatorに入れる
```

バックテストは「勝てると信じるための資料」ではなく、**本番に進めてはいけない戦略を落とすための検査体系**として作るべきです。

18:41:21.(06/14)

[1]: https://www.quantconnect.com/docs/v2/cloud-platform/backtesting "Backtesting - QuantConnect.com"
[2]: https://www.freqtrade.io/en/stable/lookahead-analysis/ "Lookahead analysis - Freqtrade"
[3]: https://vectorbt.dev/ "Getting started - VectorBT"
[4]: https://nautilustrader.io/docs/latest/concepts/backtesting/ "Backtesting | NautilusTrader"
[5]: https://hftbacktest.readthedocs.io/ "HftBacktest — hftbacktest"
[6]: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint "Exchange endpoint | Hyperliquid Docs"
[7]: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/nonces-and-api-wallets "Nonces and API wallets | Hyperliquid Docs"
[8]: https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf "270econ.p"
[9]: https://github.com/polakowo/vectorbt "GitHub - polakowo/vectorbt: The backtesting engine that gives you an unfair advantage. Run thousands of trading ideas before others finish one. · GitHub"
[10]: https://www.pybroker.com/ "Algorithmic Trading in Python with Machine Learning — PyBroker"
[11]: https://github.com/gcarq/freqtrade/blob/develop/docs/backtesting.md "freqtrade/docs/backtesting.md at develop · freqtrade/freqtrade · GitHub"
[12]: https://www.freqtrade.io/en/stable/exchanges/ "Exchange-specific Notes - Freqtrade"
[13]: https://cdn.quantconnect.com/docs/i/Quantconnect-Lean-Engine-Python.pdf "Document"
[14]: https://www.backtrader.com/ "Welcome - Backtrader"
[15]: https://kernc.github.io/backtesting.py/ "Backtesting.py - Backtest trading strategies in Python"
[16]: https://www.bitget.com/api-doc/contract/market/Get-History-Candle-Data "Get Historical Candlestick | Bitget API"
[17]: https://api.coinalyze.net/v1/doc/ "Coinalyze API documentation. Free crypto data API."


## 8

# バックテストシステム設計・実装リファレンス

過去にアップロードされた一部ファイルは期限切れのため、ここではこれまでの設計議論と、公開論文・公式ドキュメント・主要OSSの再確認をもとに、単一Markdownとして再構成します。期限切れファイルの厳密な内容まで反映したい場合は、再アップロードしてください。

---

## 0. 結論

バックテストは、**「勝てる戦略を証明する道具」ではなく、「勝って見えるだけの戦略を落とすための検査装置」**として設計するべきです。

最も重要な考え方は次です。

```txt
壊れたデータで判断しない。
未来情報を使わない。
約定を楽観しない。
コストを分解する。
試した候補を全部残す。
1つの良いバックテストだけで採用しない。
人間にもAIにも、根拠・仮定・未検証項目を説明する。
```

バックテスト基盤を作るなら、最低限この構造にします。

```txt
Data Layer
  ↓
Point-in-time Feature / Universe Layer
  ↓
Strategy / Signal Layer
  ↓
Execution Reality Layer
  ↓
Cost / Risk / Accounting Layer
  ↓
Validation Layer
  ↓
Trial Ledger / Provenance Layer
  ↓
Human / AI Report Layer
```

バックテストシステムの完成形は、単なる `strategy.backtest()` ではありません。

```txt
完成形 =
  データ品質監査
  + 未来リーク防止
  + 約定現実性
  + コスト分解
  + 過適合検査
  + 全trial保存
  + 人間/AI向け説明
  + paper/liveとの差分監査
```

PBO論文は、標準的なhold-outが投資バックテストでは不可靠になりやすく、CSCVでバックテスト過適合確率を推定する枠組みを提案しています。特に、同じ有限データ上で多数の戦略候補を試すとfalse positivesが増える点を強く警告しています。
DSRは、選択バイアス、バックテスト過適合、非正規リターン、試行回数によるSharpeの膨らみを補正するための考え方です。

---

## 1. バックテストとは何か

バックテストとは、過去データを使って、売買ルール・予測モデル・ポートフォリオルールが過去にどう動いたかを検証する仕組みです。

ただし、バックテストの意味は段階によって違います。

| 段階                  | 目的         | 判断してよいこと             | 判断してはいけないこと     |
| ------------------- | ---------- | -------------------- | --------------- |
| Toy / demo          | 実装確認       | コードが動くか              | 戦略が有効か          |
| Bar-based backtest  | 方向性確認      | ロジックに見込みがあるか         | 実運用で約定できるか      |
| Cost-aware backtest | 基本現実性      | 手数料後も残るか             | 板薄銘柄で本当に約定するか   |
| L2 replay backtest  | 約定現実性      | 注文サイズと板厚に耐えるか        | 自分の注文が市場を変える影響  |
| Paper trading       | 実時系列での運用確認 | API、fill、latencyが近いか | 実資金で同じ結果になるか    |
| Tiny-live           | 小額実弾確認     | 実コスト・約定差分            | 大きい資金でのcapacity |
| Production          | 実運用        | 収益とリスク管理             | 過去検証の永続性        |

一言で言えば、バックテストは **段階的な疑いのプロセス** です。

```txt
この戦略は勝つか？
  ではなく、

この戦略を落とす理由はないか？
  を調べる。
```

---

## 2. バックテストが証明できること・できないこと

### 証明しやすいこと

```txt
コードが仕様通り動くか
売買ルールが過去データ上で発火するか
手数料・スリッページを引いても残るか
期間ごとに成績が極端に偏っていないか
パラメータが少し変わっても壊れないか
試した候補の中で、選ばれた候補がOOSで崩れていないか
```

### 証明できないこと

```txt
将来も勝てること
市場構造が変わっても有効なこと
実運用で必ず同じ価格で約定できること
API障害・板消失・取引停止・規制変更に耐えること
大きい資金を入れても同じ成績になること
```

### よくある誤解

```txt
良いバックテスト = 良い戦略
```

これは誤りです。

正しくはこうです。

```txt
良いバックテスト
  =
  まだ落とす理由が見つかっていない候補
```

---

## 3. バックテスト基盤の最小原則

### 原則1: データを疑う

バックテストの結果は、入力データ以上には正しくなりません。

必要な考え方:

```txt
Rawを捨てない
正規化データだけを真実にしない
データ取得時刻を残す
データ欠損を記録する
schema versionを残す
data manifestを残す
```

### 原則2: 時刻を疑う

金融・時系列MLでは、時刻が壊れると未来リークが起きます。

最低限、以下を分けます。

```txt
event_time:
  市場でイベントが起きた時刻

available_time:
  Botや研究システムがその情報を使えるようになった時刻

decision_ts:
  戦略が判断した時刻

send_ts:
  注文を送信した時刻

arrival_ts:
  注文が取引所へ届いた想定時刻

ack_ts:
  注文応答を受け取った時刻
```

特徴量設計では、FeastのようなFeature Storeでも、学習用特徴量をpoint-in-time correctに作る考え方が重要です。RobustLabのような研究基盤でも、`available_time <= decision_ts` の特徴量だけを使うべきです。([docs.feast.dev][1])

### 原則3: 約定を疑う

悪い約定モデル:

```txt
成行注文はbest bid/askで全量約定
指値注文は価格に触れたら即約定
手数料なし
スリッページなし
```

これでは多くの戦略が勝ちすぎます。

最低限必要な約定モデル:

```txt
market / aggressive:
  板を上から食う sweep-depth

limit / maker:
  キュー位置を仮定する

latency:
  判断時刻ではなく、注文到着時刻の市場状態で判定する

partial/no-fill:
  板不足なら部分約定または未約定
```

HftBacktestは、market-data replay型バックテストでは自分の注文が市場データを変えないため、市場インパクトを直接表現できず、注文が市場に影響しないほど小さいという仮定が重要だと説明しています。([hftbacktest.readthedocs.io][2])

### 原則4: コストを分解する

合算コストだけでは不十分です。

```txt
fee
spread cost
slippage
market impact
funding
borrow / financing
tax / exchange fee
rounding
missed trade cost
```

特にCrypto Perpでは、`fee + slippage + funding` を分けて見ます。

### 原則5: 試した候補を全部残す

バックテスト過適合で一番危険なのは、試した候補の数を隠すことです。

悪い設計:

```txt
1000個試す
  ↓
一番良い1個だけ保存
```

良い設計:

```txt
1000個試す
  ↓
1000個すべて保存
  ↓
選ばれた理由も保存
  ↓
PBO/DSRで多重探索を補正
```

PBO論文も、ISで最良だった戦略がOOSで中央値未満に落ちる条件付き確率としてPBOを評価する考え方を示しています。

---

## 4. 汎用バックテストシステムのアーキテクチャ

推奨構成:

```txt
backtest-system/
  core/
    artifact/
    clock/
    dataquality/
    execution/
    risk/
    gate/
    metrics/
    trial/
    split/
    validation/
    report/
    policy/
    reason/
    lineage/

  profiles/
    crypto_perp/
    fx_cfd/
    equities/
    futures/
    generic_timeseries/

  strategies/
    volume_burst/
    trend_follow/
    mean_reversion/
    ml_forecast/

  apps/
    cli/
    runner/
    demo/

  fixtures/
    slippage/
    risk/
    gate/
    report/
    split/
    execution/

  configs/
    policy/
    reason_codes/
    report_policy/
```

### 責務分離

| レイヤー     | 役割            |
| -------- | ------------- |
| Core     | 市場を知らない汎用機能   |
| Profile  | 市場・取引所・商品固有処理 |
| Strategy | 売買判断・予測判断     |
| App      | CLI、実行、組み合わせ  |
| Report   | 人間/AI向け説明     |
| Artifact | すべての証跡保存      |

### 依存方向

```txt
App
  ↓
Core + Profile + Strategy
```

守るべきルール:

```txt
Coreは市場を知らない。
Profileは市場を知る。
Strategyは売買判断だけする。
Appが全部を組み合わせる。
CLIは薄く、ロジックを持たない。
各機能は単体で実行・検査できる。
```

---

## 5. Data Layer: データ設計

### Raw / Normalized / Manifest

```txt
data/
  raw/
    venue=hyperliquid/
      symbol=BTC/
        date=2026-06-01/
          ws_depth.jsonl.zst
          ws_trade.jsonl.zst

  normalized/
    candles.parquet
    trades.parquet
    l2_events.parquet
    funding_events.parquet
    instrument_meta.parquet

  manifests/
    capture_manifest.json
    normalized_manifest.json
    data_quality.json
```

### Rawを残す理由

```txt
正規化ロジックが間違っていたときに再生成できる
schema変更に対応できる
取引所API仕様変更を後から検証できる
品質監査ができる
```

### Data Manifestに入れるもの

```json
{
  "dataset_id": "hl_btc_1h_2026_01",
  "source": "hyperliquid",
  "endpoint": "candleSnapshot",
  "symbol": "BTC",
  "interval": "1h",
  "start": "2026-01-01T00:00:00Z",
  "end": "2026-02-01T00:00:00Z",
  "row_count": 744,
  "schema_version": "candle.v1",
  "raw_digest": "sha256:...",
  "normalized_digest": "sha256:...",
  "known_gaps": [],
  "created_at": "2026-02-01T01:00:00Z"
}
```

---

## 6. Time Layer: 時刻とリーク防止

### 必須時刻

```txt
exchange_ts:
  取引所・データ元の時刻

local_recv_ts:
  自分のシステムがデータを受け取った時刻

available_time:
  特徴量やデータが使える状態になった時刻

decision_ts:
  戦略が判断した時刻

send_ts:
  注文送信時刻

arrival_ts:
  注文が取引所へ届いた想定時刻

ack_ts:
  応答受信時刻
```

### no-future rule

```txt
戦略が見てよい情報 =
  available_time <= decision_ts のデータだけ
```

これを破ると、未来リークです。

### Embargo / Purging

未来リターンをラベルに使う場合、学習データとテストデータの間に空白を置きます。

```txt
Train
  ↓
Embargo
  ↓
Test
```

ラベル期間が重なる場合はpurgingで重複部分を除きます。

---

## 7. Universe Layer: 銘柄・対象選定

銘柄選定もバックテストの一部です。

悪い方法:

```txt
全期間を見て、勝っていた銘柄だけ選ぶ
```

良い方法:

```txt
fold時点で取引可能だった銘柄だけ見る
fold時点より前の情報だけでUniverseを作る
Universe snapshotを保存する
```

### Universe Snapshot

```json
{
  "fold_id": 12,
  "asof_ts": "2026-03-01T00:00:00Z",
  "symbol": "ABC",
  "tradable": true,
  "listed_at": "2025-12-01T00:00:00Z",
  "delisted": false,
  "volume_24h": 1234567,
  "spread_bps": 12.4,
  "depth_50bps_usd": 9000,
  "eligible": true,
  "reject_reason": null
}
```

### 見るべき項目

```txt
上場日時
廃止・停止状態
API取引可否
出来高
板厚
スプレッド
funding履歴
OI
価格刻み
最小注文数量
```

---

## 8. Strategy / Feature Layer

### Strategyの責務

Strategyは、原則として以下だけを行います。

```txt
入力データを見る
特徴量を見る
売買シグナルを作る
注文意図を返す
```

Strategyに入れないもの:

```txt
レポート生成
PBO/DSR計算
ファイル保存
Risk Gate
HTML生成
```

### FeatureSet

特徴量はfirst-classにします。

```json
{
  "feature_set_id": "volume_burst_features_v1",
  "features": [
    {
      "name": "return_74h",
      "lookback": "74h",
      "available_time_policy": "bar_close_plus_delay"
    },
    {
      "name": "volume_increase",
      "lookback": "74h",
      "available_time_policy": "bar_close_plus_delay"
    }
  ]
}
```

### Point-in-time feature

```txt
event_time:
  値が発生した時刻

available_time:
  戦略がその特徴量を使える時刻
```

MLモデルや特徴量検証では、available_timeを明示しないと未来リークが起きやすくなります。FeastのFeature Storeは、学習・推論で一貫した特徴量提供とpoint-in-timeな特徴量取得の考え方を持つため、設計参考になります。([docs.feast.dev][1])

---

## 9. Execution Reality Layer: 約定現実性

### 注文種別

```txt
market
limit
post_only
IOC
FOK
reduce_only
stop
```

### Fill Modelの段階

| Model               | 用途            | 採用判定での扱い   |
| ------------------- | ------------- | ---------- |
| best_price          | 理想ケース         | 参考のみ       |
| one_tick            | 雑な保守ケース       | 補助         |
| sweep_depth         | 成行・IOCの基本     | 必須寄り       |
| risk_averse_queue   | 指値・maker保守モデル | maker戦略で重要 |
| probabilistic_queue | 中立モデル         | paperで校正   |
| paper_calibrated    | 実測校正済み        | 上位段階       |

### sweep-depth

買い成行:

```txt
ask側を上から食う
必要数量に達するまで各価格帯を消費
平均約定価格 = Σ(price_i * qty_i) / Σ(qty_i)
```

売り成行:

```txt
bid側を下から食う
```

### partial/no-fill

```txt
板数量不足
  → partial fill

有効板なし
  → no-fill

スプレッド広すぎ
  → reject

stale book
  → reject
```

### Latency

バックテストで `sleep` しても意味がありません。正しくはイベント時刻を進めます。

```txt
signal_ts
  ↓
decision_ts
  ↓ compute_latency
send_ts
  ↓ order_latency
arrival_ts
  ↓
arrival_ts時点の板で約定判定
```

NautilusTraderは、LatencyModel設定時に注文コマンドを将来時刻のinflight queueへ入れ、その時刻に処理する設計を持ちます。これはevent-time latencyの考え方と一致します。([NautilusTrader][3])

---

## 10. Cost Layer: コスト分解

コストは合算せず、必ず分解します。

```json
{
  "fee": 12.4,
  "spread_cost": 8.1,
  "slippage": 21.3,
  "funding": -2.2,
  "borrow": 0.0,
  "rounding": 0.1,
  "total_cost": 39.7
}
```

### Crypto Perp

```txt
maker_fee
taker_fee
funding
mark/index乖離
liquidation buffer
tick/lot丸め
```

### FX/CFD

```txt
spread
commission
financing
rollover
session gap
```

### 株式

```txt
commission
slippage
borrow
corporate actions
settlement
market hours
```

QuantConnect LEANのReality Modelingは、fill、slippage、fee、buying power、settlementなどを分けてバックテストを現実に近づける設計参考になります。([quantconnect.com][4])

---

## 11. Risk Layer: 発注前リスクゲート

これは実運用・paper・shadowでも重要です。

### Research GateとRisk Gateは違う

```txt
Research Gate:
  この戦略を次段階へ進めてよいか

PreTrade Risk Gate:
  この注文を今出してよいか
```

### PreTrade Risk Gate

```txt
最大注文数量
最大注文金額
最大損失
価格乖離上限
最大建玉
銘柄別建玉
口座全体エクスポージャー
発注回数制限
キャンセル回数制限
重複注文防止
成行注文許可条件
reduce-only強制
```

### Order Flow

```txt
Strategy
  ↓
OrderIntent
  ↓
RiskGate
  ↓
OrderFormatter
  ↓
Execution
  ↓
FillAudit
```

---

## 12. Scenario Layer: 保守・標準・楽観

単一の約定仮定で採用してはいけません。

```txt
optimistic:
  良い約定

base:
  標準想定

conservative:
  悪めの約定、悪めのコスト、悪めの遅延
```

判定:

```txt
optimisticだけ勝つ
  → FAIL

baseで勝つがconservativeで死ぬ
  → MONITOR

conservativeでも大きく崩れない
  → 次段階へ
```

### Capacity Curve

注文サイズを変えて耐性を見ます。

```txt
0.5x
1x
2x
5x
10x
```

見るもの:

```txt
net return
slippage share
fill rate
partial fill rate
no-fill rate
drawdown
```

---

## 13. Validation Layer: 検証と過適合対策

### 最低限の検証フロー

```txt
Basic backtest
  ↓
WFO
  ↓
Null / placebo test
  ↓
PBO / DSR
  ↓
Holdout
  ↓
Paper / shadow
  ↓
Tiny-live
```

### Walk-Forward Optimization

```txt
Trainで最適化
  ↓
Embargo
  ↓
OOSで固定検証
  ↓
期間をずらして繰り返す
```

WFOは必要ですが、十分ではありません。

### PBO

PBOは、ISで最良だった候補がOOSでどの程度崩れるかを見る考え方です。PBO論文では、標準的なhold-outが投資バックテストでは不可靠になりやすく、CSCVでPBOを推定する枠組みが示されています。

### DSR

DSRは、Sharpeが試行回数・選択バイアス・非正規性で膨らんでいないかを補正する考え方です。多くの候補を試すほど重要です。

### White Reality Check / Hansen SPA

White Reality Checkは、複数モデルを同じデータで探索したあと、最良モデルが本当にbenchmarkを上回るかをdata snooping込みで検定する考え方です。([Social Science Computing Core][5])

ただし、これらは初期実装では後回しでよいです。

### Null / Placebo Test

```txt
random signal
label shuffle
time shift
inverted signal
symbol shuffle
```

もしこれでも勝つなら、評価器が壊れている可能性があります。

---

## 14. Trial Ledger / Provenance

### なぜ必要か

バックテスト結果は、次が分からないと信用できません。

```txt
何を試したか
何回試したか
どの設定だったか
どのデータだったか
どのコードだったか
どのPolicyだったか
```

MLflowは、runごとにparams、metrics、artifacts、metadataを記録する実験管理の参考になります。([MLflow AI Platform][6])

### Trial Record

```json
{
  "trial_id": "trial_000001",
  "strategy_id": "volume_burst_v1",
  "strategy_family": "volume_burst",
  "fold_id": 3,
  "params_hash": "sha256:...",
  "search_space_hash": "sha256:...",
  "comparable_group_hash": "sha256:...",
  "is_score": 1.24,
  "oos_net_return": -0.03,
  "selected": false,
  "status": "success"
}
```

### Run Manifest

```json
{
  "run_id": "run_20260614_001",
  "config_hash": "sha256:...",
  "data_manifest_hash": "sha256:...",
  "code_version": "robustlab@1.6.0",
  "git_commit": "...",
  "policy_hash": "sha256:...",
  "random_seed": 42
}
```

---

## 15. Evidence Level / Assumption Ledger / Decision Graph

### Evidence Level

検証レベルを明示します。

```txt
E0: toy/demo
E1: synthetic
E2: historical bar
E3: L2 replay
E4: paper verified
E5: tiny-live verified
```

### Assumption Ledger

仮定を一覧化します。

```json
{
  "assumptions": [
    {
      "id": "ASSUMP.SLIPPAGE_SYNTHETIC",
      "type": "execution",
      "description": "L2 VWAPではなく合成スリッページを使用",
      "risk": "低流動性銘柄で実スリッページを過小評価する可能性",
      "status": "unverified"
    }
  ]
}
```

### Decision Graph

PASS/FAILの根拠を機械判読可能にします。

```json
{
  "decision_graph": [
    {
      "gate": "GATE.LOW_TRADE_COUNT",
      "input": "total_oos_trades",
      "actual": 8,
      "threshold": 30,
      "passed": false
    }
  ]
}
```

---

## 16. Reporting Layer: 人間向け・AI向け出力

### 4層レポート

```txt
1. Executive Summary
2. Plain Explanation
3. Technical Analysis
4. Machine-readable Artifacts
```

### report.html

```txt
結論
かみ砕き説明
主要指標
技術詳細
Reason Code診断
グラフ
Assumption Ledger
Evidence Level
Artifact一覧
```

### human_report.md

```md
# Human Report

## 結論
判定: MONITOR

## かみ砕き説明
通常条件では少し利益が出ていますが、厳しい約定条件では利益が消えています。

## 技術的根拠
- total_oos_net_return: +3.2%
- slippage_x2_return: -0.8%
- DSR: approx 0.41

## 次にやること
1. L2 VWAPで再検証
2. Shadow modeで注文意図を記録
```

### ai_report.json

AI向けは、説明と判定根拠を分けます。

```json
{
  "facts": {},
  "assumptions": {},
  "decision_graph": {},
  "inferences": {},
  "human_explanation": {},
  "do_not_use_for_gate": [
    "human_explanation"
  ]
}
```

---

## 17. Reason Code

Reason Codeは標準化します。

```txt
DATA.SEQ_GAP
DATA.STALE_BOOK
EXEC.NO_LIQUIDITY
EXEC.SLIPPAGE_STRESS_FAIL
RISK.ORDER_TOO_LARGE
GATE.LOW_TRADE_COUNT
VALIDATION.PBO_HIGH
REPORT.MISSING_ARTIFACT
```

### reason_codes.yaml

```yaml
EXEC.SLIPPAGE_STRESS_FAIL:
  severity: critical
  title: "スリッページに弱い"
  plain: "注文価格が少し不利になるだけで利益が消えています。"
  technical: "Net return becomes negative under slippage stress scenario."
  suggested_actions:
    - "L2 VWAPで再検証する"
    - "注文サイズを下げてcapacity curveを見る"
```

Reason Codeを増やしすぎないために、階層を固定します。

```txt
DATA.*
EXEC.*
RISK.*
GATE.*
VALIDATION.*
REPORT.*
POLICY.*
SYSTEM.*
```

---

## 18. Policy as Config

リスク・ゲート・レポート・昇格条件は設定ファイル化します。

```yaml
policy_id: crypto_perp_research_v1
policy_type: research
market_profile: crypto_perp
allowed_modes:
  - research
  - paper
forbidden_modes:
  - live
version: 1
```

実行時に照合します。

```txt
run_mode=live
policy.forbidden_modes includes live
  → 実行停止
```

### Gate Policy

```yaml
gates:
  min_trade_count: 30
  require_positive_median_fold: true
  max_cost_to_gross_ratio: 0.5
  max_symbol_concentration: 0.5
```

### Risk Policy

```yaml
risk:
  max_order_notional_usd: 100
  max_symbol_exposure_usd: 300
  max_account_exposure_usd: 1000
  allow_market_order: false
```

---

## 19. OSS活用

OSSは中核置換ではなく、参考・比較・検証補助として使います。

| OSS               | 用途                                             | 中核置換 |
| ----------------- | ---------------------------------------------- | ---- |
| HftBacktest       | L2、latency、queue、fill realism                  | しない  |
| NautilusTrader    | event-driven、research/live parity参考            | しない  |
| QuantConnect LEAN | Reality Modeling参考                             | しない  |
| Freqtrade         | crypto workflow、lookahead/recursive analysis参考 | しない  |
| PyBroker          | ML特徴量・WFA・bootstrap補助                          | しない  |
| vectorbt          | 高速スクリーニング                                      | しない  |
| backtesting.py    | 小型fixture/smoke test                           | しない  |
| Jesse             | crypto strategy UX参考                           | しない  |
| Zipline Reloaded  | equities拡張参考                                   | しない  |

PyBrokerは、NumPy/Numbaによる高速バックテスト、MLモデルのtrain/backtest、Walkforward Analysis、bootstrap metrics、cache、parallelized computationsを機能として掲げており、ML風の特徴量検証やbar-based外部検証に向きます。([PyBroker][7])
PyBrokerのモデル学習例では、indicatorを特徴量としてモデルを訓練し、Walkforward Analysisで評価する流れが示されています。([PyBroker][8])

### ExternalEngineAdapter

```go
type ExternalEngineAdapter interface {
    EngineID() string
    Prepare(spec EngineRunSpec) error
    Run(ctx context.Context, spec EngineRunSpec) (ExternalEngineResult, error)
    Normalize(result ExternalEngineResult) (NormalizedBacktestResult, error)
}
```

### CrossEngineValidation

```txt
RobustLab internal result
  vs
External engine result
```

比較:

```txt
net_return
trade_count
max_drawdown
fee_total
slippage_total
fill_count
position series
```

---

## 20. 実装ロードマップ

### Phase 0: Skeleton

```txt
pkg/artifact
pkg/policy
pkg/reason
pkg/report
pkg/gate
pkg/trial
```

### Phase 1: Core Backtest

```txt
split WFO
trial registry
candidate results
human/AI report
reason code
policy hash
```

### Phase 2: Execution Reality

```txt
sweep-depth
maker/taker fee
event-time latency
partial/no-fill
fill_audit
scenario compare
```

### Phase 3: Data Quality

```txt
Raw manifest
Normalized manifest
DataIntegrity
DataSuitability
PointInTimeFeatureGuard
LineageEvent
```

### Phase 4: Validation

```txt
Full PBO
PSR/DSR
CPCV
Holdout Lock
Null / Placebo Test
```

### Phase 5: Paper / Tiny-live

```txt
Shadow mode
Paper fill compare
Promotion ladder
Conformance test
Calibration loop
```

---

## 21. 各機能を単体で試せるCLI

```bash
robustlab split wfo ...
robustlab trial validate --path trial_registry.jsonl
robustlab gate eval --ai-report ai_report.json
robustlab risk check --order order.json --policy risk_policy.yaml
robustlab execution simulate --order order.json --book l2_book.json
robustlab dataquality check --manifest data_manifest.json
robustlab report render --run-dir _runs/demo --format html
robustlab scenario compare --run-dir _runs/demo
robustlab explain reason --code EXEC.SLIPPAGE_STRESS_FAIL
robustlab policy validate --policy policy.yaml
robustlab doctor --run-dir _runs/demo
```

CLIは薄くします。

```txt
CLI:
  入力を読む
  core packageを呼ぶ
  出力する

Core:
  実ロジック
```

---

## 22. テスト戦略

### Unit Test

```txt
sweep-depthのVWAPが正しい
Gate判定が正しい
Reason Codeが解決できる
Policyのrun_mode guardが効く
```

### Golden Test

```txt
fixtures/input
fixtures/expected
```

例:

```txt
fixtures/slippage/order_market_buy.json
fixtures/slippage/book.json
fixtures/slippage/expected_fill.json
```

### Property Test

```txt
注文数量が増えたら、買いの平均約定価格は改善しない
fee_bpsが増えたら、net_pnlは改善しない
slippageを増やしたら、net_returnは改善しない
```

### Smoke Test

```bash
go test ./...
robustlab demo
robustlab report render --run-dir _runs/demo
robustlab doctor --run-dir _runs/demo
```

---

## 23. アンチパターン

### データ系

```txt
Rawを捨てる
正規化データだけを真実にする
timestampを1つしか持たない
available_timeを持たない
DataQualityなしでbacktestする
```

### 検証系

```txt
1回だけのbacktestで採用
ISで最良の候補だけ保存
trial数を記録しない
Sharpeだけで採用
holdoutを何度も見る
```

### 約定系

```txt
成行をbestで全量約定
指値を価格接触で即約定
手数料なし
slippageなし
fundingなし
latencyなし
```

### 設計系

```txt
StrategyがReportを生成する
CoreがCrypto固有処理を知る
CLIにロジックを書く
Policyをコードに直書きする
Reason Codeを自由文字列にする
```

---

## 24. Minimum Backtest Review Checklist

### データ

```txt
[ ] Rawが保存されている
[ ] data_manifestがある
[ ] schema_versionがある
[ ] 欠損が記録されている
[ ] available_timeがある
```

### 時刻

```txt
[ ] decision_tsがある
[ ] arrival_tsがある
[ ] 未来データを見ていない
[ ] embargo/purgingが必要なら入っている
```

### 戦略

```txt
[ ] hypothesisがある
[ ] search spaceが明示されている
[ ] paramsが保存されている
```

### 約定

```txt
[ ] feeが入っている
[ ] slippageが入っている
[ ] 成行best全量約定ではない
[ ] partial/no-fillを扱う
[ ] latency仮定がある
```

### 検証

```txt
[ ] WFOをしている
[ ] 全trialを保存している
[ ] null/placebo testがある
[ ] PBO/DSRの状態が明示されている
[ ] holdoutを温存している
```

### レポート

```txt
[ ] 結論がある
[ ] 仮定がある
[ ] 未検証項目がある
[ ] Evidence Levelがある
[ ] Reason Codeがある
[ ] AI向けJSONがある
```

---

## 25. 用語集

### IS

In-sample。最適化や学習に使う期間。

### OOS

Out-of-sample。学習・最適化後に固定パラメータで検証する期間。

### WFO

Walk-Forward Optimization。過去で調整し、未来で検証し、期間をずらして繰り返す手法。

### Embargo

TrainとTestの間に置く空白期間。情報にじみを防ぐ。

### Purging

ラベル期間が重なるデータを除く処理。

### PBO

Probability of Backtest Overfitting。ISで良かった候補がOOSで崩れる確率を見る考え方。

### DSR

Deflated Sharpe Ratio。Sharpeが試行回数・非正規性・選択バイアスで膨らんでいないかを補正する考え方。

### Sweep-depth

板を上から順に食って約定価格を計算する方法。

### VWAP

Volume Weighted Average Price。数量加重平均価格。

### Funding

Perpで一定間隔ごとに発生するlong/short間の受け払い。

### DataIntegrity

データが壊れていないか。

### DataSuitability

そのデータが特定の戦略評価に使えるか。

### Evidence Level

検証結果の信頼段階。toy、bar、L2、paper、tiny-liveなど。

### Assumption Ledger

バックテストの仮定一覧。

### Decision Graph

PASS/FAIL/MONITORの根拠を機械判読できる形にしたもの。

---

## 26. まとめ

バックテスト基盤を作るとき、最重要なのは「速く勝つ戦略を見つけること」ではありません。

重要なのはこれです。

```txt
結果を出す。
理由を出す。
仮定を出す。
未検証を出す。
試行履歴を出す。
データ品質を出す。
コスト内訳を出す。
次に何を検証するべきかを出す。
```

そして、最終的な思想はこうです。

```txt
バックテストは戦略を褒めるための道具ではない。

戦略を疑い、
データを疑い、
約定を疑い、
コストを疑い、
検証手順を疑い、
それでも残ったものだけを次段階へ進めるための道具。
```

最小構成で始めるなら、以下から実装します。

```txt
1. artifact / manifest / hash
2. trial registry / candidate results
3. WFO + embargo
4. fee / slippage / funding分解
5. conservative/base/optimistic scenario
6. human_report / ai_report
7. reason code / policy as config
8. null test
```

完成形では、次を足します。

```txt
L2 replay
sweep-depth
event-time latency
partial/no-fill
PBO/DSR/CPCV
holdout lock
paper/live calibration
promotion ladder
```

この方針なら、RobustLabだけでなく、仮想通貨Bot、FX/CFD、株式、先物、ML予測、競馬・スポーツ予測のような別プロジェクトにも横展開できます。

タイムスタンプ: 19:04:18.(06/14)

[1]: https://docs.feast.dev/ "Introduction | Feast: the Open Source Feature Store"
[2]: https://hftbacktest.readthedocs.io/en/latest/order_fill.html "Order Fill — hftbacktest"
[3]: https://nautilustrader.io/docs/latest/concepts/backtesting/ "Backtesting | NautilusTrader"
[4]: https://www.quantconnect.com/docs/v2/writing-algorithms/reality-modeling/key-concepts "Key Concepts - QuantConnect.com"
[5]: https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf "270econ.p"
[6]: https://mlflow.org/docs/latest/ml/tracking/ "ML Experiment Tracking | MLflow AI Platform"
[7]: https://www.pybroker.com/ "Algorithmic Trading in Python with Machine Learning — PyBroker"
[8]: https://www.pybroker.com/en/latest/notebooks/6.%20Training%20a%20Model.html "Training a Model — PyBroker"
















