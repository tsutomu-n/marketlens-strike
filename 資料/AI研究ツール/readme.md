結論：**これは完成すると「Trade[XYZ]専用の、実弾売買をしない純粋バックテスト基盤」になります。**
売買Bot本体ではなく、**Trade[XYZ]の15m/1h相当データで、戦略候補がコスト込みで成立するかを検証する研究・検証ツール**です。

現時点のパッチは、その完成形のうち **最初の土台部分** です。CLIで一般利用する完成ツールではなく、まずは `tests/backtest/*` で `accounting / fill / cost / no-lookahead` を固定する段階です。

---

## 1. 完成形はなにか

完成形は、こういうものです。

```txt
Trade[XYZ] Pure Backtest Engine
```

役割は次です。

* Trade[XYZ]のmarket dataを読む
* 戦略候補のsignalを読む
* 次bar以降で約定させる
* 手数料・spread/slippage・fundingを引く
* ポジション、損益、ドローダウンを計算する
* no-lookahead、つまり未来データを使っていないことを検証する
* 結果を `metrics.json`、`fills.parquet`、`equity_curve.parquet`、`backtest_report.md` などで出す

重要なのは、**既存の `uv run sis build-backtest` とは別物**として作ることです。既存 `build-backtest` はStrategy Lab / paper-only bridge寄りのsurfaceであり、新しい純粋BT engineとは分ける方針です。

---

## 2. 何ではないか

これは以下ではありません。

* 実弾売買Bot
* live execution
* wallet署名
* exchange write
* 注文送信
* nonce管理
* cloid lifecycle
* MT5 / IC Markets / CFD対応
* 汎用マルチ市場バックテスター
* HFT / MM / アービトラージ用検証器

資料でも、MVPには wallet / signing / exchange write を混ぜないこと、live execution系を入れないことが明示されています。

---

## 3. 今回のパッチでできること

今回のパッチは、完成形のうち **バックテストエンジンの核になる最小部品**です。

できることは主にこれです。

### できること

* Trade[XYZ]用market data rowのschemaを検証する
* fee / slippage / nullable fundingのcost modelを検証する
* long entry / exitのfill価格を決める
* `exec_buy_price` / `exec_sell_price` がなければ、bid/askやmid/spreadから保守的にfill価格を推定する
* `fill_price_source` を残す
* `is_tradable=false` や `block_reasons` 非空なら新規entryを止める
* portfolio accountingを検証する
* 同じbarの未来情報を使って約定しないことをテストする
* 既存 `bridge.py` / `build-backtest` を壊さずに別engineとして追加する

資料上も、最初は `schema.py`、`cost_model.py`、`order.py`、`fill.py`、`portfolio.py`、`runner.py` 程度から始めるのがよいとされています。

### まだできないこと

* CLIから本格実行すること
* report artifactを全部出すこと
* 複数銘柄検証
* short
* limit / stop
* partial fill
* L2 replay
* 実際のTrade[XYZ] quote-derived barsを使った本格検証
* RobustLab / LEM連携

---

## 4. どう使うのか

### 現時点の使い方

現時点では、**ユーザーがCLIで使うツールではなく、開発者がテストで使う基盤**です。

使い方はこうです。

```bash
git apply trade_xyz_backtest_engine_v0_1_apply.patch

uv run ruff check src/sis/backtest/engine src/sis/backtest/trade_xyz tests/backtest
uv run pytest -q tests/backtest tests/test_backtest_fixed_horizon.py tests/test_backtest_bridge.py
uv run pyrefly check src/sis/backtest/engine src/sis/backtest/trade_xyz
```

目的は、まず以下を固定することです。

```txt
- fee計算が壊れていないか
- fill価格選択が保守的か
- blockされたrowでentryしないか
- fundingを勝手に推測していないか
- no-lookaheadが守られているか
- 既存bridgeが壊れていないか
```

---

## 5. 完成後の想定CLI

PR-8以降でCLI公開するなら、最終的にはこういう使い方になります。

```bash
uv run sis backtest-trade-xyz \
  --strategy sp500-breakout-v0 \
  --symbol SP500 \
  --timeframe 1h \
  --input data/normalized/quotes.parquet \
  --fee-model configs/fee_model.trade_xyz.yaml \
  --out runs/backtest/SP500_breakout_v0
```

または、戦略候補ファイルを読む形ならこうです。

```bash
uv run sis backtest-trade-xyz \
  --candidate candidates/SC-SP500-BREAKOUT-001.json \
  --input data/normalized/quotes.parquet \
  --out runs/backtest/SC-SP500-BREAKOUT-001
```

ただし、**これはまだ今回パッチには入れていません。**
CLI公開は、contract、accounting、fill、cost、no-lookaheadが安定してからでよいです。

---

## 6. 何がわかるのか

