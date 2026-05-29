# One Doc: Strategy Parts to Implementation

この文書は、戦略部品の考え方から、この repo で実装・検証・paper 運用へ進めるまでを 1 本で読める粒度にした実装用メモです。

結論:

- 戦略は「予測モデル」ではなく、複数の安全部品を通った意思決定パイプラインとして実装する。
- 最初に作るべきものは live bot ではなく、再現可能な signal CSV、decision log、paper run である。
- `Signal Generator` は注文してはいけない。注文候補を出すだけにする。
- 実装は `feature -> signal -> risk gate -> execution plan -> paper fill -> report` の順に薄く通す。
- 1 つ目の実装対象は、複雑な AI 戦略ではなく、条件が明示できる trend pullback 型がよい。

対象外:

- すぐに実資金 live order を出す手順。
- 特定銘柄が儲かるという主張。
- 最適パラメータの提示。
- secret、wallet、private key、API key の配置方法。

---

## 1. 全体像

戦略を次の部品に分ける。

```text
Universe Selector
  -> Data Collector
  -> Data Quality Gate
  -> Feature Factory
  -> Regime Detector
  -> Signal Generator
  -> Participation Filter
  -> Position Sizer
  -> Exit Module
  -> Execution Planner
  -> Paper Broker
  -> Evaluation Harness
  -> Monitoring / Risk Guard
```

実装上の意味:

| 部品 | 役割 | 失敗すると何が起きるか |
|---|---|---|
| Universe Selector | 対象銘柄を決める | 薄い銘柄、取引不能銘柄、データ不足銘柄を混ぜる |
| Data Collector | 価格、板、出来高、状態を集める | 古い価格や欠損を本物として扱う |
| Data Quality Gate | 使ってよいデータか判定する | stale data で発注する |
| Feature Factory | 指標や特徴量を作る | 未来情報リーク、計算不整合が起きる |
| Regime Detector | 相場状態を分類する | 使うべきでない環境で戦略を動かす |
| Signal Generator | 売買候補を出す | ただの思いつきが注文になる |
| Participation Filter | 入らない条件を判定する | spread、流動性、危険トークンを無視する |
| Position Sizer | 損失上限から数量を決める | stop 距離や流動性を無視して張る |
| Exit Module | 撤退条件を決める | 損切り、利確、時間切れが曖昧になる |
| Execution Planner | 注文意図に変換する | 戦略判断と注文実行が混ざる |
| Paper Broker | 仮想約定で記録する | live 前の失敗検出ができない |
| Evaluation Harness | 採用/棄却を判定する | 都合の良いバックテストだけ残る |
| Monitoring / Risk Guard | 異常時に止める | データ、約定、状態不一致で暴走する |

重要なのは、`Signal Generator` より前に data quality と regime があり、後ろに filter、sizer、risk、execution があること。signal は注文命令ではない。

---

## 2. この repo での実装先

現状の repo には、すでに戦略実装の骨格がある。

| 目的 | 既存の場所 | 使い方 |
|---|---|---|
| 戦略関数 | `src/sis/strategies/` | feature frame から signal frame を作る |
| signal CSV 読み込み | `src/sis/backtest/signals.py` | `ts_signal, canonical_symbol, side, timeframe` を読む |
| backtest bridge | `src/sis/backtest/bridge.py` | quote と signal を decision record に変換する |
| decision context | `src/sis/core/context.py` | 判断時刻、銘柄、timeframe、状態を保持する |
| strategy decision | `src/sis/core/decision.py` | enter/skip、side、reason、score を保持する |
| execution plan | `src/sis/core/execution_plan.py` | enter/skip を注文計画にする |
| risk gate | `src/sis/risk/risk_gate.py` | stale、halt、timeframe などを拒否する |
| paper run | `src/sis/paper/runner.py` | decision record から paper order/fill/report を作る |
| tests | `tests/` | 小さい単位で仕様を固定する |

最初の戦略追加で触る候補:

```text
src/sis/strategies/<strategy_name>.py
tests/test_strategies.py
data/research/signals.csv
```

次の段階で触る候補:

