## 結論

**個人利用・純粋バックテスト・シニアSEとして部品取り/独自実装前提**なら、評価をかなり変えます。

最終的には、**既存OSSをそのまま使うのではなく、独自バックテスト基盤を作り、OSSを「速度」「検証思想」「約定モデル」「データ設計」「評価指標」の教材として使う**のが最も実務的です。

今回追加した **NautilusTrader** は、純粋バックテストの観点ではかなり重要です。ただし「最初から全面採用」ではなく、**イベント駆動・データ型・注文/約定/ポジション/会計モデルの設計教材**として見るのが適切です。

既存のGrok資料内では、Qlib、PyBroker、trading-strategy、auto-researchtrading、QuantDinger、rolling-panda、paperswithbacktest系がバックテスト関連として重要ですが、純粋BTに絞ると、LLM/Live/Bot/発注系は大幅に降格します。

---

# 最終ランキング：純粋バックテスト用途

## Sランク：最優先で見る

| OSS                | 使い方                                  | 判断                  |
| ------------------ | ------------------------------------ | ------------------- |
| **NautilusTrader** | イベント駆動BT、データモデル、注文/約定/ポジション/会計モデルの教材 | **設計参考として最重要**      |
| **vectorbt**       | 大量パラメータ探索、ベクトル化BT、粗検証                | **初期探索に強い**         |
| **PyBroker**       | ML特徴量、ウォークフォワード、実装しやすいPython BT      | **実装実験に向く**         |
| **Qlib**           | ML/ファクター/銘柄横断研究                      | **重いが研究設計の参考価値が高い** |
| **hftbacktest**    | 板、キュー、レイテンシ、部分約定モデル                  | **約定現実性の教材**        |

---

## Aランク：部品取り・設計参考

| OSS                             | 使い方                                  | 判断                          |
| ------------------------------- | ------------------------------------ | --------------------------- |
| **polars_backtest_extension**   | Polars前提の高速BT、long format処理の参考       | 個人検証なら有用。商用/法人利用はライセンス注意    |
| **barter-rs**                   | Rustイベント駆動BT/Live共通設計の参考             | Rust設計の教材。純BTだけならNautilus優先 |
| **pwb-toolbox**                 | systematic strategyのデータセット・戦略アイデア    | BTエンジンではなく研究素材              |
| **rolling-panda-san/notebooks** | trend / carry / mean-reversion の戦略思想 | 戦略テンプレート教材                  |
| **polars_ta_extension**         | PolarsでのTA特徴量生成                      | BT本体ではないが、独自基盤の部品として有用      |

---

## Bランク：参考止まり

| OSS                                                       | 修正評価                                       |
| --------------------------------------------------------- | ------------------------------------------ |
| **AutoTrader**                                            | アーカイブ済み。設計参考のみ                             |
| **QuantDinger**                                           | BT単体では広すぎる。AI/Live/UIが混ざる                  |
| **llm-agent-trader**                                      | LLM判断ログ/UIの参考。BTエンジンとしては弱い                 |
| **tradingstrategy-ai/getting-started / trading-strategy** | DEX/AMM向け。Trade[XYZ]やOrderbook型BTとは市場構造が違う |
| **ivopetiz/algotrading**                                  | 古く、Python 3実装がTODOに残る。依存しない                |
| **OctoBot**                                               | Bot/UI/Live色が強い。純BTでは低優先                   |
| **finmarketpy**                                           | FX/マクロBTの参考程度                              |

---

## Cランク：今回の純粋BTでは外す

| OSS                            | 理由                          |
| ------------------------------ | --------------------------- |
| **Shioaji / rshioaji / scone** | 台湾市場APIであり、純粋BT教材としての優先度は低い |
| **hummingbot**                 | Bot/MM/実行寄り                 |
| **pbgui / Passivbot系**         | グリッド/ナンピン/運用GUI寄り           |
| **coinbase/agentkit**          | ウォレット/Agent操作系              |
| **DeepSpeed**                  | 大規模学習基盤でBTとは別               |
| **LLM trading agent系全般**       | 仮説生成やログには使えるが、BT中核にはしない     |

---

# NautilusTraderの評価

## 判断

**NautilusTraderは、今回追加対象の中では最も重要です。**
ただし、使い方は「そのまま依存」よりも、**独自BT基盤の設計リファレンス**がよいです。

