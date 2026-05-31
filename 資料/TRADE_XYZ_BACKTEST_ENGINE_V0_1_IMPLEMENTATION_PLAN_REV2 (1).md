# Trade[XYZ] Pure Backtest Engine v0.1 実装計画 REV2

作成日: 2026-05-31
対象 repo: `/home/tn/projects/marketlens-strike`
対象 branch: `feature/backtest-engine-roadmap`
対象範囲: Trade[XYZ] 専用の純粋バックテスト基盤 v0.1
前提: 既存 Strategy Lab / paper / execution surface と分離し、wallet / signing / exchange write を一切持たない backtest-only engine として追加する。

---

## 0. REV2での修正要約

追加ZIPの code truth を確認した結果、旧計画から以下を修正する。

1. **既存 `paper` 実装は流用しない。**
   `src/sis/paper/broker.py` は paper-intent 用であり、`fee + spread/2 + funding_bps` を round-trip estimate として扱う。純粋BTの会計・cost modelへそのまま流用しない。価格優先順位や gate 思想だけ参考にする。

2. **既存 `bridge.py` はさらに明確に触らない。**
   既存 bridge は `exec_buy/sell -> mark -> mid -> oracle -> index` に近い fixed-horizon research surface。新 engine の fill priority は `exec -> bid/ask -> mid±spread/2` で別契約にする。

3. **`funding nullable` と `block_reasons` の関係を修正する。**
   Backtest schema では `funding_rate=None` を許すが、既存 normalizer は funding missing を `BLOCK_FUNDING_MISSING` として `block_reasons` に入れ得る。したがって、normalized quote 由来で `BLOCK_FUNDING_MISSING` がある row は、nullable funding 以前に entry blocked とする。`funding_rate=None => funding_cost=0` は、主に deterministic fixture または block reason が無い synthetic row の扱いである。

4. **`fee_mode=observed` の扱いを修正する。**
   `configs/fee_model.trade_xyz.yaml` の `mode: observed` は「row resolved fee を優先する」運用モードであり、fee rate class ではない。`growth` / `standard` は fallback rate class。`fee_mode=observed` かつ row fee が無い場合、v0.1 では fee unresolved として entry blocked にする。

5. **Order contract を修正する。**
   fixed notional entry では fill price が確定するまで qty が確定しない。したがって entry order は `notional_usd` を持ち、fill model が次 executable row の fill price から qty を計算する。exit order は position qty を持つ。

6. **Fill / Position accounting を修正する。**
   `Fill.fee` や `slippage` の単位混同を避けるため、`fee_bps`, `fee_amount`, `slippage_bps`, `slippage_amount`, `funding_pnl` を分ける。Position は gross と net を分け、`net_realized_pnl = gross_realized_pnl - fees_paid - slippage_paid + funding_pnl` とする。

7. **bar fixture の fill ルールを修正する。**
   OHLC の `close` や `high/low` を fill price に暗黙利用しない。bar fixture であっても、fill には `exec_buy_price/exec_sell_price`、または `best_bid/best_ask`、または `mid_price + spread_bps` を明示的に持たせる。OHLC は signal 計算専用。

8. **Discovery Bound / OI cap の派生項目を追加する。**
   `open_interest_usd`, `oi_cap_usd`, `oi_cap_usage`, `discovery_bound_pct`, `bound_distance` を MarketDataRow に予約する。v0.1 では null pass。ただし値がある場合だけ entry gate に使う。

9. **exit gate を明確化する。**
   v0.1 では entry/exit とも fill price と fee が解決できない row では fill しない。`market_status=close_only` での exit fallback は将来機能で、v0.1では実装しない。

10. **Artifact schema を具体化する。**
    `orders.parquet`, `fills.parquet`, `trades.parquet`, `equity_curve.parquet`, `metrics.json`, `backtest_run.json`, `data_manifest.json`, `candidate_result.json`, `config_hash.txt`, `backtest_report.md` の最小列を固定する。

---

## 1. Source of Truth

実装者は次の順に正本を読む。

1. repo code / tests / configs
2. `AGENTS.md`
3. `pyproject.toml`
4. `configs/fee_model.trade_xyz.yaml`
5. `src/sis/venues/trade_xyz/*`
6. `src/sis/models.py`
7. 既存 `src/sis/backtest/*`
8. 既存 `src/sis/paper/*`
9. `TRADE_XYZ_BACKTEST_REPO_BRIEF.md`
10. `TRADE_XYZ_BACKTEST_INTAKE_ADDENDUM.md`

外部仕様は、Trade[XYZ] Docs と Hyperliquid Docs を一次情報として扱う。

確認済み外部仕様の実装上の要点:

- Trade[XYZ] standard base fee は taker 0.090% / maker 0.030%。growth mode base fee は taker 0.0090% / maker 0.0030%。repo の fee config では bps として `standard.taker_bps=9.0`, `growth.taker_bps=0.9` と扱う。
- Funding は hourly。payment formula は `position_size * oracle_price * funding_rate`。long の account adjustment は、positive funding なら支払い、negative funding なら受け取りとして扱う。
- Specification Index には SP500 の discovery bound ±2%、OI cap $500m、XYZ100 の discovery bound ±3.5%、OI cap $400m などがある。repo の実装対象は外部 docs ではなく現 registry / diagnostics で確認済みの symbol を正とする。
- Hyperliquid `candleSnapshot` は直近 5000 candles 制限があり、HIP-3 asset は `xyz:XYZ100` のように dex prefix が必要。

---

## 2. 目的

`marketlens-strike` に、Trade[XYZ] 専用の純粋バックテスト基盤を追加する。

v0.1 の目的は、勝てる戦略を探すことではなく、**偽の勝ちを検出できる最小 Backtest Core** を作ること。