完成すると、戦略候補について以下がわかります。

### 1. コスト込みで残るか

```txt
gross pnl は良いが、fee / spread / slippage / funding後に死ぬか
```

Trade[XYZ]ではfee、spread、slippage、fundingを無視すると、戦略候補をかなり過大評価します。今回のengineは、最初からcost modelを分けて評価する設計です。

---

### 2. no-lookaheadをしていないか

```txt
signal barの情報で、同じbarのfillをしていないか
未来barの価格変更で過去entryが変わらないか
```

これはかなり重要です。
バックテストが良く見える典型的な原因が、無意識の未来情報混入だからです。

資料でも、signal barと同じrowのfuture informationでfillしないこと、future bar変更が過去entry decision/fillを変えないことが不変条件として示されています。

---

### 3. どの価格で約定した想定なのか

```txt
exec_buy_price
best_ask
ask_price
mid_price + half spread
```

のどれでfillしたかがわかります。

これにより、

```txt
この成績は本当に実行可能な価格か？
都合よくmidで約定していないか？
spreadが広い局面で過大評価していないか？
```

を確認できます。

---

### 4. ブロック条件で止まっているか

以下のようなTrade[XYZ]特有の条件でentryを止められます。

```txt
is_tradable=false
block_reasons非空
fee_mode=unknown
Discovery Bound近辺
OI cap近辺
market_status不適合
session_type不適合
```

MVPではまず `is_tradable`、`block_reasons`、fee解決不能を重視します。

---

### 5. 戦略候補を比較できる

将来的に `metrics.json` が出ると、候補ごとに比較できます。

```txt
- net_return_after_cost
- max_drawdown
- trade_count
- win_rate
- profit_factor
- cost_drag_bps
- fee_impact
- funding_impact
- slippage_impact
- blocked_reason_counts
```

つまり、単に「儲かったか」ではなく、

```txt
なぜ儲かったか
どのコストで死ぬか
どの条件で止まるか
どの候補を次に検証すべきか
```

が見えるようになります。

---

## 7. 最終的な利用イメージ

完成後の流れはこうです。

```txt
1. Trade[XYZ] quote / bar dataを集める
   ↓
2. normalized quotes / barsを作る
   ↓
3. 戦略候補を用意する
   ↓
4. backtest-trade-xyzを実行する
   ↓
5. fills / equity / metrics / report を出す
   ↓
6. 成績と失敗理由を見る
   ↓
7. 採用 / 保留 / 廃棄を決める
```

このengineの目的は、**勝てる戦略を自動生成することではありません。**
目的は、**戦略候補がTrade[XYZ]の実行現実に耐えるかを検査すること**です。

---

## 8. 具体例：SP500ブレイクアウト

MVPの最初の検証候補はこうです。

```txt
symbol:
  SP500

side:
  long-only

entry:
  20期間高値ブレイク

exit:
  10期間安値割れ

fill:
  market-like taker fill

cost:
  fee + spread/slippage + nullable funding

gate:
  is_tradable
  block_reasons
  fee解決
  Discovery Bound
  OI cap
```

これを実行すると、最終的には次のようなことがわかります。

```txt
- SP500の単純ブレイクアウトは、手数料込みで残るか
- spread/slippageを入れると死ぬか
- fundingを入れるとどの程度悪化するか
- entryの多くがblockされるか
- 最大DDが許容範囲か
- そもそもTrade[XYZ]で実行可能性があるか
```

---

## 9. 今回パッチの位置づけ

今回のパッチは、完成形の中でここです。

```txt
完成形:
  Trade[XYZ] Pure Backtest Engine

今回:
  contracts / schema / cost / fill / portfolio / no-lookahead の土台

次:
  metrics / artifacts / report

その次:
  sample strategy adapter

最後:
  public CLI
```

つまり、今回の成果物は **「使えるバックテストツールの完成品」ではなく、「信用できるバックテストツールを作るための最初の安全な土台」**です。

---

## 10. 次に作るべきもの

次はこれです。

```txt
PR-6: Metrics and report artifacts
```

追加するもの：

```txt
src/sis/backtest/engine/metrics.py
src/sis/backtest/engine/artifacts.py
tests/backtest/test_backtest_artifacts.py
```

出力するもの：

```txt
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

これが入ると、初めて「検証結果を人間が読む」「他の候補と比較する」段階に入ります。

---

## 一言でいうと

これは、**Trade[XYZ]で戦略候補を安全にふるい落とすためのバックテスト検査装置**です。

* 今はまだ実弾売買しない
* 今はまだ完成CLIではない
* まず嘘の少ない会計・約定・コスト・no-lookaheadを固定する
* 完成すると、戦略候補がTrade[XYZ]で本当に検証に耐えるかがわかる

17:38:33.(05/31)