NautilusTraderは、Rust-nativeのmulti-asset / multi-venue取引エンジンで、research、deterministic simulation、live executionを単一のevent-driven architectureで扱うと説明されています。バックテスト機能として、quote tick、trade tick、bar、order book、custom dataをnanosecond resolutionで扱える点が特徴です。([GitHub][1])

また、公式Docsでは、`BacktestEngine` がhistorical data streamを処理し、終了時に結果とperformance metricsを生成すると説明されています。高レベルAPIの `BacktestNode` と、低レベルAPIの `BacktestEngine` を使い分けられる構造です。([NautilusTrader][2])

## 学ぶべき点

| 学ぶ対象                               | 理由                                                       |
| ---------------------------------- | -------------------------------------------------------- |
| **イベント駆動設計**                       | candle loopより実取引に近い                                      |
| **Data object設計**                  | Bar, QuoteTick, TradeTick, OrderBookDelta, CustomDataの扱い |
| **Instrument設計**                   | tick size, lot size, currency, precisionなど               |
| **Venue設計**                        | venueごとの手数料、book type、matching条件                         |
| **Order lifecycle**                | submit, accepted, filled, cancelled, rejected            |
| **Position / Account / Portfolio** | BTで一番バグりやすい会計部分                                          |
| **Fill model**                     | 約定価格、部分約定、流動性消費                                          |
| **Latency model**                  | 短期売買では差が出る                                               |
| **Data granularity選択**             | bar / quote / trade / L2 / L3 の使い分け                      |

公式Docsでも、NautilusTraderはorder book dataを主に設計・最適化しており、データ粒度は L3 order book、L2 order book、quote tick、trade tick、bar の順で現実性が高いと説明されています。ただし、低粒度データから高粒度データを生成できるわけではない点も明記されています。([NautilusTrader][2])

## 注意点

| 注意    | 内容                                        |
| ----- | ----------------------------------------- |
| 学習コスト | かなり高い                                     |
| API変更 | active developmentでbreaking changesの可能性あり |
| ライセンス | LGPL-3.0                                  |
| 過剰機能  | 純BTだけならLive/Adapter/Executionの多くは不要       |
| データ要件 | 現実的なfillをやるほど高品質データが必要                    |

NautilusTraderのREADMEでは、active development中であり、APIは安定化しつつあるがbreaking changesが起こり得ると説明されています。([GitHub][1])
ライセンスはGitHub上でLGPL-3.0と表示されています。([GitHub][1])

**結論として、NautilusTraderは「読む価値が最も高い」。ただし、個人BT基盤の最初の実装をNautilus全面採用で始めると重すぎます。**

---

# 純粋BTとしての役割分担

## 1. 粗検証レイヤー

ここは **vectorbt / PyBroker / Polars** が強いです。

### vectorbt

vectorbtは、ループで1戦略ずつ処理するのではなく、多数の設定をNumPy配列に詰め、Numba/Rustで高速化して大量のグリッド探索を一気に回す設計です。ライセンスは Apache 2.0 with Commons Clauseで、個人・組織の無料利用は可能だが、このソフト自体を主目的とする製品/サービス販売は制限されます。([GitHub][3])

| 向く                    | 向かない                       |
| --------------------- | -------------------------- |
| MA/RSI/Breakout等の大量探索 | イベント駆動BT                   |
| パラメータ感応度              | 板・部分約定                     |
| 銘柄横断の粗検証              | 複雑な注文ライフサイクル               |
| スクリーナー型戦略             | Mark/Oracle/Funding制約の標準対応 |

**個人利用ならかなり有用。**
ただし、独自BT基盤では「最初の探索エンジン」と割り切るべきです。

---

### PyBroker

PyBrokerは、機械学習を使うアルゴリズム取引戦略向けのPythonフレームワークです。NumPy/Numbaによる高速バックテスト、複数銘柄、独自データプロバイダ、walk-forward analysis、bootstrapping、並列計算などを掲げています。([GitHub][4])

| 向く             | 向かない        |
| -------------- | ----------- |
| ML特徴量入り戦略      | 板ベースの精密約定   |
| walk-forward検証 | 低レイテンシ再現    |
| ブートストラップ評価     | 複雑な注文状態管理   |
| Pythonでの実験     | 独自市場仕様の完全再現 |

