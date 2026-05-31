結論：**完成形は「Trade[XYZ]専用のバックテスト実験装置」です。**
Bot本体ではなく、**戦略を本番やpaperへ進める前に、コスト込み・約定前提込み・no-lookahead込みで“その戦略を信じてよいか”を確認する基盤**です。

---

## 1. 完成形はなにか

完成すると、Repo内に次のような独立したバックテストエンジンができます。

```text
src/sis/backtest/
  trade_xyz/
    schema.py
    cost_model.py
    funding.py
    discovery_bounds.py
    oi_cap.py

  engine/
    order.py
    fill.py
    portfolio.py
    runner.py
    metrics.py
    artifacts.py
```

既存の `uv run sis build-backtest` は触りません。これは既存のStrategy Lab / bridge系commandであり、新しく作るPure Backtest Engineとは別物として扱います。

完成後の役割はこうです。

```text
価格データ / fixture
  ↓
Trade[XYZ]専用MarketData schema
  ↓
戦略ロジック
  ↓
BacktestOrder
  ↓
BacktestFill
  ↓
BacktestPortfolio
  ↓
trades / equity curve / metrics / report
```

つまり、**「シグナルが出たら、Trade[XYZ]で本当に勝てそうか」を会計・コスト・約定・禁止条件込みで検証する装置**です。

---

## 2. 最初の完成形 v0.1

最初のv0.1はかなり絞ります。

```text
対象:
  Trade[XYZ]のみ

銘柄:
  SP500

時間軸:
  1h相当

売買方向:
  long-only

戦略:
  20期間高値ブレイクでentry
  10期間安値割れでexit

約定:
  market-like taker fill

コスト:
  fee
  spread / slippage
  nullable funding

禁止条件:
  is_tradable=false ならentry禁止
  block_reasons非空ならentry禁止
  discovery bound近辺ならentry禁止
  OI cap超過ならentry禁止
```

資料上も、MVPは `SP500 long-only single-symbol market-like fill` から始め、`funding_rate=None` は許容、既存bridgeは触らず、CLI公開は後回しとされています。

---

## 3. どう使うのか

### 実装初期

最初はCLIではなく、テストから使います。

```bash
uv run pytest tests/backtest -q
```

理由は、まず次を固定するためです。

```text
会計が正しいか
未来情報を使っていないか
fee/slippage/fundingの扱いが正しいか
entry禁止条件が効いているか
既存build-backtestを壊していないか
```

unit testは `data/normalized/quotes.parquet` に依存せず、`tmp_path` とPolarsで小さなdeterministic fixtureを作る方針です。runtime artifactはfresh checkoutに常在しないため、unit testの正本にはしません。

---

### CLI公開後

PR-8以降に、たとえばこう使う形になります。

```bash
uv run sis backtest-trade-xyz \
  --input data/normalized/quotes.parquet \
  --symbol SP500 \
  --timeframe 1h \
  --strategy examples/breakout_sp500_1h_v0.yaml \
  --output-dir data/backtest/trade_xyz/sp500_breakout_v0
```

ただし、CLI公開は最後です。先に `accounting`, `cost`, `fill`, `no-lookahead` をテストで固定します。PR計画でも、PR-8で初めて `uv run sis backtest-trade-xyz ...` を公開する流れになっています。

---

## 4. 出力されるもの

完成すると、1回のバックテストごとに次のartifactが出ます。

```text
backtest_run.json
orders.parquet
fills.parquet
trades.parquet
equity_curve.parquet
metrics.json
candidate_result.json
data_manifest.json
config_hash.txt
backtest_report.md
```

これは新規Pure Backtest Engine用のartifactで、既存 `build-backtest` が出す `data/research/backtest_report.md` などとは別物です。

特に重要なのはこの4つです。

```text
orders.parquet
  いつ、何を、どれだけ注文した想定か

fills.parquet
  どの価格で約定した想定か
  fill_price_sourceも残る

trades.parquet
  1回ごとのentry/exit、損益、保有時間

metrics.json
  戦略全体の成績
```

さらに、metadataとして必ず以下を残します。

```text
no_live_order=true
wallet_used=false
exchange_write_used=false
fee_model_ref
funding_policy
fill_model
input_schema_hash
config_hash
```

これにより、「この結果は本番発注ではない」「どのデータ・どの設定・どの約定仮定で出たか」が追跡できます。

---

## 5. 何がわかるのか

### 5.1 その戦略がコスト後に残るか

分かること：

```text
手数料を引いた後にプラスか
spread/slippageを入れても残るか
fundingを入れると消えるか
コストがどれだけ利益を削ったか
```

見る指標：

```text
net_return_after_cost
total_return
cost_drag_bps
fee_impact
funding_impact
slippage_impact
```

資料では、最低限のmetricsとして `net_return_after_cost`, `max_drawdown`, `trade_count`, `profit_factor`, `cost_drag_bps`, `blocked_reason_counts` などを出す想定になっています。

---

### 5.2 その戦略の損益特性

分かること：

```text
総損益
最大ドローダウン
勝率
profit factor
最悪トレード
中央値トレード損益
保有時間
取引回数
```

これにより、たとえば次が判断できます。

