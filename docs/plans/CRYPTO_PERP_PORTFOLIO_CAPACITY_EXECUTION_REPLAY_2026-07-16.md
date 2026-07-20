
<!--
作成日: 2026-07-16_23:18 JST
更新日: 2026-07-20_19:49 JST
-->

# Crypto Perp Portfolio Capacity／Execution Replay 導入設計

* 対象Repo: `tsutomu-n/marketlens-strike`
* 初稿確認HEAD: `c8c950d2cb5677ed233ade7d8ac15a5f07979095`
* 再配置時の統合基準: `427de2b62ebb21a613793aee92b1d49bbe69e09c`
* 対象読者: 現行Repoの構造・Crypto Perp Candidate Pack・Backtest surfaceを把握しているSE
* 設計状態: 実装前の設計案（実装開始前に現行コードで再検証が必要）
* 主目的: **現行のイベント単位推定損益を、共通資本・同時ポジション・執行可能性を含む判断可能な推定へ引き上げる**
* 非目的: actual cash証明、live注文、万能バックテストエンジンの構築

初稿は`c8c950d2`時点のコードを調査して作成した。2026-07-20に`origin/main`の`427de2b`起点の統合ブランチへ再配置したが、この作業では設計内容の実装可否を再承認していない。実装前には、現行の`src/`、`tests/`、`schemas/`、CLI helpを正本として、対象ファイルと完了条件を再検証する。

---

# 1. 背景

## 1.1 現在できていること

MarketLens StrikeのCrypto Perp surfaceでは、次の処理が既に存在します。

```text
Event
  ↓
Source Availability
  ↓
Feature Pack
  ↓
Edge Score
  ↓
Outcome
  ↓
Cost-aware Tournament Rows
  ↓
Backtest Candidate Pack
  ↓
No-cash decision / gate / leaderboard
```

Candidate Packは同一run内に、少なくとも次を生成します。

```text
decision.json
signal_rows.jsonl
tournament_rows_v2.json
execution_assumptions.json
backtest_result.json
stress_result.json
regime_split_result.json
rolling_stability_result.json
bias_guard.json
no_lookahead_report.json
```

また、`decision.json`にはpack ID、artifact paths、component refs、summary、evidence gradeが保存されます。

現行の位置づけは明確です。

```text
Crypto Perp Backtest Candidate Pack
=
actual cashを使わないローカル推定の短期終着点
```

actual cash profitやtiny-live measurementは未証明です。

---

## 1.2 現在できていないこと

現在の`backtest_result.json`は、各イベントについて選ばれたactionの、

```text
cost_adjusted_cash_estimate_usd
```

を足し合わせています。

これはイベント単位の合計であり、1つの口座を時間順に再生しているわけではありません。

そのため、次が未反映です。

```text
同時に何件のポジションを保有したか
資本が他ポジションに拘束されていたか
現金不足で注文できなかったか
同一銘柄でポジションが重複したか
同時刻の複数候補をどの順で選んだか
exitで解放された資金を同時刻のentryへ再利用できたか
fundingや損失後の資本減少が後続取引へ影響したか
```

既存の`single_position_total_result_usd`は、execution windowが重ならない最初の取引を順に選んで合計する診断です。共通口座を再生したものでも、scoreが高い候補を選んだものでもありません。

---

## 1.3 既存Backtest Engineを拡張しない理由

既存の`src/sis/backtest/engine/`には、Order、Fill、Portfolio、Funding、Schedulingなど責務分割された部品があります。

ただし、現在の`Portfolio`は次の前提です。

```text
単一position
long-only
buy/open
sell/close
float会計
```

shortのopenやbuy/closeには対応していません。

`BacktestConfig`も、

```text
side_mode = long_only
leverage = disabled
liquidation_model = not_implemented
```

です。

さらに、既存order schedulingはTrade[XYZ]のfee modelとgateへ直接依存しています。

ここへCrypto Perpの、

```text
LONG / SHORT
共有資本
複数銘柄
margin予約
funding
同時position
```

を足すと、既存engineの責務と意味を壊します。

したがって、本設計では既存engineを拡張しません。

---

## 1.4 現行VectorBT Adapterを拡張しない理由

現行`src/sis/backtest/vectorbt_adapter.py`は、外部framework連携のsmoke用途です。

現状は、

```text
複数symbolを単一価格列へ連結
LONGのみ処理
fees=0
fixed horizon
shared capitalなし
```

です。

テストも、fakeの`Portfolio.from_signals()`を注入して呼び出し契約とartifact形状を確認するのが中心です。実VectorBTによるshort、cash sharing、共通資本の会計検証ではありません。

したがって、既存adapterは互換surfaceとして残し、Crypto Perp用の検証は別実装にします。

---

# 2. この設計の目的

## 2.1 第一目的

次の問いへ答えられるようにします。

> 初期資本3,000 USD、最大同時ポジション1・2・3件という条件で、現行Candidate Packが選んだ取引のうち、実際に資本上実行できたものはどれか。その結果、口座残高の推定経路はどうなったか。

出力したいものは次です。

```text
受理された取引
拒否された取引
拒否理由
最大同時ポジション数
最大拘束資本
資本利用率
時系列の推定口座残高
時系列の推定経済損益
最大settled-cash drawdown
同一条件のCURRENT_SELECTOR / ALWAYS_CONTINUATION / ALWAYS_REVERSAL / NO_TRADE比較
```

---

## 2.2 第二目的

VectorBTを使い、純Python参照実装の次を外部検算します。

```text
LONGのgross PnL
SHORTのgross PnL
往復費用
受理済みscheduleの最終損益
```

VectorBTの`Portfolio.from_orders()`は、事前に時刻・数量・価格・費用が決まった注文を2次元配列で処理する、最も単純かつ高速なsimulation modeです。状態依存処理が必要な場合は`from_order_func()`が適しますが、NumPy／Numba callbackの実装負担が増えます。([VectorBT][1])

初版では`from_orders()`を使い、VectorBTにstrategy判断やportfolio schedulerを再実装しません。

---

## 2.3 第三目的

将来の執行精度改善のため、Bitgetの、

```text
books15
public trades
```

をforward収集できる状態にします。