```text
src/sis/core/decision.py
src/sis/core/context.py
src/sis/risk/risk_gate.py
src/sis/core/execution_plan.py
tests/test_backtest_bridge.py
tests/test_paper_runner.py
```

最初から触らない方がよい場所:

```text
src/sis/execution/
src/sis/execution/trade_xyz_adapter.py
src/sis/execution/live_order_policy.py
```

理由は、live execution は戦略検証が終わった後の層だから。戦略の妥当性が未確認の段階で live adapter を強化しても、危険な注文を出す能力だけが増える。

---

## 3. 最小データ契約

### 3.1 Signal CSV

この repo の backtest bridge は、少なくとも次の列を持つ CSV を読める。

```csv
ts_signal,canonical_symbol,side,timeframe,signal_strength
2026-01-01T00:00:00+00:00,QQQ,long,4h,0.42
```

必須列:

| column | 意味 | 例 |
|---|---|---|
| `ts_signal` | signal が発生した時刻 | `2026-01-01T00:00:00+00:00` |
| `canonical_symbol` | repo 内の標準銘柄 | `QQQ` |
| `side` | long / short | `long` |
| `timeframe` | 保有・判断時間軸 | `4h` |

任意列:

| column | 意味 | 例 |
|---|---|---|
| `signal_strength` | 優先度や score | `0.42` |

注意:

- `side` は `buy/bull/long` を long、`sell/bear/short` を short として正規化できる。
- `timeframe` は risk 側の `check_timeframe` に通る必要がある。
- signal CSV は「発注命令」ではない。あくまで候補。

### 3.2 Normalized Quote

backtest bridge は normalized quote parquet を読む。最低限、次が必要。

| column | 意味 |
|---|---|
| `ts_client` | quote を取得した時刻 |
| `venue` | venue 名 |
| `canonical_symbol` | 標準銘柄 |
| `market_status` | open / closed / unknown |
| `is_tradable` | 取引可能か |

実際の価格評価には次のいずれかが必要。

| long entry 優先順 | short entry 優先順 |
|---|---|
| `exec_buy_price` | `exec_sell_price` |
| `mark_price` | `mark_price` |
| `mid_price` | `mid_price` |
| `oracle_price` | `oracle_price` |
| `index_price` | `index_price` |

cost/slippage には次が効く。

| column | 使い道 |
|---|---|
| `spread_bps` | round trip cost の見積もり |
| `taker_fee_bps` | venue fee |
| `maker_fee_bps` | venue fee |
| `oracle_ts_ms` | stale / missing 判定 |

---

## 4. 最初に作るべき戦略の形

最初の 1 本は、次の条件を満たすものにする。

- ルールが文章で説明できる。
- signal 発火条件が 5 個以下。
- stop または invalidation を定義できる。
- 1 銘柄から開始できる。
- 手数料と slippage を悪化させても壊れ方を見られる。
- live 注文なしで paper まで通せる。

避けるもの:

- 「SNSで話題」「AIが上がると言った」だけの signal。
- entry だけあり exit がない戦略。
- token discovery 直後に auto buy する Bot。
- ML 確率だけで position size を増やす戦略。
- 最初から複数 venue / 複数 chain / 複数 timeframe を扱う設計。

推奨する初回戦略:

```text
Trend Pullback Strategy

対象:
  QQQ または liquidity が十分ある1銘柄

前提:
  data_status == valid
  market_status == open
  is_tradable == true
  regime == trend

long candidate:
  close > sma_50
  sma_50 slope > 0
  close が sma_20 近辺へ押す
  short momentum が反転する
  event blackout ではない

exit:
  invalidation price 割れ
  max holding bars 超過
  daily loss limit
  ATR trail
```

---

## 5. 部品を実装単位に分解する

### 5.1 Universe Selector

入力:

- instrument registry
- normalized quote
- volume/depth/spread
- trading session

出力:

```python
selected_symbols: list[str]
rejected_symbols: list[dict]
```

最初の実装では、固定銘柄でよい。

```python
UNIVERSE = ["QQQ"]
```

