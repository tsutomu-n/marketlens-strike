<!--
作成日: 2026-06-01_17:40 JST
更新日: 2026-06-01_18:04 JST
-->

# Trade[XYZ] Data Collection Expansion 実装計画 2026-06-01

## 結論

実装対象は、Trade[XYZ]実データを将来のバックテストへ誤読なく流すための
**read-only data collection hardening** に限定する。

最初に作るべきものは、OSSクライアントの大規模導入ではなく、既存 `TradeXyzClient` と既存
manifest/readinessの流れを壊さない **公式WebSocket raw recorder + quality manifest + REST parity
manifest** である。

```text
実装する:
  - 公式WebSocket raw recorder
  - WebSocket capture/quality manifest
  - 既存REST collectorとのparity manifest
  - WebSocket raw row schema
  - source timestamp と receive timestamp の分離
  - subscriptionResponse / pong / heartbeat / reconnect の監査
  - schema / tests / docs
  - 必要なら direct dependency として websockets を追加

実装しない:
  - backtest engine変更
  - strategy最適化
  - live / paper / wallet / signing / exchange write
  - MT5 / IC Markets / CFD
  - ccxt / dlt / hyperliquid-python-sdk などの即時導入
```

## この計画の正本

実装時は、次の優先順位で判断する。

```text
1. src/ の現行コード
2. tests/ の現行期待値
3. schemas/ の現行契約
4. configs/ の現行設定
5. `uv run sis --help` の現行CLI surface
6. docs/ と plan/ の説明
```

この文書は実装計画であり、コードより優先しない。
コード・schema・CLI helpと矛盾した場合は、実装前にこの文書を更新してから進める。

## 実装前チェック

コーダーは実装前に必ず次を確認する。

```bash
git status --short --branch
uv run python -V
uv run sis --help
uv run python scripts/check_current_docs.py
```

確認すること:

```text
1. Python 3.13で動いている
2. `collect-trade-xyz-ws` 系コマンドがまだ存在しないことを確認する
3. `configs/trade_xyz_data_collection.yaml` の usable_start_date が 2026-05-31 のまま
4. 既存の uncommitted user changes を巻き戻さない
5. data/ や logs/ の生成物をgit管理対象へ入れない
```

## 停止条件

次の場合は実装を止め、この計画書を更新してから再開する。

```text
1. Hyperliquid公式DocsのWebSocket URLやsubscription名が、この計画と違う
2. 実payloadに `time` 等のsource timestampが無く、時刻解釈が変わる
3. 既存 `TradeXyzClient` のread-only APIとREST parity要件が合わない
4. 既存normalizerが data/raw/ws/trade_xyz/ を誤って読む可能性が見つかった
5. backtest / execution / paper / wallet / signing へ変更が必要になった
6. rate limitや有料API利用が必要になった
```

停止条件に該当した場合、推測で実装しない。
変更するのはこの計画書と関連docsだけにして、実装方針を再確定する。

## 目的

Trade[XYZ]向けバックテストの入力データで、次の誤読リスクを下げる。

```text
1. quote coverage不足を、公式WebSocket forward captureで改善する
2. raw payload と normalized artifact の追跡性を上げる
3. REST snapshotだけでは見えない欠損・切断・重複をmanifest化する
4. real market referenceをTrade[XYZ]のfill / mark / oracle / funding正本と混同しない
5. OSSや外部providerを、正本ではなくsidecar / cross-checkとして扱う
6. 2026-05-30以前の実データをreadinessへ戻さない
```

この作業の目的は、戦略成績を良く見せることではない。
目的は、`run_backtest()` へ入る前の実データを、出所・時刻・欠損・変換経路つきで説明できる状態にすることである。

## 現行確認済みの事実

2026-06-01_18:04 JST 時点で確認した事実。

```text
既存CLI:
  - collect-trade-xyz-quotes
  - collect-trade-xyz-data-cycle
  - normalize-quotes
  - build-trade-xyz-quote-coverage
  - collect-trade-xyz-real-market-reference
  - collect-trade-xyz-signal-candles
  - collect-trade-xyz-account-fee
  - collect-trade-xyz-funding-history
  - build-trade-xyz-data-readiness
  - trade-xyz-collection-status
  - build-trade-xyz-data-bundle
  - historical archive 系 commands

既存Trade[XYZ] client:
  - src/sis/venues/trade_xyz/client.py
  - base_url = https://api.hyperliquid.xyz
  - dex = xyz
  - allMids
  - meta
  - metaAndAssetCtxs
  - l2Book
  - candleSnapshot
  - fundingHistory
  - userFees

既存real market reference chain:
  - yfinance
  - yahooquery
  - stooq
  - alpaca は credentialed optional

既存設定:
  - configs/trade_xyz_data_collection.yaml
  - data_cutoff.usable_start_date = 2026-05-31
  - symbols は設定ファイル管理済み

依存関係:
  - pyproject.toml には websockets は直接依存として未記載
  - uv.lock には websockets 15.0.1 が存在する
  - WebSocket recorderを実装するなら、transitive dependencyに依存せず pyproject.tomlへ直接追加する
```