Bitget公式仕様では、`books15`は15レベルを150ms間隔でsnapshot配信します。full `books`は初回snapshot後にincremental updateとなり、クライアント側でmergeが必要です。([Bitget][2])

初期対象を`books15`へ限定することで、現行full-book mergeの不完全性を回避しつつ、100〜250 USD程度の小口taker検証に必要なdepthを取得します。

---

# 3. 非目的

この設計では、次を行いません。

```text
新しいevent detectorの開発
edge scorerの変更
Strategy Labの変更
既存Candidate Packの利益ロジック再実装
actual cashとの接続
live注文
paper注文
leverage
maintenance margin
liquidation
cross margin
maker queue
limit order
HFT
NautilusTraderの標準engine化
汎用Backtest Engine Plugin framework
別PyPI package化
分散処理
DB導入
```

本設計で作るのは、

```text
共通資本制約下での推定ポートフォリオ経路
```

と、

```text
執行再生に必要なforward data
```

です。

---

# 4. 設計方針

## 4.1 Candidate Packを正本にする

新しい層は、次を再計算しません。

```text
イベント選択
LONG / SHORT / NO_TRADE判断
before-cost return
fee estimate
funding estimate
slippage estimate
operator time cost
execution window
```

これらはCandidate Packから読みます。

費用条件を変えたい場合は、portfolio runnerへfeeを渡すのではなく、Candidate Packを再生成します。

例:

```bash
uv run sis crypto-perp-backtest-candidate-pack \
  --data-dir data/crypto_perp \
  --out data/crypto_perp/backtest_candidate_pack/fee_4bps \
  --notional-usd 100 \
  --fee-rate 0.0004 \
  --funding-rate 0.0001 \
  --slippage-bps 2

uv run sis crypto-perp-backtest-candidate-pack \
  --data-dir data/crypto_perp \
  --out data/crypto_perp/backtest_candidate_pack/fee_6bps \
  --notional-usd 100 \
  --fee-rate 0.0006 \
  --funding-rate 0.0001 \
  --slippage-bps 2
```

現在のRepoでは通常仮定が片道4bps、明示的な保守仮定が片道6bpsです。どちらも測定済みactual costではありません。

---

## 4.2 口座損益と経済損益を分ける

現行`CostAwareTournamentRow`には、

```text
before_cost_proxy_usd
fee_estimate_usd
funding_estimate_usd
slippage_estimate_usd
operator_time_cost_usd
cost_adjusted_cash_estimate_usd
stress_cash_estimate_usd
```

があります。

`cost_adjusted_cash_estimate_usd`にはoperator time costも含まれます。

しかし、operator timeは取引所口座のcashを減らしません。

そのため新しい層では、次を分離します。

```text
trading_account_delta_usd
=
before_cost_proxy_usd
- fee_estimate_usd
- funding_estimate_usd
- slippage_estimate_usd
```

```text
economic_delta_usd
=
trading_account_delta_usd
- operator_time_cost_usd
```

共通資本の受理・拒否判定には`trading_account_delta_usd`を使います。

「その取引が人間の時間を含めて割に合ったか」には`economic_delta_usd`を使います。

---

## 4.3 actual cashとは呼ばない

本設計の結果はすべて推定です。

使用する名称は次です。

```text
simulated_available_cash_usd
simulated_reserved_cash_usd
simulated_account_pnl_estimate_usd
economic_result_estimate_usd
settled_cash_drawdown_estimate_usd
```

使用しない名称:

```text
actual_cash
real_cash
realized_account_cash
proven_profit
```

現在のTournament codeは`cash_metric_basis`を持ち、before-cost proxy、cost-adjusted estimate、actual cashを分離する方向へ既に修正されています。

---

## 4.4 汎用化は第二利用者が現れてから行う

初期実装を、

```text
src/sis/backtest/portfolio_eval/
```

へ置く案は採用しません。

最初はCrypto Perp専用として、

```text
src/sis/crypto_perp/portfolio_capacity/
```

へ置きます。

理由は、現在の入力契約が、

```text
CryptoPerpBacktestCandidatePack
Tournament Rows V2
REVERSAL_SHORT
CONTINUATION_LONG
NO_TRADE
```

へ強く依存しているからです。

NDXや他市場でも同じ「Candidate Packから共通資本を再生する」責務が実際に必要になった時だけ、共通packageへ抽出します。

---

# 5. 全体アーキテクチャ

## 5.1 Portfolio Capacity層

```text
Backtest Candidate Pack
  ├─ decision.json
  ├─ signal_rows.jsonl
  ├─ tournament_rows_v2.json
  └─ execution_assumptions.json
                |
                v
        CandidatePackReader
                |
                v
      PortfolioCapacityCase
                |
       +--------+---------+
       |                  |
       v                  v
Decimal Reference     VectorBT Diff
Portfolio Path        accepted schedule検算
       |                  |
       +--------+---------+
                v
       Capacity Comparison
                |
                v
  result.json / timeline.jsonl / report.md
```

## 5.2 Execution Replay層

```text
Bitget Public WebSocket
  ├─ books15
  └─ trades
        |
        v
  Raw Capture Segments
        |
        v
  ExecutionReplayCase
        |
        +------------------+
        |                  |
        v                  v
Native Depth Replay    Nautilus Sidecar
        |                  |
        +------------------+
                   |
                   v
         Execution Comparison
```

Portfolio CapacityとExecution Replayは、別責務として維持します。

```text
Portfolio Capacity:
  その取引を資本上取れたか

Execution Replay:
  その取引をその価格・数量で約定できたか
```

---

# 6. 実装段階0：Discovery Spike

最初から`src/`へ追加しません。

## 6.1 ファイル構成

```text
tools/backtest_spikes/crypto_perp_portfolio_capacity/
├── README.md
├── __init__.py
├── models.py
├── pack_reader.py
├── reference_path.py
├── vectorbt_diff.py
├── inspect_runtime.py
├── run_matrix.py
└── tests/
    ├── test_pack_reader.py
    ├── test_reference_path.py
    ├── test_reference_properties.py
    └── test_vectorbt_diff.py
```

## 6.2 変更しないもの

```text
src/sis/
schemas/
src/sis/cli.py
docs/REPO_CLI_CATALOG_CURRENT_2026-06-17.md
pyproject.toml
uv.lock
既存Candidate Pack
既存VectorBT adapter
```