ただし、固定銘柄でも reject 理由は設計しておく。

```text
SYMBOL_NOT_IN_REGISTRY
NOT_TRADABLE
SPREAD_TOO_WIDE
DEPTH_TOO_THIN
DATA_TOO_SPARSE
```

### 5.2 Data Quality Gate

入力:

- quote row
- `ts_client`
- `oracle_ts_ms`
- `market_status`
- `is_tradable`
- price columns

出力:

```text
valid | stale | missing | closed | not_tradable
```

最低限の判定:

```text
if required price is missing:
    missing
elif oracle_ts_ms is missing:
    stale_or_untrusted
elif market_status != "open":
    closed
elif is_tradable is not true:
    not_tradable
else:
    valid
```

既存の `evaluate_risk_gate` は `oracle_ts_ms` 欠落や halt reason を拒否できる。最初は重複実装せず、signal 生成時の前処理と risk gate の両方で検知する。

### 5.3 Feature Factory

入力:

- normalized quote / research price series

出力:

```text
feature_frame
```

最低限の列:

| column | 意味 |
|---|---|
| `ts` | feature 時刻 |
| `canonical_symbol` | 銘柄 |
| `close` or `research_close` | 終値相当 |
| `sma_20` | 短期平均 |
| `sma_50` | 中期平均 |
| `close_above_sma20` | close > sma20 |
| `sma_50_slope` | trend 判定 |
| `realized_vol_20` | volatility |
| `is_event_blackout` | 指標/イベント回避 |
| `trade_allowed` | 取引許可 |
| `data_status` | valid/stale/missing |

リーク防止:

- `ts` より未来の価格を使わない。
- rolling 指標は現在足 close 後にしか使えない前提にする。
- signal timestamp と quote timestamp を分ける。

### 5.4 Regime Detector

入力:

- feature frame
- spread/depth
- realized vol
- trend slope

出力:

```text
trend | range | panic | thin_liquidity | unknown
```

最小ロジック:

```text
if data_status != valid:
    unknown
elif spread_bps > max_spread_bps:
    thin_liquidity
elif realized_vol_20 > vol_p95:
    panic
elif close > sma_50 and sma_50_slope > 0:
    trend
else:
    range
```

最初は `feature_frame` に `regime` 列を追加するだけでよい。class を作るより純粋関数で十分。

### 5.5 Signal Generator

入力:

- feature frame
- regime
- data status

出力:

```text
ts_signal, canonical_symbol, side, timeframe, signal_strength, strategy_name, reason
```

この repo の既存例:

```python
def build_qqq_trend_rates_vix_signals(feature_frame: pl.DataFrame) -> pl.DataFrame:
    ...
```

新規戦略も同じ形でよい。

望ましい出力列:

| column | 必須度 | 意味 |
|---|---|---|
| `ts_signal` | 必須 | signal 時刻 |
| `canonical_symbol` | 必須 | 銘柄 |
| `side` | 必須 | long / short |
| `timeframe` | 必須 | 例: 4h |
| `signal_strength` | 任意 | score |
| `strategy_name` | 推奨 | 戦略名 |
| `reason` | 推奨 | 発火理由 |
| `invalidation_price` | 将来追加推奨 | 仮説が壊れる価格 |
| `regime` | 将来追加推奨 | 発火時の相場状態 |

重要:

- signal は `should_enter=True` と同義ではない。
- signal は risk gate で落ちる前提にする。
- signal 生成時に `trade_allowed` や `event_blackout` を見てもよいが、risk gate 側でも別途拒否できるようにする。

### 5.6 Participation Filter

入力:

- signal candidate
- quote row
- market status
- spread
- depth
- token safety
- event blackout

出力:

```text
allow | skip(reason)
```

最小ロジック:

```text
if data_status != valid:
    skip("DATA_NOT_VALID")
elif regime in ["panic", "thin_liquidity", "unknown"]:
    skip("BAD_REGIME")
elif spread_bps > max_spread_bps:
    skip("SPREAD_TOO_WIDE")
elif event_blackout:
    skip("EVENT_BLACKOUT")
else:
    allow
```

