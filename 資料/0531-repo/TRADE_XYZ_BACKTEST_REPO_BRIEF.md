# Trade[XYZ] Pure Backtest Repo Brief

作成日: 2026-05-31
対象 repo: `/home/tn/projects/marketlens-strike`
対象ブランチ: `feature/backtest-engine-roadmap`
目的: 外部協力者または別セッションへ、Trade[XYZ] 専用の純粋バックテスト基盤を設計するための repo 情報を渡す。

関連追補: `TRADE_XYZ_BACKTEST_INTAKE_ADDENDUM.md`
補正メモ: code-truth risk pass は追補の `Code-Truth Corrections` を正とする。

## 結論

`marketlens-strike` には、Trade[XYZ] の read-only データ取得、Strategy Research Lab、paper-only preview、venue quality gate、既存の簡易 backtest surface がすでにある。

今回の追加対象は、既存の live / paper / Strategy Authoring surface と混ぜず、Trade[XYZ] 専用の純粋バックテスト基盤として分けるのが安全。

MT5 / IC Markets / CFD は今の実装対象に入れない。将来分離しやすいように `Instrument`, `Venue`, `MarketData`, `Order`, `Fill`, `Position`, `CostModel`, `FillModel`, `Portfolio`, `BacktestEngine` という名前の抽象境界だけ意識する。

## 確認した正本

- `AGENTS.md`
- `README.md`
- `pyproject.toml`
- `docs/CURRENT_STATE.md`
- `docs/CODE_STATUS.md`
- `src/sis/backtest/`
- `src/sis/venues/trade_xyz/`
- `configs/fee_model.trade_xyz.yaml`
- `tests/`
- `資料/0531-backtest-oss.md`

コード、設定、tests、生成 artifact が最終的な正本。tracked docs は現行 surface の要約として読む。

## Repo Snapshot

```text
Repo:
  path: /home/tn/projects/marketlens-strike
  branch: feature/backtest-engine-roadmap

目的:
  Trade[XYZ] research, read-only evidence collection, Strategy Research Lab,
  paper operations, safety gates.

言語:
  - Python >=3.13,<3.14

package manager:
  - uv

主要依存:
  - typer
  - pydantic
  - httpx
  - polars
  - duckdb
  - pyarrow
  - pytest
  - pytest-httpx
  - pyrefly
  - ruff

実行形態:
  - CLI: uv run sis ...
  - public CLI registration: src/sis/cli.py
  - command modules: src/sis/commands/

データ保存:
  - raw JSONL under data/raw/
  - normalized Parquet under data/normalized/
  - DuckDB under data/normalized/sis.duckdb
  - operations/report artifacts under data/ops/ and data/reports/
```

## 現在ある主要機能

```text
data collection:
  - Trade[XYZ] read-only quote collector
  - allMids / l2Book / metaAndAssetCtxs based collection
  - raw quote JSONL output
  - normalized quotes Parquet / DuckDB output

trade_xyz:
  - instrument registry builder
  - perpDexs fallback asset-id resolution
  - quote normalizer
  - fee mode propagation from configs/fee_model.trade_xyz.yaml
  - quote diagnostics
  - strict artifact validation
  - phase-gate-review integration

strategy:
  - Strategy Research Lab models and commands
  - Strategy Authoring YAML flow
  - fixed-horizon paper-only backtest style evaluation
  - generated signal / candidate / paper intent artifacts

paper:
  - paper broker / fills / orders / portfolio / report / runner
  - venue quality gated fill behavior
  - PaperIntentPreview is paper-only

execution:
  - Trade[XYZ] micro live safety adapter exists in code/tests
  - public live execution CLI is not exposed
  - wallet secrets, signing, exchange writes, production live trading are out of scope

reporting/gates:
  - implementation-status
  - refresh-operations-artifacts
  - validate-artifacts --strict
  - phase-gate-review
  - bot-preview
```

## 重要な現行境界

