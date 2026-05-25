# Phase 2 Completion Definition

## Purpose

この文書は、`marketlens-strike` における **Phase 2 = Research Layer** の完了条件を定義する。

ここでいう Phase 2 は、Phase 1 の Venue Evidence Engine の上に、研究用の市場データ・マクロデータ・イベントデータ・特徴量を生成する層を追加する作業である。

この文書は `docs/ENGINEERING_HANDOFF_NOTE.md` の代替ではない。`ENGINEERING_HANDOFF_NOTE` が定義するのは **Phase 2 に着手してよい条件** であり、この文書が定義するのは **Phase 2 が完成したと見なせる条件** である。

## Phase 2 Is Not

Phase 2 は次を含まない。

- 売買注文の実行
- Paper Trading
- Live Trading
- Execution Adapter
- QQQ baseline strategy の最終化
- signal-driven backtest の最終完成

それらは Phase 3 以降の責務とする。

## Entry Condition

Phase 2 の実装を開始する前提条件は次のとおり。

1. `P1-003` live evidence 収集が完走している。
2. `P1-005` diagnose 結果を確認済みである。
3. `P1-004` strict artifact validation が通っている。
4. `check-go-no-go` と EvidenceCard が更新済みである。

Phase 2 に入ることと、Phase 2 が完成していることは別である。

## Objective

Phase 2 の目的は、QQQ / SPY / XAU の 4h〜3d シグナル研究に必要な研究データを、再生成可能なローカル artifact として出力できるようにすること。

最低限必要なのは次の 5 系統である。

1. 研究価格データ
2. マクロデータ
3. イベントカレンダー
4. 特徴量パネル
5. 初期シグナル出力

## Required Scope

Phase 2 完成に必要な実装スコープは、ZIP の `P2-001` から `P2-008` までとする。

### P2-001 Dependencies

`pyproject.toml` に次の依存を追加する。

- `yfinance`
- `yahooquery`
- `fredapi`
- `pandas-datareader`

また、必要なら `.env.example` に次を追加する。

```env
FRED_API_KEY=
```

### P2-002 Research Policy Document

次の文書を追加する。

- `docs/RESEARCH_DATA_STRATEGY.md`

この文書は少なくとも次を固定する。

- 価格データ provider の primary / fallback
- マクロデータ provider の primary / fallback
- CSV first の event policy
- Phase 2 では `Polars first` で進めること
- provider 障害時の fail-closed / fallback 条件

### P2-003 Provider Interfaces

次のファイル群を追加する。

```txt
src/sis/research/
  __init__.py
  providers.py
  price_ingest.py
  macro_ingest.py
  event_calendar.py
  feature_panel.py
  signal_builder.py
  research_quality.py
```

`providers.py` では少なくとも次を定義する。

- `ResearchFetchRequest`
- `PriceProvider`
- `MacroProvider`

Provider interface は `polars.DataFrame` を返す契約でよい。Phase 2 では provider abstraction の最小実装を優先し、過剰な pluggable architecture は不要。

### P2-004 Price Ingest

少なくとも次の研究対象を取得できること。

- `QQQ`
- `SPY`
- `GLD`
- `^VIX`
- `UUP`
- `USDJPY=X`
- `EURUSD=X`

最低限必要な出力は次の 2 つ。

- `data/research/raw/yfinance_ohlcv.parquet`
- `data/research/market_panel.parquet`

`market_panel.parquet` は少なくとも次の列を持つ。

```txt
ts
symbol
open
high
low
close
volume
provider
provider_symbol
interval
adjustment
```

### P2-005 Macro Ingest

少なくとも次の series を取得できること。

- `DGS10`
- `DGS2`
- `T10Y2Y`
- `FEDFUNDS`

最低限必要な出力は次の 2 つ。

- `data/research/raw/fred_macro.parquet`
- `data/research/macro_panel.parquet`

`macro_panel.parquet` は少なくとも次の列を持つ。

```txt
date
series_id
value
provider
vintage_mode
realtime_start
realtime_end
```

### P2-006 Event Calendar

最初は外部 API 連携ではなく CSV first でよい。

入力例:

```csv
event_ts,event_name,event_class,importance,before_minutes,after_minutes,action
2026-06-10T12:30:00+00:00,CPI,inflation,high,120,60,BLOCK
2026-06-17T18:00:00+00:00,FOMC,central_bank,high,180,120,BLOCK
```

最低限必要な出力:

- `data/research/event_calendar.parquet`

必要列:

```txt
event_ts
event_name
event_class
importance
before_minutes
after_minutes
action
```

### P2-007 Feature Panel

価格・マクロ・イベントを結合し、研究用特徴量を生成する。

最低限必要な出力:

- `data/research/feature_panel.parquet`

最低限必要な列:

```txt
ts
canonical_symbol
research_close
research_return_4h
research_return_1d
research_return_3d
sma_20
sma_50
close_above_sma20
realized_vol_20
dgs10
dgs2
t10y2y
vix_level
dxy_proxy
is_event_blackout
minutes_to_next_event
minutes_since_last_event
venue
venue_mark_price
venue_index_price
venue_spread_bps
venue_stale_rate
venue_tradable_rate
trade_allowed
blocked_reason
```

### P2-008 Signal Builder

Feature panel から、少なくとも QQQ baseline 研究で使える `signals.csv` を生成できること。

最低限必要な出力:

- `data/research/signals.csv`

必要列:

```txt
ts_signal
canonical_symbol
side
timeframe
signal_strength
strategy_name
reason
```

注意点:

- `signals.csv` は Phase 2 完成物に含める。
- ここで求めるのは「研究入力として再現生成できる初期 signal artifact」である。
- QQQ baseline strategy の最終化と、signal-driven backtest による戦略可否判定は Phase 4 の責務。
- ただし Phase 2 完了判定では、feature panel を入力に最低 1 本の signal CSV を再現生成できる必要がある。

## CLI Contract For Phase 2

Phase 2 完成と見なすには、少なくとも次の CLI が追加されていること。

```bash
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
```

CLI 名は多少調整してよいが、次の責務は分離すること。

1. 市場価格とマクロ取得
2. event calendar build
3. feature panel build
4. signal build
5. missing / alignment / stale ではない研究品質の確認

`build-backtest` は既存 CLI なので、Phase 2 完成条件には含めない。Phase 2 は `signals.csv` を再現生成できれば足り、signal-driven backtest の戦略評価完成は Phase 4 の責務とする。

## Acceptance Criteria

Phase 2 は、次のすべてを満たしたときに完成とみなす。

### 1. Code Exists

次が repo に存在する。

- `src/sis/research/providers.py`
- `src/sis/research/price_ingest.py`
- `src/sis/research/macro_ingest.py`
- `src/sis/research/event_calendar.py`
- `src/sis/research/feature_panel.py`
- `src/sis/research/signal_builder.py`
- `src/sis/research/research_quality.py`
- `docs/RESEARCH_DATA_STRATEGY.md`

### 2. Artifacts Are Reproducible

少なくとも次がローカルで再生成できる。

- `data/research/market_panel.parquet`
- `data/research/macro_panel.parquet`
- `data/research/event_calendar.parquet`
- `data/research/feature_panel.parquet`
- `data/research/signals.csv`

### 3. Data Contracts Are Stable

各 artifact がこの文書で定義した最低限の列を持ち、列名・時刻基準・symbol 命名が run ごとに大きく揺れない。

### 4. Research Quality Can Be Checked

少なくとも次が確認できる。

- missing rate
- time alignment
- symbol coverage
- provider 名
- date range

Phase 2 完成時点では venue stale/tradable 指標ではなく、研究データとしての欠損と整列性を評価対象とする。

### 5. Targeted Tests Exist

次のいずれかの形で targeted tests があること。

- unit tests
- artifact schema / column tests
- provider fallback tests
- event blackout merge tests
- feature alignment tests

### 6. Commands Work

少なくとも次のコマンド群が成功すること。

```bash
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
```

## Phase 2 Is Complete When

最終的な判定は次の 1 文で表せる。

> Phase 2 is complete when the repository can reproducibly build market, macro, event, feature, and initial signal artifacts for QQQ / SPY / XAU research, and can validate their basic research quality without relying on manual spreadsheet work.

## Phase 2 Is Not Complete When

次のいずれかに当てはまる場合、Phase 2 は未完了とする。

- 依存追加だけされ、artifact が生成できない
- raw provider fetch はあるが panel 化できない
- `market_panel.parquet` だけあり、`macro_panel.parquet` や `feature_panel.parquet` がない
- `feature_panel.parquet` はあるが `signals.csv` を生成できない
- CLI はあるが再現可能な出力が出ない
- provider 失敗時の fallback / stop condition が未定義
- 研究品質の確認方法がなく、欠損や時刻ズレが見えない

## Relation To Later Phases

- Phase 3 は、この Phase 2 の出力を読む Decision Engine の実装。
- Phase 4 は、QQQ baseline strategy と signal-driven backtest の完成。
- Phase 5 は、paper broker / portfolio / simulated fills。
- Phase 6 は、execution adapter interface と read-only reconciliation。

したがって、Phase 2 の完成物は「研究データの基盤」であり、「トレード実行の基盤」ではない。

## Recommended Review Order

この文書を読む人は、次の順で確認するとよい。

1. `docs/ENGINEERING_HANDOFF_NOTE.md` があれば先に読む
2. `docs/ACCEPTANCE_AUDIT.md` で Phase 1 の状態を確認する
3. この文書で Phase 2 完了条件を確認する
4. ZIP の `TASK_BOARD.csv` の `P2-*` を実装タスクとして使う
