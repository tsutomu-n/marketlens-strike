<!--
作成日: 2026-06-01_17:40 JST
更新日: 2026-06-01_17:40 JST
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

2026-06-01_17:40 JST 時点で確認した事実。

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

schemas/trade_xyz_ws_capture_manifest.v1.schema.json
schemas/trade_xyz_ws_quality_manifest.v1.schema.json
schemas/trade_xyz_rest_parity_manifest.v1.schema.json

tests/test_trade_xyz_ws_envelope.py
tests/test_trade_xyz_ws_recorder.py
tests/test_trade_xyz_ws_quality.py
tests/test_trade_xyz_rest_parity.py
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
src/sis/commands/quotes.py
src/sis/venues/trade_xyz/collection_status.py
docs/TRADE_XYZ_DATA_COLLECTION_EXPANSION_OPTIONS_2026-06-01.md
docs/TRADE_XYZ_REAL_DATA_COLLECTION_CURRENT_RECORD_2026-06-01.md
```

`pyproject.toml` / `uv.lock` は、`websockets>=15` を直接依存にするために変更する。
`uv.lock` に既に `websockets 15.0.1` があるとしても、直接依存でない状態に頼らない。

`collection_status.py` は、WS manifestが存在する場合に状態へ表示するだけに留める。
readiness pass/fail判定を変える場合は、別PRまたは別タスクにする。

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

### WebSocket raw JSONL row

1行1payloadで保存する。

```json
{
  "schema_version": "trade_xyz_ws_raw.v1",
  "source": "hyperliquid_ws",
  "dex": "xyz",
  "subscription": "bbo",
  "subscription_hash": "sha256:...",
  "connection_id": "20260601T084000Z-0001",
  "recv_ts_ms": 1780000000000,
  "recv_monotonic_ns": 1234567890,
  "canonical_symbol": "SP500",
  "venue_symbol": "xyz:SP500",
  "coin": "xyz:SP500",
  "payload_sha256": "sha256:...",
  "payload": {}
}
```

必須項目:

```text
schema_version
source
dex
subscription
subscription_hash
connection_id
recv_ts_ms
recv_monotonic_ns
payload_sha256
payload
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
```

### Normalized artifact

Phase 1では、normalized quotesへ直接混入しない。
必要な場合は、WS専用normalized artifactを別名で出す。

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
bbo_bid_ask_inversion_count
malformed_payload_count
unknown_symbol_count
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
status
block_reasons
```

## CLI計画

CLI公開は collector 系に限定する。
backtest CLIは作らない。

### 追加コマンド

```bash
uv run sis collect-trade-xyz-ws \
  --symbols SP500 \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 60 \
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
4. network接続しない
5. raw JSONLを書かない
```

`build-* --dry-run` は、入力pathの存在確認と出力予定pathの表示までにする。

## タスク分解

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

### T2: WebSocket envelope実装

対象:

```text
src/sis/venues/trade_xyz/ws_envelope.py
schemas/trade_xyz_ws_capture_manifest.v1.schema.json
tests/test_trade_xyz_ws_envelope.py
```

作業:

```text
1. raw JSONL rowを組み立てる純粋関数を作る
2. payload_sha256を安定計算する
3. subscription_hashを安定計算する
4. recv_ts_ms と recv_monotonic_ns を外から注入できるようにする
5. symbol付き/なしsubscriptionを区別する
6. schema validation testを書く
```

テスト:

```text
同一payloadは同一payload_sha256になる
payload key順が違っても同一hashになる
symbol付きsubscriptionでは canonical_symbol / venue_symbol / coin が入る
global subscriptionでは symbol=__all__ としてpath解決できる
recv_ts_ms が oracle_ts_ms に変換されない
```

完了条件:

```bash
uv run pytest -q tests/test_trade_xyz_ws_envelope.py
```

### T3: WebSocket recorder core実装

対象:

```text
src/sis/venues/trade_xyz/ws_recorder.py
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
7. duration_seconds または max_messages で停止できるようにする
```

