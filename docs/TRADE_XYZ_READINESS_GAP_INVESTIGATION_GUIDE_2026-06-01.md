# Trade[XYZ] Readiness Gap Investigation Guide

作成日: 2026-06-01_14:36 JST

この文書は、現在 `quote_coverage` と `real_market_reference` が fail、`account_specific_fee` と `oracle_timestamp_provenance` が known gap になっている理由を、第三者が調査できる粒度で分解する。

コードと生成済みartifactを正とする。目的は戦略最適化ではなく、Trade[XYZ]実データを誤読せずに `run_backtest()` へ流すための不足調査である。

## 1. 現在の結論

現時点では、実務バックテスト用のデータはまだ ready ではない。

確認コマンド:

```bash
uv run sis trade-xyz-collection-status --no-refresh-coverage --no-refresh-readiness
```

確認時点の主な値:

```text
decision: COLLECT_MORE_QUOTES
backtest_data_ready: false
readiness_decision: NOT_READY
fail_count: 2
known_gap_count: 2

failing_requirements:
  - quote_coverage
  - real_market_reference

known_gap_requirements:
  - account_specific_fee
  - oracle_timestamp_provenance
```

この状態を「バックテスト可能」と言う場合でも、実務上は plumbing smoke までである。戦略評価、優位性判断、成績比較、資金投入判断には使わない。

## 2. 正本となるコードとartifact

判定ロジック:

```text
src/sis/venues/trade_xyz/readiness.py
src/sis/venues/trade_xyz/coverage.py
src/sis/venues/trade_xyz/collection_status.py
src/sis/commands/quotes.py
configs/trade_xyz_data_collection.yaml
```

現在状態のartifact:

```text
data/ops/trade_xyz_collection_status.json
data/reports/trade_xyz_collection_status.md
data/manifests/trade_xyz_data_readiness_manifest.json
data/manifests/trade_xyz_quote_coverage_manifest.json
data/manifests/trade_xyz_real_market_reference_manifest.json
data/manifests/trade_xyz_account_fee_manifest.json
data/manifests/oracle_timestamp_manifest.json
data/manifests/funding_manifest.json
data/archive/pre_2026_05_31_unusable_real_data/ARCHIVE_MANIFEST.json
```

注意:

```text
--no-refresh-coverage / --no-refresh-readiness は status確認用。
coverage/readiness manifestを再計算した証明にはならない。
最終確認では --refresh-coverage --refresh-readiness または --strict --fail-on-not-ready を使う。
```

## 3. 問題1: quote_coverage fail

### 3.1 何が問題か

`quote_coverage` は、Trade[XYZ] quote snapshot が、対象銘柄ごとに十分な期間・十分な連続性で集まっているかを見る。

現状:

```text
coverage_passed: false
symbol_count: 11
row_count: 4917
raw_row_count: 4917
traceable_only: true
coverage_completion_ratio_by_span: 0.010391765288194443
estimated_max_collection_days_required: 30
```

主因は、行数そのものよりも期間不足である。現在は各symbolの有効spanが約0.31日で、設定上必要な30日に届いていない。

### 3.2 なぜ fail になるか

`src/sis/venues/trade_xyz/readiness.py` の `_quote_coverage_requirement()` は、`data/manifests/trade_xyz_quote_coverage_manifest.json` の `coverage_passed` を見る。

`coverage_passed=false` なら、理由が何であれ `quote_coverage` は fail である。

現在見るべき主なmanifest field:

```text
coverage_passed
traceable_only
row_count
raw_row_count
excluded_missing_raw_payload_ref_count
raw_payload_ref_missing_rate_all_rows
per_symbol.*.span_days
per_symbol.*.min_days_required
per_symbol.*.max_gap_seconds
per_symbol.*.coverage_status
per_symbol.*.insufficient_reasons
per_symbol.*.missing_rates
```

### 3.3 何を調べるべきか

まず、現在のcoverage manifestを再計算する。

```bash
uv run sis build-trade-xyz-quote-coverage \
  --min-days 30 \
  --max-gap-minutes 10 \
  --traceable-only
```

次に status を再計算込みで見る。

