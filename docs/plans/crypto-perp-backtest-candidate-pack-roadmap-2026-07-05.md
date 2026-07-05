<!--
作成日: 2026-07-05_00:35 JST
更新日: 2026-07-05_00:35 JST
-->

# Crypto Perp Backtest Candidate Pack Roadmap

## 結論

actual cash を当分実装しない期間の次の終着点は、利益証明ではなく **Crypto Perp Backtest Candidate Pack v1** を完成させること。

これは、Bitget BTCUSDT public data と ticker source を timestamp-safe に接続し、actual cash なしの simulated backtest までを再現可能な artifact chain として出す計画である。

この計画は live order、tiny-live、actual cash、cash ledger、ML/LLM 売買判断を扱わない。まずは pre-actual-cash の blocker を 1 つずつ潰し、backtest candidate を `BACKTEST_REJECT` / `BACKTEST_REVISE` / `BACKTEST_COLLECT_MORE_DATA` / `BACKTEST_CANDIDATE_HOLD` に分類できる状態を作る。

## 現在地

完了済み:

- `write_pre_actual_cash_evidence_pack()` は実装済み。
- 既存 artifact 読み取りは実装済み。
- 10 fixture event / outcome dogfood は完了済み。
- 10 real-data-adjacent BTCUSDT public candle dogfood は完了済み。
- 10件 dogfood の selected blocker は `TICKER_SOURCE_MISSING_BLOCKS_COST_ADJUSTED_ESTIMATE_AND_EDGE_ACTION`。
- public pre-actual-cash CLI は追加していない。
- actual cash、tiny-live、live order、ML/LLM 判断は未実装かつスコープ外。

現状の重要な値:

- `decision=COLLECT_MORE_SOURCES`
- `event_count=10`
- `outcome_count=10`
- `selected_action_counts={'UNKNOWN': 10}`
- `leader_action=REVERSAL_SHORT`
- `leader_beats_no_trade=True`
- `bias_guard_status=BLOCKED`
- `pbo_status=NOT_ESTIMABLE`

## 目的

### 短期目的

`TICKER_SOURCE_MISSING_BLOCKS_COST_ADJUSTED_ESTIMATE_AND_EDGE_ACTION` だけを対象にし、ticker source が timestamp-safe に source availability へ反映されるか確認する。

### 中期目的

Ticker source 反映後に、actual cash なしの simulated backtest を行い、Backtest Candidate Pack v1 を出す。

### 長期目的

Backtest Candidate Pack v1 の結果を使い、候補を次の4択に分類する。

```text
BACKTEST_REJECT
BACKTEST_REVISE
BACKTEST_COLLECT_MORE_DATA
BACKTEST_CANDIDATE_HOLD
```

## 制約

### 絶対にやらないこと

- actual cash ledger を作らない。
- actual cash rows を作らない。
- actual-cash report gate を通さない。
- live measurement を行わない。
- tiny-live execution を行わない。
- wallet / signing / exchange write を行わない。
- production live trading を扱わない。
- TabPFN / TabFM / AutoGluon / Colab runner を追加しない。
- LLM に売買判断をさせない。
- public pre-actual-cash CLI を増やさない。
- source gaps を 0 埋めしない。
- 現在取得した ticker を過去 event に後付けして available 扱いしない。

### 読み替え禁止

- Backtest pass を profit proof と読まない。
- public candle outcome を actual cash evidence と読まない。
- cost-adjusted estimate を actual cash と読まない。
- `actual_cash_result_usd=null` を cash 0 と読まない。
- `selected_action=UNKNOWN` を弱い signal と読まない。
- `leader_action=NO_TRADE` を無視して取引 action を選ばない。
- `bias_guard_status=BLOCKED` を robustness pass と読まない。

## 設計方針

## 方針1: ticker source は既存 Bitget public source refresh を優先する

既存の `strategy_idea_candidates/bitget_public_source.py` は、Bitget public REST から `mix_contracts`、`mix_tickers`、`mix_history_candles` を取得できる。さらに `ticker_rows` parquet と `ticker_manifest.json` を書ける。

したがって、G3 では新しい Bitget API client を別に増やすより、既存の `strategy-idea-candidates-bitget-source-refresh` とその出力を crypto-perp source availability に接続する方を優先する。

