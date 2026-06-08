<!--
作成日: 2026-06-04_06:42 JST
更新日: 2026-06-04_06:58 JST
-->

# Trade[XYZ] WS Raw to Backtest Ingestion Final Plan 2026-06-04

## 結論

この計画の実装ゴールは完了した。
3symbol 24時間の公式WebSocket raw dataを、純粋バックテストが再現可能に読める入力artifactへ変換する最小経路を実装・検証済みである。

WS取得基盤は実装開始readyである。
ただし、これは `backtest_data_ready=true` ではない。
この計画で完成させるのは、`data/raw/ws/trade_xyz_24h_20260602_1902/` から、BBO fill snapshot候補と `activeAssetCtx` signal/state候補を分離した正規化データ、manifest、bar入力候補、no-lookahead検証を作るところまでである。

既存実装として、次はすでに存在する。

```text
src/sis/venues/trade_xyz/normalizer.py
  quote_from_ws_bbo_row()
  quote_from_ws_active_asset_ctx_row()

src/sis/storage/normalize.py
  collect_trade_xyz_ws_quote_logs()
  normalize_trade_xyz_ws_quotes()

src/sis/commands/quotes.py
  sis normalize-trade-xyz-ws-quotes
```

この計画では、上記を v0.1 adapter として残し、次の不足分を実装した。

```text
1. DONE: output artifact contractを固定する
2. DONE: raw root / manifest / row count / dropped count / event time policyをmanifest化する
3. DONE: BBOとactiveAssetCtxを混ぜずにbar候補へ渡す
4. DONE: no-lookaheadをテストで固定する
5. DONE: run_backtest()へ渡せる最小smokeを作る
6. DONE: full backtest_data_readyとは別物として文書化する
```

## 完了結果

実装済み:

```text
src/sis/venues/trade_xyz/normalizer.py:
  quote_from_ws_bbo_row()
  quote_from_ws_active_asset_ctx_row()

src/sis/storage/normalize.py:
  collect_trade_xyz_ws_quote_logs()
  normalize_trade_xyz_ws_quotes()
  trade_xyz_ws_backtest_artifact_manifest.v1 出力

src/sis/commands/quotes.py:
  sis normalize-trade-xyz-ws-quotes

src/sis/backtest/trade_xyz/ws_ingestion.py:
  build_bbo_bars_with_active_asset_state()

tests/backtest/test_trade_xyz_ws_ingestion.py:
  no-lookahead asof join
  run_backtest() minimal smoke
```

24h root実行結果:

```text
raw_ws_root: data/raw/ws/trade_xyz_24h_20260602_1902
quote_count_written: 1113529
bbo_quote_count: 861859
active_asset_ctx_quote_count: 251670
trade_row_count_skipped: 89383
control_row_count_skipped: 81
duplicate_count_skipped: 3
malformed_count: 0
output_parquet_path: .tmp/trade_xyz_ws_quotes_24h.parquet
output_duckdb_path: .tmp/trade_xyz_ws_quotes_24h.duckdb
manifest_path: .tmp/trade_xyz_ws_quotes_24h.manifest.json
```

まだ `backtest_data_ready=true` ではない。
残る境界は、長期quote coverage、real market reference、oracle timestamp provenanceである。

最終検証:

```text
./scripts/check:
  pass
  Python 3.13.7
  ruff check: pass
  ruff format --check: 378 files already formatted
  current docs check: 81 current docs ok
  pyrefly: 0 errors
  pytest: 801 passed in 21.93s
```

## 目的

目的は、Trade[XYZ]公式WebSocketから取った実データを、バックテストで誤読しない形に変換することである。

完了後にできること:

```text
1. isolated raw rootから正規化quote parquetを再生成できる
2. bbo由来のbid/ask/mid/exec priceをfill snapshot候補として使える
3. activeAssetCtx由来のmark/oracle/mid/funding/OIをsignal/state候補として使える
4. activeAssetCtxをfill snapshotとして使わないことをテストで保証できる
5. recv_ts_ms/source_ts_msをoracle timestampとして偽装しないことをテストで保証できる
6. BBO-only bar fixtureを作り、既存backtest pathへ最小smokeできる
7. artifact manifestから、元raw root、対象symbol、row count、除外理由、時刻方針を追跡できる
```

目的ではないこと:

```text
1. backtest_data_ready=true の宣言
2. live/paper order、wallet、signing、exchange write API
3. 戦略成績の最適化
4. 2026-05-30以前のarchive data復活
5. allMidsをTrade[XYZ]/xyz価格正本にすること
6. tradesをfill snapshot正本にすること
7. oracle timestamp provenance gapの解消を装うこと
```

## 現在の確認済み入力

この計画の入力raw root:

```text
data/raw/ws/trade_xyz_24h_20260602_1902/
```

確認済み観測結果:

```text
duration_seconds: 86401.202231
row_count: 1202996
reconnect_count: 8
graceful_reconnect_count: 7
unexpected_reconnect_count: 1
error_count: 1
quality_status: pass
quality_gap_count: 0
quality_source_ts_gap_count: 0
malformed_payload_count: 0
unknown_symbol_count: 0
bbo_bid_ask_inversion_count: 0
rest_parity_status: pass
rest_request_error_count: 0
missing_ws_symbols: []
missing_rest_symbols: []
mismatched_symbols: []
```

`unexpected_reconnect_count=1` と `error_count=1` は、約1.074秒のtransport reconnectで、60秒超のquote/state gapを作っていないため、WS取得v0.1としては受容済みである。
ただし、これは full `backtest_data_ready` を意味しない。

## 制約

### Hard Rules

実装者は次を破ってはいけない。

```text
1. `backtest_data_ready=true` と書かない
2. live order / paper order / wallet / signing / exchange write APIに触れない
3. 2026-05-30以前の実データをreadiness根拠へ戻さない
4. `recv_ts_ms` を `oracle_ts_ms` として使わない
5. `source_ts_ms` を `oracle_ts_ms` として使わない
6. activeAssetCtxをfill snapshotとして使わない
7. tradesをfill snapshotとして使わない
8. BBO fill fieldsとactiveAssetCtx state fieldsを同じ意味で扱わない
9. raw root指定なしで古い `data/raw/ws/trade_xyz/` と混ぜない
10. generated artifactを作るときは、source raw rootをmanifestに必ず残す
```

### 時刻方針

BBO:

```text
source_ts_ms:
  payload.data.time 由来で使える

recv_ts_ms:
  受信時刻として保持する

event time:
  初期bar fixtureでは source_ts_ms を優先する
```

activeAssetCtx:

```text
source_ts_ms:
  現payloadでは明示source timestampがない

recv_ts_ms:
  観測時刻としてだけ保持する

oracle_ts_ms:
  設定しない

event time:
  signal/state asof joinで使う場合も「観測時刻」であり、oracle/source時刻ではない
```

### データ分離方針

最初のartifactは、論理的に2種類へ分ける。

```text
fill snapshot candidate:
  source = trade_xyz_ws_bbo
  required fields = best_bid, best_ask, mid_price, exec_buy_price, exec_sell_price

signal/state candidate:
  source = trade_xyz_ws_activeAssetCtx
  required fields = mark_price, oracle_price, index_price, mid_price, funding_rate, open_interest_usd
  required non-fill behavior = is_tradable=false, BLOCK_NO_BBO_FILL_SNAPSHOT
```

1つのparquetに保存する場合でも、`source` と `is_tradable` と fill field有無で責務を分ける。
bar化では、BBO-only baselineを先に完成させ、その後に activeAssetCtx stateをasof joinする。

## 対象ファイル

### 既存ファイル

主に触るファイル:

```text
src/sis/storage/normalize.py
src/sis/commands/quotes.py
tests/test_trade_xyz_collector.py
tests/test_cli_smoke.py
```

確認だけでよいファイル:

```text
src/sis/venues/trade_xyz/normalizer.py
src/sis/backtest/trade_xyz/market_data.py
src/sis/backtest/trade_xyz/bar_builder.py
src/sis/backtest/engine/runner.py
tests/test_trade_xyz_normalizer.py
tests/backtest/test_trade_xyz_market_data.py
tests/backtest/test_trade_xyz_bar_builder.py
schemas/trade_xyz_ws_raw.v1.schema.json
schemas/trade_xyz_ws_capture_manifest.v1.schema.json
schemas/trade_xyz_ws_quality_manifest.v1.schema.json
schemas/trade_xyz_rest_parity_manifest.v1.schema.json
```

ドキュメント更新候補:

```text
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
plan/TRADE_XYZ_BACKTEST_REAL_DATA_INGESTION_HANDOFF_2026-06-01.md
.ai_memory/HANDOFF.md
```

### 新規ファイル候補

必要なら追加する。

```text
src/sis/backtest/trade_xyz/ws_ingestion.py
tests/backtest/test_trade_xyz_ws_ingestion.py
schemas/trade_xyz_ws_backtest_artifact_manifest.v1.schema.json
```

ただし、`src/sis/storage/normalize.py` の既存関数で十分なら、新規moduleを増やさない。
manifest schemaも、既存JSON出力とテストで十分なら追加しない。

## 実装タスク

### T0: Read-only Preflight

目的:

```text
現在の入力raw root、manifest、CLI surface、未コミット差分を確認する。
```

実行:

```bash
git status --short --branch
python3 -c "import json; q=json.load(open('data/manifests/trade_xyz_ws_quality_manifest.json')); r=json.load(open('data/manifests/trade_xyz_rest_parity_manifest.json')); print({'quality_status': q['status'], 'rest_status': r['status'], 'row_count': q['row_count']})"
uv run sis normalize-trade-xyz-ws-quotes --help
```

受け入れ条件:

```text
quality_status=pass
rest_status=pass
row_count=1202996
CLI helpに normalize-trade-xyz-ws-quotes が出る
作業前の未コミット差分を把握している
```

失敗時:

```text
manifestがpassでない場合は、ingestion実装へ進まない。
まずmanifest生成元raw rootを確認する。
```

### T1: Adapter Contractを固定する

目的:

```text
既存のWS row -> QuoteLog変換を仕様として固定する。
```

対象:

```text
src/sis/venues/trade_xyz/normalizer.py
tests/test_trade_xyz_normalizer.py
```

確認・追加する期待値:

```text
bbo:
  source == trade_xyz_ws_bbo
  best_bid == payload.data.bbo[0].px
  best_ask == payload.data.bbo[1].px
  mid_price == (best_bid + best_ask) / 2
  exec_buy_price == best_ask
  exec_sell_price == best_bid
  source_ts_ms == payload.data.time
  recv_ts_ms is preserved
  oracle_ts_ms is None

activeAssetCtx:
  source == trade_xyz_ws_activeAssetCtx
  mark_price == ctx.markPx
  oracle_price == ctx.oraclePx
  index_price or mid_price includes ctx.midPx
  funding_rate == ctx.funding
  open_interest_usd == ctx.openInterest
  is_tradable == false
  block_reasons contains BLOCK_NO_BBO_FILL_SNAPSHOT
  best_bid / best_ask / exec_buy_price / exec_sell_price are None
  oracle_ts_ms is None
```

受け入れ条件:

```bash
uv run pytest -q tests/test_trade_xyz_normalizer.py
```

### T2: Raw Root Loaderを安定化する

目的:

```text
raw root配下のJSONLを決定的に読み、対象subscriptionだけQuoteLog化する。
```

対象:

```text
src/sis/storage/normalize.py
tests/test_trade_xyz_collector.py
```

実装要件:

```text
1. sorted(raw_ws_root.rglob("*.jsonl")) で決定的に読む
2. subscription == bbo は quote_from_ws_bbo_row() へ渡す
3. subscription == activeAssetCtx は quote_from_ws_active_asset_ctx_row() へ渡す
4. subscription == trades はこのv0.1正規化ではスキップする
5. __control__ / subscriptionResponse / pong はスキップする
6. message_kind != data はスキップする
7. payload parse不能行は、黙って壊れたQuoteLogにせず例外またはdropped reasonへ回す
8. raw_payload_ref は path#row=N を持つ
9. asset_id / real_market_symbol / fee metadata は registryがあれば補完する
10. 重複排除する場合は key と dropped count をmanifestへ残す
```

Better案:

```text
現状の collect_trade_xyz_ws_quote_logs() はlistを返す。
24h rootは約1.1Gあるため、将来はstreaming writeへ寄せる余地がある。
ただし今回の完了条件では、まず現在のlist実装をテストで固定し、必要なら別タスクでstreaming化する。
```

受け入れ条件:

```bash
uv run pytest -q tests/test_trade_xyz_collector.py -k "ws_quotes or normalize_trade_xyz_ws_quotes"
```