- `READ_ONLY_GO` は read-only / paper gate が通っているという意味で、production live trading ready ではない。
- `bot-preview` は read-only HOLD preview artifact を生成する。実注文、wallet、signing、exchange write は使わない。
- `PaperIntentPreview` は paper-only artifact。live order として扱わない。
- `src/sis/execution/trade_xyz_adapter.py` などの micro live safety surface はあるが、標準 operator CLI にはまだ出していない。
- `data/` は git ignored runtime state。fresh checkout では存在しない artifact がある。
- 既存の `src/sis/backtest/` と `uv run sis build-backtest` は Strategy Lab / paper preview 寄りの簡易 backtest bridge であり、Trade[XYZ] 専用の独立した会計・約定・コスト検証エンジンとは分けて考える。
- `uv run sis strategy-author-run --spec <path> --through backtest` も既存 Strategy Authoring flow であり、新規純粋BT engineの public CLI ではない。
- `src/sis/execution/base.py::OrderIntent` と `src/sis/execution/trade_xyz_adapter.py::TradeXyzOrderIntent` は execution / adapter 側 contract。wallet / signing / exchange write を持たない backtest MVP contract へそのまま流用しない。
- `src/sis/strategies/sp500_trend_rates_vix.py` は `SPY`、`src/sis/strategies/qqq_trend_rates_vix.py` は `QQQ` を対象にする。Trade[XYZ] の `SP500` / `XYZ100` へ使う場合は明示的な symbol mapping と provenance check が必要。
- `InstrumentSpec` には `discovery_bound_bps` と `oi_cap_usd` がある。normalized quote row にはまだ `discovery_bound_pct` / `oi_cap_usage` はないため、BT入力では registry join 後の派生値として扱う。
- `QuoteLog.block_reasons` の model contract は `list[str]`。現 snapshot の Parquet dtype が `List(Null)` なのは、該当 snapshot で空リストしか入っていないためであり、永続 contract ではない。

## 既存 Backtest Surface

現行ファイル:

```text
src/sis/backtest/__init__.py
src/sis/backtest/bridge.py
src/sis/backtest/costs.py
src/sis/backtest/signals.py
```

現行の性格:

- `ResearchSignal` を読み、quote row と組み合わせて paper-only の fixed-horizon evaluation を行う。
- cost は `CostProfile` と `round_trip_cost_bps()` に寄せている。
- price selection は `exec_buy_price`, `exec_sell_price`, `mark_price`, `mid_price`, `oracle_price`, `index_price` の順で使う箇所がある。
- entry order, stop/take-profit, partial exit, slippage, fill fraction, spread/depth/latency/queue-position gate などの Strategy Authoring surface はある。

不足している純粋BT要素:

- 独立した `Order` / `Fill` / `Position` / `Portfolio` の event ledger
- Trade[XYZ] 固有の funding, discovery bounds, OI cap を中核に置いた cost/risk model
- accounting の不変条件テスト
- no-lookahead を engine contract として検証する test suite
- mark / oracle / external price の差分を明示的に扱う MarketData schema
- reportable な fee / funding / slippage impact breakdown

## Trade[XYZ] Backtestで特に見るべき既存データ

現行 collector は `collect_trade_xyz_quote_window()` から quote window を集める。

```text
raw:
  data/raw/quotes/trade_xyz/<YYYY-MM-DD>.jsonl

normalized:
  data/normalized/quotes.parquet
  data/normalized/sis.duckdb

summary/report:
  data/ops/trade_xyz_quote_collection_summary.json
  data/reports/trade_xyz_quote_collection_report.md
  data/ops/quote_diagnostics_summary.json
  data/reports/quote_diagnostics.md
```

特に重要な入力候補:

```text
price:
  - mid_price
  - mark_price
  - oracle_price
  - index_price / external reference price
  - exec_buy_price
  - exec_sell_price

cost:
  - taker_fee_bps
  - maker_fee_bps
  - fee_mode
  - spread_bps
  - funding

risk/filter:
  - is_tradable
  - block_reasons
  - bid/ask depth
  - open interest
  - source confidence / venue quality where available
```

Fee 設定は `configs/fee_model.trade_xyz.yaml` が現行入口。古い `0.04%` のような固定仮定を hardcode しない。