v0.1 は次を満たす。

- Trade[XYZ] quote / deterministic fixture を入力できる。
- `Order` / `Fill` / `Position` / `Portfolio` の独立した event ledger を持つ。
- fee / spread内包fill / extra slippage / nullable funding を net equity に反映できる。
- `is_tradable=false`、`block_reasons` 非空、fee unresolved、Discovery Bound / OI cap gate により entry を禁止できる。
- no-lookahead を engine contract としてテストする。
- fresh checkout で runtime `data/` artifact が無くても unit tests が通る。
- 既存 `src/sis/backtest/bridge.py`、`uv run sis build-backtest`、Strategy Authoring through-backtest flow を壊さない。

---

## 3. 非対象

| 非対象 | 理由 |
|---|---|
| live order | 純粋BT v0.1 の範囲外 |
| wallet / signing | 秘密情報を要求してはいけない |
| exchange write | read-only / backtest-only を守る |
| nonce / cloid lifecycle | live execution readiness の範囲 |
| cancel / modify / schedule cancel | v0.1 は market-like fill のみ |
| userFills / orderUpdates ingestion | reconciliation 側の範囲 |
| maker fill | v0.1 は全て taker 相当 |
| short | v0.1 は long-only |
| multi-symbol portfolio | v0.1 は single-symbol |
| limit / stop / trailing order | v0.1 は market-like entry / exit のみ |
| partial fill | v0.1 は full fill のみ |
| leverage / liquidation | v0.1 は未実装。metadata列のみ予約可 |
| L2 replay / queue position | v0.1後の別計画 |
| public CLI | v0.1では未公開。tests中心 |
| existing `bridge.py` の置換 | 既存互換維持 |
| SPY -> SP500 暗黙変換 | mapping/provenance/session差分なしでは禁止 |
| QQQ -> XYZ100 暗黙変換 | 同上 |
| MT5 / IC Markets / CFD | 将来別プロジェクトまたは別 profile |

---

## 4. 既存Repoからの実務リスク修正

### 4.1 既存 Backtest Bridge は別物

既存ファイル:

```text
src/sis/backtest/__init__.py
src/sis/backtest/bridge.py
src/sis/backtest/costs.py
src/sis/backtest/signals.py
```

性格:

- `ResearchSignal` と quote row を使う fixed-horizon / Strategy Lab / paper preview 寄りの evaluation surface。
- `Order` / `Fill` / `Position` / `Portfolio` ledger はない。
- `price selection` は新 engine と異なる。
- cost は `CostProfile` / `round_trip_cost_bps()` 中心であり、Trade[XYZ]固有の account ledger ではない。

v0.1 の対応:

- PR-0 で import compatibility と既存 tests 通過を固定する。
- 新 engine から `bridge.py` を import しない。
- `uv run sis build-backtest` の挙動を変えない。

### 4.2 既存 PaperBroker は流用しない

既存 paper surface:

```text
src/sis/paper/orders.py
src/sis/paper/fills.py
src/sis/paper/portfolio.py
src/sis/paper/broker.py
src/sis/paper/runner.py
```

参考にしてよい点:

- fill artifact に `fill_price_source` を残す思想。
- `best_ask` / `best_bid` を使う paper fill の方向性。
- paper artifact が wallet / exchange write を使わない境界。

流用してはいけない点:

- `_round_trip_cost_bps()` は paper scoring estimate であり、純粋BT会計ではない。
- `funding_rate * 10_000` をそのまま bps estimate にする処理を、v0.1 cost modelへ流用しない。
- `PaperPortfolio` は fee / slippage / funding を account ledger として十分に分離していない。

v0.1 では新規 `sis.backtest.engine` に別 contract を作る。

### 4.3 Trade[XYZ] Normalizer の block_reasons を尊重する

既存 `quote_from_l2_book()` は、ctx があるのに `mark_price`, `oracle_price`, `funding_rate`, `open_interest_usd` が欠ける場合、`BLOCK_*_MISSING` を `block_reasons` に追加し、`is_tradable=False` にし得る。

v0.1 の対応:

```text
if row.block_reasons is not empty:
    entry blocked

if row.is_tradable is False:
    entry blocked

if funding_rate is None and block_reasons is empty:
    funding_policy nullable_zero_v0 により funding impact = 0
```

つまり、`funding nullable` は `BLOCK_FUNDING_MISSING` を無視するという意味ではない。

### 4.4 Fee model の `observed` を誤読しない

現 config:

```text
fee_model.trade_xyz.mode = observed
fallback.growth.taker_bps = 0.9
fallback.standard.taker_bps = 9.0
classification.SP500 = standard
```

v0.1 fee resolution order:

1. row の `taker_fee_bps` が `>= 0` なら使う。
2. row の `fee_mode` が `standard` または `growth` で fallback があれば使う。
3. row の `symbol` が config `classification` にあり、その mode の fallback があれば使う。
4. `fee_mode=observed` だが row fee が無い場合は unresolved。
5. `fee_mode=unknown` で row fee も fallback も無ければ unresolved。

unresolved なら entry blocked。

---

## 5. 対象ファイル

### 5.1 新規作成ファイル

```text
src/sis/backtest/engine/__init__.py
src/sis/backtest/engine/order.py
src/sis/backtest/engine/fill.py
src/sis/backtest/engine/portfolio.py
src/sis/backtest/engine/runner.py
src/sis/backtest/engine/metrics.py
src/sis/backtest/engine/artifacts.py

src/sis/backtest/trade_xyz/__init__.py
src/sis/backtest/trade_xyz/schema.py
src/sis/backtest/trade_xyz/cost_model.py
src/sis/backtest/trade_xyz/gates.py

src/sis/backtest/trade_xyz/sample_strategy.py  # PR-7 only
```