### T3: Output Artifact Contractを実装する

目的:

```text
正規化parquetだけでなく、再生成条件を説明するmanifestを出す。
```

推奨出力先:

```text
data/normalized/trade_xyz_ws_24h_20260602_1902/quotes.parquet
data/normalized/trade_xyz_ws_24h_20260602_1902/quotes.duckdb
data/normalized/trade_xyz_ws_24h_20260602_1902/manifest.json
```

CLI defaultは既存互換のままでもよい。
24h実行では必ず明示pathを使う。

```bash
uv run sis normalize-trade-xyz-ws-quotes \
  --raw-ws-root data/raw/ws/trade_xyz_24h_20260602_1902 \
  --parquet-path data/normalized/trade_xyz_ws_24h_20260602_1902/quotes.parquet \
  --duckdb-path data/normalized/trade_xyz_ws_24h_20260602_1902/quotes.duckdb \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA
```

manifest必須field:

```text
schema_version: trade_xyz_ws_backtest_artifact_manifest.v1
created_at
raw_ws_root
quality_manifest_path
rest_parity_manifest_path
symbols
subscriptions_included
subscriptions_excluded
row_count_raw_seen
quote_count_written
bbo_quote_count
active_asset_ctx_quote_count
trade_row_count_skipped
control_row_count_skipped
duplicate_count_skipped
malformed_count
event_time_policy
oracle_timestamp_policy
fill_snapshot_policy
output_parquet_path
output_duckdb_path
```

受け入れ条件:

```text
manifestが存在する
raw_ws_rootが data/raw/ws/trade_xyz_24h_20260602_1902 を指す
quote_count_written > 0
bbo_quote_count > 0
active_asset_ctx_quote_count > 0
oracle_timestamp_policy が recv_ts_ms/source_ts_msをoracle_ts_msにしないと明記する
```

### T4: Backtest Market Data入力へ接続する

目的:

```text
正規化quote parquetを既存の prepare_quote_rows_for_backtest() / build_quote_bars() へ渡せることを固定する。
```

対象:

```text
src/sis/backtest/trade_xyz/market_data.py
src/sis/backtest/trade_xyz/bar_builder.py
tests/backtest/test_trade_xyz_market_data.py
tests/backtest/test_trade_xyz_bar_builder.py
tests/backtest/test_trade_xyz_ws_ingestion.py
```

初期方針:

```text
1. BBO-only baseline barを先に作る
2. close_source は mid_price を使う
3. event_time_source は source_ts_ms を使う
4. fill fieldsはBBO由来の best_bid / best_ask / exec_buy_price / exec_sell_price を使う
5. activeAssetCtxはこの段階ではbarへ混ぜない
```

受け入れ条件:

```text
BBO fixtureからbarが作れる
bar_builder == quote_bar_v1
fill_best_bid / fill_best_ask / fill_exec_buy_price / fill_exec_sell_price が埋まる
signal_source と fill_source が説明可能
```

検証:

```bash
uv run pytest -q tests/backtest/test_trade_xyz_market_data.py tests/backtest/test_trade_xyz_bar_builder.py
```

### T5: activeAssetCtx Asof Joinを追加する

目的:

```text
BBO fill snapshotとactiveAssetCtx stateを、未来情報なしでbar候補へ併合する。
```

実装方針:

```text
1. BBO barを基準にする
2. activeAssetCtx stateは、bar close時刻以前に観測済みの最後のrowだけをjoinする
3. bar closeより後のactiveAssetCtxを使わない
4. activeAssetCtx.recv_ts_msは観測時刻として使うが、oracle timestampとは呼ばない
5. join後も fill_source は bbo のままにする
6. join後の state fields は mark/oracle/index/funding/OI として別prefixで持つ
```

推奨field:

```text
state_observed_ts_ms
state_source
state_mark_price
state_oracle_price
state_index_price
state_funding_rate
state_open_interest_usd
```

禁止field:

```text
oracle_ts_ms derived from recv_ts_ms
oracle_ts_ms derived from source_ts_ms
fill_best_bid derived from activeAssetCtx
fill_best_ask derived from activeAssetCtx
```

必須テスト:

```text
1. bar closeより後のactiveAssetCtx rowがjoinされない
2. bar closeと同時刻または以前の最新activeAssetCtx rowだけjoinされる
3. activeAssetCtxしかないsymbol/time bucketではfill fieldsが埋まらない
4. oracle_priceは値として保持するが、oracle_ts_msはNoneのまま
```