VectorBTは既存optional extraの`vectorbt==1.0.0`を使用します。

## 6.3 実行

```bash
uv run --extra vectorbt pytest \
  tools/backtest_spikes/crypto_perp_portfolio_capacity/tests -q

uv run --extra vectorbt python \
  tools/backtest_spikes/crypto_perp_portfolio_capacity/inspect_runtime.py \
  --candidate-pack-dir data/crypto_perp/backtest_candidate_pack/latest \
  --out data/research/crypto_perp_portfolio_capacity/discovery

uv run --extra vectorbt python \
  tools/backtest_spikes/crypto_perp_portfolio_capacity/run_matrix.py \
  --candidate-pack-dir data/crypto_perp/backtest_candidate_pack/latest \
  --initial-cash-usd 3000 \
  --out data/research/crypto_perp_portfolio_capacity/matrix
```

---

# 7. Candidate Pack Reader

## 7.1 入力

外部から受け取るpathは1つだけです。

```text
candidate_pack_dir
```

個別に、

```text
signal_rows_path
tournament_rows_path
execution_assumptions_path
```

を指定できるAPIにはしません。

異なるrunのartifactを混ぜる事故を防ぐためです。

---

## 7.2 必須ファイル

```text
decision.json
signal_rows.jsonl
tournament_rows_v2.json
execution_assumptions.json
```

任意:

```text
backtest_result.json
stress_result.json
```

---

## 7.3 読み込み検証

### A. Pack identity

```text
decision.schema_version
  == crypto_perp_backtest_candidate_pack.v1

decision.pack_id
  が空ではない

decision.artifact_paths
  に必須ファイルが存在
```

### B. Component hash

`decision.summary.pack_component_refs`のSHA-256と実ファイルを照合します。Candidate Packは各componentの参照をsummaryへ保存しています。

不一致:

```text
PACK_COMPONENT_HASH_MISMATCH
```

として実行中止。

### C. Event set

```text
set(signal_rows.event_id)
==
set(tournament_rows_v2.event_set)
```

### D. Action rows

各eventに正確に次の3行が必要です。

```text
REVERSAL_SHORT
CONTINUATION_LONG
NO_TRADE
```

欠落:

```text
MISSING_ACTION_ROW
```

重複:

```text
DUPLICATE_ACTION_ROW
```

### E. Execution window

`tournament_rows_v2.summary.execution_windows[event_id]`から読みます。

```text
entry_at
settled_at
horizon_minutes
```

検査:

```text
information_cutoff_at < entry_at
entry_at < settled_at
settled_at - entry_at == horizon_minutes
```

### F. Assumption consistency

```text
execution_assumptions.position_size_usd
==
tournament_rows_v2.summary.cost_assumptions.notional_usd
```

次も一致必須です。

```text
fee_rate
funding_rate
slippage_bps
max_holding_minutes / horizon_minutes
```

### G. Evidence level

初版が受け付けるのは、

```text
evidence_level = cost_adjusted_estimate
actual_cash_result_usd = null
```

だけです。

actual cash入りrowは、別のcash ledger責務に属するため、初版では拒否します。

```text
UNSUPPORTED_ACTUAL_CASH_INPUT
```

### H. Evidence basis

現行Candidate Packは、

```text
entry = next_5m_open_proxy_after_signal
exit  = matured_outcome_first_horizon_close_proxy
```

です。

生成するcaseには必ず、

```text
evidence_basis = BAR_PROXY
```

を設定します。

---

# 8. データモデル

## 8.1 `PortfolioCapacityPolicy`

```python
class PortfolioCapacityPolicy(BaseModel):
    initial_cash_usd: Decimal

    max_open_positions: int | None
    max_open_positions_per_symbol: int = 1

    action_policy: Literal[
        "CURRENT_SELECTOR",
        "ALWAYS_CONTINUATION",
        "ALWAYS_REVERSAL",
        "NO_TRADE",
    ]

    metric_scenario: Literal[
        "BASE",
        "STRESS",
    ]

    same_timestamp_cash_policy: Literal[
        "NO_SAME_TIMESTAMP_REUSE",
        "EXIT_THEN_ENTRY",
    ]

    reserve_policy: Literal[
        "NOTIONAL_PLUS_ESTIMATED_TRADING_COSTS"
    ] = "NOTIONAL_PLUS_ESTIMATED_TRADING_COSTS"

    priority_policy: Literal[
        "FIRST_OBSERVED"
    ] = "FIRST_OBSERVED"
```

### `max_open_positions`

```text
None:
  上限なし

1以上:
  指定数まで
```

`999`などのmagic numberは使いません。

### `same_timestamp_cash_policy`

#### `NO_SAME_TIMESTAMP_REUSE`

同一timestampにexitとentryがあっても、exitで解放される資金・position枠をそのtimestampのentryに使いません。

BAR_PROXYでは実際の注文順序が分からないため、これを主結果とします。

#### `EXIT_THEN_ENTRY`

exitを先に処理し、解放資金を同時刻entryへ使います。

これは感度分析です。主結果にはしません。

---

## 8.2 `PortfolioTradeIntent`

```python
class PortfolioTradeIntent(BaseModel):
    event_id: str
    outcome_id: str
    symbol: str

    action: Literal[
        "REVERSAL_SHORT",
        "CONTINUATION_LONG",
    ]
    side: Literal["LONG", "SHORT"]

    information_cutoff_at: datetime
    entry_at: datetime
    exit_at: datetime

    source_row_index: int
    signal_score: Decimal | None

    notional_usd: Decimal

    entry_price_proxy: Decimal
    exit_price_proxy: Decimal

    before_cost_proxy_usd: Decimal
    fee_estimate_usd: Decimal
    funding_estimate_usd: Decimal
    slippage_estimate_usd: Decimal
    operator_time_cost_usd: Decimal

    stress_slippage_estimate_usd: Decimal

    account_delta_base_usd: Decimal
    account_delta_stress_usd: Decimal

    economic_delta_base_usd: Decimal
    economic_delta_stress_usd: Decimal

    reserve_base_usd: Decimal
    reserve_stress_usd: Decimal

    known_gaps: list[str]
```

