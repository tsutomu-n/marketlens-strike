結論: **完成形は、Trade[XYZ]専用の“純粋バックテストエンジン v0.1”です。**
これは売買Bot本体でも、live発注機能でもなく、**Trade[XYZ]のSP500などを対象に、戦略候補を手数料・スリッページ・funding・取引不可条件込みで検証するための基盤**です。

---

# 1. 完成形はなに？

完成すると、Repoに次のような機能が追加されます。

```txt
Trade[XYZ] Pure Backtest Engine v0.1

できること:
  - Trade[XYZ]のSP500を対象にバックテストする
  - long-only / single-symbolで検証する
  - bar closeでsignalを作り、次のexecutable rowで約定させる
  - fee / spread / slippage / fundingを控除する
  - is_tradable=false や block_reasonsありのrowではentryしない
  - no-lookaheadをテストで固定する
  - orders / fills / trades / equity_curve / metrics / report を出す
```

最初のMVPは、**SP500・1h相当・long-only・market-like taker fill**に絞ります。short、multi-symbol、maker fill、L2 replay、partial fill、MT5/CFD対応、live発注は入りません。これは資料側でも、MVPをSP500・long-only・single-symbol・market-like fillに限定し、既存bridgeやlive系を混ぜない方針として整理されています。

---

# 2. これは何ではない？

重要です。これは以下ではありません。

```txt
違うもの:
  - live trading bot
  - paper broker
  - Hyperliquid発注adapter
  - wallet / signing / nonce / cloid 管理
  - LEM
  - Safety Layer
  - RobustLab full integration
  - MT5 / IC Markets CFD backtester
```

今回作るものは、あくまで **Trade[XYZ]専用の純粋backtest engine** です。資料でも、`build-backtest` や既存Strategy Lab / paper surfaceと混ぜず、wallet / signing / exchange write を持たない別contractとして始めるべきとされています。

---

# 3. どう使うの？

## 実装直後の使い方

最初はCLI公開より、テストで意味を固定します。

```bash
uv run pytest -q tests/backtest/
```

この段階で確認すること:

```txt
- portfolio accountingが正しい
- fee計算が正しい
- fundingがnullableで扱える
- no-lookaheadが守られている
- is_tradable=falseでentryしない
- block_reasonsありでentryしない
- fill_price_sourceが記録される
- 既存 build-backtest を壊していない
```

## CLI公開後の使い方

後半PRでCLIを出すなら、最終的にはこういう操作になります。

```bash
uv run sis backtest-trade-xyz \
  --config configs/backtest_trade_xyz_sp500_mvp.yaml
```

入力は、最初は小さいdeterministic fixtureでよいです。実data/normalized/quotes.parquetに依存しない方針です。資料でも、unit testは `tmp_path` や小さいfixtureで完結させ、runtime artifactである `data/normalized/quotes.parquet` の常在を前提にしない方針になっています。

---

# 4. 入力はなに？

最小入力は、Trade[XYZ]のbar/quote風データです。

最低限必要な列:

```txt
ts
symbol
close or mid_price
exec_buy_price / exec_sell_price or spread_bps
taker_fee_bps / maker_fee_bps / fee_mode
is_tradable
block_reasons
```

あれば使う列:

```txt
mark_price
oracle_price
index_price
funding_rate
open_interest_usd
best_bid
best_ask
spread_bps
session_type
market_status
venue_quality_score
source_confidence
```

現行normalized quotesには、`mark_price`, `index_price`, `oracle_price`, `best_bid`, `best_ask`, `mid_price`, `spread_bps`, `funding_rate`, `open_interest_usd`, `fee_mode`, `taker_fee_bps`, `maker_fee_bps`, `is_tradable`, `block_reasons` などがあると整理されています。

---

# 5. 出力はなに？

完成すると、1回のbacktest runごとに以下が出ます。

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

これらのartifactには、最低限以下を入れます。

```txt
run_id
strategy_id
symbol
timeframe
input_data_ref
input_schema_hash
config_hash
fee_model_ref
funding_policy
fill_model
no_live_order=true
wallet_used=false
exchange_write_used=false
```

`no_live_order=true`, `wallet_used=false`, `exchange_write_used=false` を明示することで、これはlive発注ではなく純粋backtestであると証跡に残します。資料でも、このartifact contractが予定されています。

---

# 6. 何がわかるの？

## 6.1 戦略候補がコスト後に残るか

たとえば、SP500の20期間高値ブレイク / 10期間安値割れ戦略を回したときに、次が分かります。

```txt
- fee控除後で利益が残るか
- spread/slippage込みで利益が残るか
- funding込みで利益が残るか
- cost_drag_bpsがどれくらいか
- fee_impact / funding_impact / slippage_impact の内訳
```

つまり、「チャート上では勝って見えるが、コストを入れたら死ぬ」を検出できます。

---