**vectorbtより柔軟、Nautilusより軽い。**
独自BT基盤のプロトタイプにはかなり向きます。

---

### polars_backtest_extension

polars_backtest_extensionは、Rust/Arrowで書かれたPolars統合型BTで、`df.bt.backtest()`、T+1 execution、stop loss、take profit、trailing stop、OHLCによるexit検出などを備えています。([GitHub][5])

ただし、ライセンスは **PolyForm Noncommercial 1.0.0** で、商用利用には作者への連絡が必要です。([GitHub][5])

| 判断      | 内容      |
| ------- | ------- |
| 個人研究    | 使ってよい候補 |
| 独自実装の教材 | 有用      |
| 法人利用/販売 | 注意      |
| 中核依存    | 避ける方が安全 |

あなたの「個人で使う」前提なら触ってよいです。
ただし、将来、法人内利用や販売、外部提供へ広がる可能性が少しでもあるなら、**設計だけ学んで自前化**が安全です。

---

# 2. ML・ファクター研究レイヤー

## Qlib

Qlibは、AI指向のQuant投資プラットフォームで、教師あり学習、市場ダイナミクスモデル、強化学習を含む複数のMLパラダイムをサポートし、データ処理、モデル学習、バックテストを含むML pipelineを持つと説明されています。([GitHub][6])

| 向く                     | 向かない                |
| ---------------------- | ------------------- |
| 銘柄横断ファクター              | 軽量な単発BT             |
| MLモデル比較                | すぐ動かすプロトタイプ         |
| alpha seeking          | 板・約定精密再現            |
| portfolio optimization | Trade[XYZ]固有制約の標準対応 |

Qlibは **「バックテストエンジン」というより、ML Quant研究基盤」** です。
独自BTシステムを考えるなら、Qlibから学ぶべきは以下です。

| 学ぶもの                   | 内容                                     |
| ---------------------- | -------------------------------------- |
| Dataset / Handler設計    | 特徴量とラベルの分離                             |
| Workflow設計             | train / validate / test / backtest の分離 |
| Experiment管理           | 再現性・比較                                 |
| Factor pipeline        | 銘柄横断特徴量                                |
| Portfolio construction | scoreからweightへ変換する流れ                   |

最初からQlibに寄せすぎると、Trade[XYZ]や暗号Perp固有のFunding/Mark/Oracle/約定モデルを入れづらくなります。
ただし、NASDAQ/日本株/ETF系の戦略研究ではかなり参考になります。

---

# 3. 約定現実性レイヤー

## hftbacktest

hftbacktestは、HFT/MM向けのバックテストツールで、feed/order latency、order queue position、full order book、trade tick dataを使ったmarket replay型BTを重視しています。([GitHub][7])

あなたの方針では、HFT/MM戦略そのものは対象外です。
しかし、**約定モデルの教材としては非常に価値が高い**です。

| 使う                 | 使わない         |
| ------------------ | ------------ |
| queue positionの考え方 | HFT戦略        |
| feed/order latency | MM戦略         |
| partial fill       | grid trading |
| L2/L3 replay設計     | 秒・ミリ秒競争      |
| maker/taker約定差     | 板取り戦略        |

特に重要なのは、hftbacktestのREADMEが「バックテストは保守的であればよいのではなく、現実の執行を再現できなければ、以後の分析が信頼できない」と強調している点です。([GitHub][7])

これは純粋BTでは重要です。
つまり、**戦略のロジックより先に、fill simulationの嘘を潰す必要があります。**

---

## NautilusTraderとの違い

| 観点     | NautilusTrader                   | hftbacktest    |
| ------ | -------------------------------- | -------------- |
| 主用途    | 汎用イベント駆動BT/取引エンジン                | HFT/MM向け精密BT   |
| 学ぶ価値   | システム全体設計                         | 約定・板・レイテンシ     |
| データ    | bar, quote, trade, L2/L3, custom | tick, L2/L3中心  |
| 戦略対象   | 多資産・多市場                          | 高頻度・板中心        |
| 今回の使い方 | 設計の教科書                           | fill modelの教科書 |

**独自BTを作るなら、NautilusTraderを骨格、hftbacktestを約定モデルの参考にする**のが最も良いです。

---

# 4. Rust設計レイヤー

## barter-rs

