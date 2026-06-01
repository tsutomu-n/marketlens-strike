<!--
作成日: 2026-06-01_18:44 JST
更新日: 2026-06-01_19:04 JST
-->

# Trade[XYZ] WS Smoke後のData Ready到達計画 2026-06-01

## 結論

次にやるべきことは、戦略最適化ではなく、**read-only実データ収集の信頼性を段階的に上げること**である。

2026-06-01_18:44 JST 時点では、`SP500` の1分WebSocket smokeは成功している。
ただし、これは実務バックテストreadyを意味しない。確認済みなのは、次の狭い範囲だけである。

```text
確認済み:
  symbol:
    - SP500

  duration:
    - 1 minute

  subscriptions:
    - bbo
    - trades
    - activeAssetCtx

  output:
    - .tmp/trade_xyz_ws_smoke/

  WS capture:
    row_count: 170
    reconnect_count: 0
    error_count: 0
    subscription_response_count: 3
    pong_count: 0
    heartbeat_sent_count: 0

  WS quality:
    status: pass
    row_count: 170
    duplicate_payload_count: 26
    gap_count: 0
    source_ts_gap_count: 0
    malformed_payload_count: 0
    unknown_symbol_count: 0

  REST parity:
    status: pass
    request_error_count: 0
    request_count: 5
    missing_ws_symbols: []
    missing_rest_symbols: []
    mismatched_symbols: []
    known_gap_count: 0
```

`duplicate_payload_count=26` は、`activeAssetCtx` が同じctxを自然に再送する実payloadを確認したため、単独ではwarnにしない。
ただし、値は観測情報としてmanifestに残す。

追加調査後の現実的な補正:

```text
1. 1分smokeのpassは、長時間安定性の証明ではない
2. WebSocket forward captureは過去のquote coverageを埋めない
3. real_market_reference failはWS収集では解決しない
4. oracle timestamp provenanceは、payloadに明示fieldが無い限りknown gapのまま
5. 低流動時間帯のheartbeatは、現コードのままでは不十分な可能性がある
6. allMidsはdex指定なしだとTrade[XYZ]/xyz dexを見ている保証が弱い
7. reconnectが発生したrunは、欠損補完できるまでdata-ready判定に使わない
```

## この計画の正本

実装・運用判断は次の順で行う。

```text
1. src/ の現行コード
2. tests/ の現行期待値
3. schemas/ の現行契約
4. configs/ の現行設定
5. `uv run sis ... --help` の現行CLI surface
6. data/manifests/ の最新artifact
7. docs/ と plan/ の説明
```

この文書は、次の作業を安全に進めるための実行計画であり、コードより優先しない。
コード、schema、CLI helpと矛盾した場合は、実装前にこの文書を更新する。

## 目的

Trade[XYZ]純粋バックテストへ流す実データについて、次を満たす状態まで進める。

```text
1. 公式WebSocket raw captureが複数symbolで安定して取れる
2. capture / quality / REST parity manifestで、欠損・切断・重複・symbol不一致を説明できる
3. raw WS data と既存 raw quotes を混ぜずに保存できる
4. source timestamp と receive timestamp を混同しない
5. 2026-05-30以前の実データをreadinessへ戻さない
6. `run_backtest()` へ流す前に、使えるデータと使えないデータを明確に分ける
```

この計画の目的は、Trade[XYZ]実データを誤読しないことである。
成績の良い戦略を探すことではない。

## 実データ取得の基本方針

実データ取得は、理想論として「集められるものを全部集める」ではなく、
**backtestで誤読しないために必要なデータを、正本・補助・対象外に分けて積み上げる**。

```text
正本候補:
  Hyperliquid / Trade[XYZ] official REST
  Hyperliquid / Trade[XYZ] official WebSocket

補助:
  real market reference
  external underlying reference
  OSS client経由のcross-check
  historical archive metadata

対象外:
  2026-05-30以前の実データ
  recv_ts_msをsource/oracle timestamp扱いしたデータ
  external referenceをTrade[XYZ] fill/mark/oracle代替にしたデータ
  出所・時刻・取得条件をmanifestで説明できないデータ
```

最初に完成させる実データ範囲:

```text
market micro data:
  - bbo
  - trades
  - activeAssetCtx

pricing / state:
  - markPx
  - oraclePx
  - midPx
  - funding
  - openInterest
  - impactPxs

cost / account:
  - symbol fee
  - account-specific fee
  - funding history

cross-check:
  - real market reference
  - session / holiday / reference market status
```

この段階で正本化しないもの:

```text
allMids:
  dex=xyzの扱いを実装・確認するまで正本にしない。

l2Book:
  raw shape確認まで。
  L2 replay、sweep-depth、fill model接続は別計画。

external reference:
  Trade[XYZ]価格の穴埋めに使わない。
  underlying/reference/cross-checkに限る。

historical archive:
  5/30以前のデータは戻さない。
  5/31以降の取得可能性・manifest・costだけ別途検討する。
```

実データ取得の完成形:

```text
1. data/raw/ws/trade_xyz/ に公式WS rawを保存する
2. data/raw/quotes/trade_xyz/ と混ぜない
3. capture / quality / REST parity manifest を毎run残す
4. reconnect / error / gap / malformed / unknown_symbol を説明できる
5. bbo / trades / activeAssetCtx を別subscriptionとして保存する
6. mark/oracle/funding/OI は activeAssetCtx 由来として扱う
7. external reference は補助として別manifestに残す
8. 2026-05-30以前の実データをreadinessへ戻さない
9. `run_backtest()` へ渡す前に、Current Real Data Contractを実payloadに合わせて更新する
10. data-ready判定は manifest と tests で再現できる
```

## 公式Docsとの照合で確定した制約

2026-06-01_18:52 JST 時点で、Hyperliquid公式Docsと照合した実務上の制約。