## Normalized Quotes Column Snapshot

2026-05-31 時点で `data/normalized/quotes.parquet` の schema を確認した。

確認コマンド:

```bash
uv run python - <<'PY'
from pathlib import Path
import polars as pl

path = Path("data/normalized/quotes.parquet")
if not path.exists():
    print("MISSING data/normalized/quotes.parquet")
else:
    schema = pl.scan_parquet(path).collect_schema()
    for name, dtype in schema.items():
        print(f"{name}: {dtype}")
PY
```

実カラム:

```text
ts_client: String
venue: String
canonical_symbol: String
venue_symbol: String
source: String
raw_payload_sha256: String
recv_ts_ms: Int64
source_ts_ms: Int64
dex: String
coin: String
asset_id: Int64
real_market_symbol: String
pair_index: Null
pair_id: Null
chain: Null
mark_price: Float64
index_price: Float64
oracle_price: Float64
best_bid: Float64
best_ask: Float64
bid_price: Float64
ask_price: Float64
mid_price: Float64
exec_buy_price: Null
exec_sell_price: Null
spread_bps: Float64
depth_10bps_usd: Float64
depth_25bps_usd: Float64
bid_depth_10bps_usd: Float64
ask_depth_10bps_usd: Float64
bid_depth_25bps_usd: Float64
ask_depth_25bps_usd: Float64
min_side_depth_10bps_usd: Float64
funding_rate: Float64
funding_interval_minutes: Null
open_interest_usd: Float64
premium: Float64
prev_day_price: Float64
day_notional_volume: Float64
fee_mode: String
taker_fee_bps: Float64
maker_fee_bps: Float64
oracle_ts_ms: Null
market_status: String
session_type: String
is_tradable: Boolean
source_confidence: Float64
venue_quality_score: Float64
block_reasons: List(Null)
raw_payload_ref: Null
```

schema案との差分:

- 実データには `external_price` はなく、現行では `index_price` / `real_market_symbol` / tracking layer を external reference として扱う。
- 実データには `discovery_bound_pct` と `oi_cap_usage` はまだない。MVP schema では予約し、registry の `discovery_bound_bps` / `oi_cap_usd` と quote row の `open_interest_usd` から後で派生できるようにする。null の場合は MVP entry gate では pass させる。
- `exec_buy_price` / `exec_sell_price` は `QuoteLog` と normalized quotes にカラムとして存在するが、現 snapshot では Null 型。MVP fill model は `exec_buy_price` / `exec_sell_price` を最優先し、欠ける場合は `best_ask` / `best_bid`、さらに欠ける場合は `mid_price` + `spread_bps` から保守的に推定する。推定値は row を mutate せず、fill record 側に `fill_price_source` として残す。
- `funding_rate`, `open_interest_usd`, `fee_mode`, `taker_fee_bps`, `maker_fee_bps`, `session_type`, `is_tradable`, `block_reasons` は現行 normalized quotes に存在する。
- `block_reasons: List(Null)` は snapshot artifact の dtype であり、空でない理由が入れば文字列 list になる想定。BT schema では `list[str]` として扱う。

## Naming Map

実装時に名前を混同しやすい箇所:

```text
BT schema proposal        Current source
------------------------  --------------------------------------------
symbol                    canonical_symbol
ts                        ts_client parsed as timezone-aware datetime
external_price            index_price first; real_market/tracking later
discovery_bound_pct       derived from registry discovery_bound_bps
oi_cap_usage              open_interest_usd / registry oi_cap_usd
funding_rate              quote row funding_rate, semantics not guessed
fee_bps                   row taker_fee_bps / maker_fee_bps, resolved from fee model
block_reasons             QuoteLog.block_reasons as list[str]
```

`funding_rate` の単位と適用間隔は、Trade[XYZ] payload semantics を別途確認するまで推測しない。MVPでは `None` を `0` とし、値がある場合も計算式は fixture で明示された interval 前提だけに限定する。

## 推奨する追加場所