追加調査で確認した外部正本:

```text
Hyperliquid WebSocket:
  - Mainnet WebSocket URL は wss://api.hyperliquid.xyz/ws
  - subscribe request は method=subscribe と subscription object を送る
  - subscriptionResponse が返る
  - bbo / trades / activeAssetCtx / allMids / l2Book などのsubscriptionがある
  - bbo / trades / l2Book payloadには time が含まれる
  - activeAssetCtx payloadには ctx が含まれるが、source timestampが常にあるとは限らない
  - serverが60秒以上messageを受け取らない場合はtimeoutするため、client側ping/pongが必要

Hyperliquid REST/info:
  - metaAndAssetCtxs / fundingHistory / l2Book / candleSnapshot などは info endpoint のread-only payload
  - rate limitがあるため、REST parityでl2Bookを全symbolへ無制限に叩かない
```

参照:

```text
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/timeouts-and-heartbeats
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits
```

## 制約

### 絶対にしないこと

```text
live注文:
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

short / multi-symbol / leverage / L2 replay:
  この計画では実装しない

MT5 / IC Markets / CFD:
  スコープ外

2026-05-30以前の実データ:
  readinessや実務BT判断へ戻さない
```

### データ境界

```text
公式Trade[XYZ] / Hyperliquid payload:
  Trade[XYZ] market truthの候補

外部real market reference:
  underlying/reference/cross-check用
  Trade[XYZ] fill / mark / oracle / funding の代替にしない

OSS client経由データ:
  sidecar / probe / cross-check用
  canonical collectorにしない

historical archive:
  requester-pays / cost / date cutoffをmanifestに残す
```

### 時刻境界

```text
source_ts_ms:
  公式payload内に time / t / T などの時刻fieldが存在する場合のみ入れる
  field名を source_ts_field に残す

recv_ts_ms:
  collectorがpayloadを受け取ったローカルUTC時刻
  source_ts_ms の代替にしない

recv_monotonic_ns:
  collector process内の順序・gap監査用
  wall clockやexchange timestampとして扱わない

oracle_ts_ms:
  公式payloadにoracle timestamp相当のfieldが明示されるまで補完しない
```

この境界を破ると、バックテストで「取得が遅れた時刻」と「市場で発生した時刻」を混同する。

### 保存境界

```text
既存 raw quotes:
  data/raw/quotes/trade_xyz/
  既存collectorのraw quote用として維持する

新規 WebSocket raw:
  data/raw/ws/trade_xyz/
  既存 raw quotes へ直接混ぜない

外部provider:
  data/external/<provider>/
  または data/staging/<provider>/

manifest:
  data/manifests/
```

## 採用方針

### 主案

Phase 1では、次の3つだけを実装する。

```text
1. official_ws_recorder
2. ws_quality_manifest
3. rest_parity_manifest
```

これにより、現行collectorに不足している forward tick/quote capture と欠損監査を追加する。

### 採用しない案

Phase 1では、次は採用しない。

```text
hyperliquid-python-sdk:
  既存 TradeXyzClient を置き換えない。
  将来の regression probe 候補に留める。

ccxt:
  external cross-check候補。
  HIP-3固有のoracle/funding/OI cap/discovery bound正本にはしない。

dlt:
  staging/schema driftには有用。
  ただし Phase 1 では既存Polars/JSONL/manifest構成を優先する。

alpaca-py:
  Alpaca provider強化候補。
  Phase 1 のWebSocket公式captureとは別問題。

databento / Massive / OpenBB / cryptofeed:
  provider sidecar候補。
  直接 dependency にはしない。
```

理由は、現行Repoには既にREST collector、normalizer、coverage、readiness、real market reference providerがあり、
まず不足しているのは「公式forward WebSocket captureの監査可能なraw保存」だからである。

## 対象ファイル

### 新規作成するファイル

```text
src/sis/venues/trade_xyz/ws_envelope.py
src/sis/venues/trade_xyz/ws_recorder.py
src/sis/venues/trade_xyz/ws_quality.py
src/sis/venues/trade_xyz/rest_parity.py

schemas/trade_xyz_ws_raw.v1.schema.json
schemas/trade_xyz_ws_capture_manifest.v1.schema.json
schemas/trade_xyz_ws_quality_manifest.v1.schema.json
schemas/trade_xyz_rest_parity_manifest.v1.schema.json

tests/test_trade_xyz_ws_envelope.py
tests/test_trade_xyz_ws_recorder.py
tests/test_trade_xyz_ws_quality.py
tests/test_trade_xyz_rest_parity.py
tests/test_trade_xyz_ws_raw_schema.py
```

CLI公開まで同一PRで行う場合のみ、次も追加する。

```text
tests/test_trade_xyz_ws_cli.py
```

既存 `tests/test_cli_smoke.py` は大きいため、新規CLI smokeは専用test fileに分ける。
ただし、repoのCLI smoke一元管理方針が優先される場合は、既存testへ最小追加してよい。

### 変更するファイル