barter-rsは、Rustでevent-driven live-trading & backtesting systemsを作るためのOSSです。GitHub上でもRust 100%、MIT license、event-driven/backtesting frameworkとして説明されています。([GitHub][8])

| 判断       | 内容         |
| -------- | ---------- |
| Rust設計教材 | 有用         |
| 純BT中核    | Nautilus優先 |
| 個人独自基盤   | 将来的に参考     |
| 今すぐ採用    | 不要         |

NautilusTraderの方がバックテスト・データ・約定・ポジション周りの設計を詳しく学びやすいです。
barter-rsは、Rustでイベント駆動構造を作るときの比較対象として見るのがよいです。

---

# 5. 戦略アイデア・教材レイヤー

## pwb-toolbox

pwb-toolboxは、systematic trading strategy開発向けに、データセットと戦略アイデアを提供するツールボックスです。datasets moduleでは、bonds、commodities、crypto、ETFs、forex、indices、stocksなどのデータセット取得例があります。([GitHub][9])

これはBTエンジンではありません。
使い道は以下です。

| 使い道         | 内容                               |
| ----------- | -------------------------------- |
| 戦略候補集め      | momentum, carry, reversal, trend |
| データ形式の参考    | asset class横断                    |
| バックテスト例の教材  | simple strategy example          |
| 独自BTのテストデータ | 初期検証用                            |

## rolling-panda-san/notebooks

これは戦略ノートです。
直接BTシステムに入れるものではありません。

| 使い方                 | 内容                    |
| ------------------- | --------------------- |
| trend followingの考え方 | 指数・商品・大型株に移植          |
| carryの考え方           | Fundingや先物カーブに応用      |
| mean-reversionの考え方  | Mark/Oracle乖離、短期戻りに応用 |
| 評価指標の参考             | DD、Sharpe、turnoverなど  |

---

# 6. 降格・除外の修正

## AutoTrader

AutoTraderは、2025-05-04にアーカイブされ、読み取り専用になっています。READMEにも、もはや活発に保守されていないとあります。([GitHub][10])

| 前回評価        | 修正         |
| ----------- | ---------- |
| イベント駆動BT候補  | **設計参考のみ** |
| 触る価値あり      | 依存しない      |
| Python BT教材 | 参考程度       |
| ライセンス       | GPL-3.0注意  |

個人でコードを読むのは問題ありません。
ただし、自前基盤に流用するならGPL-3.0の影響を避けるため、**設計を読むだけ**にした方がよいです。

---

## ivopetiz/algotrading

ivopetiz/algotradingは、crypto向けPython frameworkで、BOT、backtest、stop loss、CSV/DB/API入力、data-driven/event-drivenに対応すると説明されています。([GitHub][11])

ただし、TODOにPython 3 implementationが残っています。([GitHub][11])
現在の個人BT基盤の参考としては古いです。

| 判断   | 内容             |
| ---- | -------------- |
| 読む価値 | 低〜中            |
| 依存   | 不要             |
| 参考点  | 古典的crypto BT構成 |
| 優先度  | 低い             |

---

## llm-agent-trader

llm-agent-traderは、LLMを使った株式バックテスト分析システムで、FastAPI backend、Next.js frontend、yfinance、SQLite、Azure OpenAI/Geminiなどを使う構成です。([GitHub][12])

純粋BTでは、LLMは不要です。
学ぶなら以下だけです。

| 学ぶ       | 学ばない                |
| -------- | ------------------- |
| 結果ログの保存  | LLM売買判断             |
| 説明レポート   | LLM signal          |
| UI/API構成 | LLM position sizing |
| 分析履歴     | LLMで採用判定            |

BTエンジンとしては優先度が低いです。

---

## QuantDinger

QuantDingerは、self-hosted/local-firstのQuant OSとして、multi-LLM research、Python strategy engine、server-side backtesting、multi-broker live executionを統合すると説明されています。([GitHub][13])

ただし、今回は「純粋BT」なので、範囲が広すぎます。

| 判断             | 内容                                                   |
| -------------- | ---------------------------------------------------- |
| UI/統合設計        | 参考                                                   |
| BT中核           | 不採用                                                  |
| LLM連携          | 今回対象外                                                |
| Live execution | 今回対象外                                                |
| ライセンス          | backendはApache-2.0だがfrontendは別ライセンス注意 ([GitHub][13]) |

---

# 独自バックテスト基盤を作るなら、こう分ける