```text
WebSocket URL:
  mainnet は wss://api.hyperliquid.xyz/ws

subscription format:
  { "method": "subscribe", "subscription": { ... } }

subscriptionResponse:
  subscription成功時に返る

切断:
  automated userはserver側disconnectを想定し、graceful reconnectが必要

heartbeat:
  60秒以上messageが無いconnectionはserverがcloseし得る
  heartbeatは { "method": "ping" } を送る
  responseは { "channel": "pong" }

rate limit:
  websocket connection上限は10
  new websocket connection上限は30/min
  websocket subscription上限は1000
  websocket送信message上限は2000/min
  REST infoの集約weight上限は1200/min

allMids:
  dex fieldがあり、未指定の場合はfirst perp dex扱い
  Trade[XYZ]/xyz用途ではdex指定の扱いを確認するまで正本にしない

info endpoint:
  time range responseは500件またはdistinct blocks上限がある
  長い期間はpaginationが必要
```

参照:

```text
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/timeouts-and-heartbeats
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
```

## 制約

### 絶対にしないこと

```text
live order:
  しない

paper execution:
  変更しない

wallet / signing:
  触らない

exchange write:
  しない

backtest engine:
  この計画では変更しない

strategy optimization:
  しない

short / leverage:
  しない

multi-symbol backtest:
  この計画では実装しない

L2 replay:
  この計画では実装しない

MT5 / IC Markets / CFD:
  スコープ外
```

### 実データの使用禁止範囲

2026-05-30以前の実データは、現在のTrade[XYZ] backtest/readinessには使わない。

```text
archive root:
  data/archive/pre_2026_05_31_unusable_real_data/

archive manifest:
  data/archive/pre_2026_05_31_unusable_real_data/ARCHIVE_MANIFEST.json

policy:
  All real data dated 2026-05-30 or earlier is unusable for current Trade[XYZ] backtest/readiness work and must remain archived.
```

### 保存境界

```text
既存REST quote raw:
  data/raw/quotes/trade_xyz/

WebSocket raw:
  data/raw/ws/trade_xyz/

一時smoke:
  .tmp/trade_xyz_ws_smoke/
  .tmp/trade_xyz_ws_smoke_multi_symbol/
  .tmp/trade_xyz_ws_smoke_15m/

manifest:
  data/manifests/trade_xyz_ws_capture_manifest.json
  data/manifests/trade_xyz_ws_quality_manifest.json
  data/manifests/trade_xyz_rest_parity_manifest.json
```

WS raw と既存 raw quotes は混ぜない。
normalizerが読む対象を変える場合は、必ず別計画に分ける。

## 現在の対象ファイル

### 既に実装済みで、次工程でも使うファイル

```text
src/sis/commands/quotes.py
src/sis/venues/trade_xyz/ws_envelope.py
src/sis/venues/trade_xyz/ws_recorder.py
src/sis/venues/trade_xyz/ws_quality.py
src/sis/venues/trade_xyz/rest_parity.py
src/sis/venues/trade_xyz/client.py
src/sis/venues/trade_xyz/collection_config.py

schemas/trade_xyz_ws_raw.v1.schema.json
schemas/trade_xyz_ws_capture_manifest.v1.schema.json
schemas/trade_xyz_ws_quality_manifest.v1.schema.json
schemas/trade_xyz_rest_parity_manifest.v1.schema.json

configs/trade_xyz_data_collection.yaml
data/registry/trade_xyz_instrument_registry.json

tests/test_trade_xyz_ws_envelope.py
tests/test_trade_xyz_ws_raw_schema.py
tests/test_trade_xyz_ws_recorder.py
tests/test_trade_xyz_ws_quality.py
tests/test_trade_xyz_rest_parity.py
tests/test_trade_xyz_ws_cli.py
tests/test_trade_xyz_collection_config.py
tests/test_trade_xyz_client.py
tests/test_trade_xyz_collection_status.py
tests/test_cli_help_contract.py
```

### この計画で変更してよい候補

変更する場合は、必ず近接テストを先に追加する。

```text
src/sis/venues/trade_xyz/ws_quality.py:
  長時間/複数symbol smokeで誤検知が出た場合のみ、quality判定を調整する。

src/sis/venues/trade_xyz/ws_recorder.py:
  実payloadでsymbol解決やheartbeat/reconnect監査に不足が見つかった場合のみ変更する。

src/sis/venues/trade_xyz/rest_parity.py:
  REST snapshotとWS captureの比較粒度を増やす場合のみ変更する。

src/sis/commands/quotes.py:
  CLI optionが足りない場合のみ追加する。

schemas/*.json:
  manifest fieldを増やす場合のみ更新する。

tests/test_trade_xyz_*.py:
  すべての挙動変更に対応するテストを追加する。
```

### この計画では変更しないファイル

```text
src/sis/backtest/**
src/sis/execution/**
src/sis/paper/**
src/sis/risk/**
src/sis/research/strategy_lab/**
```

backtest、execution、paper、wallet、signingへ波及する変更が必要になったら、この計画を止める。

## コーダー向けタスク分解

この章を上から順に実行する。
各タスクは、対象ファイル、作業内容、テスト、完了条件、停止条件を持つ。
タスクを飛ばして後段へ進まない。

### T0: baseline確認

目的:
  現在のmainが、WS smoke後の最新状態であることを確認する。

対象ファイル:

```text
なし
```

実行:

```bash
git status --short --branch
git log -1 --oneline --decorate
uv run pytest -q tests/test_trade_xyz_ws_quality.py
uv run python scripts/check_current_docs.py
```

完了条件:

```text
1. HEAD が origin/main と一致している
2. 作業ツリーに意図しない差分がない
3. test_trade_xyz_ws_quality.py がpass
4. current docs checkがpass
```

停止条件:

```text
1. 未コミット差分がある
2. HEADが想定外
3. docs checkがfail
```

### T1: application-level heartbeat実装

目的:
  Hyperliquid公式Docsに合わせ、低流動時もserver timeoutを避けられるheartbeatにする。

対象ファイル:

```text
src/sis/venues/trade_xyz/ws_recorder.py
tests/test_trade_xyz_ws_recorder.py
schemas/trade_xyz_ws_capture_manifest.v1.schema.json
```

作業内容:

```text
1. timeout時に WebSocket protocol ping ではなく `{ "method": "ping" }` をsendする
2. 実際に受け取った `{ "channel": "pong" }` をcontrol rowとして保存する
3. synthetic pongを作る場合は、実pongと区別できるfieldを入れる
4. heartbeat_sent_count は送信したapplication pingの数として扱う
5. pong_count は受信したpong rowの数として扱う
6. manifest schemaにfield追加が必要ならschemaとtestsを同時更新する
```

テスト:

```bash
uv run pytest -q tests/test_trade_xyz_ws_recorder.py
uv run pytest -q tests/test_trade_xyz_ws_cli.py tests/test_cli_help_contract.py
uv run ruff check src/sis/venues/trade_xyz/ws_recorder.py tests/test_trade_xyz_ws_recorder.py
uv run ruff format --check src/sis/venues/trade_xyz/ws_recorder.py tests/test_trade_xyz_ws_recorder.py
```

完了条件:

```text
1. fake connection testで `{ "method": "ping" }` 送信を検証している
2. pong受信がcontrol rowとして保存される
3. heartbeat_sent_count と pong_count の意味がテストで固定されている
4. websocket protocol pingだけに依存していない
5. 既存WS recorder testsがpass
```

停止条件:

```text
1. websockets clientのtest doubleが複雑になりすぎる
2. 実pongとsynthetic pongを区別できない
3. manifest schemaと実manifestがずれる
```

停止した場合:
  heartbeatだけの小計画に分離し、CLIやsmokeへ進まない。

### T2: heartbeat smoke

目的:
  application-level heartbeat実装後に、実WSでpongを観測できるか確認する。

対象ファイル:

```text
コード変更なし
生成物:
  .tmp/trade_xyz_ws_heartbeat_smoke/
  data/manifests/trade_xyz_ws_capture_manifest.json
  data/manifests/trade_xyz_ws_quality_manifest.json
```

実行:

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500 \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 2 \
  --heartbeat-seconds 5 \
  --output-dir .tmp/trade_xyz_ws_heartbeat_smoke \
  --write-control-messages

uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root .tmp/trade_xyz_ws_heartbeat_smoke \
  --recv-gap-threshold-seconds 60 \
  --source-gap-threshold-seconds 60
```

確認:

```bash
jq '{row_count, error_count, reconnect_count, heartbeat_sent_count, pong_count}' \
  data/manifests/trade_xyz_ws_capture_manifest.json
jq '{status, row_count, pong_count, gap_count, malformed_payload_count, unknown_symbol_count}' \
  data/manifests/trade_xyz_ws_quality_manifest.json