```text
pyproject.toml
uv.lock
configs/trade_xyz_data_collection.yaml
src/sis/commands/quotes.py
src/sis/venues/trade_xyz/collection_config.py
src/sis/venues/trade_xyz/collection_status.py
src/sis/venues/trade_xyz/client.py
tests/test_trade_xyz_collection_config.py
tests/test_trade_xyz_client.py
docs/TRADE_XYZ_DATA_COLLECTION_EXPANSION_OPTIONS_2026-06-01.md
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
```

`pyproject.toml` / `uv.lock` は、`websockets>=15` を直接依存にするために変更する。
`uv.lock` に既に `websockets 15.0.1` があるとしても、直接依存でない状態に頼らない。

`collection_status.py` は、WS manifestが存在する場合に状態へ表示するだけに留める。
readiness pass/fail判定を変える場合は、別PRまたは別タスクにする。

`client.py` は read-only info endpoint wrapperの追加だけ許可する。
署名・注文・cancel・wallet・exchange writeに関係するmethodは追加しない。

### 変更してはいけないファイル

```text
src/sis/backtest/
src/sis/execution/
src/sis/paper/
src/sis/venues/trade_xyz/client.py の write系追加
src/sis/execution/trade_xyz_adapter.py
src/sis/backtest/bridge.py
```

今回の作業は collector hardening であり、backtest / execution / paper の責務へ入らない。

## 新規データ契約

### WebSocket raw path

```text
data/raw/ws/trade_xyz/
  date=YYYY-MM-DD/
    subscription=<subscription>/
      symbol=<canonical_symbol>/
        part-000001.jsonl
```

`symbol` を持たないglobal subscriptionの場合は次を使う。

```text
symbol=__all__/
```

`subscriptionResponse`、`pong`、error相当のcontrol messageは次を使う。

```text
subscription=__control__/
symbol=__all__/
```

### WebSocket raw JSONL row

1行1payloadで保存する。

```json
{
  "schema_version": "trade_xyz_ws_raw.v1",
  "source": "hyperliquid_ws",
  "source_tier": "official_ws",
  "dex": "xyz",
  "ws_url": "wss://api.hyperliquid.xyz/ws",
  "channel": "bbo",
  "message_kind": "data",
  "subscription": "bbo",
  "subscription_hash": "sha256:...",
  "connection_id": "20260601T084000Z-0001",
  "sequence": 1,
  "source_ts_ms": 1780000000000,
  "source_ts_field": "time",
  "recv_ts_ms": 1780000000000,
  "recv_monotonic_ns": 1234567890,
  "canonical_symbol": "SP500",
  "venue_symbol": "xyz:SP500",
  "coin": "xyz:SP500",
  "is_snapshot": false,
  "payload_sha256": "sha256:...",
  "payload": {}
}
```

必須項目:

```text
schema_version
source
source_tier
dex
ws_url
channel
message_kind
subscription
subscription_hash
connection_id
sequence
recv_ts_ms
recv_monotonic_ns
payload_sha256
payload
```

payload内に公式source timestamp fieldがある場合のみ次を入れる。

```text
source_ts_ms
source_ts_field
```

symbol付きsubscriptionでは次も必須。

```text
canonical_symbol
venue_symbol
coin
```

禁止:

```text
recv_ts_ms を oracle_ts_ms として扱う
client timestamp を exchange timestamp として扱う
外部provider timestamp を Trade[XYZ] timestamp として扱う
payloadから存在しない field を補完する
source_ts_ms が無いmessageに recv_ts_ms を詰める
```

`channel` / `message_kind` の初期分類:

```text
data:
  bbo
  trades
  activeAssetCtx
  l2Book
  allMids

subscription_response:
  subscriptionResponse

heartbeat:
  pong

error:
  JSON parse error
  unknown shape
  websocket close/error summary
```

### Normalized artifact

Phase 1では、normalized quotesへ直接混入しない。
WS専用normalized artifactの生成も必須実装には含めない。
必要な場合は、Phase 1完了後の別タスクで別名artifactとして出す。

```text
data/normalized/trade_xyz_ws_bbo.parquet
data/normalized/trade_xyz_ws_trades.parquet
data/normalized/trade_xyz_ws_asset_ctx.parquet
```

既存 `data/normalized/quotes.parquet` へ取り込むのは、別タスクでschemaと品質条件が固まってからにする。

### Manifest

```text
data/manifests/trade_xyz_ws_capture_manifest.json
data/manifests/trade_xyz_ws_quality_manifest.json
data/manifests/trade_xyz_rest_parity_manifest.json
```

`capture_manifest` に必ず入れる項目:

```text
schema_version
source
dex
started_at
ended_at
duration_seconds
subscriptions
symbols
raw_paths
row_count
bytes_written
connection_count
reconnect_count
error_count
subscription_response_count
pong_count
heartbeat_sent_count
dry_run
git_head
command
```

`quality_manifest` に必ず入れる項目:

```text
schema_version
source_manifest_path
row_count
subscription_counts
symbol_counts
duplicate_payload_count
gap_count
max_gap_seconds
source_ts_gap_count
max_source_ts_gap_seconds
bbo_bid_ask_inversion_count
malformed_payload_count
unknown_symbol_count
subscription_response_count
pong_count
status
block_reasons
```

`rest_parity_manifest` に必ず入れる項目:

```text
schema_version
source
dex
symbols
window_start
window_end
rest_endpoints
ws_manifest_path
comparison_count
missing_ws_symbols
missing_rest_symbols
mismatched_symbols
rate_limit_sleep_seconds
request_error_count
request_count
status
block_reasons
```

## 設定計画

`configs/trade_xyz_data_collection.yaml` にWebSocket用設定を追加する。
実装時にsymbolやsubscriptionをコードへハードコードしない。

```yaml
websocket_collection:
  enabled: false
  ws_url: "wss://api.hyperliquid.xyz/ws"
  default_subscriptions:
    - bbo
    - trades
    - activeAssetCtx
  duration_minutes: 60
  heartbeat_seconds: 30
  server_timeout_seconds: 60
  reconnect:
    max_attempts: 5
    initial_delay_seconds: 1.0
    max_delay_seconds: 30.0
  output_root: "raw/ws/trade_xyz"
  write_control_messages: true
```

`src/sis/venues/trade_xyz/collection_config.py` には、既存config loaderの流儀に合わせて
typed configを追加する。

## CLI計画

CLI公開は collector 系に限定する。
backtest CLIは作らない。

### 追加コマンド

```bash
uv run sis collect-trade-xyz-ws \
  --symbols SP500 \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 60 \
  --heartbeat-seconds 30 \
  --output-dir data/raw/ws/trade_xyz
```

```bash
uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root data/raw/ws/trade_xyz
```

```bash
uv run sis build-trade-xyz-rest-parity \
  --ws-manifest-path data/manifests/trade_xyz_ws_capture_manifest.json
```

### dry-run

全コマンドに `--dry-run` を用意する。

`collect-trade-xyz-ws --dry-run` は次だけを行う。

```text
1. registry/configからsymbolを解決する
2. subscription名を検証する
3. 保存予定pathを表示する
4. ws_url / heartbeat / reconnect設定を表示する
5. network接続しない
6. raw JSONLを書かない
```

`build-* --dry-run` は、入力pathの存在確認と出力予定pathの表示までにする。

## タスク分解

この章のタスクを上から順に実行する。
タスクを飛ばしてCLIやsmokeへ進まない。

### 実装者用タスク台帳

| ID | 目的 | 対象ファイル | 範囲外 | 受け入れ基準 | 検証 | 破壊度 |
| --- | --- | --- | --- | --- | --- | --- |
| T0 | 計画と境界を確認する | `plan/TRADE_XYZ_DATA_COLLECTION_EXPANSION_IMPLEMENTATION_PLAN_2026-06-01.md`, `docs/TRADE_XYZ_DATA_COLLECTION_EXPANSION_OPTIONS_2026-06-01.md` | code変更 | 実装者が対象・禁止・検証を説明できる | `uv run python scripts/check_current_docs.py` | none |
| T1 | `websockets` を直接依存にする | `pyproject.toml`, `uv.lock` | WS実装 | `websockets>=15` が直接依存 | import smoke | low |
| T1.5 | WebSocket収集設定を追加する | `configs/trade_xyz_data_collection.yaml`, `src/sis/venues/trade_xyz/collection_config.py`, `tests/test_trade_xyz_collection_config.py` | symbol hardcode | configからws_url/subscription/heartbeatを読める | `uv run pytest -q tests/test_trade_xyz_collection_config.py` | low |
| T2 | raw envelope/schemaを固定する | `src/sis/venues/trade_xyz/ws_envelope.py`, `schemas/trade_xyz_ws_raw.v1.schema.json`, `tests/test_trade_xyz_ws_envelope.py`, `tests/test_trade_xyz_ws_raw_schema.py` | network接続 | source_ts_ms/recv_ts_ms/control messageを分離 | T2のpytest | low |
| T3 | fake sourceでWS recorder coreを実装する | `src/sis/venues/trade_xyz/ws_recorder.py`, `schemas/trade_xyz_ws_capture_manifest.v1.schema.json`, `tests/test_trade_xyz_ws_recorder.py` | real network必須化 | fake sourceでraw JSONLとcapture manifestが出る | T3のpytest | low |
| T4 | WS quality manifestを実装する | `src/sis/venues/trade_xyz/ws_quality.py`, `schemas/trade_xyz_ws_quality_manifest.v1.schema.json`, `tests/test_trade_xyz_ws_quality.py` | readiness policy変更 | gap/duplicate/bbo/control countが出る | T4のpytest | low |
| T5 | REST parity manifestを実装する | `src/sis/venues/trade_xyz/rest_parity.py`, `schemas/trade_xyz_rest_parity_manifest.v1.schema.json`, `src/sis/venues/trade_xyz/client.py`, `tests/test_trade_xyz_rest_parity.py`, `tests/test_trade_xyz_client.py` | write endpoint追加 | fake clientでparity manifestが出る | T5のpytest | low |
| T6 | collector CLIを登録する | `src/sis/commands/quotes.py`, `tests/test_trade_xyz_ws_cli.py` | backtest CLI | dry-runがnetwork/writeなしで完了 | CLI help + T6 pytest | low |
| T7 | collection statusへ表示する | `src/sis/venues/trade_xyz/collection_status.py`, `tests/test_trade_xyz_collection_status.py` | readiness判定変更 | manifestあり/なしを表示できる | T7 pytest | low |
| T8 | docsを現在の実装に合わせる | `docs/TRADE_XYZ_DATA_COLLECTION_EXPANSION_OPTIONS_2026-06-01.md`, `docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md` | code変更 | 実行方法・保存先・禁止事項が反映済み | docs checker + diff check | none |