## 主案：自前Core + OSSから学ぶ

```text
独自Backtest Core
  ├─ Data Layer: Polars / Parquet
  ├─ Feature Layer: Polars + polars_ta_extension
  ├─ Signal Layer: 自前
  ├─ Portfolio Layer: Nautilus / Qlibから学ぶ
  ├─ Order/Fill Layer: Nautilus + hftbacktestから学ぶ
  ├─ Cost Layer: 自前
  ├─ Metrics Layer: 自前
  └─ Report Layer: 自前HTML / ECharts
```

## 役割別の参照元

| 自前コンポーネント  | 参考OSS                                          |
| ---------- | ---------------------------------------------- |
| データスキーマ    | NautilusTrader, Qlib                           |
| 大量探索       | vectorbt                                       |
| ML付きBT     | PyBroker, Qlib                                 |
| イベント駆動     | NautilusTrader, barter-rs                      |
| 約定モデル      | NautilusTrader, hftbacktest                    |
| ポートフォリオ会計  | NautilusTrader, Qlib                           |
| 高速Polars処理 | polars_backtest_extension, polars_ta_extension |
| 戦略アイデア     | rolling-panda, pwb-toolbox                     |
| 評価指標       | PyBroker, vectorbt, Qlib                       |

---

# 純粋BTで必要な最小構成

Trade[XYZ]に限らず、NASDAQ/日本株/Perp系まで見据えるなら、最初からこの分離にした方がよいです。

```text
backtest_lab/
  data/
    raw/
    normalized/
    features/
  src/
    data/
      schema.py
      loader.py
      resample.py
      calendar.py
    features/
      technical.py
      regime.py
      cross_sectional.py
    engine/
      event.py
      broker.py
      portfolio.py
      order.py
      fill_model.py
      cost_model.py
      backtester.py
    strategies/
      trend.py
      mean_reversion.py
      breakout.py
    evaluation/
      metrics.py
      walk_forward.py
      sensitivity.py
      bootstrap.py
    reports/
      report_html.py
  outputs/
    runs/
    reports/
```

Python環境はあなたの方針どおり `uv` 前提で十分です。

```bash
uv init backtest_lab
cd backtest_lab
uv add polars numpy pandas pyarrow loguru pydantic pydantic-settings typer matplotlib
uv add vectorbt pybroker
uv add polars-talib
```

`polars-backtest` は個人検証で試すなら追加候補です。ただし、非商用ライセンスなので中核依存は避ける方が安全です。

```bash
uv add polars-backtest
```

---

# 最初に作るべきBacktest Coreの仕様

## 1. DataFrame入力仕様

最初はこれで十分です。

```text
ts
symbol
open
high
low
close
volume
vwap
spread_bps
fee_bps
funding_rate
session
```

Trade[XYZ]やPerpまで見据えるなら追加。

```text
mark_price
oracle_price
external_price
mark_oracle_basis_bps
discovery_bound_pct
oi_cap_usage
```

## 2. Backtestの処理順

```text
1. 時刻を進める
2. market dataを読む
3. 既存注文を約定判定する
4. portfolio/accountを更新する
5. strategyにdataを渡す
6. signalをorderに変換する
7. cost/risk gateを通す
8. orderを登録する
9. metricsを記録する
```

これはNautilusTraderのイベント駆動BTに近い考え方です。NautilusのDocsでも、各データ点で「exchangeが市場データを処理して既存注文を約定判定 → strategyがデータを受け取る → venue commandをsettleする」という流れが説明されています。([NautilusTrader][2])

## 3. Fill model

最小モデルはこれでよいです。

```text
market_order_fill_price =
    close_or_next_open
  + side * spread / 2
  + side * slippage

limit_order_fill =
    high_low_touched
    and volume_ok
    and queue_probability_ok
```

将来の精密化。

```text
L1: bid/ask quote
L2: price-level depth
L3: individual order queue
```

NautilusTraderでは、L2/L3データがある場合はbook simulationに基づいてfillが決まり、market orderは複数価格レベルを跨いで部分約定する可能性があると説明されています。L1データのみの場合は単一レベルのbookとして扱われます。([NautilusTrader][2])

## 4. 評価指標

最低限。

```text
total_return
CAGR
max_drawdown
Sharpe
Sortino
Calmar
win_rate
profit_factor
turnover
avg_holding_time
fee_impact
slippage_impact
gross_pnl
net_pnl
```

