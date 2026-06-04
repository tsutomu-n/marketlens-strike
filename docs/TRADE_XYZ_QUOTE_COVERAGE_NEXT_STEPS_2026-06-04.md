<!--
作成日: 2026-06-04_17:47 JST
更新日: 2026-06-04_22:04 JST
-->

# Trade[XYZ] Quote Coverage And 24h Backtest Smoke Next Steps 2026-06-04

この文書は、30日quote coverageを待つ間に、24時間WS artifactで先に進める作業を固定するための運用計画である。

ユーザー向けの短い判断記録は [TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md](TRADE_XYZ_QUOTE_COVERAGE_USER_DECISION_RECORD_2026-06-04.md) に分離している。

## 結論

採用方針:

```text
1. 起動中の24時間 read-only quote collector は止めない。
2. 30日 quote coverage gate は別枠で継続する。
3. その待ち時間で、24h WS artifact を使った ingest/backtest 配線検証を進める。
4. 24h smoke の結果を strategy selection / production readiness には使わない。
```

この方針で「待ち時間」を実装検証に使う。ただし、`backtest_data_ready=true` は strict gate が通るまで宣言しない。

## ユーザー向け最短版

いまの判断:

```text
いまは待つ。
PID 2484910 の collector は動いている。
raw quote file も増えている。
今この瞬間に追加の cycle や until-ready supervisor を起動しない。
```

ユーザーが見るべきもの:

```text
1. collector が生きているか
   ps -fp 2484910

2. raw file が増えているか
   find data/raw/quotes/trade_xyz -maxdepth 1 -type f -name '2026-06-0[45].jsonl' -print -exec wc -l {} \;

3. 次に使う判断表
   この文書の「status別アクション」
```

やってよいこと:

```text
起動中 collector を見守る
24h WS smoke artifact は SP500 / NVDA / XYZ100 まで確認済みなので、同じ artifact contract の回帰確認に留める
failure handling と smoke-only boundary を近接テストで固定する
```

まだやらないこと:

```text
PID 2484910 が生きている間に次cycleを起動する
PID 2484910 が生きている間に until-ready supervisor を起動する
24h smoke の結果で backtest_data_ready=true と言う
smoke metrics を性能評価やstrategy selectionに使う
```

PID 2484910 が自然終了した後の判断:

```text
1. uv run sis trade-xyz-collection-status --strict を実行する
2. failing_requirements を見る
3. quote_coverage だけなら scripts/collect_trade_xyz_data_until_ready.sh を使う
4. quote_coverage 以外が混じるなら、自動ループさせずそのfailを先に直す
```

ユーザー向けに言うと、今の作業は「実データを貯める待ち時間」と「24hデータで配線を固める作業」を分けて進めている。前者が readiness の本番判定に関係し、後者は実装の壊れを早く見つけるための検証である。

## 計画の正しさ

この計画は、次の範囲では正しい。

```text
正しい:
  30日 quote coverage を待つ
  起動中 collector を止めない
  待ち時間で 24h WS artifact を使い、ingest/backtest 配線を検証する
  24h smoke を readiness / strategy selection に使わない
  SP500 / NVDA / XYZ100 の3銘柄smoke完了後は、同じ契約の回帰確認に留める
```

次の読み方は正しくない。

```text
正しくない:
  24hデータで backtest_data_ready=true にできる
  3銘柄smoke成功を全11銘柄成功とみなす
  smoke metrics を性能評価に使う
  古い data/ops/trade_xyz_collection_status.json を現在状態として読む
  oracle timestamp provenance が解決済みだと扱う
```

したがって、次の一手は「計画を広げる」ではなく、artifact contract と failure handling を近接テストで固定すること。

## 2つのデータ系統を混同しない

この計画には、用途の違う2つのデータ系統がある。

```text
REST quote coverage collector:
  目的:
    30日 quote_coverage gate を満たす
  現在の対象:
    AAPL, AMD, AMZN, EWJ, GOOGL, META, MSFT, NVDA, SP500, TSLA, XYZ100
  出力:
    data/raw/quotes/trade_xyz/YYYY-MM-DD.jsonl
  gate:
    backtest_data_ready / readiness_decision に関係する

24h WS smoke artifact:
  目的:
    ingest/backtest 配線の実装検証
  現在の対象:
    WS rawは NVDA, SP500, XYZ100
    smoke backtest は SP500, NVDA, XYZ100
  出力:
    .tmp/trade_xyz_ws_quotes_24h.parquet
    .tmp/backtests_ws_24h/trade-xyz-smoke-SP500-1h-mid_price-source_ts_ms-ws_bbo_state/
    .tmp/backtests_ws_24h/trade-xyz-smoke-NVDA-1h-mid_price-source_ts_ms-ws_bbo_state/
    .tmp/backtests_ws_24h/trade-xyz-smoke-XYZ100-1h-mid_price-source_ts_ms-ws_bbo_state/
  gate:
    backtest_data_ready には使わない
```

現実的な作業順序は、REST collectorを止めずに、3銘柄WS smokeで見つかった契約をテストで固定すること。全11銘柄・全戦略へ広げるのは、30日coverageと別の設計判断が必要になるため今はやらない。