```text
利益は出るがDDが大きすぎる
勝率は高いが1回の負けが大きすぎる
取引回数が少なすぎて信用できない
コストを入れると期待値が消える
```

---

### 5.3 どの条件で取引できなかったか

分かること：

```text
is_tradable=falseで止まった回数
block_reasonsで止まった回数
discovery boundで止まった回数
OI capで止まった回数
fee_mode unknownで止まった回数
```

これはかなり重要です。

単に「戦略が勝った/負けた」ではなく、

```text
そもそもTrade[XYZ]上で実行可能だったのか
```

が分かります。

---

### 5.4 バックテストがズルをしていないか

特に見るのは `no-lookahead` です。

完成形では、

```text
signal barと同じbarでentryしない
entryは次のexecutable row/barで行う
未来barを変えても過去のentry/fillが変わらない
```

をテストします。資料でも、未来bar価格の変更で過去entry decision/fillが変わらないことを不変条件として固定する方針です。

つまり、**「未来の価格を見て勝ったことにしていないか」**を検査できます。

---

## 6. 何がまだ分からないのか

v0.1では、まだ次は分かりません。

```text
liveで本当に約定するか
板を食った時の正確なslippage
partial fill
limit orderの約定確率
maker fill
L2 replay
複数銘柄のportfolio allocation
short戦略
MT5 / IC Markets / CFD
本番発注の安全性
```

段階としては、資料上こうです。

```text
Phase 1:
  OHLCV / bar-like fixture + fee + spread/slippage

Phase 2:
  normalized quotesからbar生成

Phase 3:
  bid/ask-aware fill and depth gate

Phase 4:
  L2 sweep-depth / replay quality

Phase 5:
  event-driven / execution reality comparison
```

最初からL2 replayやevent-driven full simulatorには行きません。

---

## 7. 実務的には何に使うのか

主な使い方は3つです。

### 使い方1：戦略候補を捨てる

たとえば、SP500のブレイクアウト戦略を回して、

```text
net_return_after_cost < 0
trade_countが少ない
max_drawdownが大きい
cost_drag_bpsが大きすぎる
blocked_reasonが多すぎる
```

なら、その戦略は捨てます。

これは「勝てる戦略を探す」より重要です。
**嘘のバックテストで先に進まないための装置**です。

---

### 使い方2：戦略改善の比較に使う

たとえば次を比較できます。

```text
20/10 breakout
30/15 breakout
ATR stopあり
funding filterあり
discovery bound strictあり
spread filter強め
```

比較して、

```text
コスト後で改善したか
DDが減ったか
取引回数が消えていないか
blocked reasonが増えすぎていないか
```

を見ます。

---

### 使い方3：paperへ進める候補を作る

バックテストで最低条件を通った戦略だけ、次段階のpaper observationへ送ります。

この時点でも、まだliveではありません。

```text
Backtest green
  ↓
paper候補
  ↓
paper observation
  ↓
execution reality比較
  ↓
tiny-live候補
```

という段階です。

---

## 8. これと既存Repo機能の違い

既存Repoにはすでに、

```text
Trade[XYZ] quote collection
Strategy Research Lab
paper-only preview
venue quality gate
簡易 backtest bridge
```

があります。今回追加するものは、それらと混ぜず、**Trade[XYZ]専用の独立した会計・約定・コスト検証エンジン**です。

違いはこうです。

| 項目              | 既存 `build-backtest`            | 新 Pure Backtest Engine              |
| --------------- | ------------------------------ | ----------------------------------- |
| 目的              | Strategy Lab / paper preview寄り | 純粋な検証エンジン                           |
| 中心              | signals / bridge               | Order / Fill / Position / Portfolio |
| 会計不変条件          | 薄い                             | 明示テストする                             |
| no-lookahead    | 補助的                            | engine contractとして固定                |
| Trade[XYZ]固有コスト | 一部                             | 中核にする                               |
| CLI             | 既存あり                           | MVPでは未公開、最後に公開                      |
| 既存互換            | 触ると危険                          | 別pathで作る                            |

---

## 9. 具体例

たとえば、SP500の1hブレイクアウトを回すと、最終的にこういうことが分かります。

```text
戦略:
  SP500 1h
  20期間高値ブレイクでlong
  10期間安値割れでexit

結果:
  取引回数: 42
  勝率: 45%
  profit factor: 1.18
  net_return_after_cost: +3.2%
  max_drawdown: -7.5%
  cost_drag_bps: 210bps
  blocked entries:
    is_tradable=false: 3
    block_reasons: 5
    discovery_bound: 2
```

この場合に分かることは、

```text
コスト後でも一応プラス
ただしDDに対して利益が薄い
blocked entryが一定ある
パラメータ改善またはfilter改善が必要
paperへ進めるには弱い
```

のような判断です。

---

## 10. ひと言でいうと

これは、完成するとこういう道具です。

```text
Trade[XYZ]で戦略を動かしたつもりになったとき、
本当にコスト後で勝っているのか、
約定前提は現実的か、
未来情報を使っていないか、
そもそも取引可能な状態だったのか、
を検査するバックテスト装置。
```

最初の完成形は、**SP500専用・long-only・単一戦略の検査装置**です。
最終的には、**複数戦略をpaperへ進める前の選別ゲート**になります。

17:17:50.(05/31)