---

## 8.3 LONG／SHORT計算の整合検査

Crypto Perp Outcomeでは、

```text
LONG:
  raw_return

SHORT:
  -raw_return
```

です。

これはlinear USDT Perpで、

```text
qty = notional / entry_price
```

とした時の、

```text
LONG gross PnL
= qty × (exit - entry)

SHORT gross PnL
= qty × (entry - exit)
```

と一致します。

既存の一般`net_return()`はSHORTについて、

```python
entry_price / exit_price - 1
```

を使っています。

この式はCandidate Packのlinear short returnと一致しません。

したがって、本設計では既存`net_return()`を再利用しません。

Readerで次を検証します。

```text
expected_long_before_cost
=
notional × (exit - entry) / entry

expected_short_before_cost
=
notional × (entry - exit) / entry
```

Tournament Rowの`before_cost_proxy_usd`との差がDecimal toleranceを超えた場合:

```text
BEFORE_COST_PROXY_FORMULA_MISMATCH
```

として中止します。

---

## 8.4 派生値

### Base account delta

```text
account_delta_base_usd
=
before_cost_proxy_usd
- fee_estimate_usd
- funding_estimate_usd
- slippage_estimate_usd
```

### Base economic delta

```text
economic_delta_base_usd
=
account_delta_base_usd
- operator_time_cost_usd
```

### Stress account delta

```text
account_delta_stress_usd
=
before_cost_proxy_usd
- fee_estimate_usd
- funding_estimate_usd
- stress_slippage_estimate_usd
```

### Stress economic delta

```text
economic_delta_stress_usd
=
account_delta_stress_usd
- operator_time_cost_usd
```

### Reserve

```text
reserve_base_usd
=
notional_usd
+ fee_estimate_usd
+ funding_estimate_usd
+ slippage_estimate_usd
```

```text
reserve_stress_usd
=
notional_usd
+ fee_estimate_usd
+ funding_estimate_usd
+ stress_slippage_estimate_usd
```

これは正確なmargin cashflowではありません。

意味は、

> その取引のため、他の取引に使わないと仮定する保守的な資金枠

です。

---

## 8.5 `PortfolioPosition`

```python
class PortfolioPosition(BaseModel):
    event_id: str
    symbol: str
    action: str

    entry_at: datetime
    exit_at: datetime

    reserve_usd: Decimal
    account_delta_usd: Decimal
    economic_delta_usd: Decimal
```

---

## 8.6 `PortfolioTimelineRow`

```python
class PortfolioTimelineRow(BaseModel):
    timestamp: datetime
    event_kind: Literal[
        "ENTRY_ACCEPTED",
        "ENTRY_REJECTED",
        "EXIT_SETTLED",
        "NO_TRADE_SKIPPED",
        "UNKNOWN_SKIPPED",
    ]

    event_id: str
    symbol: str
    action: str

    available_cash_before_usd: Decimal
    available_cash_after_usd: Decimal

    reserved_cash_before_usd: Decimal
    reserved_cash_after_usd: Decimal

    open_position_count_before: int
    open_position_count_after: int

    account_delta_usd: Decimal
    economic_delta_usd: Decimal

    reason_code: str | None
```

---

## 8.7 `PortfolioCapacityResult`

```python
class PortfolioCapacityResult(BaseModel):
    schema_version: Literal[
        "crypto_perp_portfolio_capacity_result.v1"
    ]

    result_id: str
    case_id: str
    pack_id: str
    row_set_id: str

    engine_id: Literal[
        "decimal_reference"
    ]

    evidence_basis: Literal["BAR_PROXY"]
    metric_scenario: Literal["BASE", "STRESS"]
    same_timestamp_cash_policy: str

    initial_cash_usd: Decimal
    final_available_cash_usd: Decimal
    final_reserved_cash_usd: Decimal

    simulated_account_pnl_estimate_usd: Decimal
    economic_result_estimate_usd: Decimal

    accepted_trade_count: int
    rejected_trade_count: int
    skipped_trade_count: int

    peak_open_positions: int
    peak_reserved_cash_usd: Decimal
    peak_capital_utilization: Decimal

    settled_cash_drawdown_estimate_usd: Decimal

    accepted_action_counts: dict[str, int]
    rejected_reason_counts: dict[str, int]

    rejected_counterfactual_estimate_usd: Decimal

    run_status: Literal[
        "COMPLETE",
        "INCONCLUSIVE",
        "INVALID_INPUT",
    ]

    known_limits: list[str]
    timeline: list[PortfolioTimelineRow]

    actual_cash_used: Literal[False]
    profit_proven: Literal[False]
    mark_to_market_modeled: Literal[False]
    liquidation_modeled: Literal[False]
```

---

# 9. Portfolio Pathアルゴリズム

## 9.1 Action Policy

### `CURRENT_SELECTOR`

`signal_rows.selected_action`を使用します。

```text
CONTINUATION_LONG:
  対応LONG rowをintent化

REVERSAL_SHORT:
  対応SHORT rowをintent化

NO_TRADE:
  intentを作らない

UNKNOWN:
  intentを作らない
```

### `ALWAYS_CONTINUATION`

全eventで`CONTINUATION_LONG`rowを選択。

### `ALWAYS_REVERSAL`

全eventで`REVERSAL_SHORT`rowを選択。

### `NO_TRADE`

一件もintentを作りません。

---

## 9.2 Entry優先順位

v1ではscore優先を使いません。

```text
1. information_cutoff_at昇順
2. source_row_index昇順
3. event_id昇順
```

理由は、portfolio accounting追加と同時に新しいselector policyを作らないためです。

score優先は別trialで扱います。

---

## 9.3 時系列イベント

各intentから作るもの:

```text
ENTRY(event_id, entry_at)
EXIT(event_id, exit_at)
```

すべてtimestamp順に処理します。

---

## 9.4 `NO_SAME_TIMESTAMP_REUSE`

同一timestampの処理単位をbatchとします。

entry判定は、

```text
batch開始前のavailable cash
batch開始前のopen position数
```

を基準にします。

同じtimestampでexit予定のpositionがあっても、その解放資金とposition枠をentryへ使いません。

処理後にexitをsettleし、その後entry accepted分をstateへ反映します。