この repo では、当面は `risk_gate` と `strategy signal generation` に分散している。より明確にするなら、将来 `src/sis/risk/participation_filter.py` を足す。ただし最初は新しい層を作るより、`reason` と `blocked_reasons` をきちんと記録する方が重要。

### 5.7 Position Sizer

入力:

- equity
- entry price
- invalidation price
- max risk per trade
- liquidity cap
- portfolio exposure

出力:

```text
quantity
size_reason
```

基本式:

```text
risk_amount = equity * risk_per_trade
stop_distance = abs(entry_ref - invalidation_price)
raw_qty = risk_amount / stop_distance
qty = min(raw_qty, liquidity_cap, portfolio_cap)
```

現状の `run_paper_step` は `quantity=1.0` 固定で order を作る。研究初期としては許容できるが、実装粒度としては不足している。

次に必要な変更:

```text
ExecutionPlan に quantity / risk_amount / invalidation_price を入れる
PaperBroker が ExecutionPlan.quantity を使う
tests/test_paper_runner.py に quantity 反映テストを足す
```

### 5.8 Exit Module

入力:

- open position
- current quote
- invalidation price
- trailing stop
- max holding time
- risk state

出力:

```text
hold | exit(reason)
```

exit は最低 4 種類に分ける。

| exit | 意味 |
|---|---|
| `INVALIDATION_EXIT` | 仮説が壊れた |
| `RISK_EXIT` | daily loss / panic / halt |
| `PROFIT_PROTECTION_EXIT` | 利益保護 |
| `TIME_EXIT` | 動かないので閉じる |

現状の backtest bridge は、signal の次の quote を exit として使う簡易評価に近い。初期検証には使えるが、実戦的な exit module とは言えない。

次に必要な変更:

```text
DecisionRecord に exit_reason を持てる設計を検討
Backtest bridge に holding horizon / max holding bars を導入
PaperPortfolio の open position に exit evaluation を追加
```

### 5.9 Execution Planner

入力:

- DecisionContext
- StrategyDecision
- RiskDecision
- sizing result

出力:

```text
ExecutionPlan
```

既存の `ExecutionPlan` は次を持つ。

```text
action
venue
canonical_symbol
timeframe
price_reference
source_confidence
venue_quality_score
tracking_trade_allowed
fee_mode
estimated_round_trip_cost_bps
fill_price_source
notes
```

不足している可能性が高いもの:

```text
side
quantity
entry_ref
invalidation_price
max_slippage_bps
strategy_name
risk_amount
participation_reason
```

すぐ全部足す必要はない。最初は `notes` と decision log で追跡し、paper sizing を入れる段階で型を拡張する。

---

## 6. 最初の実装スライス

### 6.1 スライス A: signal generator だけ作る

目的:

- feature frame から signal frame を作れるようにする。
- 注文、paper、risk はまだ触らない。

追加候補:

```text
src/sis/strategies/trend_pullback.py
tests/test_strategies.py
```

期待する関数:

```python
from __future__ import annotations

import polars as pl


def build_trend_pullback_signals(feature_frame: pl.DataFrame) -> pl.DataFrame:
    if feature_frame.is_empty():
        return pl.DataFrame(
            schema={
                "ts_signal": pl.Datetime(time_zone="UTC"),
                "canonical_symbol": pl.Utf8,
                "side": pl.Utf8,
                "timeframe": pl.Utf8,
                "signal_strength": pl.Float64,
                "strategy_name": pl.Utf8,
                "reason": pl.Utf8,
            }
        )

    return (
        feature_frame
        .filter(pl.col("data_status") == "valid")
        .filter(pl.col("regime") == "trend")
        .filter(pl.col("trade_allowed"))
        .filter(~pl.col("is_event_blackout"))
        .filter(pl.col("close") > pl.col("sma_50"))
        .filter(pl.col("sma_50_slope") > 0)
        .filter(pl.col("distance_to_sma20_pct").abs() <= 0.01)
        .filter(pl.col("short_momentum_turns_up"))
        .with_columns(
            pl.col("ts").alias("ts_signal"),
            pl.lit("long").alias("side"),
            pl.lit("4h").alias("timeframe"),
            (
                pl.col("sma_50_slope").fill_null(0.0)
                - pl.col("realized_vol_20").fill_null(0.0) * 0.1
            ).alias("signal_strength"),
            pl.lit("trend_pullback").alias("strategy_name"),
            pl.lit("trend_pullback_resume").alias("reason"),
        )
        .select(
            "ts_signal",
            "canonical_symbol",
            "side",
            "timeframe",
            "signal_strength",
            "strategy_name",
            "reason",
        )
        .sort("ts_signal")
    )
```