検証:

```bash
uv run pytest -q tests/backtest/test_trade_xyz_ws_ingestion.py
```

### T6: CLI Smokeを固定する

目的:

```text
実装者以外でもCLIで再生成できることを固定する。
```

対象:

```text
src/sis/commands/quotes.py
tests/test_cli_smoke.py
```

必要ならCLIに追加するoption:

```text
--manifest-path
--fail-on-malformed / --allow-malformed
--include-subscriptions
--exclude-subscriptions
```

ただし、初期実装ではoptionを増やしすぎない。
明示pathで24h rootを渡せること、output pathを表示すること、manifestを書けることを優先する。

受け入れ条件:

```bash
uv run pytest -q tests/test_cli_smoke.py -k normalize_trade_xyz_ws_quotes
```

CLI smoke expected output:

```text
quote_count=<positive integer>
raw_ws_root=<explicit raw root>
normalized_ws_quotes_path=<explicit parquet path>
duckdb_path=<explicit duckdb path>
manifest_path=<manifest path>
```

### T7: run_backtest()最小Smoke

目的:

```text
生成したBBO-only bar fixtureが、既存backtest runnerへ渡せることだけ確認する。
```

対象:

```text
src/sis/backtest/engine/runner.py
tests/backtest/
```

やること:

```text
1. 小さなfixtureでBBO quote rowsを作る
2. prepare_quote_rows_for_backtest() でevent_ts/closeを作る
3. build_quote_bars() でbarへ変換する
4. 既存runnerが必要とするmarket data shapeへ渡す
5. 結果の損益や戦略品質ではなく、shapeとno exceptionだけを見る
```

やらないこと:

```text
1. strategy performanceを評価しない
2. 24h実データ全体でheavy testをCIに入れない
3. live readinessと混同しない
```

受け入れ条件:

```text
focused smoke testがpassする
CIで1秒から数秒程度に収まる小fixtureを使う
```

### T8: Docs / Handoff更新

目的:

```text
次の作業者が、どこまで完了したか、何をreadyと言ってよいかを誤読しないようにする。
```

更新対象:

```text
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
plan/TRADE_XYZ_BACKTEST_REAL_DATA_INGESTION_HANDOFF_2026-06-01.md
.ai_memory/HANDOFF.md
```

書くこと:

```text
1. normalize-trade-xyz-ws-quotes の実行コマンド
2. generated artifact paths
3. manifest path
4. quote_count / bbo_quote_count / active_asset_ctx_quote_count
5. tests run
6. full backtest_data_ready remains false
7. 次のRestart Contract action
```

禁止:

```text
docsだけ更新してtestsを回さず完了扱いにしない
artifactだけ作ってsource raw rootを書かず完了扱いにしない
```

## テスト方針

### Focused Tests

```bash
uv run pytest -q tests/test_trade_xyz_normalizer.py
uv run pytest -q tests/test_trade_xyz_collector.py -k "ws_quotes or normalize_trade_xyz_ws_quotes"
uv run pytest -q tests/test_cli_smoke.py -k normalize_trade_xyz_ws_quotes
uv run pytest -q tests/backtest/test_trade_xyz_market_data.py tests/backtest/test_trade_xyz_bar_builder.py
uv run pytest -q tests/backtest/test_trade_xyz_ws_ingestion.py
```

### Static / Formatting

```bash
uv run ruff check src/sis tests
uv run ruff format --check src/sis tests
uv run python scripts/check_current_docs.py
```

### Broad Gate

最後は必ず実行する。

```bash
./scripts/check
```

### テストデータ方針

CIテストでは、24h raw root全体を読まない。
小さなJSONL fixtureを使う。
24h root全体を読むのは、手動確認またはartifact生成コマンドだけにする。

必須fixture:

```text
1. valid bbo row
2. valid activeAssetCtx row
3. control subscriptionResponse row
4. trades row
5. duplicate bbo row
6. malformed payload row
7. activeAssetCtx row after bar close
8. activeAssetCtx row before bar close
```

## 完了条件

この計画は、次をすべて満たしたら完了である。