## 現在の確認済み状態

確認時刻:

```text
2026-06-04_22:04 JST
```

起動中 collector:

```text
PID:
  2484910

child:
  sis collect-trade-xyz-data-cycle

command:
  uv run sis collect-trade-xyz-data-cycle
  --collection-config configs/trade_xyz_data_collection.yaml
  --duration-minutes 1440
  --interval-seconds 60
  --seed-path configs/instrument_registry.seed.json
  --symbols AAPL,AMD,AMZN,EWJ,GOOGL,META,MSFT,NVDA,SP500,TSLA,XYZ100
  --strict
  --skip-signal-candles

started:
  2026-06-04_16:39 JST

expected finish:
  2026-06-05_16:39 JST 前後

log:
  logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log

raw quote file:
  data/raw/quotes/trade_xyz/2026-06-04.jsonl
  2026-06-05_09:00 JST 以降は UTC日付が変わるため、
  data/raw/quotes/trade_xyz/2026-06-05.jsonl にも書かれる可能性がある

2026-06-04_22:04 JST 時点:
  process alive
  .tmp/trade_xyz_data_cycle.lock/pid = 2484910
  data/raw/quotes/trade_xyz/2026-06-04.jsonl rows = 3542
  raw quote file mtime = 2026-06-04_22:03 JST
  log は開始行だけだが、raw file が増えているため、それだけでは停止扱いしない
```

current status artifact:

```text
data/ops/trade_xyz_collection_status.json

generated_at:
  2026-06-04T13:03:33.604482+00:00

decision:
  COLLECT_MORE_QUOTES

backtest_data_ready:
  false

readiness_decision:
  NOT_READY

fail_count:
  1

known_gap_count:
  1

failing_requirements:
  quote_coverage

known_gap_requirements:
  oracle_timestamp_provenance

collector_running:
  true

progress_status:
  collecting_ok

raw_quote_inventory:
  row_count: 20194
  traceable_row_count: 20194
  malformed_row_count: 0
  missing_symbol_row_count: 0
  source_counts: trade_xyz_l2Book:20194
  symbol_counts: AAPL:1836, AMD:1836, AMZN:1836, EWJ:1836, GOOGL:1836, META:1836, MSFT:1836, NVDA:1836, SP500:1836, TSLA:1835, XYZ100:1835

注意:
  2026-06-04_22:03 JST に --no-refresh-coverage --no-refresh-readiness で更新した。
  process状態とraw inventoryは新しいが、coverage / readiness の完了判定には full refresh を使う。
  raw_quote_inventory.row_count は過去raw fileを含む合計で、最新file単体の行数とは別。
```

24h WS normalized artifact:

```text
manifest:
  .tmp/trade_xyz_ws_quotes_24h.manifest.json

parquet:
  .tmp/trade_xyz_ws_quotes_24h.parquet

duckdb:
  .tmp/trade_xyz_ws_quotes_24h.duckdb

raw root:
  data/raw/ws/trade_xyz_24h_20260602_1902

symbols:
  NVDA
  SP500
  XYZ100

quote_count_written:
  1113529

bbo_quote_count:
  861859

active_asset_ctx_quote_count:
  251670
```

24h WS smoke backtest artifact:

```text
SP500 run_dir:
  .tmp/backtests_ws_24h/trade-xyz-smoke-SP500-1h-mid_price-source_ts_ms-ws_bbo_state

input_data_ref:
  .tmp/trade_xyz_ws_quotes_24h.parquet

symbol:
  SP500

timeframe:
  1h

entry_lookback:
  2

exit_lookback:
  2

trade_count:
  5

net_return_after_cost:
  -0.0009731640906773809

max_drawdown:
  -0.0011721687793645463

fee_row_resolved_rate:
  1.0

open_position_at_end:
  false

smoke_only:
  true

usable_for_strategy_selection:
  false

no_live_order:
  true

wallet_used:
  false

exchange_write_used:
  false

2026-06-04_20:23 JST 再実行:
  SP500 smoke pass
  trade_count: 5
  fee_row_resolved_rate: 1.0
  open_position_at_end: false

2026-06-04_20:24 JST 追加確認:
  NVDA smoke pass
  run_dir: .tmp/backtests_ws_24h/trade-xyz-smoke-NVDA-1h-mid_price-source_ts_ms-ws_bbo_state
  strategy_id: nvda_breakout_v0
  trade_count: 3
  fee_row_resolved_rate: 1.0
  open_position_at_end: false

2026-06-04_20:28 JST 追加確認:
  XYZ100 smoke pass
  run_dir: .tmp/backtests_ws_24h/trade-xyz-smoke-XYZ100-1h-mid_price-source_ts_ms-ws_bbo_state
  strategy_id: xyz100_breakout_v0
  trade_count: 5
  fee_row_resolved_rate: 1.0
  open_position_at_end: false

2026-06-04_21:36 JST current code 再確認:
  SP500 / NVDA / XYZ100 smoke pass
  entry_lookback: 2
  exit_lookback: 2
  smoke_only: true
  usable_for_strategy_selection: false
  no_live_order: true
  wallet_used: false
  exchange_write_used: false
  fee_row_resolved_rate: 1.0
  open_position_at_end: false
  trade_count:
    SP500: 5
    NVDA: 3
    XYZ100: 5
```