既存の `src/sis/backtest/` を無理に汎用巨大化するより、Trade[XYZ] 純粋BTの責任境界を明確にする。

推奨案:

```text
src/sis/backtest/
  trade_xyz/
    __init__.py
    schema.py
    market_data.py
    asset_spec.py
    cost_model.py
    funding.py
    session.py
    discovery_bounds.py
    oi_cap.py

  engine/
    __init__.py
    event.py
    order.py
    fill.py
    portfolio.py
    runner.py
    metrics.py
```

ただし、最初の slice では大きな directory tree を一気に作らない。まず以下だけでよい。

```text
src/sis/backtest/trade_xyz/schema.py
src/sis/backtest/trade_xyz/cost_model.py
src/sis/backtest/engine/order.py
src/sis/backtest/engine/fill.py
src/sis/backtest/engine/portfolio.py
src/sis/backtest/engine/runner.py
```

tests:

```text
tests/backtest/
  test_trade_xyz_schema.py
  test_trade_xyz_cost_model.py
  test_fill_model.py
  test_portfolio_accounting.py
  test_no_lookahead.py
```

fixture policy:

- 既存 tests は `tmp_path` に `pl.DataFrame(...).write_parquet(...)` で小さい Parquet を作る流儀が多い。
- MVP も tracked binary Parquet fixture を増やすより、test 内または helper で deterministic DataFrame を生成する。
- `tests/fixtures/` に置くなら、既存と同じく小さい JSON sample を優先する。
- runtime artifact の `data/normalized/quotes.parquet` には unit test を依存させない。必要なら integration-ish test で存在時だけ読む。

## 最初に固定する入力 schema 案

Trade[XYZ] 専用の market data row:

```text
ts
symbol
open
high
low
close
volume
mid_price
mark_price
oracle_price
external_price
exec_buy_price
exec_sell_price
funding_rate
spread_bps
taker_fee_bps
maker_fee_bps
fee_mode
session_type
discovery_bound_pct
oi_cap_usage
is_tradable
block_reasons
```

必須度:

```text
MVP required:
  - ts
  - symbol
  - close or mid_price
  - exec_buy_price / exec_sell_price or spread_bps
  - taker_fee_bps / maker_fee_bps / fee_mode
  - is_tradable
  - block_reasons

MVP nullable but schema reserved:
  - mark_price
  - oracle_price
  - external_price
  - funding_rate
  - discovery_bound_pct
  - oi_cap_usage
```

## Order / Fill / Position Contract 案

Order:

```text
order_id
ts
symbol
side
order_type
qty
price
reduce_only
```

Fill:

```text
fill_id
order_id
ts
symbol
side
qty
fill_price
fee
slippage
liquidity_flag
```

Position:

```text
symbol
qty
avg_price
realized_pnl
unrealized_pnl
funding_pnl
fees_paid
```

Metrics:

```text
total_return
max_drawdown
sharpe
sortino
profit_factor
win_rate
avg_holding_time
turnover
fee_impact
funding_impact
slippage_impact
```

## Execution Semantics

MVP の時間・約定ルール:

```text
signal timing:
  - bar close で signal を生成した扱いにする
  - entry は同じ bar ではなく、次の executable row / bar で行う
  - no-lookahead test は、signal bar の high/low/close を entry fill に使わないことを確認する

market-like fill:
  - long entry: exec_buy_price -> best_ask -> conservative mid/spread estimate
  - long exit: exec_sell_price -> best_bid -> conservative mid/spread estimate
  - fill_price_source を必ず残す

untradable row:
  - is_tradable=false は entry 禁止
  - block_reasons が非空なら entry 禁止
  - open position の exit は、MVPでは close-only fallback を別 test で明示するまで禁止または stale exit として扱う

cost:
  - row の taker_fee_bps / maker_fee_bps を優先する
  - 欠ける場合は configs/fee_model.trade_xyz.yaml 由来の mode fallback を使う
  - fee_mode が unknown で fee rate も解決できない場合、MVPは entry 不可にする
  - fee hardcode はしない
```