### 5.2 新規 test ファイル

```text
tests/backtest/test_existing_surface_compatibility.py
tests/backtest/test_trade_xyz_schema.py
tests/backtest/test_trade_xyz_cost_model.py
tests/backtest/test_fill_model.py
tests/backtest/test_portfolio_accounting.py
tests/backtest/test_no_lookahead.py
tests/backtest/test_runner_minimal.py
tests/backtest/test_backtest_artifacts.py
tests/backtest/test_sample_strategy_breakout.py  # PR-7 only
```

### 5.3 原則変更しないファイル

```text
src/sis/backtest/bridge.py
src/sis/backtest/costs.py
src/sis/backtest/signals.py
src/sis/execution/base.py
src/sis/execution/trade_xyz_adapter.py
src/sis/cli.py
src/sis/commands/*
src/sis/paper/*
```

例外:

- `src/sis/backtest/__init__.py` は import surface 追加が本当に必要な場合のみ最小変更可。
- `src/sis/cli.py` は PR-8 まで変更しない。

---

## 6. Data Contract

### 6.1 `MarketDataRow`

実装場所:

```text
src/sis/backtest/trade_xyz/schema.py
```

Pydantic v2 `BaseModel` で実装する。

field:

```text
event_ts: datetime
symbol: str
data_kind: Literal["bar", "quote", "quote_derived_bar"] = "quote"
event_time_source: Literal["fixture", "ts_client", "source_ts_ms", "recv_ts_ms"] = "fixture"

open: float | None = None
high: float | None = None
low: float | None = None
close: float | None = None
volume: float | None = None

mid_price: float | None = None
mark_price: float | None = None
oracle_price: float | None = None
external_price: float | None = None
index_price: float | None = None
exec_buy_price: float | None = None
exec_sell_price: float | None = None
best_bid: float | None = None
best_ask: float | None = None
spread_bps: float | None = None

taker_fee_bps: float | None = None
maker_fee_bps: float | None = None
fee_mode: str | None = None

funding_rate: float | None = None
funding_interval_minutes: int | None = None

open_interest_usd: float | None = None
oi_cap_usd: float | None = None
oi_cap_usage: float | None = None

discovery_bound_pct: float | None = None
bound_distance: float | None = None

market_status: str | None = None
session_type: str | None = None
is_tradable: bool
block_reasons: list[str]
source_confidence: float | None = None
venue_quality_score: float | None = None

source_ts_ms: int | None = None
recv_ts_ms: int | None = None
raw_payload_ref: str | None = None
```

validation:

- `event_ts` は timezone-aware にする。naive datetime は UTC として補正するか、validation error。v0.1 では UTC 補正でよい。
- `symbol` は trim + upper。
- price 系 field は `None` または `> 0`。
- `spread_bps >= 0`。
- `taker_fee_bps`, `maker_fee_bps` は `None` または `>= 0`。
- `block_reasons` は必ず `list[str]`。
- `block_reasons=None` は `[]`。
- `block_reasons` が list 以外なら validation error。
- `bound_distance` は `None` または `>= 0`。
- `oi_cap_usage` は `None` または `>= 0`。

重要:

- `close` は signal 計算用であり、fill price には暗黙利用しない。
- `high/low` は sample strategy の breakout/breakdown 判定用であり、fill 判定には使わない。

### 6.2 `from_normalized_quote_row()`

signature:

```text
from_normalized_quote_row(
    row: Mapping[str, Any],
    *,
    discovery_bound_bps: float | None = None,
    oi_cap_usd: float | None = None,
) -> MarketDataRow
```

mapping:

```text
ts_client -> event_ts, event_time_source="ts_client"
canonical_symbol -> symbol
index_price -> index_price and external_price
best_bid -> best_bid
best_ask -> best_ask
mid_price -> mid_price
mark_price -> mark_price
oracle_price -> oracle_price
exec_buy_price -> exec_buy_price
exec_sell_price -> exec_sell_price
spread_bps -> spread_bps
funding_rate -> funding_rate
funding_interval_minutes -> funding_interval_minutes
open_interest_usd -> open_interest_usd
fee_mode -> fee_mode
taker_fee_bps -> taker_fee_bps
maker_fee_bps -> maker_fee_bps
market_status -> market_status
session_type -> session_type
is_tradable -> is_tradable
block_reasons -> block_reasons
source_confidence -> source_confidence
venue_quality_score -> venue_quality_score
source_ts_ms -> source_ts_ms
recv_ts_ms -> recv_ts_ms
raw_payload_ref -> raw_payload_ref
```

optional derivation:

```text
if discovery_bound_bps is not None:
    discovery_bound_pct = discovery_bound_bps / 100

if oi_cap_usd and open_interest_usd:
    oi_cap_usage = open_interest_usd / oi_cap_usd

if discovery_bound_pct and external_price and reference_price:
    reference_price = mark_price or mid_price or close
    bound_distance = abs(reference_price - external_price) / (external_price * discovery_bound_pct / 100)
```

No derivation if source values are missing. Do not guess.

### 6.3 `from_bar_fixture_row()`

Add a small helper only for tests.

Rules:

- `open/high/low/close/volume` may exist.
- Fill still requires executable fields: `exec_buy_price/exec_sell_price`, or `best_bid/best_ask`, or `mid_price+spread_bps`.
- Do not map `close -> mid_price` implicitly unless fixture explicitly sets `mid_price=close`.

---

## 7. Order / Fill / BlockedEvent Contract

### 7.1 `Order`

実装場所:

```text
src/sis/backtest/engine/order.py
```

field:

```text
order_id: str = uuid4 hex
created_ts: datetime
symbol: str
side: Literal["buy", "sell"]
order_type: Literal["market"] = "market"
qty: float | None = None
notional_usd: float | None = None
reduce_only: bool = False
signal_id: str | None = None
signal_ts: datetime | None = None
reason: str | None = None
```

validation:

- v0.1 は `order_type="market"` のみ。
- `buy` entry は `notional_usd > 0` を持つ。`qty` は fill model が決める。
- `sell` exit は `qty > 0` を持つ。`reduce_only=True`。
- `qty` と `notional_usd` の両方が同時に positive は禁止。
- `symbol` は upper。

### 7.2 `Fill`

実装場所:

```text
src/sis/backtest/engine/fill.py
```

field:

```text
fill_id: str = uuid4 hex
order_id: str
order_created_ts: datetime
fill_ts: datetime
symbol: str
side: Literal["buy", "sell"]
qty: float
fill_price: float
notional_usd: float
fee_bps: float
fee_amount: float
fee_source: Literal["row_taker_fee_bps", "fee_model_fee_mode", "fee_model_symbol_classification"]
slippage_bps: float = 0.0
slippage_amount: float = 0.0
funding_pnl: float = 0.0
liquidity_flag: Literal["taker"] = "taker"
fill_price_source: Literal[
    "exec_buy_price",
    "exec_sell_price",
    "best_ask",
    "best_bid",
    "mid_plus_half_spread",
    "mid_minus_half_spread",
]
```

validation:

- `qty > 0`
- `fill_price > 0`
- `notional_usd == qty * fill_price` within small tolerance
- `fee_bps >= 0`
- `fee_amount >= 0`
- `slippage_bps >= 0`
- `slippage_amount >= 0`
- `funding_pnl` は正負どちらも許容。

Blocked fill は作らない。Blocked は `BlockedEvent` で表す。

### 7.3 `BlockedEvent`

実装場所:

```text
src/sis/backtest/engine/fill.py
```

field:

```text
event_id: str = uuid4 hex
ts: datetime
symbol: str
order_id: str | None
signal_id: str | None
reason: str
source_reasons: list[str] = []
context: dict[str, str | int | float | bool | None] = {}
```

allowed reason examples:

```text
is_not_tradable
block_reasons_non_empty
fee_unresolved
discovery_bound_near
oi_cap_exceeded
cash_insufficient
position_already_open
sell_qty_exceeds_position
fill_price_unresolved
funding_interval_unknown
order_expired_untradable_row
```

---

## 8. Portfolio / Accounting Contract

### 8.1 `Position`

実装場所:

```text
src/sis/backtest/engine/portfolio.py
```

field:

```text
symbol: str
qty: float = 0.0
avg_price: float = 0.0
gross_realized_pnl: float = 0.0
unrealized_pnl: float = 0.0
fees_paid: float = 0.0
slippage_paid: float = 0.0
funding_pnl: float = 0.0
```

computed property:

```text
net_realized_pnl = gross_realized_pnl - fees_paid - slippage_paid + funding_pnl
```

rules:

- v0.1 は long-only。`qty < 0` 禁止。
- first buy で `avg_price = fill_price`。
- v0.1 では追加 buy は blocked。平均単価更新は将来。
- sell fill で `qty` を減らす。
- sell qty が current qty を超える場合は blocked。
- full exit 後は `qty=0`, `avg_price=0`, `unrealized_pnl=0`。

### 8.2 `Portfolio`

field:

```text
initial_cash: float
cash: float
positions: dict[str, Position]
orders: list[Order]
fills: list[Fill]
blocked_events: list[BlockedEvent]
equity_snapshots: list[EquitySnapshot]
```

methods:

```text
apply_fill(fill: Fill) -> None
record_order(order: Order) -> None
record_blocked(event: BlockedEvent) -> None
mark_to_market(symbol: str, price: float, ts: datetime) -> EquitySnapshot
can_open(symbol: str) -> bool
can_close(symbol: str, qty: float) -> bool
```

cash rules:

Long entry:

```text
cash -= qty * fill_price
cash -= fee_amount
cash -= slippage_amount
position.qty += qty
position.avg_price = fill_price
position.fees_paid += fee_amount
position.slippage_paid += slippage_amount
```

Long exit:

```text
gross_pnl = qty * (fill_price - avg_price)
cash += qty * fill_price
cash -= fee_amount
cash -= slippage_amount
cash += funding_pnl
position.gross_realized_pnl += gross_pnl
position.fees_paid += fee_amount
position.slippage_paid += slippage_amount
position.funding_pnl += funding_pnl
position.qty -= qty
```

Equity:

```text
market_value = sum(position.qty * mark_price)
equity = cash + market_value
```

Do not adjust cash separately from `net_realized_pnl`. Cash is source of truth for account value; PnL fields are reporting decomposition.

---

## 9. Cost Model

### 9.1 実装場所

```text
src/sis/backtest/trade_xyz/cost_model.py
```

### 9.2 FeeModel

Implement:

```text
FeeModel.from_yaml(path: Path) -> FeeModel
resolve_fee_bps(row: MarketDataRow, symbol: str, liquidity_flag: "taker") -> FeeResolution
calculate_fee_amount(qty: float, fill_price: float, fee_bps: float) -> float
```

`FeeResolution`:

```text
fee_bps: float | None
source: Literal[
  "row_taker_fee_bps",
  "fee_model_fee_mode",
  "fee_model_symbol_classification",
  "unresolved",
]
blocked: bool
blocked_reason: str | None
```

resolution order:

1. row `taker_fee_bps` is not None and `>=0` -> use it.
2. row `fee_mode in {standard,growth}` and config fallback exists -> use fallback.
3. row `symbol` in config classification -> use classified mode fallback.
4. otherwise unresolved.