## 用語と責任境界

### 24h smoke

意味:

```text
24時間程度の実データで、raw -> normalized -> bar -> run_backtest artifact の配線が壊れていないことを確認する作業。
```

使ってよい用途:

```text
ingest code の回帰確認
bar builder の入力列確認
BBO fill snapshot と activeAssetCtx state の分離確認
no-lookahead join の確認
fee row resolution の確認
artifact writer の確認
report / manifest の生成確認
```

使ってはいけない用途:

```text
strategy selection
performance claim
production readiness
wallet / signing / exchange write readiness
backtest_data_ready=true 宣言
30日 quote coverage gate の代替
```

### 30日 quote coverage

意味:

```text
readiness gate 上の quote_coverage 要件。
現行 manifest は min_days_required=30.0 を要求する。
```

現在の扱い:

```text
待つ対象。
24h smoke が成功しても、この gate は解消しない。
```

### oracle timestamp provenance

意味:

```text
oracle_ts_ms が、source payload 内の根拠ある oracle timestamp field から来ているかを確認する gate。
```

現在の扱い:

```text
known gap。
recv_ts_ms / source_ts_ms / client timestamp で埋めない。
```

## 実行計画

### Phase 0: ループ治具の扱い

結論:

```text
新しい常駐ツールは作らない。
既存の scripts/collect_trade_xyz_data_until_ready.sh を、quote coverage 用のループ治具として使う。
```

理由:

```text
既存 wrapper は cycle lock、supervisor lock、stale raw file、status artifact、strict readiness を既に扱っている。
追加で必要だったのは、ループの判断条件を狭くし、状態をJSONで残し、重いcoverage再計算をpollごとに走らせないこと。
DB、daemon framework、scheduler、別CLIを増やす段階ではない。
```

現在の治具の挙動:

```text
collector が動いている間:
  trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness で軽量監視する
  latest raw file stale、cycle lock stale、supervisor lock stale は異常終了する
  archive / account fee の外部前提はmonitor pollの停止条件にしない

collector が止まっている時:
  full refresh の trade-xyz-collection-status を実行する
  backtest_data_ready=true なら exit 0
  failing_requirements が quote_coverage だけなら次cycle起動へ進む
  failing_requirements が quote_coverage 以外なら exit 7 で止める
  次cycle起動直前に archive preflight / account fee の起動前gateを確認する
```

状態ファイル:

```text
data/ops/trade_xyz_until_ready_supervisor_state.json
```

主に見るfield:

```text
event
decision
backtest_data_ready
failing_requirements
known_gap_requirements
collector_running
collector_process_count
latest_file_stale
latest_file_age_seconds
cycle_lock_stale
supervisor_lock_stale
progress_status
cycle_count
log_path
```

この治具でやらないこと:

```text
quote_coverage 以外の fail を無視して次cycleを回す
signal_candles / real_market_reference / account_specific_fee / archive preflight の問題を自動で握りつぶす
smoke metrics を readiness に混ぜる
source_ts_ms / recv_ts_ms を oracle_ts_ms に流用する
lock directory を手動削除する
起動中 PID 2484910 と重複して次cycleを始める
```

### Phase A: 起動中 collector を安全に見守る

目的:

```text
現在走っている24時間 cycle を完走させる。
```

確認コマンド:

```bash
ps -fp 2484910
pstree -ap 2484910 || true
pgrep -af "collect-trade-xyz-data-cycle|collect_trade_xyz_data_cycle|collect-trade-xyz-quotes" || true
tail -80 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
find data/raw/quotes/trade_xyz -maxdepth 1 -type f -name '2026-06-0[45].jsonl' -print -exec wc -l {} \;
find data/raw/quotes/trade_xyz -maxdepth 1 -type f -name '2026-06-0[45].jsonl' -printf '%TY-%Tm-%Td %TH:%TM %s %p\n' | sort
```

正常な途中状態:

```text
PID 2484910 が存在する
子プロセスに sis collect-trade-xyz-data-cycle がある
raw quote JSONL の mtime が更新される
raw quote row count が増える
log に fatal error がない
```

実務上の目安:

```text
interval_seconds=60 かつ 11 symbols なので、
正常時はおおむね1分あたり約11 rows増える。
2-3 interval 連続で行数が増えない場合は、
process / lock / latest raw file / network error を確認する。
ただし、logが開始行だけでも raw file が増えていれば停止とは判断しない。
```

注意:

```text
このcycleは UTC日付をまたぐ。
2026-06-05_09:00 JST 以降に 2026-06-04.jsonl の行数が止まっても、
2026-06-05.jsonl が増えているなら正常な可能性が高い。
```

やらないこと:

```text
collector を理由なく kill しない
collector が生きている状態で次cycleを重複起動しない
lock directory を手動削除しない
```

running中に status を見たい場合は、重いcoverage再計算を毎回走らせず、必要最小限にする。