破壊度:

```text
none:
  docs/checkのみ

low:
  tracked source/config/test/schemaのみ
  data/やlogs/の生成物をcommitしない
  外部writeや不可逆操作なし
```

### T0: 計画と境界確認

対象:

```text
plan/TRADE_XYZ_DATA_COLLECTION_EXPANSION_IMPLEMENTATION_PLAN_2026-06-01.md
docs/TRADE_XYZ_DATA_COLLECTION_EXPANSION_OPTIONS_2026-06-01.md
```

作業:

```text
1. この計画を正本としてレビューする
2. Phase 1の実装範囲が collector hardening のみであることを確認する
3. OSS導入をPhase 1から外すことを確認する
4. backtest/execution/paperへ触らないことを確認する
```

完了条件:

```text
実装者が対象ファイル・除外ファイル・テスト方針を説明できる
```

### T1: direct dependency追加

対象:

```text
pyproject.toml
uv.lock
```

作業:

```text
1. pyproject.toml の dependencies に `websockets>=15` を追加する
2. `uv lock` または repo標準のlock更新手順で uv.lock を更新する
3. websockets が直接依存として入ったことを確認する
```

完了条件:

```bash
uv run python - <<'PY'
import websockets
print(websockets.__version__)
PY
```

注意:

```text
uv.lockに既に存在するからといって、pyproject.tomlへの直接追加を省略しない
```

### T1.5: WebSocket config contract追加

対象:

```text
configs/trade_xyz_data_collection.yaml
src/sis/venues/trade_xyz/collection_config.py
tests/test_trade_xyz_collection_config.py
```

作業:

```text
1. websocket_collection sectionを追加する
2. default_subscriptionsを設定ファイルから読む
3. ws_urlを設定ファイルから読む
4. heartbeat_seconds / server_timeout_seconds / reconnect設定を読む
5. invalid subscriptionをconfig load時またはCLI実行時に検出する
6. 既存quote_collection設定を壊さない
```

テスト:

```text
既存configが引き続きloadできる
websocket_collectionがdefault値つきでloadできる
invalid subscriptionはValueErrorまたはCLI exit code 2になる
symbolsは既存symbols listを使い、コードへ固定しない
```

完了条件:

```bash
uv run pytest -q tests/test_trade_xyz_collection_config.py
```

### T2: WebSocket envelope実装

対象:

```text
src/sis/venues/trade_xyz/ws_envelope.py
schemas/trade_xyz_ws_raw.v1.schema.json
tests/test_trade_xyz_ws_envelope.py
tests/test_trade_xyz_ws_raw_schema.py
```

作業:

```text
1. raw JSONL rowを組み立てる純粋関数を作る
2. payload_sha256を安定計算する
3. subscription_hashを安定計算する
4. recv_ts_ms と recv_monotonic_ns を外から注入できるようにする
5. source_ts_ms/source_ts_fieldをpayload内fieldからだけ抽出する
6. channel/message_kindを分類する
7. subscriptionResponse / pong / unknownをcontrol messageとして分類する
8. symbol付き/なしsubscriptionを区別する
9. schema validation testを書く
```

テスト:

```text
同一payloadは同一payload_sha256になる
payload key順が違っても同一hashになる
symbol付きsubscriptionでは canonical_symbol / venue_symbol / coin が入る
global subscriptionでは symbol=__all__ としてpath解決できる
recv_ts_ms が oracle_ts_ms に変換されない
source_ts_msが無いpayloadではsource_ts_msを補完しない
subscriptionResponseはmessage_kind=subscription_responseになる
pongはmessage_kind=heartbeatになる
unknown shapeはmessage_kind=errorになる
```

完了条件:

```bash
uv run pytest -q tests/test_trade_xyz_ws_envelope.py tests/test_trade_xyz_ws_raw_schema.py
```

### T3: WebSocket recorder core実装

対象:

```text
src/sis/venues/trade_xyz/ws_recorder.py
schemas/trade_xyz_ws_capture_manifest.v1.schema.json
tests/test_trade_xyz_ws_recorder.py
```

作業:

```text
1. async message sourceを注入可能にする
2. 本番用は websockets.connect を使う
3. テスト用は fake async source を使う
4. append-only JSONL writerを作る
5. part file単位で安全にflushする
6. reconnect_count / error_count をmanifestへ出す
7. heartbeat_secondsごとにpingを送る
8. pong / subscriptionResponse をcontrol messageとして記録またはmanifest countへ反映する
9. duration_seconds または max_messages で停止できるようにする
10. reconnect時にconnection_idを変え、sequenceをconnection内で単調増加させる
```

テスト:

```text
fake source 3 messagesで3 JSONL rowsを書く
payloadごとに payload_sha256 が入る
duration/max_messagesで停止する
reconnect発生時に connection_count / reconnect_count が増える
malformed messageは error_count に入り、raw rowへ混ぜない
subscriptionResponse_countが増える
pong_count / heartbeat_sent_countが増える
dry_runではnetwork接続もraw書き込みもしない
```

完了条件:

```bash
uv run pytest -q tests/test_trade_xyz_ws_recorder.py
```

### T4: WebSocket quality manifest実装

対象:

```text
src/sis/venues/trade_xyz/ws_quality.py
schemas/trade_xyz_ws_quality_manifest.v1.schema.json
tests/test_trade_xyz_ws_quality.py
```

作業:

```text
1. raw WS JSONLを読み込む
2. subscription別 / symbol別 countを出す
3. duplicate_payload_countを出す
4. recv_ts_ms gapを計算する
5. source_ts_msがあるsubscriptionではsource_ts gapを別計算する
6. bbo payloadでは bid <= ask を検査する
7. subscriptionResponse / pong countを出す
8. malformed payloadを block_reasons へ入れる
9. status = pass / warn / fail を決める
```

初期statusルール:

```text
pass:
  row_count > 0
  malformed_payload_count = 0
  bbo_bid_ask_inversion_count = 0

warn:
  gap_count > 0
  source_ts_gap_count > 0
  duplicate_payload_count > 0

fail:
  row_count = 0
  malformed_payload_count > 0
  bbo_bid_ask_inversion_count > 0
```

テスト:

```text
正常BBOはpass
bid > ask はfail
同一payload_sha256重複はduplicate_countに入る
時間gapはgap_count/max_gap_secondsに入る
source_ts_msがある場合はsource_ts_gap_countに入る
subscriptionResponse / pong はdata row_countと区別される
空ファイルはfail
schema validationが通る
```

完了条件:

```bash
uv run pytest -q tests/test_trade_xyz_ws_quality.py
```

### T5: REST parity manifest実装

対象:

```text
src/sis/venues/trade_xyz/client.py
src/sis/venues/trade_xyz/rest_parity.py
schemas/trade_xyz_rest_parity_manifest.v1.schema.json
tests/test_trade_xyz_rest_parity.py
tests/test_trade_xyz_client.py
```

作業:

```text
1. 既存 TradeXyzClient を使う
2. 必要なら client.py にread-only info endpoint wrapperだけ追加する
3. allMids / metaAndAssetCtxs の最小parityを取る
4. l2Book parityは default off または max-symbols制限つきにする
5. perpsAtOpenInterestCap / perpDexStatus / perpDexLimits は取れる範囲でread-only metadataとして保存する
6. WS manifestのsymbolsとREST結果のsymbolsを比較する
7. rate-limit配慮としてrequest_delay_secondsを持つ
8. RESTだけでfill価格を作らない
9. REST結果をTrade[XYZ] WebSocket payloadの欠損検査としてだけ使う
10. 公式Docsまたは実payloadで確認できないendpointは推測実装せず、known gapとしてmanifestに残す
```

テスト:

```text
fake TradeXyzClientでREST payloadを注入できる
WSに存在してRESTにないsymbolはmissing_rest_symbolsに入る
RESTに存在してWSにないsymbolはmissing_ws_symbolsに入る
l2Book parityはdefaultでは全symbol実行されない
request_delay_secondsがmanifestに入る
未確認endpointはskipされ、block_reasonsまたはknown_gapsに入る
一致すればstatus=pass
不一致があればstatus=warnまたはfailになる
schema validationが通る
```

完了条件:

```bash
uv run pytest -q tests/test_trade_xyz_rest_parity.py tests/test_trade_xyz_client.py
```

### T6: CLI registration

対象:

```text
src/sis/commands/quotes.py
tests/test_trade_xyz_ws_cli.py
```

作業:

```text
1. register_quote_commands() に collector commandを追加する
2. dry-runが network/write なしで完了するようにする
3. --symbols は既存 registry 解決流儀に合わせる
4. --subscriptions はconfig defaultを使い、CLI指定で上書きできる
5. --max-symbols が必要なら既存collectorに合わせる
6. --output-dir は data/raw/ws/trade_xyz をdefaultにする
7. --ws-url / --heartbeat-seconds はconfig defaultを使い、CLI指定で上書きできる
8. CLI helpに collector intent が表示されることを確認する
```

テスト:

```text
uv run sis --help に新規commandが出る
collect-trade-xyz-ws --dry-run が dry_run=true を出す
dry-runでraw fileが作られない
invalid subscriptionはexit code 2
unknown symbolはexit code 2
CLI引数なしではconfigのdefault_subscriptionsを使う
```