```bash
uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

調査すること:

```text
1. 11銘柄すべてが対象になっているか
2. per_symbol.*.span_days が伸びているか
3. per_symbol.*.max_gap_seconds が 600秒以内に収まっているか
4. insufficient_reasons が span_days_below_min だけか
5. missing_rates.raw_payload_ref が 0.0 か
6. exec_buy_price / exec_sell_price / fee_bps / funding_rate の欠損率が増えていないか
7. collector_running=true なのに traceable row が増えない状態になっていないか
```

### 3.4 解決方法

基本解は、有効なquote collectionを継続することである。

```bash
scripts/collect_trade_xyz_data_until_ready.sh
```

collectorがすでに動いているなら、理由なく止めない。止める場合は、coverageの到達が遅れるだけで、既存データは壊れない。

historical archive backfill を使う場合は、AWS requester-pays の前提を解決する必要がある。

```bash
scripts/check_trade_xyz_data_prereqs.sh
uv run sis check-trade-xyz-historical-archive-preflight
```

ただし、5/30以前の実データは禁止である。archive済みデータを戻して `coverage_passed=true` に見せてはいけない。

### 3.5 完了条件

```text
data/manifests/trade_xyz_quote_coverage_manifest.json:
  coverage_passed: true
  traceable_only: true
  symbol_count: 11
  per_symbol.*.coverage_status: pass
  per_symbol.*.span_days >= 30.0
  per_symbol.*.max_gap_seconds <= 600
```

## 4. 問題2: real_market_reference fail

### 4.1 何が問題か

`real_market_reference` は、Trade[XYZ]商品を検証するための外部参照系列である。これはlive execution dataではなく、research/backtest用の参照データである。

現状:

```text
status: fail
provider: yfinance
interval: 1d
row_count: 2
returned_symbols:
  - EURUSD=X
  - USDJPY=X
missing_mapped_symbols:
  - AAPL
  - AMD
  - AMZN
  - EWJ
  - GOOGL
  - META
  - MSFT
  - NVDA
  - QQQ
  - SPY
  - TSLA
missing_requested_symbols:
  - AAPL
  - AMD
  - AMZN
  - EWJ
  - GOOGL
  - META
  - MSFT
  - NVDA
  - QQQ
  - SPY
  - TSLA
  - UUP
  - ^VIX
```

5/30以前のreference dataをarchiveしたため、`--start 2026-05-31` で取り直した。しかし 2026-05-31 は市場休場で、多くの株式・ETF・index proxyが返っていない。

### 4.2 なぜ fail になるか

`src/sis/venues/trade_xyz/readiness.py` の `_real_market_reference_requirement()` は、以下をすべて満たす場合だけ pass にする。

```text
manifest.status == "pass"
row_count > 0
missing_mapped_symbols が空
missing_requested_symbols が空
```

現在は `row_count=2` で、欠損symbolが残っているため fail である。

### 4.3 何を調べるべきか

まず現在のmanifestを見る。

```bash
uv run python - <<'PY'
import json
from pathlib import Path

p = Path("data/manifests/trade_xyz_real_market_reference_manifest.json")
data = json.loads(p.read_text())
for key in [
    "generated_at",
    "status",
    "provider",
    "interval",
    "row_count",
    "requested_symbols",
    "returned_symbols",
    "missing_mapped_symbols",
    "missing_requested_symbols",
]:
    print(key, data.get(key))
PY
```

調査すること:

```text
1. 欠損symbolが市場休場によるものか
2. yfinance側の一時的取得失敗か
3. registryの real_market_symbol mapping が正しいか
4. extra regime symbols の ^VIX / UUP が必要か
5. 取得期間 start/end が市場営業日を含んでいるか
6. 5/30以前禁止ルールに反して古いreferenceを戻していないか
```

### 4.4 解決方法

開場日を含む期間で再取得する。

```bash
uv run sis collect-trade-xyz-real-market-reference \
  --start 2026-05-31 \
  --interval 1d
```

必要なら、終了日を明示して市場営業日を含める。

```bash
uv run sis collect-trade-xyz-real-market-reference \
  --start 2026-05-31 \
  --end 2026-06-03 \
  --interval 1d
```

再取得後:

```bash
uv run sis build-trade-xyz-data-readiness
uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