実務上は追加。

```text
walk_forward_score
parameter_stability
out_of_sample_return
bootstrap_confidence
symbol_contribution
session_contribution
tail_loss
max_consecutive_losses
```

---

# 実務的な採用順

## Phase 1：高速粗検証

| 目的           | ツール                 |
| ------------ | ------------------- |
| 大量条件を試す      | vectorbt            |
| Pythonで柔軟に試す | PyBroker            |
| データ処理        | Polars              |
| 特徴量          | polars_ta_extension |

この段階では、まだ完璧な約定再現は不要です。
目的は **明らかにダメな戦略を落とすこと** です。

---

## Phase 2：自前Cost / Fill model

| 目的                         | 参考                  |
| -------------------------- | ------------------- |
| 注文/約定モデル                   | NautilusTrader      |
| queue/latency/partial fill | hftbacktest         |
| portfolio/accounting       | NautilusTrader      |
| strategy evaluation        | PyBroker / vectorbt |

この段階で、既存OSSをそのまま使うより、自前Coreに寄せるのがよいです。

---

## Phase 3：ML/ファクター研究

| 目的           | 参考       |
| ------------ | -------- |
| 銘柄横断factor   | Qlib     |
| 学習/検証分離      | Qlib     |
| walk-forward | PyBroker |
| OOS評価        | 自前       |

QlibはBT単体ではなく、ML研究ワークフローの教材として使うのがよいです。

---

## Phase 4：イベント駆動BTの本格化

| 目的                 | 参考             |
| ------------------ | -------------- |
| BacktestEngine構造   | NautilusTrader |
| MessageBus / Cache | NautilusTrader |
| Actor / Strategy分離 | NautilusTrader |
| Order lifecycle    | NautilusTrader |
| Rust実装比較           | barter-rs      |

この段階で初めて、NautilusTraderを深く読む価値が出ます。

---

# 最終判断

## 今すぐ触る

| OSS                     | 理由                |
| ----------------------- | ----------------- |
| **vectorbt**            | 粗検証速度が高い          |
| **PyBroker**            | Python実験とML特徴量に向く |
| **NautilusTrader**      | 独自BT設計の教材として最重要   |
| **hftbacktest**         | 約定現実性の教材として重要     |
| **Qlib**                | ML/ファクター研究設計の参考   |
| **polars_ta_extension** | 特徴量生成に実用的         |

## 触ってよいが依存しない

| OSS                           | 理由                       |
| ----------------------------- | ------------------------ |
| **polars_backtest_extension** | 速いが非商用ライセンス              |
| **barter-rs**                 | Rust設計参考。純BTではNautilus優先 |
| **pwb-toolbox**               | 戦略アイデア・データ教材             |
| **rolling-panda**             | 戦略思想教材                   |
| **QuantDinger**               | 統合UI/構成参考。純BTでは過剰        |
| **llm-agent-trader**          | LLM分析ログ参考。BT本体ではない       |

## 実務上は後回し/除外

| OSS                      | 理由                    |
| ------------------------ | --------------------- |
| **AutoTrader**           | アーカイブ済み               |
| **ivopetiz/algotrading** | 古い。Python 3 TODO      |
| **OctoBot**              | Bot/Live/Grid/DCA色が強い |
| **tradingstrategy-ai系**  | DEX/AMM向けで市場構造が違う     |
| **Shioaji系**             | 台湾市場APIで今回の純BT主眼から外れる |

---

# 主案・代替案・トレードオフ

## 主案：独自BT Core + OSS教材

```text
Polars
+ 自前 engine/order/fill/portfolio/cost/metrics
+ vectorbt/PyBrokerで粗検証
+ NautilusTrader/hftbacktestから設計を学ぶ
```

| 速度 | コスト | リスク | 効果       |
| -- | --- | --- | -------- |
| 中  | 低   | 中   | 長期的に一番強い |

最もシニアSE向きです。
最初は時間がかかりますが、Trade[XYZ]、NASDAQ、日本株、暗号Perpなどへ横展開しやすいです。

---

## 代替案1：vectorbt / PyBroker中心

```text
vectorbt
+ PyBroker
+ Polars
+ 自前cost model
```

| 速度 | コスト | リスク | 効果      |
| -- | --- | --- | ------- |
| 高  | 低   | 中   | 初期探索に強い |