これは意図的に保守的です。

---

## 9.5 `EXIT_THEN_ENTRY`

```text
1. 同一timestampのEXITを処理
2. 資金・position枠を解放
3. ENTRYを優先順に処理
```

これは感度分析用です。

BAR_PROXYの主判断は`NO_SAME_TIMESTAMP_REUSE`とします。

---

## 9.6 Entry判定

順番に検査します。

```text
同じeventが既にopen
→ DUPLICATE_EVENT_POSITION

同じsymbolのopen position数が上限
→ MAX_POSITION_PER_SYMBOL

全体position数が上限
→ MAX_OPEN_POSITIONS

available_cash < reserve_usd
→ INSUFFICIENT_AVAILABLE_CASH
```

通過した場合:

```text
available_cash -= reserve_usd
reserved_cash += reserve_usd
open_positions[event_id] = position
```

---

## 9.7 Exit処理

```text
position = open_positions.pop(event_id)

reserved_cash -= position.reserve_usd

available_cash += position.reserve_usd
available_cash += position.account_delta_usd

economic_result += position.economic_delta_usd
```

---

## 9.8 Insolvency

次の場合:

```text
position.reserve_usd
+ position.account_delta_usd
< 0
```

runを、

```text
INCONCLUSIVE
```

にします。

理由:

* v1は保有中のmark-to-marketを再生しない。
* liquidationを再生しない。
* SHORTの損失はnotionalを超える可能性がある。
* 負のcashをそのまま後続取引へ流すと、存在しない口座状態を作る。

reason code:

```text
UNMODELED_INSOLVENCY_OR_LIQUIDATION
```

結果を0へ丸めたり、margin額で損失を打ち切ったりしません。

---

## 9.9 不変条件

各timeline処理後:

```text
available_cash_usd >= 0
reserved_cash_usd >= 0
open_position_count == len(open_positions)
reserved_cash_usd == sum(open position reserves)
```

完了時:

```text
final_reserved_cash_usd == 0
open_positions == {}
```

全intentにexitが存在するため、open positionが残れば入力または実装エラーです。

---

# 10. Scenario Matrix

Spikeでは次の組合せを全て実行します。

```text
action_policy:
  CURRENT_SELECTOR
  ALWAYS_CONTINUATION
  ALWAYS_REVERSAL
  NO_TRADE

max_open_positions:
  1
  2
  3
  unlimited

metric_scenario:
  BASE
  STRESS

same_timestamp_cash_policy:
  NO_SAME_TIMESTAMP_REUSE
  EXIT_THEN_ENTRY
```

合計:

```text
4 × 4 × 2 × 2 = 64 cases
```

fee 4bpsと6bpsはCandidate Pack自体を分けます。

したがって両方比較する場合は最大128 casesですが、30event程度なら実行負荷は問題になりません。

結果を見て、

```text
score priority
holding period
entry時刻
exit時刻
```

を変更してはいけません。

---

# 11. VectorBT Differential設計

## 11.1 VectorBTの責務

初版ではReference Pathが受理したscheduleをVectorBTへ渡します。

VectorBTが検証するのは:

```text
LONG gross PnL
SHORT gross PnL
固定fee／slippage費用
受理済み取引集合の最終損益
```

VectorBTが検証しないもの:

```text
max position scheduler
同時timestampの資金再利用policy
Candidate Packのaction selection
funding
operator time
liquidation
partial fill
```

つまり、VectorBTはReference schedulerの正しさを証明しません。

---

## 11.2 VectorBT入力行列

各eventを独立columnにします。

```text
column = event_id
index  = 全entry_at / exit_atのunion
```

同一symbolで複数eventがあっても、異なるeventを1本の連続価格系列へつなぎません。

### Entry

```text
price = entry_price_proxy
size  = notional_usd / entry_price_proxy
```

LONG:

```text
entry  = buy
exit   = sell
```

SHORT:

```text
entry  = sell
exit   = buy
```

### Valuation

entryとexitの間はentry price proxyをvaluation用に維持します。

これは実市場価格ではありません。

目的は、

```text
entry/exit二点間のPnL計算比較
```

だけです。

---

## 11.3 Cost

初版では、Candidate Packの、

```text
fee_estimate_usd
slippage_estimate_usd
```

を固定費として2分割します。

```text
entry fixed fee
=
(fee_estimate + slippage_estimate) / 2

exit fixed fee
=
(fee_estimate + slippage_estimate) / 2
```

VectorBTの`from_orders()`は、percentage feeだけでなく、order単位の`fixed_fees`を受け取れます。([VectorBT][1])

fundingとoperator timeはVectorBTへ入れません。

ComparisonでReference結果へ事後加算・比較します。

---

## 11.4 Cash sharing

```text
cash_sharing=True
group_by=True
```

を設定します。

VectorBTは同じgroup内のcolumnでcashを共有できます。([VectorBT][1])

ただしReferenceで既に受理済みのscheduleを渡すため、VectorBTのcash rejectionをportfolio schedulerの正本にはしません。

VectorBTが受理済みscheduleを拒否した場合:

```text
VECTORBT_CASH_SEMANTICS_MISMATCH
```

として比較失敗とします。

---

## 11.5 Call Sequence

`call_seq="auto"`は使いません。

VectorBTは同一timestamp内のcolumn処理順でcash結果が変わり得ます。また、`auto`ではorder価値を事前推定して順番を変更するため、cash依存のsizeでは非最適になる可能性が公式に注意されています。([VectorBT][1])

Reference timelineと同じ順序を明示的に渡します。

---

## 11.6 Comparison結果

```python
class VectorbtDifferentialResult(BaseModel):
    vectorbt_version: str

    reference_result_id: str

    reference_trade_count: int
    vectorbt_order_count: int

    reference_gross_pnl_usd: Decimal
    vectorbt_gross_pnl_usd: Decimal

    reference_fixed_trading_cost_usd: Decimal
    vectorbt_fixed_trading_cost_usd: Decimal

    reference_final_delta_usd: Decimal
    vectorbt_final_delta_usd: Decimal

    absolute_difference_usd: Decimal

    validated_components: list[str]
    unvalidated_components: list[str]

    decision: Literal[
        "MATCH",
        "MISMATCH",
        "VECTORBT_NOT_APPLICABLE",
    ]
```