### 既存出力で使うもの

```text
source_root/data/ticker_rows/exchange=bitget/symbol=BTCUSDT/date=*/ticker_rows.parquet
source_root/data/ticker_manifest.json
bitget_public_source_refresh_manifest.json
```

### ticker_rows の重要列

```text
ts_exchange_ms
ts_received_ms
symbol_canonical
last_px
bid_px
ask_px
bid_sz
ask_sz
mid_px
mark_px
index_px
funding_rate
next_funding_time_ms
open_interest
volume_24h_base
volume_24h_quote
run_id
```

## 方針2: ticker は funding source ではない

Bitget ticker row には `funding_rate` が含まれるが、これを `funding` source として自動的に満たさない。

最初のG3では、`ticker` source だけを改善対象にする。Funding semantics は ticker 追加後にまだ blocker が残る場合だけ扱う。

## 方針3: as-of 条件を必須にする

Ticker row は、次の条件を満たす場合だけ event に利用可能とする。

```text
ticker.ts_received_ms <= event.information_cutoff_at
and event.information_cutoff_at - ticker.ts_received_ms <= max_staleness_seconds
```

`ts_exchange_ms` ではなく `ts_received_ms` を availability の主判定に使う。理由は、実際にローカル側がその値を知り得た時刻は exchange timestamp ではなく受信時刻だからである。

既存の過去 10 event に、現在取得した ticker row を後付けしてはいけない。後付けした場合、source gap は減るが、時系列リークになる。

## Phase 1: Ticker source availability adapter

### 目的

既存 `ticker_rows` parquet / `ticker_manifest.json` から、event cutoff 時点で利用可能な ticker row を選び、source availability に `ticker` available を反映できるようにする。

### 対象ファイル

新規候補:

```text
src/sis/crypto_perp/ticker_source.py
```

変更候補:

```text
src/sis/crypto_perp/source_availability.py
tests/crypto_perp/test_source_availability.py
tests/crypto_perp/test_profit_readiness_local_automation.py
```

必要なら追加:

```text
schemas/crypto_perp_ticker_source_link.v1.schema.json
```

ただし、単に `source_availability.source_refs` と `metadata` に反映できるなら、新schemaは増やさない方がよい。

### 実装内容

`src/sis/crypto_perp/ticker_source.py` に、少なくとも次の helper を置く。

```text
load_ticker_rows(source_root: Path, symbol: str) -> rows
find_latest_ticker_before_cutoff(rows, information_cutoff_at, max_staleness_seconds) -> row | None
build_ticker_source_status_metadata(row, cutoff) -> metadata
```

source availability に渡す値:

```text
available_sources={"ticker": True}
row_counts={"ticker": 1}
source_refs=[ticker_manifest or ticker_rows parquet ref]
source_metadata={"ticker": {...}}
```

Ticker が見つからない場合:

```text
available_sources={"ticker": False}
row_counts={"ticker": 0}
reason=TICKER_SOURCE_MISSING_BEFORE_CUTOFF or TICKER_SOURCE_STALE
```

`reason` を `SourceAvailabilityStatus.reason` に直接指定するAPIが現状なければ、metadata / known_gaps で明示する。

### テスト方針

最小テスト:

1. ticker row の `ts_received_ms` が cutoff より前なら available。
2. ticker row の `ts_received_ms` が cutoff より後なら missing。
3. ticker row が stale なら missing。
4. ticker row が available の場合、`can_compute_cost_adjusted_estimate` が funding/bars/event の条件と合わせて改善する。
5. 現在tickerを過去eventに後付けできないことを明示的に落とす。

### 完了条件

- ticker source availability が as-of で判定される。
- source availability の `ticker` が 10 event で available / missing / stale に分かれる。
- `known_gaps_by_source.ticker.missing_event_count` の変化を読める。
- `decision.json` と `decision.md` に ticker source の変化が反映される。
- public pre-actual-cash CLI は追加しない。
- actual cash / tiny-live / live order は追加しない。

## Phase 2: Ticker付き10 event dogfood

### 目的

Ticker source を入れた状態で、10 event / 10 outcome の pre-actual-cash pack を再生成し、前回との差分を見る。

### 重要な制約