```bash
uv run sis trade-xyz-collection-status --no-refresh-coverage --refresh-readiness --strict
```

ただし、この command も `data/ops/trade_xyz_collection_status.json` と report を書き換える。さらに `--no-refresh-coverage` の結果は、coverage進捗やready判定には使わない。raw行数だけ見たい時は shell commands で十分。

supervisor の通常pollではさらに軽くする。

```bash
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness --strict
```

受け入れ条件:

```text
log に finished が出る
PID が自然終了する
trade-xyz-collection-status を再実行できる
```

### Phase B: 24h WS smoke artifact を開発検証に使う

目的:

```text
30日coverageを待たずに、ingest/backtest 周辺の実装品質を上げる。
```

現在使える artifact:

```text
.tmp/trade_xyz_ws_quotes_24h.parquet
.tmp/trade_xyz_ws_quotes_24h.manifest.json
.tmp/backtests_ws_24h/trade-xyz-smoke-SP500-1h-mid_price-source_ts_ms-ws_bbo_state/
.tmp/backtests_ws_24h/trade-xyz-smoke-NVDA-1h-mid_price-source_ts_ms-ws_bbo_state/
.tmp/backtests_ws_24h/trade-xyz-smoke-XYZ100-1h-mid_price-source_ts_ms-ws_bbo_state/
```

現在の範囲:

```text
SP500 / NVDA / XYZ100 の 3 WS symbols は smoke pass 済み。
11銘柄へ広げる計画ではない。
REST quote coverage collector の11銘柄とは別物として扱う。
smoke pass は ingest/backtest 配線確認であり、strategy selection や performance 評価には使わない。
```

直近の実行単位:

```text
T1:
  DONE: SP500 smoke を再実行する

T2:
  DONE: data_manifest.json / backtest_run.json / metrics.json / fills.parquet を確認する

T3:
  DONE: 近接テストを実行する

T4:
  DONE: NVDAとXYZ100を追加で試した

T5:
  DONE: --ws-bbo-state smoke の artifact contract と missing BBO failure handling を近接テストで固定した

T6:
  DONE: WS state join が canonical_symbol だけでなく symbol column alias でも target symbol を絞れることを近接テストで固定した

T7:
  DONE: trade rows が fill snapshot candidate に混ざらず、BBO rows だけが fill price を作ることを近接テストで固定した

T8:
  DONE: --ws-bbo-state smoke script が存在しない BBO target symbol を no bbo rows for symbol で明確に拒否することを近接テストで固定した

T9:
  DONE: WS frame の source column 欠落を明確に拒否することを近接テストで固定した

T10:
  DONE: optional state columns が欠けた activeAssetCtx rows を null state として扱い、不要に落ちないよう実装と近接テストを追加した

T11:
  DONE: BBO rows の source_ts_ms 欠損を明確に拒否する実装と近接テストを追加した

T12:
  DONE: activeAssetCtx の recv_ts_ms が欠けた場合は state をjoinせず、BBO barだけを残す実装と近接テストを追加した

T13:
  DONE: --ws-bbo-state smoke script の空symbol入力を symbol must not be empty で明確に拒否する実装と近接テストを追加した

T14:
  DONE: --ws-bbo-state と raw_quote_rows timeframe の組み合わせを明確に拒否する近接テストを追加した

T15:
  DONE: --ws-bbo-state は mid_price / source_ts_ms 固定であることを実装と近接テストで明確に拒否条件化した

T16:
  DONE: entry_lookback / exit_lookback の0以下入力を must be positive で明確に拒否する実装と近接テストを追加した

T17:
  DONE: BBO source_ts_ms 欠損チェックを target symbol のBBOに限定し、他symbolの壊れたBBOが対象symbolのsmokeを落とさないことを近接テストで固定した

T18:
  DONE: build_bbo_bars_with_active_asset_state の空symbol入力を symbol must not be empty で明確に拒否する実装と近接テストを追加した

T19:
  DONE: BBO rows の symbol column 欠落を WS BBO rows missing symbol column で明確に拒否する近接テストを追加した

2026-06-04_21:52 JST 追加調査:
  DONE: 30日 quote coverage 未完でも進められる Phase B/C の実装・テスト項目は、現時点で T1-T19 まで完了していると判断した
  DONE: 追加で広げるより、今は collector を重複起動せず、PID 2484910 の自然終了後に strict status を更新する方が安全と判断した
  残り: collector終了後の full status refresh、quote_coverage だけ fail なら until-ready、quote_coverage 以外が混じるならそのfail修正

2026-06-04_21:58 JST 追加検証:
  DONE: ./scripts/check が pass した
  DONE: pytest は 828 passed
  DONE: collector PID 2484910 はまだ alive、raw quote rows は増加中

T20:
  DONE: trade-xyz-collection-status の raw inventory に symbol_counts / source_counts / malformed_row_count / missing_symbol_row_count を追加し、収集中の銘柄偏りとJSONL破損を軽量監視できるようにした

2026-06-04_22:04 JST 追加確認:
  DONE: --no-refresh-coverage --no-refresh-readiness の status で collector_running=true / progress_status=collecting_ok を確認した
  DONE: raw inventory total 20194 rows、traceable 20194、malformed 0、missing symbol 0 を確認した
  DONE: 11 symbols は AAPL/AMD/AMZN/EWJ/GOOGL/META/MSFT/NVDA/SP500 が 1836 rows、TSLA/XYZ100 が 1835 rows で、収集中の大きな銘柄欠落は見えていない

停止条件:
  smoke_only=true / usable_for_strategy_selection=false / no_live_order=true が崩れたら止める
  source_ts_ms / recv_ts_ms を oracle_ts_ms として扱う必要が出たら止める
  live / wallet / signing / exchange write へ触れそうなら止める
```