テスト観点:

- empty frame で schema だけ返る。
- `regime != trend` は出ない。
- `data_status != valid` は出ない。
- `event_blackout` は出ない。
- 条件を満たす QQQ だけ signal が出る。
- 出力列が `load_research_signals` に渡せる形になっている。

### 6.2 スライス B: signal CSV に落とす

目的:

- backtest bridge が読める形式へ出す。

出力:

```text
data/research/signals.csv
```

必要列:

```text
ts_signal,canonical_symbol,side,timeframe,signal_strength
```

検証:

```text
uv run python - <<'PY'
from pathlib import Path
from sis.backtest.signals import load_research_signals
signals = load_research_signals(Path("data/research/signals.csv"))
print(len(signals))
print(signals[:3])
PY
```

期待:

- parse error が出ない。
- timeframe が risk policy に拒否されない。
- symbol が uppercase になる。

### 6.3 スライス C: backtest bridge に通す

目的:

- signal が risk gate と execution plan を通るか確認する。

入力:

```text
data/normalized/quotes.parquet
data/research/signals.csv
data/research/venue_cost_matrix.csv
```

確認する出力:

```text
data/evidence/decision_logs/*.jsonl
data/research/decision_summary.json
```

見るべき項目:

| 項目 | 良い状態 |
|---|---|
| `signals_considered` | signal 数と一致 |
| `executed_count` | 0 でもよいが理由が説明可能 |
| `blocked_count` | block 理由が残る |
| `blocked_reason_counts` | stale / halt / timeframe などが見える |
| decision log | context, strategy, risk, execution_plan が揃う |

### 6.4 スライス D: paper run に通す

目的:

- paper order/fill/report を作る。

確認する出力:

```text
data/paper/orders.parquet
data/paper/fills.parquet
data/paper/positions.parquet
data/paper/daily_pnl.parquet
data/reports/daily_paper_report.md
```

最初の期待:

- fill が 0 でも失敗ではない。
- 0 の場合は、risk gate / quote lookup / price missing のどれで止まったか見る。
- fill が出たら、価格参照と fee 前提を確認する。

---

## 7. 採用/棄却の評価基準

戦略候補は、利益額だけで採用しない。

最低限の scorecard:

| 項目 | 記録する内容 |
|---|---|
| 仮説 | なぜこの signal が機能すると思ったか |
| 対象 | symbol, venue, timeframe |
| データ期間 | start / end |
| 除外条件 | stale, closed, event blackout |
| cost 前提 | fee, spread, slippage |
| signal 数 | 発火数 |
| executed 数 | risk 通過数 |
| blocked 数 | 拒否数 |
| blocked 理由 | stale, halt, spread 等 |
| total return | 総リターン |
| max drawdown | 最大DD |
| worst trade | 最悪取引 |
| exposure ratio | 市場に晒した割合 |
| stress | cost x2 / slippage x2 |
| 判定 | adopt / reject / observe |

採用しない条件:

- trade count が少なすぎる。
- 最適パラメータ一点だけが良い。
- cost x2 で簡単に消える。
- skip した取引の方が良い。
- block 理由を無視すると成績が出る。
- exit が未定義。
- live で取得できないデータを使っている。

---

## 8. Bot 化する前の条件

live Bot 化の前に、最低限これを満たす。

```text
1. signal が再現可能
2. decision log が残る
3. risk gate の block 理由が説明可能
4. paper order/fill が残る
5. position state を復元できる
6. unknown order / unknown position 時に止まる設計がある
7. daily loss limit がある
8. max position / max exposure がある
9. stale data 時に新規注文しない
10. 手動停止できる
```