MVP では maker fill を扱わない。すべて taker 相当の market-like fill として始める。

## Accounting Invariants

最初の test で最低限固定する不変条件:

```text
flat start:
  cash/equity baseline is explicit
  position qty starts at 0

long entry:
  qty increases
  avg_price equals fill_price for first entry
  fees_paid increases
  realized_pnl remains 0

long exit:
  qty returns to 0
  realized_pnl equals gross pnl - fees - slippage - funding
  unrealized_pnl returns to 0

blocked entry:
  no order/fill/position change
  blocked reason is recorded

no lookahead:
  changing future bar prices must not change prior entry decision/fill
```

これを通すまでは、short、multi-symbol、limit/stop、partial fill、portfolio allocation は入れない。

## 最初の実装順

派手な戦略ではなく、BT基盤の嘘を減らす順で進める。

```text
1. Trade[XYZ] market data schema
2. cost model
3. fill model
4. portfolio/accounting
5. no-lookahead test
6. metrics
7. 最小サンプル戦略
```

最初のサンプル戦略:

```text
symbol:
  SP500

timeframe:
  1h 相当。現行 quote window だけで足りない場合は resample/fixture で作る。

entry:
  20期間高値ブレイクで long

exit:
  10期間安値割れで exit

cost:
  fee + spread/slippage + funding を控除

filter:
  Discovery Bound 近辺では entry しない
  is_tradable=false または block_reasons 非空なら entry しない
```

## MVP Decision Record

2026-05-31 時点の実装前仮置きは以下で確定してよい。

```text
MVP:
  - symbol: SP500
  - timeframe: 1h相当
  - side: long-only
  - position: single-symbol only
  - order: market entry / market exit 相当
  - fill: exec_buy_price / exec_sell_price 優先
  - fallback fill: best_ask / best_bid, then conservative mid/spread estimate
  - fixture: deterministic tmp_path fixture first
  - funding: nullable, nullなら funding_cost=0
  - fee: configs/fee_model.trade_xyz.yaml 経由
  - discovery bound: entry gate only
  - OI cap: entry gate only
  - existing bridge: 触らない
  - CLI: MVPでは未公開。tests中心で engine を固めてから公開する
```

7点への回答:

1. `SP500 long-only single-symbol market-like fill` から始めてよい。
2. 最初の engine test は deterministic fixture 中心でよい。fresh checkout で runtime artifact に依存しない。既存 test 流儀に合わせ、基本は `tmp_path` に小さい Parquet を生成する。
3. `funding_rate=None` は許容する。schema と metrics には funding impact を残す。
4. fee 設定入口は `configs/fee_model.trade_xyz.yaml` と normalized row の `fee_mode` / `taker_fee_bps` / `maker_fee_bps` に寄せる。row に解決済み fee があれば row を優先する。hardcode はしない。
5. Discovery Bound / OI cap は MVP では entry 禁止フィルターだけでよい。null の場合は pass とし、将来 strict mode を追加する。
6. 既存 `src/sis/backtest/bridge.py` は Strategy Lab / paper-only compatibility surface として温存する。
7. CLI は後回し。最初は `tests/backtest/*` で `accounting`, `no-lookahead`, `cost`, `fill` を固める。

## Stop Conditions

実装に入る場合、以下に当たったらその場で止めて資料または plan を更新する。

- `fee_mode=unknown` で fee rate を解決できないのに entry できてしまう。
- `block_reasons` 非空または `is_tradable=false` の row で新規 entry できてしまう。
- `funding_rate` の単位を推測で年率化・時間按分している。
- signal row と同じ row の future information で fill している。
- 既存 `src/sis/backtest/bridge.py` の public behavior を壊す必要が出る。
- CLI を公開しないと test できない設計になっている。
- `data/normalized/quotes.parquet` が無い fresh checkout で unit test が落ちる。

## MT5 / IC Markets / CFD の扱い

今の repo に MT5 / IC Markets / CFD を入れない。

将来のために名前だけ衝突しにくくする。