2026-06-04_20:24 JST の修正:

```text
src/sis/backtest/trade_xyz/ws_ingestion.py:
  activeAssetCtx state を target symbol で絞ってから no-lookahead join する。
  SP500 bar に NVDA / XYZ100 state が混ざらないようにした。

scripts/run_trade_xyz_backtest_smoke.py:
  strategy_id を symbol 連動にした。
  SP500 は sp500_breakout_v0、NVDA は nvda_breakout_v0 になる。

tests:
  cross-symbol state混入防止を追加
  NVDA smoke script の strategy_id 確認を追加
  --ws-bbo-state smoke の data_manifest / backtest_run / candidate_result / metrics 契約を追加
  BBO rows がない WS frame を明確に拒否するテストを追加
  canonical_symbol ではなく symbol column だけの WS frame でも state join が動くことを追加
  trade rows が BBO fill snapshot に混ざらないことを追加
  --ws-bbo-state smoke script が missing BBO target symbol を no bbo rows for symbol で拒否することを追加
  WS frame の source column 欠落を missing source column で拒否することを追加
  funding_rate / open_interest_usd などの optional state columns 欠落時に null state として扱うことを追加
  BBO rows の source_ts_ms 欠損を BBO rows missing source_ts_ms で拒否することを追加
  activeAssetCtx recv_ts_ms 欠損時は state を使わず BBO bars を残すことを追加
  空白だけの --symbol を symbol must not be empty で拒否することを追加
  --ws-bbo-state と raw_quote_rows timeframe の併用を --ws-bbo-state requires a bar timeframe で拒否することを追加
  --ws-bbo-state で --close-source mid_price 以外、--event-time-source source_ts_ms 以外を拒否することを追加
  entry_lookback / exit_lookback の0以下入力を must be positive で拒否することを追加
  他symbolのBBO source_ts_ms欠損がtarget symbolのbar生成を落とさないことを追加
  build_bbo_bars_with_active_asset_state の空symbol入力を symbol must not be empty で拒否することを追加
  BBO rows の symbol column 欠落を WS BBO rows missing symbol column で拒否することを追加
```

再実行コマンド:

```bash
uv run python scripts/run_trade_xyz_backtest_smoke.py \
  --input .tmp/trade_xyz_ws_quotes_24h.parquet \
  --funding-events '' \
  --symbol SP500 \
  --timeframe 1h \
  --event-time-source source_ts_ms \
  --out .tmp/backtests_ws_24h \
  --entry-lookback 2 \
  --exit-lookback 2 \
  --ws-bbo-state
```

NVDA / XYZ100 を回帰確認する時は `--symbol` だけを変える。生成される `strategy_id` は
`nvda_breakout_v0` / `xyz100_breakout_v0` になる。

検証する観点:

```text
raw_ws_root と input_data_ref が追跡可能
BBO rows だけが fill snapshot candidate になる
activeAssetCtx rows は state として no-lookahead join される
activeAssetCtx の source_ts_ms=None で落ちない
recv_ts_ms を oracle_ts_ms として使っていない
fills.parquet が生成される
metrics.json が生成される
backtest_run.json に smoke_only=true が残る
usable_for_strategy_selection=false が残る
no_live_order=true / wallet_used=false / exchange_write_used=false が残る
```

近接テスト:

```bash
uv run pytest -q tests/backtest/test_real_quotes_smoke.py tests/backtest/test_trade_xyz_ws_ingestion.py
```

広めの検証:

```bash
./scripts/check
```

受け入れ条件:

```text
実データ smoke が exit 0
fills.parquet / metrics.json / data_manifest.json / backtest_report.md が生成される
fee_row_resolved_rate が 1.0
open_position_at_end が false
smoke_only=true
usable_for_strategy_selection=false
./scripts/check が pass
```

### Phase C: 24h smoke で見つけるべき改善点

優先して見るもの:

```text
1. timestamp boundary
   source_ts_ms がある行とない行の分離
   recv_ts_ms の用途が observation time に限定されているか
   BBO fill snapshot rows には source_ts_ms が必須であることを拒否条件で固定しているか

2. fill boundary
   BBO 以外が exec_buy_price / exec_sell_price を作っていないか
   activeAssetCtx / trades が fill snapshot として混ざっていないか
   trade rows があっても fill_mid_price / exec_* は BBO rows 由来のままか

3. state join
   activeAssetCtx state が未来参照なしで bar に付くか
   state_observed_ts_ms が bar event_ts を超えていないか
   canonical_symbol / symbol のどちらでも target symbol filter が効くか
   optional state columns が欠けても null state として扱われるか
   recv_ts_ms がない activeAssetCtx state は join されないか

4. artifact contract
   manifest に input_data_ref / input hash / policy が残るか
   smoke artifact が production artifact と誤読されないか

5. failure handling
   source_ts_ms=None で落ちないか
   empty symbol / empty BBO / malformed row の error message が明確か
   missing BBO rows は no bbo rows for fill snapshots で拒否されるか
   missing BBO target symbol は no bbo rows for symbol で拒否されるか
   empty symbol は symbol must not be empty で拒否されるか
   raw_quote_rows timeframe は --ws-bbo-state と併用できないことを拒否できるか
   --ws-bbo-state の artifact名と実処理がズレないよう mid_price / source_ts_ms 固定を拒否条件で守っているか
   entry_lookback / exit_lookback の0以下入力を拒否できるか
   BBO source_ts_ms 欠損チェックは target symbol の BBO だけにかかるか
   build_bbo_bars_with_active_asset_state の空symbol入力を拒否できるか
   BBO rows の symbol column 欠落を拒否できるか
   missing source column は missing source column で拒否されるか
```

後回しにするもの:

```text
strategy performance tuning
parameter optimization
multi-strategy selection
live order simulation
wallet / signing / exchange write
```

よりBetterな当面の順序:

```text
1. DONE: SP500 smoke を再実行して artifact が再現することを確認する
2. DONE: data_manifest / backtest_run / metrics / fills の必須fieldを確認する
3. DONE: NVDA / XYZ100 を追加し、symbol-specific strategy_id と smoke boundary を確認する
4. DONE: --ws-bbo-state smoke の artifact contract と missing BBO failure handling を近接テストで固定する
5. DONE: symbol column alias の state join fallback を近接テストで固定する
6. DONE: trade rows を fill snapshot に混ぜない境界を近接テストで固定する
7. DONE: missing BBO target symbol を --ws-bbo-state smoke script で明確に拒否する近接テストを固定する
8. DONE: missing source column を明確に拒否する近接テストを固定する
9. DONE: optional state columns 欠損を null state として扱う実装と近接テストを追加する
10. DONE: BBO source_ts_ms 欠損を明確に拒否する実装と近接テストを追加する
11. DONE: activeAssetCtx recv_ts_ms 欠損時は state をjoinせずBBO barsを残す実装と近接テストを追加する
12. DONE: empty symbol を --ws-bbo-state smoke script で明確に拒否する実装と近接テストを追加する
13. DONE: --ws-bbo-state と raw_quote_rows timeframe の不正な組み合わせを拒否する近接テストを追加する
14. DONE: --ws-bbo-state の close_source / event_time_source 固定を実装と近接テストで明確にする
15. DONE: entry_lookback / exit_lookback の0以下入力を拒否する実装と近接テストを追加する
16. DONE: 他symbolのBBO source_ts_ms欠損でtarget symbolのsmokeが落ちないよう、BBO target symbol filterを実装と近接テストで固定する
17. DONE: build_bbo_bars_with_active_asset_state の空symbol入力を拒否する実装と近接テストを追加する
18. DONE: BBO rows の symbol column 欠落を拒否する近接テストを追加する
19. DONE: 2026-06-04_21:52 JST 時点で、30日coverage未完でも進められる既知項目に追加実装候補が残っていないことを確認する
20. DONE: collection status の raw inventory に symbol/source/malformed/missing-symbol breakdown を追加し、収集中の偏りと壊れたJSONLを見えるようにする
21. 今後問題が出たら、まず tests/backtest/test_real_quotes_smoke.py と
   tests/backtest/test_trade_xyz_ws_ingestion.py に近接テストを足す
22. その後に src/sis/backtest/trade_xyz/ws_ingestion.py か
   scripts/run_trade_xyz_backtest_smoke.py を最小修正する
```

やらないこと:

```text
全11銘柄 smoke 対応へ飛ばない
DB migration や新しい永続storageを作らない
public CLI化しない
strategy parameter tuning を始めない
```

### Phase D: 24h collector 完了後に status を更新する

collector が自然終了したら実行する:

```bash
uv run sis trade-xyz-collection-status --strict
```

wrapperは正常終了時に `uv run sis trade-xyz-collection-status` を呼ぶが、再開者は自分の時点で再実行してよい。`data/ops/trade_xyz_collection_status.json` は古い可能性があるため、JSONを読む前に status command を実行する。

coverage / readiness の判定には full refresh を使う。

```text
判定に使う:
  uv run sis trade-xyz-collection-status --strict
  uv run sis trade-xyz-collection-status --strict --fail-on-not-ready

判定に使わない:
  uv run sis trade-xyz-collection-status --no-refresh-coverage ...
```

ready 判定を明示的に確認する:

```bash
uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
```

CLI stdout / reportで見る項目:

```text
backtest_data_ready
readiness_decision
fail_count
known_gap_count
failing_requirements
known_gap_requirements
coverage_min_span_days
coverage_max_remaining_days_exact
coverage_completion_ratio_by_span
latest_raw_file_age_minutes
progress_status
signal_candles_status
signal_candles_request_error_count
real_market_reference_status
oracle_timestamp_provenance_status
account_specific_fee_status
```