## 6.2 どのentryが禁止されたか

次のようなrowではentryしません。

```txt
is_tradable=false
block_reasonsが非空
fee_mode unknownでfee解決不可
discovery bound / OI cap に引っかかる
```

そのため、次が分かります。

```txt
- どれだけのsignalが取引不可でブロックされたか
- どのblock reasonが多いか
- 取引可能時間だけで戦略が成立するか
```

これはTrade[XYZ]では重要です。参照市場、session、market_status、取引不可条件がCrypto native perpより複雑になりやすいためです。

---

## 6.3 約定価格の根拠

fillごとに `fill_price_source` を残します。

例:

```txt
exec_buy_price
best_ask
mid_plus_spread_estimate
exec_sell_price
best_bid
mid_minus_spread_estimate
```

これにより、次が分かります。

```txt
- 実行価格として信頼できる列を使えたか
- fallback推定に頼っている割合が高すぎないか
- fill結果がどれくらい保守推定に依存しているか
```

現snapshotでは `exec_buy_price` / `exec_sell_price` はカラムとして存在するがNull型であるため、fallback設計が必須です。資料でも、欠ける場合は `best_ask` / `best_bid`、さらに欠ける場合は保守的なmid/spread推定に落とし、fill record側に `fill_price_source` を残す方針になっています。

---

## 6.4 no-lookaheadが守られているか

このbacktest engineでは、signalを作った同じbarで都合よく約定しません。

```txt
signal:
  bar closeで生成

entry:
  次のexecutable row/barでfill
```

そのため、次が分かります。

```txt
- 未来の価格を使っていないか
- signal barのhigh/low/closeをentry fillに使っていないか
- 未来barを書き換えても過去entryが変わらないか
```

これはバックテストの信用度に直結します。

---

## 6.5 会計が壊れていないか

以下の不変条件がテストされます。

```txt
entry:
  position qty increases
  avg_price = first fill price
  fees_paid increases
  realized_pnl remains 0

exit:
  qty returns to 0
  realized_pnl = gross pnl - fees - slippage - funding
  unrealized_pnl returns to 0

blocked entry:
  no order/fill/position change
```

これにより、次が分かります。

```txt
- PnL計算が正しいか
- feeが二重控除されていないか
- fundingが未反映ではないか
- blocked entryでポジションが動いていないか
```

---

# 7. 最初のサンプル戦略はなに？

MVPではこれです。

```txt
SP500 long-only breakout

entry:
  過去20本高値を上抜けたらlong

exit:
  過去10本安値を下抜けたらexit

fill:
  market-like taker fill

cost:
  fee + spread/slippage + nullable funding

filter:
  is_tradable
  block_reasons
  discovery bound
  OI cap
```

これは「勝つための最終戦略」ではありません。
**backtest engineの意味を固定するための最小戦略**です。

---

# 8. 完成すると最終的に何を判断できる？

判断できること:

```txt
- このTrade[XYZ]戦略候補は、最低限のコスト後で残るか
- 取引不可条件を入れても成立するか
- fee/slippage/fundingのどれで利益が消えるか
- fill価格が実データ由来か、fallback推定に依存しているか
- no-lookaheadを守った検証になっているか
- accountingが壊れていないか
- RobustLabへ渡すcandidate_resultとして最低限耐えるか
```

判断できないこと:

```txt
- 本番で勝てるか
- live executionで同じslippageになるか
- L2板を食ったときの正確なfill
- maker指値が本当に約定するか
- 複数銘柄portfolioで成立するか
- short戦略が成立するか
- liquidation riskを含めた安全性
- MT5 / CFDでも使えるか
```

ここを誤解しないことが重要です。

---

# 9. この完成形の価値

このv0.1の価値は、派手な戦略発見ではありません。

```txt
価値:
  既存Repoに、責務が混ざらないTrade[XYZ]専用backtest engineの芯を作ること。
```

特に次を固定できます。

```txt
- live/paper/Strategy Labと混ざらない
- fee hardcodeしない
- runtime artifactに依存しない
- no-lookaheadをテストで縛る
- accountingをテストで縛る
- SPY→SP500を暗黙変換しない
- MT5/CFD抽象化を今やらない
```

---

# 10. 一言でいうと

```txt
これは、Trade[XYZ]の戦略候補を
「本当に検証できる形」にするための最小バックテスト基盤。
```

もう少し具体的に言うと:

```txt
SP500のようなTrade[XYZ]銘柄について、
シンプルな戦略を、
取引不可条件・手数料・スプレッド・funding・no-lookahead込みで検証し、
orders / fills / trades / equity_curve / metrics / reportとして残す道具。
```

そして最終的に分かるのはこれです。

```txt
この戦略は、理想価格ではなく、
Trade[XYZ]で実際に取引可能だった前提に寄せても、
次の検証段階へ進めるだけの価値があるか？
```

15:31:08.(05/31)