```text
Trade[XYZ]:
  Venue = TradeXYZ
  Instrument = Perpetual
  Cost = fee + funding + spread + slippage
  Risk = discovery bounds + OI cap + thin liquidity

MT5 / IC Markets CFD:
  Venue = MT5 / ICMarkets
  Instrument = CFD
  Cost = spread + commission + swap
  Risk = margin level + leverage + trading session
```

今は CFD 用の `swap`, `contract size`, `point`, `digits`, `margin mode` は実装しない。

## 外部協力者へ渡す最小情報

この repo で追加設計を依頼するなら、以下を渡す。

```text
Repo:
  path: /home/tn/projects/marketlens-strike
  branch: feature/backtest-engine-roadmap

目的:
  Trade[XYZ]専用の純粋バックテストを追加したい。
  live tradingとの接続は今回は対象外。

現在の構成:
  Python: >=3.13,<3.14
  package manager: uv
  DB: DuckDB runtime artifact
  data storage: JSONL / Parquet / DuckDB / generated reports
  CLI: Typer app via uv run sis ...

現在ある機能:
  - data collection: Trade[XYZ] read-only quote collector
  - strategy: Strategy Research Lab / Strategy Authoring YAML
  - execution: paper and micro live safety surface, not production live
  - risk: venue quality gates, halt/scalping policies
  - reporting: ops/reports/phase gates
  - tests: pytest, pytest-httpx, strategy_authoring slice

取得済みデータ:
  - storage path: data/raw/quotes/trade_xyz/*.jsonl
  - normalized path: data/normalized/quotes.parquet
  - registry: data/registry/trade_xyz_instrument_registry.json
  - runtime artifacts are generated and git ignored

バックテストしたい最初の戦略:
  SP500 1h
  20期間高値ブレイクで long
  10期間安値割れで exit
  fee + funding + slippageを控除
  Discovery Bound近辺では entry しない

制約:
  - Python 3.13
  - uv
  - Polars優先
  - OSS丸ごと採用ではなく部品取り
  - MT5/IC Markets CFDは将来別プロジェクト
```

## 実装前に確認する質問

現時点では blocking question はない。MVPでは上記の仮置き推奨で進める。

実装が Phase 2 に入る前に再確認するなら次だけでよい。

1. 最初の engine 入力は quote row からの resample bar にするか、bar fixture から始めるか。
   回答: MVP は deterministic bar fixture first。quote-derived fixture は integration-ish test として追加する。

2. cost model の MVP に funding を必須にするか、nullable にして fee/spread から始めるか。
   回答: nullable。`None` は `0` として計算し、metrics の列は残す。

3. 既存 `src/sis/backtest/bridge.py` を拡張するか、別 engine として作るか。
   回答: 別 engine として作る。既存 bridge は Strategy Lab / paper-only surface の互換を守る。

## 仕様化 readiness

ready.

前提:

- 今回は docs / 付録としての設計整理であり、実装はまだしない。
- Trade[XYZ] 専用BTを先に作り、MT5 / CFD は名前の拡張余地だけ残す。
- live trading readiness と read-only / paper readiness を混同しない。
- 既存 Strategy Authoring の fixed-horizon backtest surface は壊さない。

## Omission / Error-Risk Pass

今回の資料化で潰した主な誤謬リスク:

- `READ_ONLY_GO` を live-ready と読める余地を排除した。
- `exec_buy_price` / `exec_sell_price` が常に入っている前提を排除し、現 snapshot では Null 型であることを書いた。
- `external_price`, `discovery_bound_pct`, `oi_cap_usage` が現 normalized quotes に存在するかのような誤読を避け、派生値として扱う方針を書いた。
- `block_reasons: List(Null)` を contract と誤読しないよう、Pydantic model では `list[str]` であることを書いた。
- fee の hardcode を避け、row resolved fee と `configs/fee_model.trade_xyz.yaml` の責任を分けた。
- funding の単位を推測しない stop condition を追加した。
- tracked binary fixture を増やす前提を避け、既存 tests と同じ `tmp_path` 生成方針に寄せた。
- no-lookahead の具体的な時間ルールを追加した。