Bot 化してはいけない状態:

- signal の理由が自然文だけ。
- entry はあるが exit がない。
- backtest が quote fallback だけで signal-driven になっていない。
- paper fill の価格参照が確認できていない。
- rejected / unknown order の扱いがない。
- wallet / secret 管理が設計されていない。
- 実行 adapter を通す必要性だけが先行している。

---

## 9. Solana / Meme Token 戦略に使う場合

Solana bot は、最初から auto buy にしない。

最初の実装順:

```text
Token Discovery
  -> Token Safety Filter
  -> Paper Observation
  -> Sellability Check
  -> Manual Review
  -> Small Paper Strategy
  -> Live Canary
```

Token Safety Filter の最低項目:

| 項目 | 危険な状態 |
|---|---|
| Mint Authority | 追加発行可能 |
| Freeze Authority | 凍結可能 |
| Transfer Fee | 売買コスト不明 |
| Holder Concentration | 上位 holder 集中 |
| LP Depth | 流動性不足 |
| Sell Simulation | 売却不能 |
| Pool Age | 生成直後で履歴不足 |

最初の出力は `buy` ではなくこれにする。

```text
safe_to_observe
needs_manual_review
unsafe
```

`safe_to_observe` は `safe_to_buy` ではない。

---

## 10. 理想的ナラティブの危険

| ナラティブ | 危険 | 実装上の修正 |
|---|---|---|
| AI が精度を上げれば勝てる | 約定、cost、regime、data quality が無視される | ML は最初 filter / anomaly detection に使う |
| Bot 化すれば優位性になる | 自動化は損失も自動化する | まず paper observer にする |
| 早く入れば勝てる | 薄い板、rug、売却不能を踏む | token safety と sell simulation を先に置く |
| signal が多いほど良い | 低品質 trade が増える | participation filter と skip PnL を見る |
| 勝率が高ければ良い | tail loss で死ぬ | worst trade, max DD, loss streak を見る |
| バックテストが良いなら良い | 過剰最適化かもしれない | walk-forward, cost x2, parameter neighborhood を見る |

---

## 11. 実装チェックリスト

### 11.1 実装前

- 仮説を 1 文で書ける。
- 対象 symbol が決まっている。
- timeframe が決まっている。
- entry 条件が 5 個以下。
- exit 条件がある。
- invalidation がある。
- data source が live 時点で利用可能。
- cost/slippage を入れる。

### 11.2 signal 実装

- empty frame の schema がある。
- 必須列を出す。
- event blackout を除外する。
- data status を見る。
- regime を見る。
- reason を残す。
- `tests/test_strategies.py` で固定する。

### 11.3 backtest 実装

- signal CSV が parse できる。
- decision log が出る。
- risk gate の block 理由が出る。
- executed / blocked が summary に出る。
- cost matrix を使う。
- quote fallback と signal-driven を区別する。

### 11.4 paper 実装

- order が出る。
- fill が出る、または出ない理由が分かる。
- position が保存される。
- daily report が出る。
- realized PnL が記録される。
- quantity 固定が残る場合、制約として明記する。

### 11.5 live 前

- read-only / paper で十分な window がある。
- unknown order 時に止まる。
- unknown position 時に止まる。
- stale data 時に止まる。
- daily loss で止まる。
- manual kill switch がある。
- secret を docs/repo に置かない。

---

## 12. 具体的な first issue

最初に切るなら、この issue がよい。

```text
Title:
  Add trend_pullback signal generator and tests

Scope:
  - Add src/sis/strategies/trend_pullback.py
  - Add tests in tests/test_strategies.py
  - Do not touch live execution
  - Do not add new dependencies

Acceptance:
  - Empty input returns expected schema
  - Non-trend regime emits no signal
  - Invalid data emits no signal
  - Event blackout emits no signal
  - Valid trend pullback emits one long 4h signal
  - Output can be written as signal CSV columns

Verification:
  uv run pytest tests/test_strategies.py
```