```

完了条件:

```text
1. commandがexit 0
2. error_count == 0
3. reconnect_count == 0
4. heartbeat_sent_count と pong_count が説明可能
5. quality status == pass
```

停止条件:

```text
1. pongが一度も返らず、低流動時のtimeout対策を確認できない
2. heartbeat送信後にserver disconnectが起きる
3. heartbeat rowがschema validationを壊す
```

### T3: 複数symbol 1分smoke

目的:
  symbol解決、subscriptionResponse、path partitionを複数symbolで確認する。

対象ファイル:

```text
コード変更なし
生成物:
  .tmp/trade_xyz_ws_smoke_multi_symbol/
  data/manifests/*.json
```

実行:
  Phase 1 のコマンドをそのまま使う。

完了条件:

```text
1. subscription_response_count >= 9
2. error_count == 0
3. reconnect_count == 0
4. unknown_symbol_count == 0
5. malformed_payload_count == 0
6. bbo/trades/activeAssetCtx のsymbol別pathが作られる
7. REST parity status == pass
```

停止条件:

```text
1. どれかのsymbolがREST parityからmissingになる
2. path partitionがsymbolごとに分かれない
3. tradesが少ないことを欠損と誤判定している
```

### T4: 15分smokeと保存量見積もり

目的:
  長時間前に、row_count、bytes_written、disk usage、duplicate傾向を確認する。

対象ファイル:

```text
コード変更なし
生成物:
  .tmp/trade_xyz_ws_smoke_15m/
  data/manifests/*.json
```

実行:
  Phase 2 のコマンドをそのまま使う。

追加確認:

```bash
du -sh .tmp/trade_xyz_ws_smoke_15m
jq '{row_count, bytes_written, connection_count, reconnect_count, error_count, raw_paths}' \
  data/manifests/trade_xyz_ws_capture_manifest.json
jq '{status, subscription_counts, symbol_counts, duplicate_payload_count, gap_count, source_ts_gap_count}' \
  data/manifests/trade_xyz_ws_quality_manifest.json
```

完了条件:

```text
1. quality status == pass
2. reconnect_count == 0
3. error_count == 0
4. disk usageが記録されている
5. 60分runへ進める保存量である
```

停止条件:

```text
1. 保存量が想定を大きく超える
2. activeAssetCtx duplicate以外の重複が大量に出る
3. gap_count > 0 を説明できない
4. source_ts_gap_count > 0 を説明できない
```

### T5: 60分smoke

目的:
  3symbolの1時間収集で、日常運用の最小単位が成立するか見る。

対象ファイル:

```text
コード変更なし
生成物:
  .tmp/trade_xyz_ws_smoke_60m/
  data/manifests/*.json
```

実行:

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 60 \
  --output-dir .tmp/trade_xyz_ws_smoke_60m \
  --write-control-messages

uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root .tmp/trade_xyz_ws_smoke_60m \
  --recv-gap-threshold-seconds 60 \
  --source-gap-threshold-seconds 60

uv run sis build-trade-xyz-rest-parity \
  --symbols SP500,XYZ100,NVDA \
  --ws-manifest-path data/manifests/trade_xyz_ws_capture_manifest.json \
  --request-delay-seconds 0.2 \
  --skip-l2-book
```

完了条件:

```text
1. quality status == pass
2. REST parity status == pass
3. reconnect_count == 0
4. error_count == 0
5. row_count / bytes_written / disk usageを記録している
```

停止条件:

```text
1. reconnect_count > 0 かつ欠損区間を説明できない
2. error_count > 0
3. REST parityがwarn/fail
4. 60分時点で保存量が運用不能
```

### T6: 11symbol 60分smoke

目的:
  registry上の現行対象11symbolへ広げたときのrate/storage/qualityを確認する。

対象ファイル:

```text
コード変更なし
生成物:
  .tmp/trade_xyz_ws_smoke_11symbols_60m/
  data/manifests/*.json
```

実行:

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA,AAPL,MSFT,AMZN,GOOGL,META,TSLA,AMD,EWJ \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 60 \
  --output-dir .tmp/trade_xyz_ws_smoke_11symbols_60m \
  --write-control-messages
```

その後、Phase 5 と同じ quality / REST parity を実行する。

完了条件:

```text
1. official rate limit内で動く
2. connection_countが想定内
3. subscription数が 11 * 3 = 33 と説明できる
4. quality status == pass、またはfail理由がmanifestで説明できる
5. REST parity status == pass、またはmissing理由が公式仕様・symbol状態で説明できる
```

停止条件:

```text
1. rate limitに接触する
2. 保存量が運用不能
3. symbolごとのrow_count偏りを説明できない
4. unknown_symbol_count > 0
```

### T7: Current Real Data Contract更新

目的:
  `market_data.py` / `bar_builder.py` 実装前に、実payloadに合わせて契約を更新する。

対象ファイル:

```text
plan/TRADE_XYZ_BACKTEST_V0_1_2_REAL_DATA_HARDENING_PLAN_REV5.md
または後継REV
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
docs/集めるべき実データ0531-2108/README.md
```

作業内容:

```text
1. bbo field inventoryを書く
2. trades field inventoryを書く
3. activeAssetCtx field inventoryを書く
4. source_ts_msがある/ないpayloadを分ける
5. signal fields と fill snapshot fields を分ける
6. recv_ts_msをsource/oracle timestampとして使わないルールを書く
7. external referenceをTrade[XYZ]価格穴埋めに使わないルールを書く
```

テスト:

```bash
uv run python scripts/check_current_docs.py
git diff --check
```

完了条件:

```text
1. 実payloadに基づくfield inventoryがある
2. backtest ingestion前の禁止事項が明記されている
3. no-lookahead観点が書かれている
4. docs checkがpass
```

### T8: runbook作成

目的:
  第三者がread-only収集を再実行できるようにする。

対象ファイル:

```text
docs/TRADE_XYZ_WS_COLLECTION_RUNBOOK_2026-06-01.md
```

作業内容:

```text
1. dry-run手順
2. 1分smoke手順
3. 15分smoke手順
4. 60分capture手順
5. 11symbol capture手順
6. quality確認手順
7. REST parity確認手順
8. disk usage確認手順
9. fail時の調査順
10. 停止条件
11. data-readyにしてはいけない条件
```

テスト:

```bash
uv run python scripts/check_current_docs.py
git diff --check
```

完了条件:

```text
1. コマンドがそのままコピー実行できる
2. 生成artifact pathが明記されている
3. secret/wallet/signing不要が明記されている
4. fail時の確認artifactが明記されている
```

### T9: 24時間read-only観測

目的:
  日跨ぎ、低流動時間、休場、server disconnectを含む運用確認を行う。

対象ファイル:

```text
コード変更なし
生成物:
  data/raw/ws/trade_xyz/
  data/manifests/*.json
  docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
```

完了条件:

```text
1. 24時間runのcapture/quality/rest parity manifestがある
2. 日付partitionが壊れていない
3. disk usageが記録されている
4. reconnect/gap/errorが説明できる
5. current recordに結果が追記されている
```

停止条件:

```text
1. reconnect_count > 0 で欠損区間を説明できない
2. day partitionが壊れる
3. disk usage増加が運用不能
4. source timestampとrecv timestampの混同が見つかる
```

### T10: 実データ取得v0.1完了判定

目的:
  取得基盤として完了したか、未完了かを明確に宣言する。

対象ファイル:

```text
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
docs/CURRENT_STATE.md
docs/CODE_STATUS.md
必要なら plan/ の後継計画
```

完了条件:

```text
1. Phase 0.5からPhase 9まで完了
2. 3symbol 24時間runがpass、またはfail理由が説明可能
3. 11symbol 60分runがpass、またはfail理由が説明可能
4. Current Real Data Contract更新済み
5. runbook作成済み
6. ./scripts/check がpass
```

停止条件:

```text
1. data-ready条件を満たしていないのにreadyと書きそうになった
2. quote coverage / real market reference / oracle timestamp gapを解決済み扱いしそうになった
3. backtest engine変更へ作業が逸れた
```

## 作業順序

### Phase 0: baseline確定

目的:
  WS smoke後の最新コードがcommit済みで、次の実測へ進める状態であることを確認する。

2026-06-01_18:44 JST 時点のbaseline:

```text
HEAD:
  ade98dc Remove duplicate_payload_count from warn status condition in ws_quality, keeping it informational only, and add test_build_trade_xyz_ws_quality_manifest_keeps_duplicate_payloads_informational verifying pass status with duplicate_payload_count=1

意味:
  duplicate_payload_countはmanifestに残すが、単独ではstatus=warnにしない。
```

やること:

```bash
git status --short --branch
git log -1 --oneline --decorate
uv run pytest -q tests/test_trade_xyz_ws_quality.py
./scripts/check
```

完了条件:

```text
1. duplicate_payload_count単独ではstatus=warnにならない
2. duplicate_payload_countはmanifestに残る
3. threshold gapは引き続きstatus=warnになる
4. ./scripts/check がpassする
5. 作業ツリーに、意図しない未コミット差分がない
```

### Phase 0.5: 長時間smoke前の現実補正

目的:
  15分以上の実収集へ進む前に、短時間smokeでは見えない運用上の穴を潰す。

現時点で分かっている穴:

```text
heartbeat:
  公式Docsは { "method": "ping" } の送信を要求している。
  現行 ws_recorder.py は timeout時に WebSocket protocol ping を送っている。
  低流動channelでは、serverが期待するapplication-level pingにならない可能性がある。

allMids:
  公式Docsでは allMids に dex fieldがある。
  現行 WsSubscriptionTarget は coin中心で、allMidsのdex指定を表現していない。
  Trade[XYZ]/xyz正本として使う前に、dex指定を実装または明示的に対象外にする。

reconnect:
  公式Docsはdisconnectが定期的・予告なしに起きる前提を示している。
  現行manifestは reconnect_count/error_count を記録するが、reconnect中の欠損補完はしない。
  したがって reconnect_count > 0 のrunをdata-ready扱いにしてはいけない。

保存量:
  SP500 1分で row_count=170。
  単純比例なら11symbol/60分で10万行超の可能性がある。
  長時間run前に bytes_written と disk usage を記録する。
```

実装または明示確認すること:

```text
1. ws_recorder.py:
   application-level heartbeat `{ "method": "ping" }` を送る方式へ修正する。
   pong受信は実payloadとして記録し、synthetic pongと区別できるようにする。

2. tests/test_trade_xyz_ws_recorder.py:
   timeout時に application-level ping が送られることをfake connectionで固定する。

3. schemas/trade_xyz_ws_capture_manifest.v1.schema.json:
   必要なら heartbeat_sent_count と pong_count の意味を明確にするfieldを追加する。

4. allMids:
   Phase 3までは実務正本にしない。
   使う場合は dex=xyz を表現できる設計へ先に直す。
```

完了条件:

```text
1. application-level heartbeatのテストがある
2. 低流動時のping/pongをmanifestで説明できる
3. reconnect_count > 0 のrunをdata-readyから除外するルールが明記されている
4. allMidsはdex指定対応まで正本にしない
5. ./scripts/check がpassする
```

このPhaseを飛ばして15分/60分runへ進まない。

### Phase 1: 複数symbol 1分 smoke

目的:
  SP500単一symbolだけでなく、registry上の複数symbolでWS captureが壊れないことを確認する。

対象:

```text
symbols:
  - SP500
  - XYZ100
  - NVDA

subscriptions:
  - bbo
  - trades
  - activeAssetCtx

duration:
  1 minute

output:
  .tmp/trade_xyz_ws_smoke_multi_symbol/
```

実行:

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 1 \
  --output-dir .tmp/trade_xyz_ws_smoke_multi_symbol \
  --write-control-messages

uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root .tmp/trade_xyz_ws_smoke_multi_symbol \
  --recv-gap-threshold-seconds 60 \
  --source-gap-threshold-seconds 60

uv run sis build-trade-xyz-rest-parity \
  --symbols SP500,XYZ100,NVDA \
  --ws-manifest-path data/manifests/trade_xyz_ws_capture_manifest.json \
  --request-delay-seconds 0.2 \
  --skip-l2-book
```

確認するartifact:

```bash
jq . data/manifests/trade_xyz_ws_capture_manifest.json
jq . data/manifests/trade_xyz_ws_quality_manifest.json
jq . data/manifests/trade_xyz_rest_parity_manifest.json
find .tmp/trade_xyz_ws_smoke_multi_symbol -type f | sort
```

完了条件:

```text
capture:
  error_count == 0
  reconnect_count == 0
  subscription_response_count >= 9
  raw_paths に bbo/trades/activeAssetCtx の各symbol pathが存在する

quality:
  status == pass
  row_count > 0
  malformed_payload_count == 0
  unknown_symbol_count == 0
  bbo_bid_ask_inversion_count == 0
  gap_count == 0

rest parity:
  status == pass
  request_error_count == 0
  missing_rest_symbols == []
  mismatched_symbols == []
```

停止条件:

```text
1. subscriptionResponseがsymbol数 * subscription数より少ない
2. unknown_symbol_count > 0
3. bbo pathだけ存在し、trades/activeAssetCtxが作られない
4. REST parityで特定symbolがmissingになる
5. row_countまたはbytes_writtenが想定より大きく、保存量見積もりなしで15分runへ進むのが危険
```

停止した場合:

```text
1. raw payloadのchannel/data/coin構造を確認する
2. ws_envelope.py / ws_recorder.py のsymbol解決を修正する
3. fixture testを追加する
4. smokeを再実行する
```

### Phase 2: 15分 smoke

目的:
  短時間では見えないheartbeat、gap、reconnect、duplicate、source timestampの傾向を見る。

対象:

```text
symbols:
  - SP500
  - XYZ100
  - NVDA

subscriptions:
  - bbo
  - trades
  - activeAssetCtx

duration:
  15 minutes

output:
  .tmp/trade_xyz_ws_smoke_15m/
```

実行:

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 15 \
  --output-dir .tmp/trade_xyz_ws_smoke_15m \
  --write-control-messages

uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root .tmp/trade_xyz_ws_smoke_15m \
  --recv-gap-threshold-seconds 60 \
  --source-gap-threshold-seconds 60

uv run sis build-trade-xyz-rest-parity \
  --symbols SP500,XYZ100,NVDA \
  --ws-manifest-path data/manifests/trade_xyz_ws_capture_manifest.json \
  --request-delay-seconds 0.2 \
  --skip-l2-book
```

完了条件:

```text
capture:
  error_count == 0
  reconnect_count == 0
  row_count > Phase 1 row_count

quality:
  status == pass
  malformed_payload_count == 0
  unknown_symbol_count == 0
  bbo_bid_ask_inversion_count == 0
  gap_count == 0

rest parity:
  status == pass
  request_error_count == 0
```

注意:
  `pong_count=0` は、15分中にmessageが継続して届いた場合だけ問題ではない。
  低流動時間帯の検証では、application-level ping/pongを実際に確認する。

保存量確認:

```bash
du -sh .tmp/trade_xyz_ws_smoke_15m
jq '{row_count, bytes_written, raw_paths}' data/manifests/trade_xyz_ws_capture_manifest.json
```

15分run後に判断すること:

```text
1. row_countが線形に増えているか
2. activeAssetCtxの同一再送がどの程度出るか
3. tradesが少ないsymbolを欠損扱いしていないか
4. 60分runへ進める保存量か
5. reconnect_count > 0 の場合、欠損補完方針なしで進めていないか
```

### Phase 3: allMids / l2Bookの扱いを確定

目的:
  `allMids` と `l2Book` を今のv0.1.1/v0.1.2 hardeningに含めるか、後続に送るか決める。

現時点の推奨:

```text
allMids:
  現時点では原則後回し。
  公式Docsでは dex fieldがあるため、dex=xyz を表現できるまでTrade[XYZ]正本にしない。
  symbol別pathにならない可能性もあるため、normalized inputにはまだ使わない。

l2Book:
  L2 replayは対象外。
  ただしraw captureのpayload shape確認だけなら1symbol/1分でよい。
  fill modelやsweep-depthには接続しない。
```

実行する場合:

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500 \
  --subscriptions l2Book \
  --duration-minutes 1 \
  --output-dir .tmp/trade_xyz_ws_smoke_l2book \
  --write-control-messages

uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500 \
  --subscriptions allMids \
  --duration-minutes 1 \
  --output-dir .tmp/trade_xyz_ws_smoke_allmids \
  --write-control-messages
```

完了条件:

```text
1. l2Book/allMids のraw payload shapeを記録する
2. v0.1のbar_builderやrun_backtest入力にはまだ接続しない
3. L2 replayやmulti-symbol backtestに作業を広げない
```

停止条件:

```text
1. allMidsがsymbol targetなしの全市場payloadで、現row partitionと合わない
2. allMidsでdex=xyzが確認できない
3. l2Book payloadが高頻度すぎて1分でも大量生成する
4. source timestampやsymbol解決が既存schemaに合わない
```

停止した場合:
  別計画 `Trade[XYZ] L2/allMids raw capture appendix` を作り、この計画には混ぜない。

### Phase 4: 本番raw保存先での短時間収集

目的:
  `.tmp` ではなく、通常のraw保存先に短時間だけ保存して、manifestとpathの運用を確認する。

対象:

```text
symbols:
  - SP500
  - XYZ100
  - NVDA

subscriptions:
  - bbo
  - trades
  - activeAssetCtx

duration:
  15 minutes

output:
  data/raw/ws/trade_xyz/
```

実行:

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500,XYZ100,NVDA \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 15 \
  --output-dir data/raw/ws/trade_xyz \
  --write-control-messages

uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root data/raw/ws/trade_xyz \
  --recv-gap-threshold-seconds 60 \
  --source-gap-threshold-seconds 60

uv run sis build-trade-xyz-rest-parity \
  --symbols SP500,XYZ100,NVDA \
  --ws-manifest-path data/manifests/trade_xyz_ws_capture_manifest.json \
  --request-delay-seconds 0.2 \
  --skip-l2-book
```

完了条件:

```text
1. data/raw/ws/trade_xyz/ に date/subscription/symbol partitionが作られる
2. data/manifests/trade_xyz_ws_capture_manifest.json が最新runを指す
3. data/manifests/trade_xyz_ws_quality_manifest.json が status=pass
4. data/manifests/trade_xyz_rest_parity_manifest.json が status=pass
5. data/raw/quotes/trade_xyz/ には影響しない
```

注意:
  `data/raw/ws/trade_xyz/` は生成物であり、原則gitに入れない。

### Phase 5: 1時間収集とcollection status連携判断

目的:
  WS collectorを通常のcollection status/readinessへ接続する前に、1時間単位で安定するか確認する。

対象:

```text
symbols:
  まず3symbol
    - SP500
    - XYZ100
    - NVDA

  3symbolがpassした後に11symbolへ拡張
    - SP500
    - XYZ100
    - NVDA
    - AAPL
    - MSFT
    - AMZN
    - GOOGL
    - META
    - TSLA
    - AMD
    - EWJ

subscriptions:
  - bbo
  - trades
  - activeAssetCtx

duration:
  60 minutes
```

完了条件:

```text
1. 3symbol 60分で capture/quality/rest parity がpass
2. 11symbol 60分で capture/quality/rest parity がpass、またはfail理由がmanifestで説明できる
3. row_count、subscription_counts、symbol_countsが極端に偏らない
4. reconnect_count/error_countが0
5. source_ts_gap_count/gap_countが0、または市場休止・低流動として説明できる
```

現実的な判定:

```text
reconnect_count > 0:
  収集プロセスとしては成功でも、backtest入力としては保留。
  欠損区間をREST/infoや再取得で説明できるまでdata-ready扱いしない。

trades rowが少ない:
  低流動の可能性がある。
  tradesが少ないこと自体を欠損と断定しない。

bbo/activeAssetCtxはあるがtradesがない:
  取引が無かった可能性がある。
  quote coverageとtrade tape coverageを分けて評価する。

activeAssetCtx duplicateが多い:
  同値再送として記録する。
  単独ではwarn/failにしない。
```

collection statusへ接続してよい条件:

```text
1. 1時間収集が3回以上pass
2. 失敗時のblock_reasonsが運用者に読める
3. data/raw/ws/trade_xyz/ の保存量が許容範囲
4. normalizerがWS rawを誤って既存quote rawとして読まない
5. 2026-05-30以前のarchiveを参照しない
```

まだ接続しない条件:

```text
1. symbol別pathが不安定
2. activeAssetCtxの同一再送を重複エラー扱いする処理が残っている
3. allMids/l2Bookを混ぜないとqualityが説明できない
4. REST parityがsymbolによってmissingになる
5. source timestampの扱いが不明
```

### Phase 6: backtest入力へ流す前の設計更新

目的:
  実データを `run_backtest()` に流す前に、schemaとbar_builderの境界を再確認する。

前提:
  このPhaseまではbacktest engineを変更しない。

更新候補:

```text
plan/TRADE_XYZ_BACKTEST_V0_1_2_REAL_DATA_HARDENING_PLAN_REV5.md
または後継REV:
  Current Real Data Contract

docs/集めるべき実データ0531-2108/README.md:
  実際に取得できたWS payloadと、まだ不足しているfieldを追記

docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md:
  WS smoke / 15m / 60m の結果を追記
```

実装前に必ず決めること:

```text
1. signal fields と fill snapshot fields を混ぜない
2. activeAssetCtxの markPx/oraclePx/midPx/funding/openInterest をどの層で読むか
3. bbo bid/ask をfill snapshotとして使うか、quality referenceとしてだけ使うか
4. tradesをtrade tapeとして保存するだけか、bar aggregationへ使うか
5. source_ts_msが無いpayloadをbar timestampの正本にしない
```

完了条件:

```text
1. Current Real Data Contractが実payloadに合わせて更新されている
2. market_data.py / bar_builder.py 実装前にschema差分が文書化されている
3. signal fields と fill snapshot fields の分離方針が明記されている
4. no-lookahead test方針が明記されている
```

### Phase 7: WS rawを正規化候補へ昇格する前の契約作成

目的:
  WS rawをただ保存する状態から、backtest入力候補として扱える状態へ進める。

前提:
  このPhaseでもまだ `run_backtest()` へ直接流さない。

やること:

```text
1. WS raw sourceごとのfield inventoryを作る
2. activeAssetCtx / bbo / trades の用途を分ける
3. signal fields と fill snapshot fields を別contractに分ける
4. source_ts_msが無いpayloadのtimestamp policyを明記する
5. recv_ts_msしか無いfieldをbacktest event timeにしない
6. quality manifestのpass/warn/failをreadiness条件へどう接続するか決める
```

作成・更新する文書:

```text
plan/TRADE_XYZ_BACKTEST_V0_1_2_REAL_DATA_HARDENING_PLAN_REV5.md
  または後継REV:
    Current Real Data Contract

docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md:
  WS payload inventory
  smoke results
  known gaps

docs/集めるべき実データ0531-2108/README.md:
  実際に取得可能だったfield
  取得できないfield
  backtestへ入れてはいけないfield
```

完了条件:

```text
1. activeAssetCtx由来fieldの用途が明記されている
2. bbo由来fieldの用途が明記されている
3. trades由来fieldの用途が明記されている
4. source timestampが無いfieldの扱いが明記されている
5. external referenceでTrade[XYZ]価格を穴埋めしないことが明記されている
```

### Phase 8: 取得継続運用の最小runbook化

目的:
  一度だけのsmokeではなく、同じ手順で日次・再開・失敗調査ができる状態にする。

作成するもの:

```text
docs/TRADE_XYZ_WS_COLLECTION_RUNBOOK_2026-06-01.md
```

runbookに含めること:

```text
1. dry-run
2. 1分smoke
3. 15分smoke
4. 60分capture
5. 11symbol capture
6. quality manifest確認
7. REST parity確認
8. disk usage確認
9. fail時の調査順
10. 停止してよい条件
11. 停止してはいけない条件
12. data-readyにしてはいけない条件
```

完了条件:

```text
1. 第三者がrunbookだけでread-only captureを再実行できる
2. 生成artifactのpathがすべて明記されている
3. 秘密情報・wallet・signingが不要であることが明記されている
4. 失敗時に何を見るかが明記されている
```

### Phase 9: 24時間以上のread-only観測

目的:
  取引時間、低流動時間、休場、日跨ぎ、reconnectを含む実運用の偏りを見る。

前提:
  Phase 0.5からPhase 8まで完了していること。

対象:

```text
symbols:
  まず3symbol:
    - SP500
    - XYZ100
    - NVDA

  その後11symbol:
    - SP500
    - XYZ100
    - NVDA
    - AAPL
    - MSFT
    - AMZN
    - GOOGL
    - META
    - TSLA
    - AMD
    - EWJ

subscriptions:
  - bbo
  - trades
  - activeAssetCtx

duration:
  - 24 hours
```

完了条件:

```text
1. 24時間runのcapture manifestが残る
2. 24時間runのquality manifestが残る
3. 24時間runのREST parity manifestが残る
4. disk usageが記録されている
5. reconnect_count/error_count/gap_countが説明できる
6. 日付partitionが複数日にまたがっても壊れない
7. 取引が薄い時間帯を欠損と誤判定していない
```

data-readyへ進めない条件:

```text
1. reconnect_count > 0 で欠損区間が説明できない
2. 日跨ぎpartitionが壊れる
3. raw_pathsが想定外のpathを指す
4. disk usageが運用不能な速度で増える
5. session/holiday/reference market状態を説明できない
```

### Phase 10: 実データ取得v0.1完了判定

目的:
  「今のRepoでbacktestへ流してよい実データ取得状態」を明確に宣言する。

v0.1完了条件:

```text
1. Phase 0.5からPhase 9まで完了
2. 3symbol 24時間runがpass
3. 11symbol 60分runがpass、またはfail理由がmanifestで説明できる
4. application-level heartbeatが実装・テスト済み
5. reconnect_count > 0 の扱いがreadiness条件に入っている
6. allMids/l2Bookを正本にしていない、または別計画で扱っている
7. Current Real Data Contractが実payloadに合わせて更新済み
8. runbookがある
9. docs/current recordが最新化済み
10. ./scripts/check がpass
```

v0.1で完了と呼んでよいこと:

```text
Trade[XYZ]公式REST/WS由来のforward captureを、出所・保存先・quality・parityつきで運用できる。
```

v0.1で完了と呼んではいけないこと:

```text
1. 30日coverageが埋まった
2. historical backfillが完了した
3. oracle timestamp provenanceが解決した
4. real market referenceが完全になった
5. L2 replayができる
6. 実務backtestの全戦略がready
7. live/paper executionがready
```

### Phase 11: backtest ingestion計画への引き継ぎ

目的:
  実データ取得計画を閉じ、次の計画へ渡す。

引き継ぎ先:

```text
Trade[XYZ] Backtest Real Data Ingestion Plan
```

引き継ぎ内容:

```text
1. WS raw contract
2. REST quote contract
3. activeAssetCtx field inventory
4. bbo field inventory
5. trades field inventory
6. quality manifest contract
7. readiness gate条件
8. known gaps
9. 使ってはいけないデータ
10. no-lookahead test方針
```

ここで初めて検討すること:

```text
1. market_data.py
2. bar_builder.py
3. signal fields / fill snapshot fields分離
4. run_backtest() への入力adapter
5. no-lookahead tests
```

このPhaseまでは、backtest engineを変更しない。

## テスト方針

### 近接テスト

変更したファイルに応じて、最低限これを回す。

```bash
uv run pytest -q \
  tests/test_trade_xyz_ws_quality.py \
  tests/test_trade_xyz_rest_parity.py \
  tests/test_trade_xyz_ws_recorder.py \
  tests/test_trade_xyz_ws_cli.py \
  tests/test_cli_help_contract.py
```

### 全体検証

作業単位ごとに必ず回す。

```bash
./scripts/check
```

### 実データsmoke

外部read-only APIを使うため、テストではなく運用確認として扱う。

```bash
uv run sis collect-trade-xyz-ws ...
uv run sis build-trade-xyz-ws-quality ...
uv run sis build-trade-xyz-rest-parity ...
```

smoke結果は、チャットだけでなくdocsまたはmanifestに残す。

## 完了条件

この計画全体の完了条件は次の通り。

```text
1. baseline commitが確認済み
2. 3symbol 1分 smoke がpass
3. 3symbol 15分 smoke がpass
4. 3symbol 60分 smoke がpass
5. 11symbol 60分 smoke の結果がpass、またはfail理由が明確
6. 3symbol 24時間runがpass、またはfail理由がmanifestで説明できる
7. application-level heartbeatが実装・テスト済み
8. WS quality manifestがstatus/pass/warn/failを現実的に判定できる
9. REST parity manifestがstatus/passで、missing_rest_symbols/mismatched_symbolsが空
10. raw WS dataと既存raw quotesの保存境界が守られている
11. 2026-05-30以前の実データを参照していない
12. Current Real Data Contractが実payloadに合わせて更新されている
13. runbookがある
14. docs/current recordに最新の実測結果が記録されている
15. `./scripts/check` がpass
```

## data-readyにしない条件

次のどれかに該当する場合、たとえ収集コマンドがexit 0でも `backtest_data_ready=true` にしない。

```text
1. reconnect_count > 0 かつ欠損補完が未実施
2. error_count > 0
3. unknown_symbol_count > 0
4. malformed_payload_count > 0
5. bbo_bid_ask_inversion_count > 0
6. gap_count > 0 で、市場休止・低流動・意図した停止として説明できない
7. source_ts_gap_count > 0 で、payload仕様として説明できない
8. allMidsをdex=xyz確認なしにTrade[XYZ]正本として使っている
9. recv_ts_msをsource/oracle timestampとして扱っている
10. 2026-05-30以前のarchiveを参照している
11. real_market_reference failをWS passで解決済み扱いしている
12. quote coverage failを短時間WS smokeで解決済み扱いしている
```

## 最終的にまだ残る可能性があるリスク

この計画を完了しても、次は残り得る。

```text
oracle_timestamp_provenance:
  activeAssetCtxなどにoracle timestamp fieldが無い場合は、引き続きknown gap。
  recv_ts_msで補完してはいけない。

real_market_reference:
  Trade[XYZ]のmark/oracle/fillの代替ではない。
  外部市場参照として別manifestで扱う。

historical coverage:
  WebSocketはforward captureであり、過去を埋められない。
  2026-05-30以前のarchiveを戻してはいけない。

L2 replay:
  この計画ではraw shape確認まで。
  fill modelやsweep-depthは別計画。

long-running reliability:
  1時間passしても、24時間・週末・休場・低流動時間帯は別途確認が必要。

rate limit / storage:
  現状の3symbol/11symbol設計は公式limit内に見えるが、保存量と送信message数は実測で見る。
  収集対象を増やすときは subscription数、connection数、new connection/min、bytes_writtenをmanifestで確認する。
```

## 付録A: 現時点の推奨次コマンド

まずbaselineが最新commitであることを確認する。

```bash
git status --short --branch
git log -1 --oneline --decorate
uv run pytest -q tests/test_trade_xyz_ws_quality.py
./scripts/check
```

次にT1としてapplication-level heartbeatを実装する。

```bash
uv run pytest -q tests/test_trade_xyz_ws_recorder.py
uv run pytest -q tests/test_trade_xyz_ws_cli.py tests/test_cli_help_contract.py
uv run ruff check src/sis/venues/trade_xyz/ws_recorder.py tests/test_trade_xyz_ws_recorder.py
uv run ruff format --check src/sis/venues/trade_xyz/ws_recorder.py tests/test_trade_xyz_ws_recorder.py
```

T1が完了したらT2としてheartbeat smokeを実行する。

```bash
uv run sis collect-trade-xyz-ws \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --symbols SP500 \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 2 \
  --heartbeat-seconds 5 \
  --output-dir .tmp/trade_xyz_ws_heartbeat_smoke \
  --write-control-messages

uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root .tmp/trade_xyz_ws_heartbeat_smoke \
  --recv-gap-threshold-seconds 60 \
  --source-gap-threshold-seconds 60

jq '{row_count, error_count, reconnect_count, heartbeat_sent_count, pong_count}' \
  data/manifests/trade_xyz_ws_capture_manifest.json
jq '{status, row_count, pong_count, gap_count, malformed_payload_count, unknown_symbol_count}' \
  data/manifests/trade_xyz_ws_quality_manifest.json
```

## 付録B: readiness判定

現時点の判定:

```text
read-only WS smoke:
  partially passed

REST parity:
  SP500 1分smoke範囲ではpass

実務backtest ready:
  まだreadyではない

理由:
  1. 単一symbol・1分しか確認していない
  2. 既存quote coverage不足はこの1分smokeだけでは解決しない
  3. oracle timestamp provenanceはknown gapのまま
  4. real market reference不足は別系統で残る
```

この文書のPhase 1からPhase 11を終えるまで、`backtest_data_ready=true` と見なしてはいけない。
実データ取得v0.1としても、Phase 10を終えるまで完了扱いにしない。