### 4.5 完了条件

```text
data/manifests/trade_xyz_real_market_reference_manifest.json:
  status: pass
  row_count > 0
  missing_mapped_symbols: []
  missing_requested_symbols: []
```

## 5. 問題3: account_specific_fee known gap

### 5.1 何が問題か

symbol-level fee snapshot はあるが、実アカウント固有のfeeが未取得である。

現状:

```text
account_fee_user_address_configured: false
account_fee_manifest_exists: false
account_fee_manifest_status: null
account_fee_user_taker_fee_bps: null
account_fee_user_maker_fee_bps: null
```

この状態で、実アカウントの maker/taker fee を知っているとは言えない。

### 5.2 なぜ known gap になるか

`src/sis/venues/trade_xyz/readiness.py` の `_fee_requirement()` は、`data/manifests/trade_xyz_account_fee_manifest.json` があり、次を満たす場合だけ `account_specific_fee` を pass にする。

```text
status == "pass"
parsed.user_taker_fee_bps が null ではない
parsed.user_maker_fee_bps が null ではない
envに SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS がある場合は manifestのuser hashと一致
```

manifestが無い場合、symbol-level fee manifest が `account_specific_fee_status=not_collected_no_wallet_or_user_context` を持っていれば known gap になる。

### 5.3 何を調べるべきか

調査すること:

```text
1. public user addressを使ってよいか
2. そのaddressは実際に評価対象のアカウントか
3. SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS が設定されているか
4. trade_xyz_account_fee_manifest.json が存在するか
5. manifest内の user_address_sha256 が env設定値のsha256と一致するか
6. parsed.user_taker_fee_bps / parsed.user_maker_fee_bps が入っているか
7. builder feeが必要な戦略か
```

確認コマンド:

```bash
printenv SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS
uv run sis trade-xyz-collection-status --fail-on-account-fee-missing
```

### 5.4 解決方法

public user addressを設定し、read-onlyで userFees を取得する。

```bash
export SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=0x...
uv run sis collect-trade-xyz-account-fee \
  --user-address "$SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS"
uv run sis build-trade-xyz-data-readiness
```

これはread-onlyであり、wallet、秘密鍵、signing、live order、exchange writeは不要である。

### 5.5 完了条件

```text
data/manifests/trade_xyz_account_fee_manifest.json:
  status: pass
  user_address_sha256: present
  parsed.user_taker_fee_bps: present
  parsed.user_maker_fee_bps: present

trade-xyz-collection-status:
  account_fee_manifest_exists: true
  account_fee_manifest_status: pass
  account_fee_manifest_user_matches_env: true または env未設定で比較対象なし
  account_fee_user_taker_fee_bps: not null
  account_fee_user_maker_fee_bps: not null
```

## 6. 問題4: oracle_timestamp_provenance known gap

### 6.1 何が問題か

oracle price 自体は quote snapshot にあるが、その oracle price がいつの時点の値なのかを示す独立した `oracle_ts_ms` がsource payloadに無い。

現状:

```text
oracle_timestamp_provenance_status: known_gap
oracle_ts_missing_rate: 1.0

data/manifests/oracle_timestamp_manifest.json:
  row_count: 4851
  oracle_ts_present_count: 0
  oracle_ts_missing_count: 4851
  oracle_ts_missing_reasons:
    asset_ctx_missing_oracle_timestamp_field: 4851
```

### 6.2 なぜ known gap になるか

`src/sis/venues/trade_xyz/readiness.py` の `_oracle_requirement()` は、`oracle_timestamp_manifest.json` を見る。

判定:

```text
row_count <= 0:
  fail

oracle_ts_missing_count > 0 または oracle_ts_present_count <= 0:
  known_gap

全rowにoracle timestampがある:
  pass
```

現状は row はあるが `oracle_ts_ms` が全欠損なので known gap である。

### 6.3 何を調べるべきか

調査すること:

```text
1. raw quote JSONLのasset context payloadにoracle timestamp相当fieldが本当に無いか
2. Hyperliquid / Trade[XYZ] の該当public endpointにoracle timestampが存在するか
3. 取得しているpayloadのどの階層に oracle price / mark price / recv_ts / source_ts があるか
4. source_ts_ms が l2Book timestampなのか、oracle timestampなのか
5. recv_ts_ms / client timestamp を oracle_ts_ms に読み替えていないか
6. oracle price freshnessを別の方法で評価する必要があるか
```