```text
1. `sis normalize-trade-xyz-ws-quotes` が明示raw rootから正規化artifactを作れる
2. output parquet / duckdb / manifest が生成される
3. manifestが source raw root と source manifests を指す
4. manifestに row count / dropped count / duplicate count / malformed count がある
5. BBO rowがfill snapshot候補として必要fieldを持つ
6. activeAssetCtx rowがsignal/state候補として必要fieldを持つ
7. activeAssetCtx rowがfill snapshotにならない
8. recv_ts_ms/source_ts_msがoracle_ts_msへ転用されない
9. BBO-only bar fixtureが作れる
10. activeAssetCtx asof joinが未来情報を使わない
11. run_backtest()最小smokeがpassする
12. docsとHANDOFFに実行コマンド、artifact path、テスト結果が残る
13. `./scripts/check` がpassする
14. `backtest_data_ready=true` を宣言していない
```

## 抜け、漏れ、誤謬リスクと修正方針

### Risk 1: 古いraw root混入

問題:

```text
data/raw/ws/trade_xyz/ には過去runがあり得る。
明示せずdefault rootを使うと、isolated 24h runと混ざる。
```

修正:

```text
24h artifact生成では必ず --raw-ws-root data/raw/ws/trade_xyz_24h_20260602_1902 を指定する。
manifestにも raw_ws_root を保存する。
```

### Risk 2: activeAssetCtxをfillに使う

問題:

```text
activeAssetCtxにはmark/oracle/midがあるため、誤って約定価格として使いやすい。
```

修正:

```text
activeAssetCtx normalizerは is_tradable=false と BLOCK_NO_BBO_FILL_SNAPSHOT を維持する。
bar/asof join後も fill fields はBBO由来だけにする。
```

### Risk 3: oracle timestamp偽装

問題:

```text
activeAssetCtxにoraclePxはあるが、oracle timestampはない。
recv_ts_msをoracle_ts_msにすると、provenance gapを偽って解消したことになる。
```

修正:

```text
oracle_priceは保持してよい。
oracle_ts_msはNoneのままにする。
テストで recv_ts_ms/source_ts_ms が oracle_ts_ms に入らないことを固定する。
```

### Risk 4: tradesをcoverage証明に使う

問題:

```text
tradesは低流動で自然にgapが出る。
tradesだけでquote coverageやfill readinessを判断すると誤る。
```

修正:

```text
v0.1ではtradesをnormalize targetから除外し、manifestにskipped countとして残す。
将来使う場合もactivity reference扱いにする。
```

### Risk 5: no-lookahead不足

問題:

```text
bar close後のactiveAssetCtxをjoinすると、未来情報を戦略へ渡す。
```

修正:

```text
asof joinは bar close時刻以前の最後のstateだけを使う。
未来stateがjoinされないテストを必須にする。
```

### Risk 6: 24h全量をCIで読む

問題:

```text
24h raw rootは約1.1Gであり、CIや通常testへ入れると遅く不安定になる。
```

修正:

```text
CIは小fixtureだけ使う。
全量artifact生成は手動コマンドで行い、manifestで再現性を確認する。
```

### Risk 7: adapter実装済み部分と計画のズレ

問題:

```text
すでに normalize-trade-xyz-ws-quotes が追加されている。
計画が新規module前提だけになると、既存差分と衝突する。
```

修正:

```text
既存adapterをv0.1として尊重する。
不足が明確な場合だけ src/sis/backtest/trade_xyz/ws_ingestion.py を追加する。
```

## 最終採用方針

最終採用する方針は次である。

```text
1. API-firstではなく、現時点のCLI付きadapterをv0.1として安定化する
2. BBOとactiveAssetCtxは同一parquetに入っても責務を混ぜない
3. BBO-only bar baselineを先に完成させる
4. activeAssetCtxはasof state joinとして後段に追加する
5. manifestを必須にして、raw rootと除外理由を追跡可能にする
6. 24h全量はCIに入れず、小fixtureで契約を固定する
7. 最後に `./scripts/check` で全体確認する
8. full backtest_data_readyは別gateに残す
```

この方針がBetterである理由:

```text
1. 既存実装を活かすため、差分が小さい
2. fillとsignal/stateの責務分離を崩さない
3. no-lookaheadを先にテストで固定できる
4. artifact manifestにより、将来の再開時にraw root混入を防げる
5. live/paper/order系へ波及しない
```