次の issue:

```text
Title:
  Carry quantity through execution plan into paper broker

Scope:
  - Add quantity to ExecutionPlan
  - Use quantity in PaperOrder and PaperBroker fill
  - Keep default quantity=1.0 for backward compatibility

Acceptance:
  - Existing tests still pass
  - New test shows non-1.0 quantity reaches paper order/fill
  - No live adapter changes

Verification:
  uv run pytest tests/test_paper_runner.py tests/test_backtest_bridge.py
```

---

## 13. 現状ドキュメントの正直な評価

`STRATEGY_PARTS_DEEP_DIVE.md` は、部品の意味を理解するには使える。

しかし、これ 1 本だけで実装まで進めるには不足していた。

不足していたもの:

- repo の既存実装先との対応。
- signal CSV の実際の列。
- normalized quote の必要列。
- 最初に触るファイル。
- 触らない方がよい live execution 層。
- first issue の切り方。
- テスト観点。
- paper run で何を見るか。
- `quantity=1.0` 固定など、現状実装の制約。
- exit module がまだ粗いことの明記。

この文書で補ったもの:

- 部品から実装ファイルへの対応表。
- signal 生成関数の具体例。
- signal CSV / quote parquet の契約。
- backtest / paper への接続順。
- 採用/棄却 scorecard。
- Bot 化前の停止条件。
- Solana bot の observer-first 手順。
- 実装 issue の粒度。

---

## 14. 最小の成功定義

この文書を読んだ後、実装者ができるべきこと:

```text
1. 戦略仮説を1文にする
2. feature frame の必要列を決める
3. signal generator を1関数で作る
4. tests/test_strategies.py にテストを足す
5. signal CSV に出す
6. backtest bridge に通す
7. decision log の block 理由を見る
8. paper run に通す
9. report と fills を確認する
10. live execution に進むべきでない条件を判断する
```

これができないなら、まだドキュメントとして薄い。

現時点では、この文書を正本にし、`STRATEGY_PARTS_DEEP_DIVE.md` と `STRATEGY_PARTS_HANDBOOK.md` は補助資料として扱うのがよい。

---

## 15. 図表・付録で見る場合

長文だけで把握しにくい場合は、`appendix_materials/` を使う。

| 目的 | 付録 |
|---|---|
| 全体の流れを図で見る | `appendix_materials/01_PIPELINE_DIAGRAMS.md` |
| 部品を1枚カードで見る | `appendix_materials/02_COMPONENT_CARDS.md` |
| repoの実装先を見る | `appendix_materials/03_REPO_IMPLEMENTATION_MAP.md` |
| signal CSVやdecision logの例を見る | `appendix_materials/04_ARTIFACT_EXAMPLES.md` |
| 売買発生シグナルを設計する | `appendix_materials/12_SIGNAL_DESIGN_PLAYBOOK.md` |
| シグナル型を選ぶ | `appendix_materials/13_SIGNAL_PATTERN_LIBRARY.md` |
| シグナル候補を採点する | `appendix_materials/14_SIGNAL_REVIEW_SCORECARD.md` |
| Trend Pullbackを通しで見る | `appendix_materials/05_WORKED_EXAMPLE_TREND_PULLBACK.md` |
| leakage / walk-forwardを確認する | `appendix_materials/06_VALIDATION_LEAKAGE_AND_WALK_FORWARD.md` |
| LightGBM / Polars / VectorBTの誤用を避ける | `appendix_materials/07_MODEL_AND_FEATURE_RISK_SHEETS.md` |
| Crypto/DeFi固有の安全確認を見る | `appendix_materials/08_SOLANA_JITO_TOKEN_SAFETY_SHEETS.md` |
| 作業テンプレートを使う | `appendix_materials/09_CHECKLISTS_AND_TEMPLATES.md` |
| 理想的ナラティブを疑う | `appendix_materials/10_NARRATIVE_RISK_FLASHCARDS.md` |
| 実装直前の公式情報入口を見る | `appendix_materials/11_CURRENTNESS_SOURCE_NOTES.md` |