確認コマンド例:

```bash
uv run sis build-trade-xyz-reference-data
uv run sis build-trade-xyz-data-readiness
uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

raw payload確認例:

```bash
uv run python - <<'PY'
import json
from pathlib import Path

paths = sorted(Path("data/raw/quotes/trade_xyz").glob("*.jsonl"))
for path in paths[:1]:
    for line in path.read_text().splitlines()[:3]:
        row = json.loads(line)
        print(json.dumps(row, indent=2, sort_keys=True)[:4000])
PY
```

### 6.4 解決方法

現時点で安全な解決は、source payloadにoracle timestampがあるかを確認し、ある場合だけ parser / manifest に追加することである。

やってはいけないこと:

```text
source_ts_ms を oracle_ts_ms として使う
recv timestamp を oracle_ts_ms として使う
client timestamp を oracle_ts_ms として使う
欠損を現在時刻で埋める
oracle_ts_ms が無いのに freshness確認済みと書く
```

sourceに無い場合は、known gapとして残す。これは実装漏れではなく、誤読防止のためのfail-softである。

### 6.5 完了条件

passにするなら:

```text
data/manifests/oracle_timestamp_manifest.json:
  row_count > 0
  oracle_ts_present_count == row_count
  oracle_ts_missing_count == 0
  oracle_ts_missing_rate == 0.0
```

sourceに無いと判断するなら:

```text
known gapとして維持
raw payload調査結果をdocsに記録
run_backtest()側でoracle timestamp freshnessを前提にした評価をしない
```

## 7. 優先順位

現実的な順序:

```text
1. quote_coverage
   collectorを継続し、30日spanを満たす。最も時間がかかる。

2. real_market_reference
   市場営業日を含む期間で再取得する。解決しやすい。

3. account_specific_fee
   public user addressを決めてread-only取得する。秘密鍵不要。

4. oracle_timestamp_provenance
   source payload調査が必要。sourceに無ければknown gapとして残す。
```

## 8. まとめて確認するコマンド

最新状態を正しく見る:

```bash
uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

strict gate:

```bash
uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
```

外部前提:

```bash
scripts/check_trade_xyz_data_prereqs.sh
```

個別manifest:

```bash
uv run sis build-trade-xyz-quote-coverage --traceable-only
uv run sis collect-trade-xyz-real-market-reference --start 2026-05-31 --interval 1d
uv run sis collect-trade-xyz-account-fee --user-address 0x...
uv run sis build-trade-xyz-reference-data
uv run sis build-trade-xyz-data-readiness
```

## 9. 完了条件

最終的には以下を満たす。

```text
trade-xyz-collection-status:
  backtest_data_ready: true
  readiness_decision: READY
  fail_count: 0
  known_gap_count: 0

quote_coverage:
  pass

real_market_reference:
  pass

account_specific_fee:
  pass

oracle_timestamp_provenance:
  pass
```

ただし、`oracle_timestamp_provenance` がsource仕様上取得不能と確認された場合は、以下の条件で known gap として維持する。

```text
readiness_decision:
  READY_WITH_KNOWN_GAPS only

docs:
  raw payload調査結果を記録

backtest:
  oracle timestamp freshnessを前提にしない
```

`READY_WITH_KNOWN_GAPS` を、完全な実務readyと呼んではいけない。

## 10. 誤謬リスク

特に危険な誤読:

```text
row_countが増えたのでquote_coverage passだと判断する
real_market_referenceのrow_count>0だけでpassだと判断する
5/30以前のarchive dataを戻して欠損を埋める
symbol-level feeをaccount-specific feeだと扱う
recv/client/source timestampをoracle timestampとして扱う
--no-refresh-readiness後の古いreadiness manifestを最新状態と同一視する
signal candlesをfill snapshotとして使う
known gapを無視してREADYと言う
```

この文書で扱う4項目は、いずれも live/paper/wallet/signing/exchange write を必要としない。解決作業は read-only の範囲で行う。