完了条件:

```bash
uv run pytest -q tests/test_trade_xyz_ws_cli.py
uv run sis --help | rg 'collect-trade-xyz-ws|build-trade-xyz-ws-quality|build-trade-xyz-rest-parity'
```

### T7: collection statusへの表示追加

対象:

```text
src/sis/venues/trade_xyz/collection_status.py
tests/test_trade_xyz_collection_status.py
```

作業:

```text
1. WS capture manifestがある場合だけ collection status に表示する
2. manifestがない場合は known gap として表示する
3. readiness判定そのものは変えない
4. live readiness と read-only data readiness を混同しない
```

テスト:

```text
manifestありで ws_capture_status が表示される
manifestなしで missing_ws_capture_manifest が表示される
readiness pass/failの既存期待値を壊さない
```

完了条件:

```bash
uv run pytest -q tests/test_trade_xyz_collection_status.py
```

### T8: docs更新

対象:

```text
docs/TRADE_XYZ_DATA_COLLECTION_EXPANSION_OPTIONS_2026-06-01.md
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
```

作業:

```text
1. WebSocket recorder追加後の実行方法を記録する
2. WS raw / existing raw quotes / external provider の保存先分離を明記する
3. 2026-05-30以前の実データを使わないことを再明記する
4. OSS候補は sidecar/probe として残し、Phase 1実装済みと誤読されないようにする
5. Markdown metadata headerの更新日を更新する
```

完了条件:

```bash
uv run python scripts/check_current_docs.py
git diff --check
```

## テスト方針

### 原則

```text
CI / unit tests:
  live networkを使わない
  fake source / fake client / fixtureで検証する

smoke:
  dry-run中心
  network接続は明示コマンドだけ

実データ収集:
  operatorが明示的に実行する
  raw dataとmanifestは基本的にgit管理しない
```

### 必須テスト

```text
tests/test_trade_xyz_ws_envelope.py
tests/test_trade_xyz_ws_raw_schema.py
tests/test_trade_xyz_ws_recorder.py
tests/test_trade_xyz_ws_quality.py
tests/test_trade_xyz_rest_parity.py
tests/test_trade_xyz_ws_cli.py
tests/test_trade_xyz_collection_status.py
```

### 実行コマンド

変更箇所に近いテスト:

```bash
uv run pytest -q \
  tests/test_trade_xyz_ws_envelope.py \
  tests/test_trade_xyz_ws_raw_schema.py \
  tests/test_trade_xyz_ws_recorder.py \
  tests/test_trade_xyz_ws_quality.py \
  tests/test_trade_xyz_rest_parity.py \
  tests/test_trade_xyz_ws_cli.py
```

関連既存テスト:

```bash
uv run pytest -q \
  tests/test_trade_xyz_collector.py \
  tests/test_trade_xyz_collection_config.py \
  tests/test_trade_xyz_collection_status.py \
  tests/test_trade_xyz_client.py \
  tests/test_trade_xyz_data_readiness.py \
  tests/test_cli_smoke.py
```

品質ゲート:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
uv run python scripts/check_current_docs.py
git diff --check
```

最終ゲート:

```bash
./scripts/check
```

## 完了条件

この計画の実装は、次をすべて満たしたら完了とする。

```text
1. WebSocket raw recorderが fake source でテスト済み
2. WebSocket raw JSONL rowが schema_version / channel / message_kind / payload_sha256 / recv_ts_ms を持つ
3. source_ts_ms と recv_ts_ms を分離している
4. recv_ts_ms / recv_monotonic_ns を oracle_ts_ms と誤用していない
5. WS rawは data/raw/ws/trade_xyz/ に分離されている
6. 既存 data/raw/quotes/trade_xyz/ へ直接混ぜていない
7. quality manifest が duplicate / gap / bid-ask inversion / malformed を出せる
8. quality manifest が subscriptionResponse / pong / heartbeat countを出せる
9. REST parity manifest が既存 TradeXyzClient で作れる
10. REST parity がrate limit配慮をmanifestに残す
11. 新規CLIは dry-run で network/write なしに完了する
12. symbol/subscription/ws_url/heartbeatがconfigまたはCLIから解決され、コード固定されていない
13. `websockets>=15` が pyproject.toml の直接依存になっている
14. backtest / execution / paper / wallet / signing / exchange write を変更していない
15. 2026-05-30以前の実データをreadinessへ戻していない
16. 追加docsが current docs checker を通る
17. 近接テスト・lint・type check・docs checkが通る
```

## 実データsmoke手順

実装後、operatorが明示的に実行する。
この手順はCIには入れない。

```bash
uv run sis collect-trade-xyz-ws \
  --symbols SP500 \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 10 \
  --heartbeat-seconds 30 \
  --output-dir data/raw/ws/trade_xyz
```

```bash
uv run sis build-trade-xyz-ws-quality \
  --raw-ws-root data/raw/ws/trade_xyz
```

```bash
uv run sis build-trade-xyz-rest-parity \
  --ws-manifest-path data/manifests/trade_xyz_ws_capture_manifest.json