テスト:

```text
fake source 3 messagesで3 JSONL rowsを書く
payloadごとに payload_sha256 が入る
duration/max_messagesで停止する
reconnect発生時に connection_count / reconnect_count が増える
malformed messageは error_count に入り、raw rowへ混ぜない
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
5. bbo payloadでは bid <= ask を検査する
6. malformed payloadを block_reasons へ入れる
7. status = pass / warn / fail を決める
```

初期statusルール:

```text
pass:
  row_count > 0
  malformed_payload_count = 0
  bbo_bid_ask_inversion_count = 0

warn:
  gap_count > 0
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
src/sis/venues/trade_xyz/rest_parity.py
schemas/trade_xyz_rest_parity_manifest.v1.schema.json
tests/test_trade_xyz_rest_parity.py
```

作業:

```text
1. 既存 TradeXyzClient を使う
2. allMids / metaAndAssetCtxs / l2Book の最小parityを取る
3. WS manifestのsymbolsとREST結果のsymbolsを比較する
4. RESTだけでfill価格を作らない
5. REST結果をTrade[XYZ] WebSocket payloadの欠損検査としてだけ使う
```

テスト:

```text
fake TradeXyzClientでREST payloadを注入できる
WSに存在してRESTにないsymbolはmissing_rest_symbolsに入る
RESTに存在してWSにないsymbolはmissing_ws_symbolsに入る
一致すればstatus=pass
不一致があればstatus=warnまたはfailになる
schema validationが通る
```

完了条件:

```bash
uv run pytest -q tests/test_trade_xyz_rest_parity.py
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
4. --max-symbols が必要なら既存collectorに合わせる
5. --output-dir は data/raw/ws/trade_xyz をdefaultにする
6. CLI helpに collector intent が表示されることを確認する
```

テスト:

```text
uv run sis --help に新規commandが出る
collect-trade-xyz-ws --dry-run が dry_run=true を出す
dry-runでraw fileが作られない
invalid subscriptionはexit code 2
unknown symbolはexit code 2
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
  tests/test_trade_xyz_ws_recorder.py \
  tests/test_trade_xyz_ws_quality.py \
  tests/test_trade_xyz_rest_parity.py \
  tests/test_trade_xyz_ws_cli.py
```

関連既存テスト:

```bash
uv run pytest -q \
  tests/test_trade_xyz_collector.py \
  tests/test_trade_xyz_collection_status.py \
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
2. WebSocket raw JSONL rowが schema_version / payload_sha256 / recv_ts_ms を持つ
3. recv_ts_ms / recv_monotonic_ns を oracle_ts_ms と誤用していない
4. WS rawは data/raw/ws/trade_xyz/ に分離されている
5. 既存 data/raw/quotes/trade_xyz/ へ直接混ぜていない
6. quality manifest が duplicate / gap / bid-ask inversion / malformed を出せる
7. REST parity manifest が既存 TradeXyzClient で作れる
8. 新規CLIは dry-run で network/write なしに完了する
9. `websockets>=15` が pyproject.toml の直接依存になっている
10. backtest / execution / paper / wallet / signing / exchange write を変更していない
11. 2026-05-30以前の実データをreadinessへ戻していない
12. 追加docsが current docs checker を通る
13. 近接テスト・lint・type check・docs checkが通る
```

## 実データsmoke手順

実装後、operatorが明示的に実行する。
この手順はCIには入れない。

```bash
uv run sis collect-trade-xyz-ws \
  --symbols SP500 \
  --subscriptions bbo,trades,activeAssetCtx \
  --duration-minutes 10 \
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
2. T2 ws_envelope
3. T3 ws_recorder core
4. T4 ws_quality
5. T5 rest_parity
6. T6 CLI registration
7. T7 collection status
8. T8 docs update
9. 近接テスト
10. lint / format / type / docs
11. ./scripts/check
12. operator smoke
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
```