Special cases:

- `fee_mode=observed` with no row fee => unresolved.
- `fee_mode=unknown` with no row fee/fallback => unresolved.
- `maker_fee_bps` is stored but unused in v0.1.
- hardcode `0.04%` is forbidden.

### 9.3 FundingPolicy

Implement:

```text
FundingPolicy(name="nullable_zero_v0")
calculate_funding_pnl(side, qty, oracle_price, funding_rate, funding_interval_minutes) -> FundingResult
```

v0.1 rule:

```text
if funding_rate is None:
    funding_pnl = 0
    warning = None

if funding_rate is not None and funding_interval_minutes is None:
    funding_pnl = 0
    warning = "funding_rate_present_but_interval_unknown"

if funding_rate is not None and funding_interval_minutes is explicit:
    funding_payment = qty * oracle_price * funding_rate
    long funding_pnl = -funding_payment
```

Do not annualize. Do not time-apportion unless fixture explicitly sets interval semantics.

### 9.4 Slippage

`slippage_bps` is extra configured slippage only. Spread is already embedded in fill price.

```text
slippage_amount = notional_usd * slippage_bps / 10_000
```

Default `slippage_bps=0.0`.

---

## 10. Trade[XYZ] Gates

実装場所:

```text
src/sis/backtest/trade_xyz/gates.py
```

entry gate:

```text
row.is_tradable is True
row.block_reasons is empty
fee can be resolved
if config.max_bound_distance is not None and row.bound_distance is not None:
    row.bound_distance <= config.max_bound_distance
if config.max_oi_cap_usage is not None and row.oi_cap_usage is not None:
    row.oi_cap_usage <= config.max_oi_cap_usage
if config.min_source_confidence is not None and row.source_confidence is not None:
    row.source_confidence >= config.min_source_confidence
if config.min_venue_quality_score is not None and row.venue_quality_score is not None:
    row.venue_quality_score >= config.min_venue_quality_score
```

v0.1 null rule:

- `bound_distance=None` pass.
- `oi_cap_usage=None` pass.
- `source_confidence=None` pass unless config strict future mode says otherwise.
- `venue_quality_score=None` pass unless config strict future mode says otherwise.

exit gate:

- v0.1では exit も fill price と fee が解決できる row のみ fill する。
- `market_status=close_only` fallback は未実装。
- `is_tradable=false` / `block_reasons` 非空の row で exit を強行しない。代わりに blocked event を残し、position は open のまま。

---

## 11. Fill Model

実装場所:

```text
src/sis/backtest/engine/fill.py
```

signature:

```text
fill_market_like_order(
    order: Order,
    row: MarketDataRow,
    portfolio: Portfolio,
    fee_model: FeeModel,
    config: BacktestConfig,
) -> Fill | BlockedEvent
```

price priority:

Long entry / buy:

```text
1. exec_buy_price
2. best_ask
3. mid_price * (1 + spread_bps / 2 / 10_000)
```

Long exit / sell:

```text
1. exec_sell_price
2. best_bid
3. mid_price * (1 - spread_bps / 2 / 10_000)
```

If all fail: `BlockedEvent(reason="fill_price_unresolved")`.

quantity:

```text
buy entry:
  qty = notional_usd / fill_price

sell exit:
  qty = order.qty
```

cash check:

```text
required_cash = qty * fill_price + fee_amount + slippage_amount
if side == buy and required_cash > portfolio.cash:
    blocked cash_insufficient
```

position checks:

```text
if side == buy and portfolio.can_open(symbol) is False:
    blocked position_already_open

if side == sell and portfolio.can_close(symbol, qty) is False:
    blocked sell_qty_exceeds_position
```

---

## 12. Runner

実装場所:

```text
src/sis/backtest/engine/runner.py
```

### 12.1 `BacktestConfig`

field:

```text
run_id: str
strategy_id: str
symbol: str
timeframe: str = "fixture"
initial_cash_usd: float = 10_000.0
position_sizing_mode: Literal["fixed_notional"] = "fixed_notional"
notional_usd: float = 1_000.0
fee_model_ref: str = "configs/fee_model.trade_xyz.yaml"
fill_model: str = "trade_xyz_market_like_v0"
funding_policy: str = "nullable_zero_v0"
slippage_bps: float = 0.0
max_bound_distance: float | None = None
max_oi_cap_usage: float | None = None
min_source_confidence: float | None = None
min_venue_quality_score: float | None = None
allow_entry_on_unknown_fee: bool = False
allow_entry_on_untradable: bool = False
allow_entry_with_block_reasons: bool = False
```

validation:

- `initial_cash_usd > 0`
- `notional_usd > 0`
- v0.1 tests use `notional_usd <= initial_cash_usd`
- allow flags default false and should remain false in v0.1 tests.

### 12.2 StrategyProtocol

```text
class StrategyProtocol(Protocol):
    def on_row(self, row: MarketDataRow, portfolio: Portfolio) -> Signal | None: ...
```

The strategy receives only the current row and portfolio. It must not receive the full future row list.

Signal:

```text
signal_id: str
signal_ts: datetime
symbol: str
action: Literal["buy", "sell", "hold"]
reason: str | None
```

### 12.3 Event order

```text
1. rows を event_ts 昇順に sort / validate
2. pending order があれば current row で fill 判定
3. fill または blocked event を portfolio ledger に反映
4. portfolio を current row の mark/mid/close の明示 mark price で mark-to-market
5. strategy に current row と portfolio を渡し signal を得る
6. signal を order に変換する。ただし fill は次 row 以降
7. order を pending queue に入れる
8. equity snapshot を保存する
```

no-lookahead rule:

- signal at row `i` fills at row `i+1` or later.
- same row's `high/low/close` must not be used for fill.
- future row `i+2` changes must not affect row `i+1` fill.

v0.1 pending order rule:

- one pending order at a time.
- pending order gets one fill/block attempt at next row, then expires.
- entry signal when position already open is ignored or blocked with `position_already_open`.
- exit signal when flat is ignored or blocked with `sell_qty_exceeds_position`.

---

## 13. Metrics

実装場所:

```text
src/sis/backtest/engine/metrics.py
```

required metrics:

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
fee_impact
funding_impact
slippage_impact
blocked_reason_counts
source_confidence_gate_pass_rate
venue_quality_gate_pass_rate
taker_fill_ratio
maker_fill_ratio
symbol_breakdown
session_breakdown
market_status_breakdown
```

rules:

- `sharpe_like_metric` is not annualized unless cadence is explicitly known.
- `maker_fill_ratio = 0` in v0.1.
- `funding_impact = 0` if nullable zero policy did not apply funding.
- `fee_impact`, `slippage_impact`, `funding_impact` are USD and optionally bps versions.

---

## 14. Artifact Contract

実装場所:

```text
src/sis/backtest/engine/artifacts.py
```

Function:

```text
write_backtest_artifacts(result: BacktestResult, out_dir: Path) -> BacktestArtifactPaths
```

All tests write to `tmp_path`.

### 14.1 `backtest_run.json`

required fields:

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
no_live_order: true
wallet_used: false
exchange_write_used: false
blocked_reason_counts
```

### 14.2 `orders.parquet`

columns:

```text
order_id
created_ts
symbol
side
order_type
qty
notional_usd
reduce_only
signal_id
signal_ts
reason
```

### 14.3 `fills.parquet`

columns:

```text
fill_id
order_id
order_created_ts
fill_ts
symbol
side
qty
fill_price
notional_usd
fee_bps
fee_amount
fee_source
slippage_bps
slippage_amount
funding_pnl
liquidity_flag
fill_price_source
```

### 14.4 `trades.parquet`

v0.1 closed long trades only.

columns:

```text
trade_id
symbol
entry_fill_id
exit_fill_id
entry_ts
exit_ts
qty
entry_price
exit_price
gross_pnl
fees_paid
slippage_paid
funding_pnl
net_pnl
holding_seconds
```

Open positions are reported in `backtest_run.json` or future `positions.parquet`; do not fake a closed trade.

### 14.5 `equity_curve.parquet`

columns:

```text
event_ts
cash
market_value
equity
gross_realized_pnl
net_realized_pnl
unrealized_pnl
open_qty
```

### 14.6 `metrics.json`

Contains all required metrics in section 13.

### 14.7 `data_manifest.json`

fields:

```text
input_rows
input_start_ts
input_end_ts
input_symbols
input_schema_hash
source_kind: fixture | normalized_quote | quote_derived_bar
runtime_artifact_used: false for unit tests
```

### 14.8 `candidate_result.json`

Minimal placeholder for future RobustLab.

fields:

```text
run_id
strategy_id
symbol
status: completed | blocked | failed
metrics_ref
artifacts_ref
not_for_live: true
```

### 14.9 `config_hash.txt`

Deterministic hash of normalized config dict. Same config must produce same hash.

### 14.10 `backtest_report.md`

Minimal Markdown summary:

```text
run_id
strategy_id
symbol
period
net_return_after_cost
max_drawdown
trade_count
blocked_reason_counts
no_live_order=true
wallet_used=false
exchange_write_used=false
```

---

## 15. Test 方針

### 15.1 全体方針

- unit tests は runtime artifact に依存しない。
- `tmp_path` に small deterministic Polars DataFrame / Parquet を作る。
- まず accounting / cost / fill / no-lookahead を固定する。
- runner / metrics / sample strategy はその後。
- 既存 bridge の互換確認を最初に固定する。
- tracked binary fixture は増やさない。

### 15.2 受け入れコマンド

Minimum:

```bash
uv run pytest \
  tests/backtest \
  tests/test_backtest_bridge.py \
  tests/test_backtest_fixed_horizon.py \
  tests/test_trade_xyz_normalizer.py \
  tests/test_trade_xyz_registry.py
```

可能なら:

```bash
./scripts/check
```

ZIPに `scripts/check` が含まれない場合は repo 本体で実行する。手元 context bundle だけでは `./scripts/check` の存在を前提にしない。

---

## 16. Test Cases

### 16.1 `test_existing_surface_compatibility.py`

cases:

```text
import sis.backtest.bridge works
import sis.backtest.costs works
import sis.backtest.signals works
existing run_backtest_bridge symbol remains importable
existing ResearchSignal remains importable
```

acceptance:

- `tests/test_backtest_bridge.py` and `tests/test_backtest_fixed_horizon.py` pass unchanged.

### 16.2 `test_trade_xyz_schema.py`

cases:

```text
MarketDataRow accepts minimum quote fields
MarketDataRow rejects missing symbol
MarketDataRow normalizes symbol to upper
MarketDataRow makes naive datetime UTC-aware or rejects by documented rule
block_reasons None becomes []
block_reasons non-list raises validation error
from_normalized_quote_row maps canonical_symbol to symbol
from_normalized_quote_row maps ts_client to event_ts
from_normalized_quote_row maps index_price to external_price
exec_buy_price / exec_sell_price may be None
funding_rate may be None
open_interest_usd may be present
oi_cap_usage is derived if oi_cap_usd is provided
bound_distance is derived only if all inputs exist
close is not considered executable price by helper
```

### 16.3 `test_trade_xyz_cost_model.py`

cases:

```text
row taker_fee_bps is used first
fee_model fee_mode fallback is used when row fee missing
fee_model symbol classification fallback is used when row fee/mode missing
fee_mode observed with missing row fee is unresolved
fee_mode unknown with no fallback blocks entry
fee_amount = abs(qty * fill_price) * bps / 10000
funding_rate None yields funding_pnl 0
funding_rate present but interval unknown yields funding_pnl 0 and warning
funding_rate positive on long produces negative funding_pnl when interval explicit
funding_rate negative on long produces positive funding_pnl when interval explicit
extra slippage default is 0
spread is not double-counted when fill source is best_ask / best_bid
```

### 16.4 `test_fill_model.py`

cases:

```text
long entry uses exec_buy_price first
long entry falls back to best_ask
long entry falls back to mid_plus_half_spread
long exit uses exec_sell_price first
long exit falls back to best_bid
long exit falls back to mid_minus_half_spread
fill_price_source is always set
fee_bps and fee_amount are set
untradable row blocks entry
block_reasons non-empty blocks entry
BLOCK_FUNDING_MISSING blocks entry even if funding nullable policy exists
fee unresolved blocks entry
cash insufficient blocks entry
position already open blocks additional buy
sell qty > position qty blocks exit
all price sources missing blocks fill_price_unresolved
```

### 16.5 `test_portfolio_accounting.py`

cases:

```text
flat start has explicit cash/equity baseline
long entry decreases cash by notional + fee + slippage
long entry increases qty
first entry avg_price equals fill_price
long entry changes fees_paid but not gross_realized_pnl
additional buy is blocked in v0.1
long exit returns qty to zero
long exit updates gross_realized_pnl
full trade net_realized_pnl equals gross - fees - slippage + funding
full exit resets avg_price and unrealized_pnl
blocked entry changes no cash/position/fills
mark_to_market updates unrealized_pnl and equity
cash cannot go negative in v0.1 no-leverage mode
```

### 16.6 `test_no_lookahead.py`

cases:

```text
signal at row i creates pending order only
pending order fills at row i+1, not row i
changing row i+1 executable price changes fill
changing row i close/high/low after signal calculation does not change fill
changing future row i+2 does not change row i+1 fill
strategy protocol does not receive full future row list
bar fixture high/low are used only for signal, not fill
```

### 16.7 `test_runner_minimal.py`

cases:

```text
runner sorts rows by event_ts
pending order fills on next executable row
entry signal creates pending order, not immediate fill
exit signal closes open long on next executable row
untradable next row blocks pending entry and expires order
runner records orders/fills/equity snapshots
runner records blocked_reason_counts
runner leaves position open if exit is blocked
```

### 16.8 `test_backtest_artifacts.py`

cases:

```text
artifact writer writes all required files under tmp_path
backtest_run.json contains no_live_order=true, wallet_used=false, exchange_write_used=false
metrics.json contains fee_impact, funding_impact, slippage_impact
orders.parquet schema includes notional_usd
fills.parquet schema includes fill_price_source, fee_bps, fee_amount
trades.parquet includes net_pnl and does not fake open trades as closed
candidate_result.json includes not_for_live=true
config_hash.txt is deterministic for same config
unit test does not read runtime data/
```

### 16.9 `test_sample_strategy_breakout.py` PR-7 only

cases:

```text
20-period high breakout generates buy signal
10-period low breakdown generates sell signal
strategy is long-only
strategy respects runner gate through blocked events
strategy does not trade before warmup period
strategy stores only rolling state, not future rows
```

---

## 17. PR Plan

### PR-0: Existing surface compatibility lock

Files:

```text
tests/backtest/test_existing_surface_compatibility.py
```

Tasks:

1. Create `tests/backtest/` directory.
2. Add import compatibility tests for existing bridge/costs/signals.
3. Run existing backtest bridge tests.

Acceptance:

```bash
uv run pytest tests/backtest/test_existing_surface_compatibility.py tests/test_backtest_bridge.py tests/test_backtest_fixed_horizon.py
```

### PR-1: Backtest contracts and accounting

Files:

```text
src/sis/backtest/engine/__init__.py
src/sis/backtest/engine/order.py
src/sis/backtest/engine/fill.py
src/sis/backtest/engine/portfolio.py
tests/backtest/test_portfolio_accounting.py
```

Tasks:

1. Implement `Order`.
2. Implement `Fill`.
3. Implement `BlockedEvent`.
4. Implement `Position`.
5. Implement `Portfolio`.
6. Add accounting invariant tests.

Acceptance:

- entry/exit accounting passes.
- additional buy blocked.
- full exit resets position.
- no runtime data dependency.

### PR-2: Trade[XYZ] market data schema

Files:

```text
src/sis/backtest/trade_xyz/__init__.py
src/sis/backtest/trade_xyz/schema.py
tests/backtest/test_trade_xyz_schema.py
```

Tasks:

1. Implement `MarketDataRow`.
2. Implement `from_normalized_quote_row()`.
3. Implement `from_bar_fixture_row()` if needed for tests.
4. Implement optional OI cap / bound distance derivation.
5. Add schema tests.

Acceptance:

- normalized quote subset maps correctly.
- nullable executable fields are accepted.
- close/high/low are not executable fill by default.

### PR-3: Fee / slippage / nullable funding model

Files:

```text
src/sis/backtest/trade_xyz/cost_model.py
tests/backtest/test_trade_xyz_cost_model.py
```

Tasks:

1. Implement `FeeModel`.
2. Implement `FeeResolution`.
3. Implement `resolve_fee_bps()`.
4. Implement `calculate_fee_amount()`.
5. Implement `FundingPolicy` and `FundingResult`.
6. Implement extra slippage calculation.
7. Add tests for row fee, config fallback, observed/unknown, funding sign.