最初に戦略仮説を大量に潰すには最適です。
ただし、イベント駆動・約定現実性は弱いです。

---

## 代替案2：NautilusTrader中心

```text
NautilusTrader
+ custom data
+ custom venue/instrument
+ custom strategy
```

| 速度 | コスト | リスク | 効果      |
| -- | --- | --- | ------- |
| 低  | 中   | 中〜高 | 精密BTに強い |

最初からやるには重いです。
ただし、将来的に本格的なBT基盤を作るなら、学習価値は最も高いです。

---

# 次の一手

1. **vectorbt/PyBrokerで粗検証用Notebookを作る**
   目的は、戦略候補を100個作ることではなく、ダメな仮説を早く捨てること。

2. **NautilusTraderのBacktesting / Execution / Orders / Positions / Accountingだけ読む**
   Live/Adapter/AI/Integrationは今は読まない。

3. **自前Backtest Coreの最小版をPolarsで作る**
   `data → signal → order → fill → portfolio → metrics` だけでよい。最初からLive接続は入れない。

最終方針は、**NautilusTraderを先生にして、自分の軽量BT Coreを作る**です。既存OSSを丸ごと抱えるより、長期的に保守しやすく、Trade[XYZ]や日本株/NASDAQにも拡張しやすいです。

12:00:42.(05/31)

[1]: https://github.com/nautechsystems/nautilus_trader "GitHub - nautechsystems/nautilus_trader: Production-grade Rust-native trading engine with deterministic event-driven architecture · GitHub"
[2]: https://nautilustrader.io/docs/latest/concepts/backtesting/ "NautilusTrader Documentation"
[3]: https://github.com/polakowo/vectorbt "GitHub - polakowo/vectorbt: The backtesting engine that gives you an unfair advantage. Run thousands of trading ideas before others finish one. · GitHub"
[4]: https://github.com/edtechre/pybroker "GitHub - edtechre/pybroker: Algorithmic Trading in Python with Machine Learning · GitHub"
[5]: https://github.com/Yvictor/polars_backtest_extension "GitHub - Yvictor/polars_backtest_extension: Blazingly fast portfolio backtesting for Polars · GitHub"
[6]: https://github.com/microsoft/qlib "GitHub - microsoft/qlib: Qlib is an AI-oriented Quant investment platform that aims to use AI tech to empower Quant Research, from exploring ideas to implementing productions. Qlib supports diverse ML modeling paradigms, including supervised learning, market dynamics modeling, and RL, and is now equipped with https://github.com/microsoft/RD-Agent to automate R&D process. · GitHub"
[7]: https://github.com/nkaz001/hftbacktest "GitHub - nkaz001/hftbacktest: Free, open source, a high frequency trading and market making backtesting and trading bot, which accounts for limit orders, queue positions, and latencies, utilizing full tick data for trades and order books(Level-2 and Level-3), with real-world crypto trading examples for Binance and Bybit · GitHub"
[8]: https://github.com/barter-rs/barter-rs "GitHub - barter-rs/barter-rs: Open-source Rust framework for building event-driven live-trading & backtesting systems · GitHub"
[9]: https://github.com/paperswithbacktest/pwb-toolbox "GitHub - paperswithbacktest/pwb-toolbox: The toolbox for developing systematic trading strategies. It includes datasets and strategy ideas to assist in developing and backtesting trading algorithms. · GitHub"
[10]: https://github.com/kieran-mackle/AutoTrader "GitHub - kieran-mackle/AutoTrader: A Python-based development platform for automated trading systems - from backtesting to optimisation to livetrading. · GitHub"
[11]: https://github.com/ivopetiz/algotrading "GitHub - ivopetiz/algotrading: Algorithmic trading framework for cryptocurrencies. · GitHub"
[12]: https://github.com/jason8745/llm-agent-trader "GitHub - jason8745/llm-agent-trader: AI-powered stock trading backtesting system with LLM-based decision analysis, FastAPI backend, and Next.js frontend. · GitHub"
[13]: https://github.com/brokermr810/QuantDinger "GitHub - brokermr810/QuantDinger: AI quantitative trading platform for crypto, stocks, and forex with backtesting, live trading, market data, and multi-agent research.vibe-trading ,trading-agents,ai-trader,ai-trading · GitHub"