```

smokeの合格条件:

```text
row_count > 0
error_count = 0
malformed_payload_count = 0
bbo_bid_ask_inversion_count = 0
subscription_response_count > 0
heartbeat_sent_count >= 0
manifest schema validation pass
raw path が data/raw/ws/trade_xyz/ 配下
```

smokeの不合格を、実装失敗と即断しない。
network、subscription名、symbol、Hyperliquid側仕様変更の可能性を manifest に分けて記録する。

## 残リスクと潰し方

### R1: WebSocket subscription名の仕様差

リスク:

```text
公式WS subscription名やpayload形状が想定と違う可能性がある
```

潰し方:

```text
1. 実装時に最小smokeで実payloadを保存する
2. payloadをschemaへ即固定しすぎない
3. unknown payloadは捨てず、malformed/unknownとしてmanifestに記録する
```

### R2: websocketsがtransitive dependencyのままになる

リスク:

```text
uv.lockに存在しても、直接依存でなければ将来消える
```

潰し方:

```text
pyproject.tomlへ `websockets>=15` を追加する
```

### R3: WS rawと既存quotesを混ぜてしまう

リスク:

```text
source semanticsが違うrawを同一rootへ入れると、normalizerが誤読する
```

潰し方:

```text
WS rawは data/raw/ws/trade_xyz/ に固定する
既存 quotes.parquet への取り込みは別タスクにする
```

### R4: 外部providerをTrade[XYZ]正本として使ってしまう

リスク:

```text
real_market_referenceやccxtをfill/mark/oracle/fundingの代替にするとBTが歪む
```

潰し方:

```text
data/external/ または data/staging/ に分離する
manifestに source_tier = external_reference を出す
oracle_ts_ms へ変換しない
```

### R5: 2026-05-30以前のデータが戻る

リスク:

```text
古い実データがreadinessやBT smokeへ混ざる
```

潰し方:

```text
configs/trade_xyz_data_collection.yaml の usable_start_date = 2026-05-31 を維持する
manifestに data_cutoff を出す
pre-2026-05-31 dataは archive扱いにする
```

### R6: readiness判定を一気に変えてしまう

リスク:

```text
collector追加とreadiness policy変更を同時に行うと、何が効いたか分からない
```

潰し方:

```text
Phase 1では status表示まで
readiness pass/fail policy変更は別タスクにする
```

### R7: control messageをmarket dataとして数えてしまう

リスク:

```text
subscriptionResponse / pong / error summaryをbbo/trades等のdata rowと同じ扱いにすると、
coverageやgap評価が歪む
```

潰し方:

```text
message_kindを必須化する
control messageはsubscription=__control__に分離する
quality manifestでdata_countとcontrol_countを分ける
```

### R8: activeAssetCtxにsource_ts_msを補完してしまう

リスク:

```text
ctxに時刻fieldが無い場合、recv_ts_msをsource_ts_msとして入れるとmark/oracle/fundingの時刻を誤読する
```

潰し方:

```text
payload内に公式時刻fieldが無い場合はsource_ts_ms=nullにする
oracle timestamp provenanceはknown gapのまま扱う
```

### R9: REST parityでrate limitを踏む

リスク:

```text
l2Book等を全symbolへ高頻度に叩くとrate limitや一時failをcollector品質問題と誤認する
```

潰し方:

```text
l2Book parityはdefault offまたはmax-symbols制限
request_delay_secondsを持つ
request_count / request_error_count / rate_limit_sleep_secondsをmanifestに出す
```

## Betterにする余地

Phase 1完了後に、次を検討する。

```text
1. hyperliquid-python-sdk probe:
   既存 TradeXyzClient とpayload差分を比較するだけのprobeを作る

2. ccxt_reference:
   external comparisonとしてOHLCV/ticker/orderbookを保存する

3. dlt_staging:
   external/provider系データのschema driftとincremental loadに使う

4. Alpaca official SDK:
   既存Alpaca providerの保守性を上げる

5. paid vendor sidecar:
   Databento / Massive / Tardis / Allium / 0xArchive 等を必要時だけ評価する
```

ただし、これらはすべて Phase 1 のWebSocket raw captureとquality manifestが安定してから行う。

## 実装順序

最短で安全に進める順序。

```text
1. T1 direct dependency追加
2. T1.5 WebSocket config contract追加
3. T2 ws_envelope
4. T3 ws_recorder core
5. T4 ws_quality
6. T5 rest_parity
7. T6 CLI registration
8. T7 collection status
9. T8 docs update
10. 近接テスト
11. lint / format / type / docs
12. ./scripts/check
13. operator smoke
```

## 仕様化readiness

```text
ready with assumptions
```

前提:

```text
1. Phase 1では公式WebSocket captureを追加する
2. backtest/execution/paperは変更しない
3. OSS client導入はPhase 1では行わない
4. WebSocket subscription名やpayload形状は、実装時の最小smokeで確認し、必要ならこの文書を更新する
5. source_ts_msは公式payload内fieldからのみ採用し、recv_ts_msでは補完しない
```