JSON artifactを直接見る場合は、nested path を使う。

```bash
jq '{
  decision,
  backtest_data_ready,
  readiness_decision,
  fail_count,
  known_gap_count,
  failing_requirements: .readiness_requirements.fail,
  known_gap_requirements: .readiness_requirements.known_gap,
  collector_running: .collector_process.running,
  collector_process_count: .collector_process.process_count,
  cycle_lock_stale: .locks.cycle.stale,
  supervisor_lock_stale: .locks.supervisor.stale,
  coverage_min_span_days: .coverage.min_span_days,
  coverage_max_remaining_days_exact: .coverage.max_remaining_days_exact,
  coverage_completion_ratio_by_span: .coverage.completion_ratio_by_span,
  latest_file_age_seconds: .raw_quote_inventory.latest_file_age_seconds,
  raw_row_count: .raw_quote_inventory.row_count,
  traceable_row_count: .raw_quote_inventory.traceable_row_count,
  malformed_row_count: .raw_quote_inventory.malformed_row_count,
  missing_symbol_row_count: .raw_quote_inventory.missing_symbol_row_count,
  symbol_counts: .raw_quote_inventory.symbol_counts,
  source_counts: .raw_quote_inventory.source_counts,
  progress_status: .progress_since_previous_status.status,
  signal_candles_status: .readiness_requirement_details.signal_candles.status,
  signal_candles_request_error_count: .readiness_requirement_details.signal_candles.request_error_count,
  real_market_reference_status: .readiness_requirement_details.real_market_reference.status,
  oracle_timestamp_provenance_status: .readiness_requirement_details.oracle_timestamp_provenance.status,
  account_specific_fee_status: .readiness_requirement_details.account_specific_fee.status
}' data/ops/trade_xyz_collection_status.json
```

想定される結果:

```text
quote_coverage はまだ fail の可能性が高い。
この場合は backtest_data_ready=false のまま、次の24h cycleを検討する。
1 cycleで30日要件に届く想定を置かない。
```

### Phase E: 次の24h cycle を起動する

次の全てを満たす場合だけ起動する:

```text
現在の collector が終了している
data-cycle lock が stale でない、または wrapper が安全に回復できる状態
直近 status が更新済み
自動supervisorで回す場合、failing_requirements が quote_coverage だけ
signal_candles_request_error_count が 0、または failed subset 再取得を先に済ませる判断をしている
```

重複起動を避ける確認:

```bash
pgrep -af "collect-trade-xyz-data-cycle|collect_trade_xyz_data_cycle|collect-trade-xyz-quotes" || true
uv run sis trade-xyz-collection-status --strict
```

推奨起動コマンド:

```bash
setsid -f scripts/collect_trade_xyz_data_until_ready.sh >/tmp/trade_xyz_until_ready.nohup 2>&1 < /dev/null
```

この command は、現collectorが自然終了した後に使う。起動直後に既存 collector が動いていれば新cycleを重複起動しない実装だが、PID 2484910 が生きている間に追加起動する運用にはしない。現collector終了後、full refresh で `failing_requirements=quote_coverage` だけであることを確認できた時だけ次cycleへ進む。`quote_coverage` 以外の fail が残る場合は exit 7 で止まる。

手動で1cycleだけ回す代替コマンド:

```bash
stamp="$(date -u +%Y%m%d_%H%M%S)"
mkdir -p .tmp/launchers
setsid -f zsh -lc "cd /home/tn/projects/marketlens-strike && env SIS_TRADE_XYZ_CYCLE_DURATION_MINUTES=1440 SIS_TRADE_XYZ_CYCLE_INTERVAL_SECONDS=60 SIS_TRADE_XYZ_CYCLE_SYMBOLS=AAPL,AMD,AMZN,EWJ,GOOGL,META,MSFT,NVDA,SP500,TSLA,XYZ100 SIS_TRADE_XYZ_CYCLE_COLLECT_SIGNAL_CANDLES=0 SIS_TRADE_XYZ_CYCLE_REFRESH_REGISTRY=1 scripts/collect_trade_xyz_data_cycle.sh >> .tmp/launchers/trade_xyz_data_cycle_${stamp}.setsid.log 2>&1"
```

起動後確認:

```bash
pgrep -af "collect-trade-xyz-data-cycle|collect_trade_xyz_data_cycle|collect-trade-xyz-quotes"
latest_log="$(ls -t logs/trade_xyz_data_cycle/*.log | head -1)"
printf 'latest_log=%s\n' "${latest_log}"
tail -40 "${latest_log}"
```

起動したら、PID、log path、起動時刻を `docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md` と `.ai_memory/HANDOFF.md` に残す。

supervisor を使った場合は、あわせて次も見る。

```bash
jq . data/ops/trade_xyz_until_ready_supervisor_state.json
```

## status別アクション

### quote_coverage だけが fail

行動:

```text
scripts/collect_trade_xyz_data_until_ready.sh で次の24h cycle を回す。
同時に 24h smoke artifact で backtest 周辺の検証を続ける。
数cycle連続で progress_status が warning になる場合は、
次cycleを増やす前に raw inventory と coverage_refresh の失敗原因を見る。
```

### signal_candles が fail

行動:

```text
readiness manifest の next action を優先する。
failed symbols / intervals の subset 再取得を先に行う。
```

確認:

```bash
uv run sis trade-xyz-collection-status --strict
python3 - <<'PY'
import json
from pathlib import Path

path = Path("data/manifests/trade_xyz_data_readiness_manifest.json")
manifest = json.loads(path.read_text())
for action in manifest.get("next_actions", []):
    if action.get("key") == "collect_signal_candles":
        print(action.get("command"))
PY
```

### real_market_reference が fail

行動:

```text
missing symbol を確認してから再収集する。
古い archive や 2026-05-30以前の reference artifact を現行ready判定へ戻さない。
```

再収集例:

```bash
uv run sis collect-trade-xyz-real-market-reference --start 2026-05-31 --interval 1d
uv run sis trade-xyz-collection-status --strict
```

### oracle_timestamp_provenance が残る

行動:

```text
known gap として扱う。
```

禁止:

```text
recv_ts_ms を oracle_ts_ms にする
source_ts_ms を oracle_ts_ms にする
oracle_freshness_proxy を oracle_ts_ms の代替にする
```

strict ready にする条件:

```text
根拠ある oracle timestamp source を実装する
provenance manifest を更新する
tests を追加する
recv/source/client timestamp の流用でないことを確認する
```

## 記録更新ルール

次のどれかが起きたら記録を更新する:

```text
24h cycle が正常完了した
cycle が途中停止した
次cycleを起動した
readiness の failing_requirements が変わった
24h smoke artifact の入力・出力・検証結果が変わった
backtest_data_ready が true になった
oracle timestamp provenance の方針を変えた
```

更新先:

```text
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
plan/TRADE_XYZ_BACKTEST_REAL_DATA_INGESTION_HANDOFF_2026-06-01.md
docs/TRADE_XYZ_QUOTE_COVERAGE_NEXT_STEPS_2026-06-04.md
.ai_memory/HANDOFF.md
```

ドキュメント更新時は Tokyo time を `YYYY-MM-DD_HH:mm JST` 形式で書く。

## やってはいけないこと

```text
起動中 collector を理由なく kill する
collector が生きている状態で次cycleを重複起動する
2026-05-30以前の実データをready判定に戻す
archive download を費用承認なしに実行する
source_ts_ms / recv_ts_ms / client timestamp を oracle_ts_ms として偽装する
signal candles を fill snapshot として使う
activeAssetCtx / trades を fill snapshot として使う
real market reference を live execution data として扱う
wallet / signing / exchange write API へ進む
strict gate 前に backtest_data_ready=true と言う
24h smoke metrics を strategy selection に使う
```

## 最短再開手順

再開したら、まずこれを実行する:

```bash
cd /home/tn/projects/marketlens-strike
ps -fp 2484910 || true
pstree -ap 2484910 || true
tail -120 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
find data/raw/quotes/trade_xyz -maxdepth 1 -type f -name '2026-06-0[45].jsonl' -print -exec wc -l {} \;
uv run sis trade-xyz-collection-status --strict
```

分岐:

```text
collector still running:
  待つ。
  並行して 24h WS smoke artifact を使った ingest/backtest 検証を進める。

collector exited:
  status の failing_requirements を見る。
  quote_coverage だけなら scripts/collect_trade_xyz_data_until_ready.sh を起動する。
  quote_coverage 以外が混じるなら自動ループさせず、その fail を先に直す。

smoke artifact を再確認したい:
  scripts/run_trade_xyz_backtest_smoke.py --ws-bbo-state を再実行する。
```

## 抜け・漏れ・誤謬リスク確認

確認済み:

```text
24h smoke は backtest_data_ready ではない
30日 quote coverage は別 gate
oracle timestamp provenance は known gap
BBO と activeAssetCtx の責任境界は分離
live / wallet / signing / exchange write は範囲外
collector 重複起動は禁止
```

残るリスク:

```text
collector が途中停止した場合、status更新前に次cycleを起動すると原因が見えにくくなる
2026-06-05_09:00 JST 以降はUTC日付が変わるため、2026-06-04.jsonlだけを見ると収集停止と誤認する
古い data/ops/trade_xyz_collection_status.json をそのまま読むと collector process 状態を誤認する
until-ready supervisor を使わず手動cycleだけを繰り返すと、非 quote_coverage の fail を見落としやすい
起動中 collector がある間に until-ready supervisor も起動すると、監視logとlockが増えて状態把握が紛らわしくなる
REST quote coverage collector と WS smoke artifact を混同すると、ready判定を誤る
3銘柄smoke成功を全11銘柄・全戦略の成功に一般化すると、実装リスクを見落とす
24h smoke metrics は少数取引なので性能評価に使うと誤解を生む
archive backfill は requester-pays / AWS preflight のリスクがあるため、費用承認なしに進めない
oracle timestamp は source payload に根拠がない限り解消しない
```