既存の 2026-06-27 過去eventへ、現在tickerを後付けしない。

実データdogfoodは次のどちらかで行う。

```text
A. 新しいticker capture後に、新しいevent/outcomeを作る
B. テスト用fixtureとして、cutoff以前のticker rowsを明示的に作る
```

Aは実務dogfood、Bはunit/integration test。Bを実務evidenceと呼ばない。

### 対象ファイル

```text
src/sis/crypto_perp/ticker_source.py
src/sis/crypto_perp/pre_actual_cash.py
tests/crypto_perp/test_profit_readiness_local_automation.py
docs/crypto_perp/pre_actual_cash_*_dogfood_*/
docs/final-summary.md
```

### 出力

```text
decision.json
decision.md
source_availability_matrix.json
known_gaps_by_source.json
edge_score_summary.json
tournament_rows_v2_summary.json
bias_guard_summary.json
blocker.md
```

### 比較する値

```text
known_gaps_by_source.ticker.missing_event_count
source_availability.can_compute_cost_adjusted_estimate_count
edge_score_summary.selected_action_counts
tournament_rows_v2_summary.leader_action
tournament_rows_v2_summary.leader_beats_no_trade
bias_guard_summary.guard_status
bias_guard_summary.pbo_status
decision.reason_codes
```

### 完了条件

- 10 event / 10 outcome で ticker付きpackが生成される。
- decision schema validation が通る。
- non_goal_flags はすべて false。
- ticker追加前後の差分が `blocker.md` または `final-summary` に記録される。
- `selected_action=UNKNOWN` が減るか、減らない理由が明示される。

## Phase 3: 分岐判定

Ticker追加後は、次のどれかだけを選ぶ。

### A. 改善した場合

条件:

```text
can_compute_cost_adjusted_estimate_count が増える
selected_action=UNKNOWN が減る
reason_codes から ticker blocker が消える
```

次へ進む:

```text
30 event / 30 outcome dogfood
```

### B. tickerは入ったが funding が曖昧な場合

条件:

```text
funding_rate="0" が measured funding として扱われている疑いが残る
can_compute_cost_adjusted_estimate が期待通り改善しない
```

次へ進む:

```text
funding source semantics check
```

Funding は ticker とは別sourceとして扱う。Ticker内の funding_rate を funding source として自動昇格しない。

### C. ticker/fundingでも UNKNOWN が続く場合

条件:

```text
source availability は改善している
それでも selected_action=UNKNOWN または NO_TRADE が継続
```

次へ進む:

```text
event definition / cutoff / outcome window / edge rule review
```

この時点まで、trades/books/replayへ飛ばない。

## Phase 4: 30 event dogfood

### 目的

10件ではなく、30 event / 30 outcome で NO_TRADE 比較と bias guard を少し読める状態にする。

### 開始条件

- ticker source の扱いが決まっている。
- funding の扱いが少なくとも誤読されないようになっている。
- 10 event dogfoodで主blockerが1つに絞れている。
- event definition が明らかに壊れていない。

### 完了条件

- 30 event / 30 outcome のpackを生成できる。
- `selected_action=UNKNOWN` だけで終わるかどうかが読める。
- `leader_action` と `leader_beats_no_trade` が複数eventで読める。
- bias guard が `sample insufficient` だけで止まるか、次の reason に進むかが読める。
- 4択decisionに落ちる。

## Phase 5: Crypto Perp Backtest Candidate Pack v1

### 目的

actual cashなしで、timestamp-safeな simulated backtest を行い、候補を4択に分類する。

### Decision values

```text
BACKTEST_REJECT
BACKTEST_REVISE
BACKTEST_COLLECT_MORE_DATA
BACKTEST_CANDIDATE_HOLD
```

### 対象ファイル

新規候補:

```text
src/sis/crypto_perp/backtest_candidate_pack.py
schemas/crypto_perp_backtest_candidate_pack.v1.schema.json
tests/crypto_perp/test_backtest_candidate_pack.py
```

既存連携候補:

```text
src/sis/backtest/data_availability.py
src/sis/backtest/no_lookahead.py
src/sis/backtest/execution_simulation.py
src/sis/backtest/stress.py
src/sis/backtest/regime_split.py
src/sis/backtest/rolling_stability.py
src/sis/crypto_perp/pre_actual_cash.py
src/sis/crypto_perp/tournament_rows.py
```

