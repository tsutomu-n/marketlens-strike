# Trade[XYZ] Backtest Intake Addendum

作成日: 2026-05-31
対象 repo: `/home/tn/projects/marketlens-strike`
関連資料: `TRADE_XYZ_BACKTEST_REPO_BRIEF.md`
目的: 重複する intake メモを統合し、外部共有・設計レビュー・実装計画化に使う追補資料として残す。

## 結論

Repo について伝えるべき情報は、すでに `TRADE_XYZ_BACKTEST_REPO_BRIEF.md` にかなり入っている。

この追補では、重複を増やさず、次の不足分だけを追加する。

- 外部公開情報から見た Trade[XYZ] / Hyperliquid / HIP-3 前提
- Repo ZIP または抜粋共有時のチェックリスト
- Trade[XYZ] 専用 backtest intake の記入済み版
- RobustLab / LEM へ将来つなぐ場合の artifact 境界
- PR 単位の実装計画たたき台
- live / wallet / signing / exchange write を混ぜない stop condition

## 確認した外部ソース

2026-05-31 時点で、実装判断に使う外部情報は一次情報を優先する。

- [Trade[XYZ] Docs: XYZ Architecture](https://docs.trade.xyz/)
- [Trade[XYZ] Docs: Mark Price](https://docs.trade.xyz/perp-mechanics/mark-price)
- [Trade[XYZ] Docs: Specification Index](https://docs.trade.xyz/consolidated-resources/specification-index)
- [Trade[XYZ] Docs: Fees](https://docs.trade.xyz/perp-mechanics/fees)
- [Trade[XYZ] Docs: Funding](https://docs.trade.xyz/perp-mechanics/funding)
- [Hyperliquid Docs: WebSocket Subscriptions](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions)
- [Hyperliquid Docs: Exchange Endpoint](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/exchange-endpoint)
- [Hyperliquid Docs: Nonces and API Wallets](https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/nonces-and-api-wallets)
- [S&P DJI announcement: S&P 500 licensed to Trade[XYZ] for perpetual contracts on Hyperliquid](https://www.spglobal.com/spdji/en/index-announcements/article/sp-dow-jones-indices-licenses-sp-500-to-trade-xyz-for-perpetual-contracts-on-hyperliquid/)

WSJ / Barron's などの報道は補助参考にできるが、repo 仕様へ落とす根拠は公式 docs と S&P DJI announcement を優先する。

## External Premise

Trade[XYZ] Docs 上の整理:

- Hyperliquid は perpetual trading markets への permissionless access を提供する chain / venue。
- HIP-3 は independent builders が Hyperliquid 上に perpetual markets を deploy / operate する仕組み。
- XYZ protocol は HIP-3 DEX として market listings, oracle sources, leverage limits などを定義する。
- trade[XYZ] は XYZ markets と他 Hyperliquid markets へアクセスする interface であり、XYZ markets への唯一の入口ではない。

設計上の読み替え:

```text
Execution venue:
  Hyperliquid

Product / market profile:
  Trade[XYZ] / XYZ protocol markets

Backtest target:
  Trade[XYZ] symbols on Hyperliquid / HIP-3
```

この repo では当面、`venue=trade_xyz` として扱う。将来 live execution を設計する時だけ、`TradeXYZProfile` と `HyperliquidExecutionVenue` の責務分離を改めて検討する。

## Code-Truth Corrections

この追補で使う「現状」は、2026-05-31 時点の repo code / CLI / tests を正とする。

重要な補正:

```text
existing backtest surface:
  uv run sis build-backtest
  src/sis/backtest/bridge.py
  tests/test_backtest_bridge.py
  tests/test_backtest_fixed_horizon.py

proposed new surface:
  Trade[XYZ] 専用の純粋 backtest engine
  まだ public CLI として登録しない
```

`build-backtest` は既存の Strategy Lab / bridge 系 command であり、この資料で提案している新規純粋 backtest engine ではない。実装時は既存 bridge の互換性を壊さないことを先に固定する。

既存 execution contract も用途を分ける。

```text
src/sis/execution/base.py:
  OrderIntent
  live / adapter 側の最小 intent contract

src/sis/execution/trade_xyz_adapter.py:
  TradeXyzOrderIntent
  post_only / tif / cloid / leverage などを持つ execution adapter 側 contract

new backtest:
  wallet / signing / exchange write を持たない別 contract として開始する
```

既存 strategy symbol もそのまま Trade[XYZ] symbol とは見なさない。

```text
src/sis/strategies/sp500_trend_rates_vix.py:
  canonical_symbol == "SPY" を対象に signal を作る

src/sis/strategies/qqq_trend_rates_vix.py:
  canonical_symbol == "QQQ" を対象に signal を作る

Trade[XYZ] registry examples:
  SP500
  XYZ100
```

したがって、`SPY -> SP500` や `QQQ -> XYZ100` は現 code の暗黙契約ではない。使う場合は、明示的な symbol mapping / data provenance / session 差分 / execution gate を別タスクとして作る。

`data/`, `logs/`, `.tmp/` 配下は runtime artifact として扱う。`data/paper/*`, `data/research/*`, `data/ops/*`, `data/normalized/*` は「実行すれば生成され得るもの」であり、fresh checkout に常在する前提で unit test や docs を書かない。

## Market Mechanics To Preserve

Trade[XYZ] 専用 backtest で無視しないもの:

```text
price:
  - oracle price
  - mark price
  - index / external reference price
  - best bid / best ask / mid
  - last trade if later collected

cost:
  - taker fee
  - maker fee
  - growth / standard fee mode
  - spread
  - slippage
  - funding

risk and filters:
  - discovery bound
  - open interest cap
  - market_status
  - session_type
  - holiday / maintenance closure
  - source_confidence
  - venue_quality_score
  - block_reasons
```

外部 docs からの重要メモ:

- mark price は oracle, mid-oracle basis の EWMA, bid/ask/last trade median を使う仕組みとして説明されている。MVP では再計算せず、row の `mark_price` を使う。
- specification index には instrument ごとの max leverage, discovery bound, margin mode, external/internal session hours, OI cap がある。MVP では registry / quote row に無い項目を推測で埋めない。
- fees は standard / growth mode で異なる。公式 docs の tier 0 は standard taker 0.090% / maker 0.030%、growth taker 0.0090% / maker 0.0030% と説明される。repo の `configs/fee_model.trade_xyz.yaml` では bps 表現として扱い、row の `fee_mode` / `taker_fee_bps` / `maker_fee_bps` を優先する。
- funding は hourly payment として説明され、payment には oracle price を使う。公式 docs では `funding_payment = position_size * oracle_price * funding_rate` と説明される。MVP では funding rate の単位・interval を fixture / schema で固定するまで推測しない。

## Repo Sharing Checklist

このローカル repo を外部協力者へ渡す場合:

含める:

```text
AGENTS.md
README.md
pyproject.toml
uv.lock
.env.example
configs/
schemas/
src/
tests/
docs/
plan/README.md
資料/0531-repo/
```

除外する:

```text
.git/
.venv/
node_modules/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
dist/
build/
logs/
.env
secrets
API keys
wallet private keys
mnemonic
real account IDs
large runtime data not needed for review
```

`data/` は原則 runtime artifact なので、全部を ZIP に入れない。必要な場合だけ以下を少量 sample として別添する。

```text
data/normalized/quotes.parquet schema output
raw Trade[XYZ] quote JSONL 100 rows
one symbol / one day sample
data/registry/trade_xyz_instrument_registry.json
data/ops/trade_xyz_quote_collection_summary.json
data/ops/quote_diagnostics_summary.json
```

tree 出力例:

```bash
tree -a -L 4 -I '.git|.venv|node_modules|__pycache__|.pytest_cache|.ruff_cache|dist|build|logs|data'
```

## Filled Intake For This Repo

```text
プロジェクト名:
  marketlens-strike

現在の目的:
  Trade[XYZ] research, read-only evidence collection, Strategy Research Lab,
  paper operations, and safety gates.

今回作りたいもの:
  Trade[XYZ] 専用の純粋 backtest engine.

将来構想:
  MT5 / IC Markets / CFD は別プロジェクトまたは別 profile で検討。
  今回は実装対象外。

言語:
  Python >=3.13,<3.14

package manager:
  uv

主要ライブラリ:
  Typer, Pydantic, httpx, Polars, DuckDB, PyArrow, pytest, pytest-httpx,
  pyrefly, ruff.

DB / storage:
  Runtime artifact として DuckDB.
  raw JSONL, normalized Parquet, reports JSON/Markdown.

実行入口:
  uv run sis ...
  Typer root: src/sis/cli.py
  command modules: src/sis/commands/

テスト:
  pytest
  ./scripts/check

現状動く主な command:
  uv run sis --help
  uv run sis probe trade-xyz
  uv run sis collect-trade-xyz-quotes --write-summary --write-report
  uv run sis validate-artifacts --strict
  uv run sis phase-gate-review
  uv run sis bot-preview
  uv run sis build-backtest
  uv run sis strategy-author-run --spec <path> --through backtest
```

command の切り分け:

```text
existing current bridge:
  uv run sis build-backtest
  既存 decision / Strategy Lab surface から research artifact を作る。

existing strategy authoring:
  uv run sis strategy-author-run --spec <path> --through backtest
  Strategy Authoring spec の through-backtest flow。

proposed pure Trade[XYZ] engine:
  まだ CLI 未公開。
  tests/backtest/* で contracts / accounting / no-lookahead を先に固定する。
```

## Current Data Inventory

現行で backtest input として使える可能性があるもの:

```text
raw quote JSONL:
  data/raw/quotes/trade_xyz/<YYYY-MM-DD>.jsonl

normalized quote parquet:
  data/normalized/quotes.parquet

normalized DuckDB:
  data/normalized/sis.duckdb

instrument registry:
  data/registry/trade_xyz_instrument_registry.json

paper artifacts:
  data/paper/orders.parquet
  data/paper/fills.parquet
  data/paper/positions.parquet
  data/paper/daily_pnl.parquet

Strategy Lab artifacts:
  data/research/strategy_signals.parquet
```

上記は runtime artifact であり、存在は command 実行履歴に依存する。unit tests は `tests/fixtures/` または `tmp_path` で完結させ、`data/normalized/quotes.parquet` や `data/research/*` の常在を前提にしない。

現行 normalized quotes にある重要列:

```text
ts_client
recv_ts_ms
source_ts_ms
canonical_symbol
coin
asset_id
real_market_symbol
mark_price
index_price
oracle_price
best_bid
best_ask
bid_price
ask_price
mid_price
spread_bps
bid_depth_10bps_usd
ask_depth_10bps_usd
funding_rate
open_interest_usd
fee_mode
taker_fee_bps
maker_fee_bps
market_status
session_type
is_tradable
source_confidence
venue_quality_score
block_reasons
```

timestamp policy:

```text
ts_client:
  local client timestamp. Backtest event timeとして使う場合は明示する。

recv_ts_ms:
  receive timestamp.

source_ts_ms:
  exchange/source timestamp if payload supplies it.

MVP:
  deterministic fixture で event time を固定する。
  runtime artifact の timestamp semantics を truth として過信しない。
```

## Target Symbols

現 registry snapshot で active / api_orderable / standard fee として確認した symbol:

```text
SP500
XYZ100
NVDA
AAPL
MSFT
AMZN
GOOGL
META
TSLA
AMD
EWJ
```

現 docs の latest diagnostics で明示されている主要確認 symbol:

```text
SP500
XYZ100
NVDA
AAPL
MSFT
```

MVP の初期対象:

```text
SP500
```

ユーザーメモにある GOLD / JPY などは Trade[XYZ] Docs の specification index には出るが、この repo の現 active registry には入っていない。追加する場合は registry seed / live registry / fee mode / diagnostics を先に更新する。

外部 specification index は実装候補の上限であり、repo 内の実装対象は `data/registry/trade_xyz_instrument_registry.json` と diagnostics で確認できる範囲を正とする。外部 docs に symbol があるだけでは、collector / normalizer / fee model / diagnostics / tests の実装対象とは見なさない。

## Strategy Intake

現 repo に存在する strategy module:

```text
src/sis/strategies/qqq_trend_rates_vix.py
src/sis/strategies/sp500_trend_rates_vix.py
```

現 strategy の性格:

- Polars `feature_frame` を入力にする。
- `ts_signal`, `canonical_symbol`, `side`, `timeframe`, `signal_strength`, `strategy_name`, `reason`, `source_confidence`, `venue_quality_score` を出す。
- 直接発注、wallet、signing、nonce、exchange endpoint は触らない。

ユーザーメモ上の優先候補:

```text
qqq_trend_rates_vix:
  既存実装あり。ただし canonical_symbol は QQQ なので Trade[XYZ] XYZ100 と同一視しない。

sp500_trend_rates_vix:
  既存実装あり。現 code では feature_frame 上の SPY signal を作るため、Trade[XYZ] SP500 と同一視しない。

trend_orderbook_confirmation:
  現 repo に同名実装なし。将来候補。

regime_riskguard_trend:
  現 repo に同名実装なし。将来候補。
```

MVP strategy:

```text
SP500 long-only.
20期間高値ブレイク entry.
10期間安値割れ exit.
market-like fill.
fee + spread/slippage + nullable funding.
is_tradable / block_reasons / discovery bound / OI cap entry gate.
```

優先時間軸メモ:

```text
30m
4h
1d
3d
```

MVP では `1h相当` または deterministic fixture の bar cadence から始める。30m / 4h / 1d / 3d は metrics comparison phase で増やす。

## Backtest Granularity

段階:

```text
Phase 1:
  OHLCV / bar-like fixture + fee + spread/slippage.

Phase 2:
  quote-derived bars from normalized quotes.

Phase 3:
  bid/ask-aware fill and depth gate.

Phase 4:
  L2 sweep-depth / replay quality.

Phase 5:
  event-driven / execution reality comparison.
```

最初から L2 replay や event-driven full simulator へ行かない。

## Output Artifact Contract

MVP backtest が出すべき artifact:

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

これは新規純粋 engine 向けの予定 contract。現行 `build-backtest` が作る既存 artifact は別物として扱う。

現行 bridge command の代表 artifact:

```text
data/research/backtest_report.md
data/research/backtest_metrics.json
data/research/backtest_metrics_summary.json
decision JSONL inputs / Strategy Lab research artifacts
```

現行 paper 系 artifact:

```text
data/paper/orders.parquet
data/paper/fills.parquet
data/paper/positions.parquet
data/paper/daily_pnl.parquet
```

どちらも runtime-generated であり、fresh checkout の常在物として扱わない。

必須 metadata:

```text
run_id
created_at
strategy_id
symbol
timeframe
input_data_ref
input_schema_hash
config_hash
code_version_or_git_commit
fee_model_ref
funding_policy
fill_model
no_live_order=true
wallet_used=false
exchange_write_used=false
```

RobustLab へ渡す候補:

```text
candidate_result.json
trial_registry.jsonl
metrics.json
data_manifest.json
```

LEM へ将来渡す候補:

```text
order intent
expected execution
fill expectation
```

現 repo の MVP では RobustLab / LEM 連携を実装しない。artifact 名と責任境界だけを予約する。

## Metrics

最低限:

```text
net_return_after_cost
total_return
max_drawdown
trade_count
win_rate
profit_factor
sharpe_like_metric
median_trade_pnl
worst_trade_pnl
exposure_time
turnover
cost_drag_bps
blocked_reason_counts
source_confidence_gate_pass_rate
venue_quality_gate_pass_rate
```

Trade[XYZ] 追加:

```text
fee_impact
funding_impact
slippage_impact
taker_fill_ratio
maker_fill_ratio
symbol_breakdown
session_breakdown
market_status_breakdown
liquidity_regime_breakdown
max_leverage_used
liquidation_buffer
```

MVP では maker fill, leverage, liquidation buffer は列予約または `not_implemented` として出す。

## Hyperliquid / Live Execution Notes

Hyperliquid Docs では、WebSocket subscriptions に `orderUpdates`, `userEvents`, `userFills` があり、Exchange endpoint の order payload は limit TIF として `Alo`, `Ioc`, `Gtc` を持つ。`cloid` は optional client order id として扱われる。nonce は signer ごとに管理され、上位 nonce window と時刻範囲の制約がある。

この情報は将来の LEM / live execution readiness には重要だが、MVP backtest には入れない。

MVP に入れないもの:

```text
live order
wallet
signing
exchange write
nonce
cloid lifecycle
cancel / cancel by cloid
schedule cancel
modify order
userFills ingestion
orderUpdates ingestion
reconciliation
kill switch
```

ただし、将来の接続を壊さないように、backtest 側の fill/order artifact には次を残す。

```text
order_id
client_order_id optional
fill_id
side
qty
fill_price
fee
liquidity_flag
fill_price_source
expected_vs_actual fields reserved
```

## Implementation PR Plan Draft

既存 repo に合わせた初期 PR 計画:

```text
PR-0: Existing surface compatibility lock
  - uv run sis build-backtest の現責務を変えない
  - src/sis/backtest/bridge.py を新 engine に混ぜない
  - tests/test_backtest_bridge.py と tests/test_backtest_fixed_horizon.py を互換性確認に使う
  - Strategy Authoring through-backtest flow を新 engine と混同しない

PR-1: Backtest contracts
  - src/sis/backtest/engine/order.py
  - src/sis/backtest/engine/fill.py
  - src/sis/backtest/engine/portfolio.py
  - tests/backtest/test_portfolio_accounting.py

PR-2: Trade[XYZ] market data schema
  - src/sis/backtest/trade_xyz/schema.py
  - tests/backtest/test_trade_xyz_schema.py

PR-3: Fee / slippage / nullable funding model
  - src/sis/backtest/trade_xyz/cost_model.py
  - tests/backtest/test_trade_xyz_cost_model.py

PR-4: Fill model and no-lookahead rules
  - src/sis/backtest/engine/fill.py
  - tests/backtest/test_fill_model.py
  - tests/backtest/test_no_lookahead.py

PR-5: Minimal runner
  - src/sis/backtest/engine/runner.py
  - deterministic tmp_path parquet fixtures in tests

PR-6: Metrics and report artifacts
  - src/sis/backtest/engine/metrics.py
  - JSON / Parquet artifact writers
  - tests/backtest/test_backtest_artifacts.py

PR-7: Sample strategy adapter
  - breakout sample as test-only or docs example first
  - no public CLI yet

PR-8: CLI exposure after contracts stabilize
  - uv run sis backtest-trade-xyz ...
  - only after unit tests pin semantics
```

L2 / sweep-depth は PR-8 の後に別計画で扱う。

## Developer Docs Package

ZIP 化された開発者向け docs を作るなら、最小構成は以下。

```text
資料/0531-repo/
  TRADE_XYZ_BACKTEST_REPO_BRIEF.md
  TRADE_XYZ_BACKTEST_INTAKE_ADDENDUM.md

docs/
  CURRENT_STATE.md
  CODE_STATUS.md
  OPERATIONS_RUNBOOK.md
  ARCHITECTURE_AND_PHASES.md
  strategy_research_lab/README.md
  strategy_research_lab/08_CURRENT_CAPABILITIES.md

configs/
  fee_model.trade_xyz.yaml
  instrument_registry.seed.json

schemas/
  strategy_authoring_spec.v1.schema.json
  strategy_authoring_backtest_result.v1.schema.json

source pointers:
  src/sis/backtest/
  src/sis/venues/trade_xyz/
  src/sis/strategies/
  src/sis/execution/base.py
  src/sis/execution/trade_xyz_adapter.py
  tests/test_backtest_bridge.py
  tests/test_trade_xyz_collector.py
  tests/test_trade_xyz_normalizer.py
  tests/test_trade_xyz_registry.py
```

Do not include `.env` or private runtime state.

## Stop Conditions

設計・実装時に止める条件:

- `bot-preview` を注文候補生成 Bot に変える必要が出た。
- `PaperIntentPreview` を live `OrderIntent` として扱い始めた。
- BacktestEngine が wallet / signing / exchange write を必要とした。
- Hyperliquid nonce / cloid / cancel logic が MVP backtest に入り始めた。
- `fee_mode=unknown` のまま entry できる。
- `funding_rate` の単位を docs / fixture なしで推測している。
- `data/normalized/quotes.parquet` が存在しない fresh checkout で unit test が落ちる。
- `data/research/*`, `data/paper/*`, `data/ops/*` を常在 artifact として docs / tests が前提化している。
- 既存 `uv run sis build-backtest` の挙動を互換テストなしに変える。
- `SPY -> SP500` または `QQQ -> XYZ100` を mapping table / provenance / session差分なしで暗黙変換する。
- live adapter 側の `TradeXyzOrderIntent` を backtest MVP の contract としてそのまま流用する。
- MT5 / IC Markets / CFD の `swap`, `contract size`, `point`, `digits`, `margin mode` を今の Trade[XYZ] engine に入れ始めた。

## Skipped As Duplicate

以下は `TRADE_XYZ_BACKTEST_REPO_BRIEF.md` にすでにあるため、この追補では詳述しない。

- repo 技術スタック
- current normalized quotes schema 全列
- MVP long-only / single-symbol / market-like fill decision
- existing `src/sis/backtest/bridge.py` を触らない方針
- fixture first
- no-lookahead / accounting invariants
- MT5 / IC Markets / CFD を今やらない判断

## Readiness

ready.

この addendum は、次に `Trade[XYZ] Backtest Engine v0.1 実装計画` を PR / file / test 単位で作るための intake として使える。