許容誤差:

```text
absolute_difference_usd <= 0.000001 USD
```

float変換由来の差だけ許容します。

---

# 12. Discovery SpikeのGolden Cases

| ID  | ケース                       | 必須結果                           |
| --- | ---------------------------- | ---------------------------------- |
| G01 | 単一LONG・利益               | account cash増加                   |
| G02 | 単一LONG・損失               | account cash減少                   |
| G03 | 単一SHORT・利益              | account cash増加                   |
| G04 | 単一SHORT・損失              | account cash減少                   |
| G05 | 同時2件・max=1               | 1件受理、1件拒否                   |
| G06 | 同時2件・max=2               | 2件受理                            |
| G07 | cash不足                     | `INSUFFICIENT_AVAILABLE_CASH`    |
| G08 | 同一symbol重複               | 後続拒否                           |
| G09 | 同時刻exit/entry・no reuse   | entryは解放資金を使えない          |
| G10 | 同時刻exit/entry・exit first | entryは解放資金を使える            |
| G11 | operator costあり            | account cash不変、economicのみ減少 |
| G12 | NO_TRADE                     | 取引0、cash不変                    |
| G13 | UNKNOWN                      | skip記録                           |
| G14 | lossがreserve超過            | `INCONCLUSIVE`                   |
| G15 | action row欠落               | input reject                       |
| G16 | component hash不一致         | input reject                       |
| G17 | notional不一致               | input reject                       |
| G18 | short formula不一致          | input reject                       |

---

# 13. Property-based Tests

Hypothesisを使います。既にdev dependencyとして存在します。

必須property:

```text
initial_cashを増やしてaccepted trade数が減らない

max_open_positionsを増やしてaccepted trade数が減らない

fee_estimateを増やしてfinal account cashが増えない

slippage_estimateを増やしてfinal account cashが増えない

operator_time_costを変えてもaccount cashは変わらない

operator_time_costを増やすとeconomic resultは増えない

NO_TRADEではtimeline上のcashが変化しない

同じinputでtimelineとresult IDが一致する

reserved_cashは常にopen positionsのreserve合計と一致する

run完了時にreserved cashとopen positionsが0になる
```

`NO_SAME_TIMESTAMP_REUSE`と`EXIT_THEN_ENTRY`について:

```text
EXIT_THEN_ENTRYのaccepted count
>=
NO_SAME_TIMESTAMP_REUSEのaccepted count
```

は通常成り立ちますが、損失exitによってcashが減る場合は必ずしも成り立ちません。

したがって、この性質を無条件propertyにはしません。

---

# 14. Spikeの出力

```text
data/research/crypto_perp_portfolio_capacity/<run>/
├── runtime_inventory.json
├── case.json
├── reference_results.jsonl
├── scenario_matrix.json
├── vectorbt_differential.json
└── decision.md
```

## `runtime_inventory.json`

```text
pack_id
row_set_id
event_count
unique_symbol_count
time_range
selected_action_counts
notional_usd
fee_rate
funding_rate
slippage_bps
operator_cost_non_zero_count
execution_window_peak_overlap
same_timestamp_entry_exit_count
source_coverage_counts
known_gaps
```

## `scenario_matrix.json`

各caseについて:

```text
action_policy
max_open_positions
metric_scenario
same_timestamp_cash_policy
accepted_trade_count
rejected_trade_count
final_available_cash
simulated_account_pnl
economic_result
peak_reserved_cash
settled_cash_drawdown
run_status
```

## `decision.md`

結論は次のどれか一つです。

```text
PROMOTE_PORTFOLIO_CAPACITY
KEEP_SPIKE_ONLY
USE_EXISTING_CANDIDATE_PACK_ONLY
ADD_VECTORBT_DIFFERENTIAL
DO_NOT_USE_VECTORBT_FOR_PORTFOLIO
COLLECT_MORE_RUNTIME_DATA
INVALID_CANDIDATE_PACK_INPUT
```

---

# 15. 製品化条件

次を全て満たした場合だけ`src/`へ昇格します。

```text
全Golden Case PASS

全property test PASS

Candidate Packのcomponent hashを検証できる

現行runtime sampleで、
overlapまたはcash制約による拒否が1件以上発生する

既存backtest_resultと異なる意思決定情報が得られる

reference implementationが500行程度以内

既存Candidate Packのevent/score/outcome logicを重複実装していない
```

次の場合は製品化しません。

```text
position overlapが実質存在しない

初期資本3,000 USDでcash制約が一度も起きない

既存single-position診断と同じ情報しか出ない

pack readerの複雑さがCandidate Pack本体を上回る

VectorBT差分が説明不能
```

---

# 16. 製品化後のファイル構成

```text
src/sis/crypto_perp/portfolio_capacity/
├── __init__.py
├── models.py
├── pack_reader.py
├── path.py
├── vectorbt_diff.py
└── rendering.py

src/sis/commands/
└── crypto_perp_portfolio_capacity.py

schemas/
├── crypto_perp_portfolio_capacity_case.v1.schema.json
├── crypto_perp_portfolio_capacity_result.v1.schema.json
└── crypto_perp_portfolio_capacity_comparison.v1.schema.json

tests/crypto_perp/portfolio_capacity/
├── test_pack_reader.py
├── test_path.py
├── test_properties.py
├── test_vectorbt_diff.py
└── test_cli.py
```

---

# 17. 製品版CLI

1回のcommandで1policyだけ実行します。

```bash
uv run --extra vectorbt sis crypto-perp-portfolio-capacity \
  --candidate-pack-dir data/crypto_perp/backtest_candidate_pack/fee_6bps \
  --initial-cash-usd 3000 \
  --max-open-positions 1 \
  --action-policy CURRENT_SELECTOR \
  --metric-scenario STRESS \
  --same-timestamp-cash-policy NO_SAME_TIMESTAMP_REUSE \
  --with-vectorbt-diff \
  --out data/crypto_perp/portfolio_capacity/current_selector_max1
```

出力:

```text
case.json
result.json
timeline.jsonl
vectorbt_differential.json
report.md
```

Matrix専用CLIは作りません。

個人利用なのでshell loopで十分です。