Acceptance:

- unknown fee blocks entry.
- `0.04%` hardcode absent.
- funding is not annualized or guessed.

### PR-4: Gates and fill model

Files:

```text
src/sis/backtest/trade_xyz/gates.py
src/sis/backtest/engine/fill.py
tests/backtest/test_fill_model.py
tests/backtest/test_no_lookahead.py
```

Tasks:

1. Implement entry/exit gate helpers.
2. Implement fill price resolver.
3. Implement `fill_market_like_order()`.
4. Ensure `fill_price_source` is mandatory.
5. Ensure blocked events are recorded with reasons.
6. Add no-lookahead fill tests.

Acceptance:

- entry and exit fill priority fixed.
- `BLOCK_FUNDING_MISSING` blocks via block_reasons.
- no same-row fill.

### PR-5: Minimal runner

Files:

```text
src/sis/backtest/engine/runner.py
tests/backtest/test_runner_minimal.py
```

Tasks:

1. Implement `BacktestConfig`.
2. Implement `Signal`.
3. Define `StrategyProtocol`.
4. Implement runner event loop.
5. Implement pending order queue.
6. Implement fixed notional sizing via fill price.
7. Implement equity snapshots.
8. Aggregate `blocked_reason_counts`.

Acceptance:

- deterministic rows run entry -> exit -> flat.
- pending order fills next row.
- blocked entry expires.

### PR-6: Metrics and artifacts

Files:

```text
src/sis/backtest/engine/metrics.py
src/sis/backtest/engine/artifacts.py
src/sis/backtest/engine/runner.py
tests/backtest/test_backtest_artifacts.py
```

Tasks:

1. Implement `compute_metrics()`.
2. Implement trades pairing for closed long trades.
3. Implement artifact writers.
4. Implement deterministic config/input schema hash.
5. Implement minimal markdown report.

Acceptance:

- required artifact files written to `tmp_path`.
- metadata proves no live/wallet/exchange write.
- open trades are not faked as closed.

### PR-7: Sample strategy adapter

Files:

```text
src/sis/backtest/trade_xyz/sample_strategy.py
tests/backtest/test_sample_strategy_breakout.py
```

Tasks:

1. Implement stateful `BreakoutLongOnlyStrategy`.
2. 20-period high breakout entry.
3. 10-period low breakdown exit.
4. Warmup protection.
5. No public CLI.

Acceptance:

- sample strategy runs only as tests/docs example.
- not described as profitable or production strategy.

### PR-8: CLI exposure after contracts stabilize

Not part of v0.1 required completion.

Files if implemented later:

```text
src/sis/commands/backtest_trade_xyz.py
src/sis/cli.py
tests/test_cli_backtest_trade_xyz.py
```

---

## 18. Stop Conditions

Stop and update plan if any occurs:

- `fee_mode=unknown` or `fee_mode=observed` with no row fee still permits entry.
- `block_reasons` non-empty row permits new entry.
- `is_tradable=false` row permits new entry.
- `BLOCK_FUNDING_MISSING` is ignored as if nullable funding allowed entry.
- funding rate is annualized, time-apportioned, or guessed without explicit fixture interval.
- signal row and fill row are the same row.
- bar `high/low/close` becomes fill price without explicit executable price field.
- runtime `data/normalized/quotes.parquet` is required for unit tests.
- `data/research/*`, `data/paper/*`, `data/ops/*` are assumed to exist in unit tests.
- existing `uv run sis build-backtest` behavior changes without compatibility tests.
- `SPY -> SP500` or `QQQ -> XYZ100` is implicit.
- live adapter `TradeXyzOrderIntent` is used as backtest contract.
- BacktestEngine needs wallet / signing / exchange write.
- Hyperliquid nonce / cloid / cancel logic enters v0.1.
- MT5 / IC Markets / CFD fields enter Trade[XYZ] engine.
- CLI is required to test engine.

---

## 19. v0.1 完了条件

All required:

1. Existing backtest bridge tests pass unchanged.
2. New engine is under `src/sis/backtest/engine/` and `src/sis/backtest/trade_xyz/`.
3. No changes to live/paper/execution contracts are required.
4. `Order`, `Fill`, `BlockedEvent`, `Position`, `Portfolio` exist.
5. Accounting tests pass.
6. `MarketDataRow` and quote mapping exist.
7. `close/high/low` are not implicit fill prices.
8. Cost model uses row fee/config fallback and blocks unresolved fee.
9. Funding nullable policy does not ignore `block_reasons`.
10. Fill model preserves `fill_price_source`.
11. Runner enforces next-row fill.
12. No-lookahead tests pass.
13. Artifacts are written under `tmp_path`.
14. Artifacts include `no_live_order=true`, `wallet_used=false`, `exchange_write_used=false`.
15. Runtime `data/` is not required for unit tests.
16. Public CLI remains unpublished in v0.1.

Acceptance command:

```bash
uv run pytest \
  tests/backtest \
  tests/test_backtest_bridge.py \
  tests/test_backtest_fixed_horizon.py \
  tests/test_trade_xyz_normalizer.py \
  tests/test_trade_xyz_registry.py
```

Optional full repo check:

```bash
./scripts/check
```

---

## 20. 実装者への最終指示

1. Do not start with strategy performance. Start with accounting and no-lookahead.
2. Do not reuse paper broker or bridge code as implementation. Read only for contrast.
3. Do not infer Trade[XYZ] mechanics absent from row/config/fixture.
4. Keep v0.1 small: long-only, single-symbol, market-like taker fill.
5. Keep live/wallet/exchange boundaries impossible to cross from this engine.
6. Treat the first working result as a correctness harness, not as a profitable trading system.