### 出力案

```text
data/crypto_perp/backtest_candidate_pack/latest/
  signal_rows.jsonl
  source_availability_summary.json
  execution_assumptions.json
  no_lookahead_report.json
  backtest_result.json
  stress_result.json
  regime_split_result.json
  rolling_stability_result.json
  decision.json
  decision.md
```

### signal_rows最小列

```text
signal_id
event_id
outcome_id
symbol
information_cutoff_at
signal_generated_at
selected_action
signal_score
source_availability_id
feature_pack_id
edge_score_id
no_trade_reason
```

### execution_assumptions最小列

```text
entry_price_rule
exit_price_rule
fee_rate
slippage_bps
funding_rate_policy
position_size_usd
max_holding_minutes
no_fill_policy
```

ゼロコストは禁止する。最初は保守的な固定仮定でよい。

### No-lookahead条件

```text
feature / ticker / source used_at <= information_cutoff_at
signal_generated_at >= information_cutoff_at
entry timestamp > signal timestamp
outcome は signal生成に使わない
train/test split を使う場合は時系列順
```

### 完了条件

- Backtest Candidate Pack v1 が1候補で生成される。
- no-lookahead report が pass または blocker を返す。
- cost前後の結果が分かれる。
- decisionが4択へ落ちる。
- profit proof / live readiness / actual cash readiness を主張しない。

## Phase 6: Candidate ledger connection

### 目的

Backtest Candidate Pack v1 の結果を strategy idea / candidate 管理へ接続する。

### 対象

```text
src/sis/strategy_idea_candidates/perp_bridge.py
src/sis/strategy_idea_candidates/ledger.py
src/sis/strategy_idea_candidates/review_packet.py
```

### 完了条件

- candidateごとに backtest decision が残る。
- rejected reason が残る。
- similar candidate の重複再生成を抑制できる。
- `BACKTEST_CANDIDATE_HOLD` が増えすぎる場合、理由を集計できる。

## テスト方針

### 必須

```bash
uv run pytest tests/crypto_perp/test_profit_readiness_local_automation.py -q
uv run pytest tests/crypto_perp/test_source_availability.py -q
uv run ruff check src/sis/crypto_perp tests/crypto_perp
uv run ruff format --check src/sis/crypto_perp tests/crypto_perp
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
```

### G3完了時

```bash
./scripts/check
```

### 新schema追加時

- `jsonschema.Draft202012Validator.check_schema()` をテストに入れる。
- negative test を必ず入れる。
- `profit_proven=true` 相当の過大主張を拒否する。

## Stop conditions

次の場合は次phaseへ進めない。

- tickerを過去eventへ後付けしている。
- source gaps を0埋めしている。
- selected_action=UNKNOWN を signal と読んでいる。
- NO_TRADEを邪魔者扱いしている。
- fundingを ticker の副産物として自動的にsource availableにしている。
- 10 event dogfoodを profit evidence と読んでいる。
- backtest passを actual cash readiness と読んでいる。

## コーダーへの最短実行指示

```text
まず G3 だけ実装する。
既存 Bitget public source refresh が出す ticker_rows / ticker_manifest を使い、event cutoff 時点で利用可能な ticker row を source availability に反映する。
現在tickerを過去eventへ後付けしない。
新public pre-actual-cash CLI、actual cash、tiny-live、live、MLは追加しない。
10 event dogfoodで ticker追加前後の差分を記録する。
その結果で、funding semantics / event definition / 30 event dogfood のどれに進むかを決める。
```

## 完了条件まとめ

この計画全体の完成条件は、次の状態である。

```text
actual cashなしで、ticker-aware source availability、signal rows、execution assumptions、no-lookahead check、simulated backtest、stress/regime/rolling確認を含む Backtest Candidate Pack v1 が出る。
候補は BACKTEST_REJECT / BACKTEST_REVISE / BACKTEST_COLLECT_MORE_DATA / BACKTEST_CANDIDATE_HOLD のどれかに分類される。
この状態でも profit proof、actual cash readiness、tiny-live readiness、live trading readiness は主張しない。
```