---

# 18. 高解像度Market Capture設計

Portfolio Capacityとは別PRです。

## 18.1 目的

現在のCandidate PackはBAR_PROXYです。

VectorBTへ渡しても改善するのは、

```text
共通資本
同時ポジション
注文順序
```

までです。

執行価格・slippage・partial fillを改善するには、forwardの板・約定データが必要です。

---

## 18.2 初期対象

```text
channel:
  books15
  trades

symbol:
  固定1〜2銘柄

duration:
  30分
```

初回からwatchdeck上位5銘柄を24時間保存しません。

`books15`は150ms間隔の15レベルsnapshotなので、保存量が大きくなる可能性があります。まず実測し、圧縮後の1時間・1日換算容量を出します。Bitget公式では`books15`は毎回snapshot、full `books`はincrementalです。([Bitget][2])

---

## 18.3 ファイル構成

```text
src/sis/crypto_perp/
├── market_capture.py
├── recorder.py
├── segments.py
├── ws_protocol.py
└── book.py

src/sis/commands/
└── crypto_perp_market_capture.py

tests/crypto_perp/
├── test_market_capture.py
├── test_recorder_streaming.py
└── test_segment_rotation.py
```

---

## 18.4 責務

### `market_capture.py`

```text
WebSocket接続
subscribe
heartbeat
pong timeout
reconnect
resubscribe
per-message receive time
shutdown
```

### `recorder.py`

既存batch関数は互換維持します。

追加する`CaptureSession`は:

```text
raw message parse
event time抽出
book validation
gap/checksum集計
row生成
segment writerへappend
manifest counter更新
```

### `segments.py`

追加する`RotatingGzipJsonlWriter`:

```text
60秒または10,000行でrotate
tmp fileへ書く
close
fsync
atomic replace
SHA-256
row count / min ts / max ts
```

---

## 18.5 Row contract

```text
schema_version
capture_id
connection_id
connection_sequence
event_id
provider_id
native_symbol
channel
ts_event
ts_received
recv_monotonic_ns
raw_payload
```

`ts_received`をcapture開始時刻で一括代入してはいけません。

messageごとに取得します。

---

## 18.6 full `books`

初版では購読禁止です。

現在の`BitgetOrderBook.apply_depth()`は受け取ったbids/asksでbook全体を置き換えます。

Bitgetのfull `books` updateはincrementalであり、価格levelごとの置換・削除・挿入が必要です。([Bitget][2])

したがって:

```text
books15:
  operationally allowed

books1:
  optional

books:
  disabled until merge implementation is complete
```

---

## 18.7 Capture受入条件

30分smokeで次を出します。

```text
row_count
compressed_bytes
uncompressed_estimated_bytes
messages_per_second
projected_gzip_bytes_per_day
connection_count
reconnect_count
pong_count
gap_count
checksum_failure_count
min_event_ts
max_event_ts
receive_delay_ms p50 / p90 / p99
```

停止条件:

```text
projected storageが運用予算を超える
gap率が許容不能
ts_eventが取れない
tradesにaggressor情報がない
30分で再接続後の復旧を確認できない
```

保存量が大きい場合:

```text
symbol数を減らす
capture時間を短くする
event/near-miss候補のみ収集する
```

を優先します。

---

# 19. Native Execution Replay設計

Market Captureが運用可能になった後に実装します。

## 19.1 ファイル構成

```text
src/sis/crypto_perp/execution_replay/
├── __init__.py
├── models.py
├── case_builder.py
├── book_selector.py
├── depth_fill.py
├── runner.py
└── rendering.py
```

---

## 19.2 `ExecutionReplayCase`

```python
class ExecutionReplayCase(BaseModel):
    event_id: str
    symbol: str
    side: Literal["LONG", "SHORT"]

    decision_at: datetime
    entry_arrival_at: datetime
    planned_exit_at: datetime
    exit_arrival_at: datetime

    entry_latency_ms: int
    exit_latency_ms: int

    notional_usd: Decimal

    max_book_age_ms: int
    allow_partial_fill: bool

    instrument_snapshot_ref: ArtifactRef
    capture_manifest_ref: ArtifactRef
    funding_ref: ArtifactRef | None

    evidence_basis: Literal["DEPTH15_SNAPSHOT"]
```

---

## 19.3 Book選択

Entry:

```text
entry_arrival_at以降の最初のvalid books15 snapshot
```

Exit:

```text
exit_arrival_at以降の最初のvalid books15 snapshot
```

次なら拒否:

```text
snapshotがない
book invalid
capture gap内
snapshot age > max_book_age_ms
```

---

## 19.4 Depth消費

LONG:

```text
entry:
  asksを価格昇順に消費

exit:
  bidsを価格降順に消費
```

SHORT:

```text
entry:
  bidsを価格降順に消費

exit:
  asksを価格昇順に消費
```

結果:

```text
FILLED
PARTIAL
UNFILLABLE
STALE_BOOK
DATA_GAP
INVALID_BOOK
```

板の15レベルを超えて外挿しません。

---

## 19.5 Funding

現行Tournament Rowsのfundingは保有時間比例の推定です。

Execution Replayでは、取得済みのfunding eventがある場合だけ、実boundaryを跨いだpositionへ適用します。

```text
positive funding:
  LONG debit
  SHORT credit

negative funding:
  LONG credit
  SHORT debit
```

NautilusTraderも`FundingRateUpdate`に`next_funding_ns`がある場合、またはeventがfunding interval boundaryに一致する場合にsettlementします。([NautilusTrader][3])

funding eventがない場合:

```text
FUNDING_NOT_REPLAYED
```

をknown limitへ入れます。

0として実測済み扱いしません。

---

# 20. NautilusTrader Sidecar

## 20.1 導入時期

次をすべて満たした場合だけ実装します。

```text
Portfolio CapacityでCURRENT_SELECTORがNO_TRADEを上回る

ALWAYS_CONTINUATIONまたはALWAYS_REVERSALに対して
selectorの追加価値が残る

STRESSでも口座損益推定が正

5〜20bpsの執行差で結論が変わる

対象eventにbooks15/tradesがある

Native Execution Replayでは解決できない差がある
```

---

## 20.2 隔離構成

```text
tools/backtest_spikes/nautilus_bitget/
├── pyproject.toml
├── uv.lock
├── README.md
├── converter.py
├── runner.py
├── result_writer.py
└── tests/
```

rootの`pyproject.toml`と`uv.lock`には追加しません。

---

## 20.3 入力

```text
ExecutionReplayCase
books15 capture
trade capture
instrument snapshot
funding events
```

Nautilus側に次を実装しません。

```text
event detector
edge scorer
action selector
portfolio priority policy
```

---

## 20.4 Order book変換

`books15`はsnapshotです。

sidecarでは次のいずれかをspikeで比較します。

```text
上位10levelをDepth10へ変換

または

snapshotごとに
CLEAR + ADD deltasへ変換
```

採用基準:

```text
15レベルのdepth消費結果を保持できる
変換後のbest bid/askが元データと一致する
timestamp順序を保持する
```

---

## 20.5 Nautilus設定

```text
taker entry
taker exit
NETTING
leverage 1x相当
liquidity_consumption=True
queue modelなし
makerなし
```

NautilusTraderはL2/L3データでは表示板のdepthでslippageと部分約定を扱えます。ただし、historical book自体は不変なので、`liquidity_consumption=True`で同じ表示流動性の重複利用を抑える必要があります。([NautilusTrader][3])

15分足だけを入れたNautilus runは採用しません。bar-onlyでは`on_bar`後の注文はbar close状態で処理され、nativeなnext-bar-open executionも提供されません。([NautilusTrader][3])

---

## 20.6 Nautilus採用条件

Nautilus導入の成功条件は、

```text
動いた
```

でも、

```text
VectorBTと一致した
```

でもありません。

最終条件は:

```text
Native Replayよりactual fill誤差が小さい
```

です。

actual fillがない段階では、次だけを確認します。

```text
converterが正しい
golden caseと一致する
funding boundaryが正しい
partial fillが期待通り
再実行結果が安定
```

---

# 21. PR分割

## PR-BT0: Discovery Spike

変更範囲:

```text
tools/backtest_spikes/crypto_perp_portfolio_capacity/
```

成果物:

```text
runtime_inventory.json
golden_case_results.json
scenario_matrix.json
vectorbt_differential.json
decision.md
```

---

## PR-BT1: Portfolio Capacity製品化

新規:

```text
src/sis/crypto_perp/portfolio_capacity/
src/sis/commands/crypto_perp_portfolio_capacity.py
schemas/crypto_perp_portfolio_capacity_*.schema.json
tests/crypto_perp/portfolio_capacity/
```

既存Candidate Packは変更しません。

---

## PR-BT2: Market Capture Smoke

最初は固定1〜2symbol、30分。

```text
market_capture.py
CaptureSession
RotatingGzipJsonlWriter
books15/trades
```

保存量と通信品質を測ります。

---

## PR-BT3: Operational Capture

BT2が成功した場合のみ。

```text
候補symbol切替
segment rotation
再接続
継続manifest
storage budget
```

---

## PR-BT4: Native Execution Replay

```text
latency-aware book selection
entry/exit depth consumption
partial/unfillable
discrete funding
```

---

## PR-BT5: Nautilus Sidecar

条件付き。

root dependencyへは入れません。

---

# 22. 完了条件

## Portfolio Capacity完了

```text
Candidate Pack lineageを検証できる
同一event setを維持する
共通資本を時系列再生できる
最大position数を適用できる
同一symbol重複を拒否できる
BASE/STRESSを分離できる
同時timestamp ambiguityを2policyで比較できる
account PnLとeconomic resultを分けられる
ReferenceとVectorBTの限定範囲が一致する
```

## Market Capture完了

```text
books15/tradesを30分取得できる
per-message event/receive timestampがある
segment rotationできる
再接続後に継続できる
gap/checksumを記録できる
1日換算容量を測定できる
```

## Execution Replay完了

```text
decision + latencyに対応するbookを選べる
LONG/SHORTのentry/exitをdepthで再生できる
PARTIAL/UNFILLABLE/STALE/GAPを区別できる
板外を外挿しない
```

---

# 23. 重大な停止条件

## Portfolio Capacity

```text
Candidate Pack component hashが検証できない
event set不一致
notional/cost assumption不一致
short PnL formula不一致
Reference golden case不一致
operator time costがaccount cashへ混入
```

## VectorBT

```text
ReferenceとのLONG/SHORT差を説明できない
fixed fee差を説明できない
accepted scheduleをVectorBTが不明な理由で拒否する
変換コードがReference実装より大きくなる
```

## Capture

```text
30分smokeの保存量が実用範囲を超える
gapが頻発する
event timestampが安定しない
再接続後の復旧ができない
```

## NautilusTrader

```text
Portfolio CapacityがNO_TRADE以下
STRESSで負
高解像度データがない
Native Replayとの差が判断を変えない
2営業日以内に1eventを再生できない
```

---

# 24. コーダーへの最初の指示

最初に実装するのは`PR-BT0`だけです。

```text
目的:
  現行Candidate Packを、
  共通資本・同時position制約下で時系列再生する価値を確認する。

変更可能:
  tools/backtest_spikes/crypto_perp_portfolio_capacity/

変更禁止:
  src/
  schemas/
  Candidate Pack
  現行VectorBT adapter
  pyproject.toml
  uv.lock
  CLI catalog
  NautilusTrader
```

必須実装:

```text
pack_reader
runtime inventory
Decimal reference path
18 golden cases
Hypothesis properties
64 scenario matrix
VectorBT gross+fixed-cost differential
decision.md
```

必須報告:

```text
現行packで実際にoverlapが何件発生したか
max position 1/2/3で何件拒否されたか
CURRENT_SELECTORとstatic actionの差
BASE/STRESSの差
同時timestamp policyによる差
VectorBTとの差
製品化する価値があるか
```

この結果が出るまで、`src/`への製品化、高解像度replay、NautilusTrader統合へ進みません。

07月16日(木)_午後9時12分18秒.

[1]: https://vectorbt.dev/api/portfolio/base/
[2]: https://www.bitget.com/api-doc/contract/websocket/public/Order-Book-Channel
[3]: https://nautilustrader.io/docs/latest/concepts/backtesting/
