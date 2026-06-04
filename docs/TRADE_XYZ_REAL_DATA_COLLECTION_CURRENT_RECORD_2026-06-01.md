<!--
作成日: 2026-06-01_15:03 JST
更新日: 2026-06-05_08:05 JST
-->

# Trade[XYZ] Real Data Collection Current Record

更新日: 2026-06-05_08:05 JST

この文書は、第三者が `marketlens-strike` の現在状態を引き継ぐための記録である。コード、設定、生成済みartifactを正として書く。

この文書は追記型の履歴記録でもある。古い節にある pytest 件数、current-docs count、row count、fail list はその節の timestamp 時点の snapshot として読み、現在判断は最新節、`README.md`、`docs/CURRENT_STATE.md`、`docs/CODE_STATUS.md`、`docs/OPERATIONS_RUNBOOK.md`、および生成済み manifest を優先する。

## 0. 追加実装（2026-06-01_18:18 JST）

Trade[XYZ] 実データhardening向けに、次を実装済み。

```text
WebSocket capture:
  uv run sis collect-trade-xyz-ws

WebSocket quality manifest:
  uv run sis build-trade-xyz-ws-quality

REST parity manifest:
  uv run sis build-trade-xyz-rest-parity
```

生成されるmanifest:

```text
data/manifests/trade_xyz_ws_capture_manifest.json
data/manifests/trade_xyz_ws_quality_manifest.json
data/manifests/trade_xyz_rest_parity_manifest.json
```

保存境界:

```text
WS raw:
  data/raw/ws/trade_xyz/

既存raw quotes:
  data/raw/quotes/trade_xyz/

ルール:
  WS raw と既存 raw quotes を混ぜない
  recv_ts_ms を source/oracle timestampとして使わない
```

## 0.1 WS smoke後の追加実装と実測（2026-06-01_19:51 JST）

`plan/TRADE_XYZ_AFTER_WS_SMOKE_DATA_READY_PLAN_2026-06-01.md` の T1 から T4 まで進めた。

実装済み:

```text
application-level heartbeat:
  timeout時に WebSocket protocol ping ではなく { "method": "ping" } を送る
  heartbeat_sent_count は送信した application ping 数
  pong_count は受信した { "channel": "pong" } row 数

deadline stop:
  source側にも stop_time_monotonic を渡し、期限後に追加ping待ちで残らないようにした

trades list payload symbol resolution:
  trades.data[] の coin が単一なら canonical_symbol / coin / path partition に反映する
  mixed coin payload は単一symbolとして扱わない
```

近接テスト:

```bash
uv run pytest -q tests/test_trade_xyz_ws_recorder.py tests/test_trade_xyz_ws_envelope.py tests/test_trade_xyz_ws_quality.py
uv run ruff check src/sis/venues/trade_xyz/ws_recorder.py src/sis/venues/trade_xyz/ws_envelope.py tests/test_trade_xyz_ws_recorder.py tests/test_trade_xyz_ws_envelope.py
uv run ruff format --check src/sis/venues/trade_xyz/ws_recorder.py src/sis/venues/trade_xyz/ws_envelope.py tests/test_trade_xyz_ws_recorder.py tests/test_trade_xyz_ws_envelope.py
```

確認済み:

```text
pytest:
  14 passed

ruff check:
  pass

ruff format --check:
  pass
```

heartbeat 実測:

```text
output:
  .tmp/trade_xyz_ws_deadline_probe_20260601_1945/

symbols:
  EWJ

subscriptions:
  trades

duration:
  1 minute

capture:
  row_count: 13
  reconnect_count: 0
  error_count: 0
  heartbeat_sent_count: 11
  pong_count: 11
  subscription_response_count: 1

quality:
  status: pass
  row_count: 13
  pong_count: 11
  gap_count: 0
  malformed_payload_count: 0
  unknown_symbol_count: 0
```

3symbol 1分 smoke:

```text
output:
  .tmp/trade_xyz_ws_smoke_multi_symbol_20260601_1920/

symbols:
  SP500
  XYZ100
  NVDA

subscriptions:
  bbo
  trades
  activeAssetCtx

capture:
  row_count: 807
  reconnect_count: 0
  error_count: 0
  subscription_response_count: 9

quality:
  status: pass
  row_count: 807
  gap_count: 0
  source_ts_gap_count: 0
  malformed_payload_count: 0
  unknown_symbol_count: 0
  duplicate_payload_count: 39

REST parity:
  status: pass
  request_error_count: 0
  missing_ws_symbols: []
  missing_rest_symbols: []
  mismatched_symbols: []
  known_gap_count: 0

disk usage:
  836K
```

3symbol 15分 smoke:

```text
output:
  .tmp/trade_xyz_ws_smoke_15m_20260601_1950/

symbols:
  SP500
  XYZ100
  NVDA

subscriptions:
  bbo
  trades
  activeAssetCtx

capture:
  row_count: 10408
  bytes_written: 9812449
  connection_count: 1
  reconnect_count: 0
  error_count: 0
  heartbeat_sent_count: 0
  pong_count: 0
  subscription_response_count: 9

quality:
  status: pass
  row_count: 10408
  gap_count: 0
  source_ts_gap_count: 0
  malformed_payload_count: 0
  unknown_symbol_count: 0
  bbo_bid_ask_inversion_count: 0
  duplicate_payload_count: 837

REST parity:
  status: pass
  request_error_count: 0
  missing_ws_symbols: []
  missing_rest_symbols: []
  mismatched_symbols: []
  known_gap_count: 0

disk usage:
  9.5M
```

3symbol 60分 smoke:

```text
output:
  .tmp/trade_xyz_ws_smoke_60m_20260601_2015/

symbols:
  SP500
  XYZ100
  NVDA

subscriptions:
  bbo
  trades
  activeAssetCtx

capture:
  row_count: 47254
  bytes_written: 44412326
  connection_count: 1
  reconnect_count: 0
  error_count: 0
  heartbeat_sent_count: 0
  pong_count: 0
  subscription_response_count: 9

quality:
  status: pass
  row_count: 47254
  gap_count: 0
  source_ts_gap_count: 0
  malformed_payload_count: 0
  unknown_symbol_count: 0
  bbo_bid_ask_inversion_count: 0
  duplicate_payload_count: 3043
  subscription_counts:
    __control__: 9
    activeAssetCtx: 10524
    bbo: 32978
    trades: 3743
  symbol_counts:
    NVDA: 14194
    SP500: 12354
    XYZ100: 20697

REST parity:
  status: pass
  request_error_count: 0
  missing_ws_symbols: []
  missing_rest_symbols: []
  mismatched_symbols: []
  known_gap_count: 0

disk usage:
  43M
```

11symbol 60分 smoke:

```text
output:
  .tmp/trade_xyz_ws_smoke_11symbols_60m_20260601_2100/

symbols:
  SP500
  XYZ100
  NVDA
  AAPL
  MSFT
  AMZN
  GOOGL
  META
  TSLA
  AMD
  EWJ

subscriptions:
  bbo
  trades
  activeAssetCtx

capture:
  row_count: 118930
  bytes_written: 111243093
  connection_count: 1
  reconnect_count: 0
  error_count: 0
  heartbeat_sent_count: 0
  pong_count: 0
  subscription_response_count: 33

quality:
  status: warn
  row_count: 118930
  gap_count: 1
  max_gap_seconds: 62.655
  source_ts_gap_count: 1
  max_source_ts_gap_seconds: 62.456
  malformed_payload_count: 0
  unknown_symbol_count: 0
  bbo_bid_ask_inversion_count: 0
  duplicate_payload_count: 13174
  trade_gap_count: 101
  max_trade_gap_seconds: 658.029
  trade_source_ts_gap_count: 100
  max_trade_source_ts_gap_seconds: 657.098
  subscription_counts:
    __control__: 33
    activeAssetCtx: 38478
    bbo: 74742
    trades: 5677
  symbol_counts:
    AAPL: 5501
    AMD: 10622
    AMZN: 6962
    EWJ: 7573
    GOOGL: 6737
    META: 8278
    MSFT: 14167
    NVDA: 12533
    SP500: 14101
    TSLA: 10460
    XYZ100: 21963

REST parity:
  status: pass
  request_error_count: 0
  missing_ws_symbols: []
  missing_rest_symbols: []
  mismatched_symbols: []
  known_gap_count: 0

disk usage:
  107M
```

11symbol 60分 smokeの判定:

```text
capture:
  pass

REST parity:
  pass

quality:
  warn

warn理由:
  bbo AAPL に 62.655秒の receive gap が1件あった。
  source timestamp gapも同じ箇所で 62.456秒。

trade_gap_count:
  tradesは低流動により間隔が空くため、品質warn条件から分離し情報値として残す。
  trade_gap_count=101 は trade tape sparsity として扱い、単独では欠損扱いしない。
```

3symbol 24時間 read-only 観測:

```text
status:
  running

started_at:
  2026-06-01_22:04 JST

pid:
  846741

command:
  uv run sis collect-trade-xyz-ws --registry-path data/registry/trade_xyz_instrument_registry.json --symbols SP500,XYZ100,NVDA --subscriptions bbo,trades,activeAssetCtx --duration-minutes 1440 --output-dir data/raw/ws/trade_xyz --write-control-messages

output:
  data/raw/ws/trade_xyz/

log:
  .tmp/trade_xyz_ws_24h_logs/collect_3symbols_20260601_2205.log

completion:
  未完了。capture/quality/REST parity manifest は24時間run終了後に生成・確認する。
```

途中確認:

```text
checked_at:
  2026-06-01_22:10 JST

process:
  pid: 846741
  elapsed: 00:06:08
  status: running

disk usage:
  4.8M

jsonl row counts:
  total: 5302
  __control__/__all__: 9
  activeAssetCtx/NVDA: 366
  activeAssetCtx/SP500: 366
  activeAssetCtx/XYZ100: 366
  bbo/NVDA: 999
  bbo/SP500: 978
  bbo/XYZ100: 1769
  trades/NVDA: 188
  trades/SP500: 133
  trades/XYZ100: 128

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:12 JST

process:
  pid: 846741
  elapsed: 00:08:21
  status: running

disk usage:
  8.5M

jsonl row counts:
  total: 9151
  __control__/__all__: 9
  activeAssetCtx/NVDA: 491
  activeAssetCtx/SP500: 491
  activeAssetCtx/XYZ100: 491
  bbo/NVDA: 1797
  bbo/SP500: 1973
  bbo/XYZ100: 2817
  trades/NVDA: 292
  trades/SP500: 364
  trades/XYZ100: 426

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:14 JST

process:
  pid: 846741
  elapsed: 00:10:23
  status: running

disk usage:
  12M

jsonl row counts:
  total: 12598
  __control__/__all__: 9
  activeAssetCtx/NVDA: 605
  activeAssetCtx/SP500: 605
  activeAssetCtx/XYZ100: 605
  bbo/NVDA: 2477
  bbo/SP500: 2886
  bbo/XYZ100: 3878
  trades/NVDA: 343
  trades/SP500: 571
  trades/XYZ100: 619

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:15 JST

process:
  pid: 846741
  elapsed: 00:11:19
  status: running

disk usage:
  14M

jsonl row counts:
  total: 14176
  __control__/__all__: 9
  activeAssetCtx/NVDA: 659
  activeAssetCtx/SP500: 659
  activeAssetCtx/XYZ100: 659
  bbo/NVDA: 2789
  bbo/SP500: 3355
  bbo/XYZ100: 4365
  trades/NVDA: 368
  trades/SP500: 629
  trades/XYZ100: 684

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:17 JST

process:
  pid: 846741
  elapsed: 00:12:54
  status: running

disk usage:
  16M

jsonl row counts:
  total: 16725
  __control__/__all__: 9
  activeAssetCtx/NVDA: 751
  activeAssetCtx/SP500: 751
  activeAssetCtx/XYZ100: 751
  bbo/NVDA: 3306
  bbo/SP500: 4011
  bbo/XYZ100: 5194
  trades/NVDA: 423
  trades/SP500: 725
  trades/XYZ100: 804

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:19 JST

process:
  pid: 846741
  elapsed: 00:15:02
  status: running

disk usage:
  18M

jsonl row counts:
  total: 19439
  __control__/__all__: 9
  activeAssetCtx/NVDA: 875
  activeAssetCtx/SP500: 875
  activeAssetCtx/XYZ100: 875
  bbo/NVDA: 3762
  bbo/SP500: 4687
  bbo/XYZ100: 6195
  trades/NVDA: 465
  trades/SP500: 818
  trades/XYZ100: 878

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:20 JST

process:
  pid: 846741
  elapsed: 00:16:15
  status: running

disk usage:
  20M

jsonl row counts:
  total: 21360
  __control__/__all__: 9
  activeAssetCtx/NVDA: 946
  activeAssetCtx/SP500: 946
  activeAssetCtx/XYZ100: 946
  bbo/NVDA: 4149
  bbo/SP500: 5217
  bbo/XYZ100: 6810
  trades/NVDA: 521
  trades/SP500: 882
  trades/XYZ100: 934

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:21 JST

process:
  pid: 846741
  elapsed: 00:17:24
  status: running

disk usage:
  22M

jsonl row counts:
  total: 23229
  __control__/__all__: 9
  activeAssetCtx/NVDA: 1013
  activeAssetCtx/SP500: 1013
  activeAssetCtx/XYZ100: 1013
  bbo/NVDA: 4504
  bbo/SP500: 5738
  bbo/XYZ100: 7414
  trades/NVDA: 563
  trades/SP500: 953
  trades/XYZ100: 1009

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:23 JST

process:
  pid: 846741
  elapsed: 00:18:59
  status: running

disk usage:
  24M

jsonl row counts:
  total: 25761
  __control__/__all__: 9
  activeAssetCtx/NVDA: 1104
  activeAssetCtx/SP500: 1104
  activeAssetCtx/XYZ100: 1104
  bbo/NVDA: 5012
  bbo/SP500: 6425
  bbo/XYZ100: 8253
  trades/NVDA: 613
  trades/SP500: 1027
  trades/XYZ100: 1110

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:24 JST

process:
  pid: 846741
  elapsed: 00:20:24
  status: running

disk usage:
  26M

jsonl row counts:
  total: 28020
  __control__/__all__: 9
  activeAssetCtx/NVDA: 1187
  activeAssetCtx/SP500: 1187
  activeAssetCtx/XYZ100: 1187
  bbo/NVDA: 5565
  bbo/SP500: 6997
  bbo/XYZ100: 8921
  trades/NVDA: 679
  trades/SP500: 1105
  trades/XYZ100: 1183

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:28 JST

process:
  pid: 846741
  elapsed: 00:23:55
  status: running

disk usage:
  31M

jsonl row counts:
  total: 33407
  __control__/__all__: 9
  activeAssetCtx/NVDA: 1392
  activeAssetCtx/SP500: 1392
  activeAssetCtx/XYZ100: 1392
  bbo/NVDA: 6722
  bbo/SP500: 8215
  bbo/XYZ100: 10668
  trades/NVDA: 867
  trades/SP500: 1359
  trades/XYZ100: 1391

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:30 JST

process:
  pid: 846741
  elapsed: 00:25:58
  status: running

disk usage:
  34M

jsonl row counts:
  total: 36536
  __control__/__all__: 9
  activeAssetCtx/NVDA: 1510
  activeAssetCtx/SP500: 1510
  activeAssetCtx/XYZ100: 1510
  bbo/NVDA: 7380
  bbo/SP500: 8915
  bbo/XYZ100: 11690
  trades/NVDA: 996
  trades/SP500: 1473
  trades/XYZ100: 1543

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:32 JST

process:
  pid: 846741
  elapsed: 00:28:04
  status: running

disk usage:
  38M

jsonl row counts:
  total: 41031
  __control__/__all__: 9
  activeAssetCtx/NVDA: 1632
  activeAssetCtx/SP500: 1632
  activeAssetCtx/XYZ100: 1632
  bbo/NVDA: 8519
  bbo/SP500: 9950
  bbo/XYZ100: 12779
  trades/NVDA: 1372
  trades/SP500: 1680
  trades/XYZ100: 1826

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:34 JST

process:
  pid: 846741
  elapsed: 00:29:48
  status: running

disk usage:
  42M

jsonl row counts:
  total: 44522
  __control__/__all__: 9
  activeAssetCtx/NVDA: 1733
  activeAssetCtx/SP500: 1733
  activeAssetCtx/XYZ100: 1733
  bbo/NVDA: 9418
  bbo/SP500: 10752
  bbo/XYZ100: 13711
  trades/NVDA: 1613
  trades/SP500: 1803
  trades/XYZ100: 2017

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:36 JST

process:
  pid: 846741
  elapsed: 00:32:17
  status: running

disk usage:
  46M

jsonl row counts:
  total: 49553
  __control__/__all__: 9
  activeAssetCtx/NVDA: 1877
  activeAssetCtx/SP500: 1877
  activeAssetCtx/XYZ100: 1877
  bbo/NVDA: 10799
  bbo/SP500: 11895
  bbo/XYZ100: 15060
  trades/NVDA: 1929
  trades/SP500: 1972
  trades/XYZ100: 2258

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:38 JST

process:
  pid: 846741
  elapsed: 00:34:02
  status: running

disk usage:
  49M

jsonl row counts:
  total: 52950
  __control__/__all__: 9
  activeAssetCtx/NVDA: 1980
  activeAssetCtx/SP500: 1980
  activeAssetCtx/XYZ100: 1980
  bbo/NVDA: 11735
  bbo/SP500: 12640
  bbo/XYZ100: 16029
  trades/NVDA: 2118
  trades/SP500: 2074
  trades/XYZ100: 2405

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:40 JST

process:
  pid: 846741
  elapsed: 00:35:42
  status: running

disk usage:
  52M

jsonl row counts:
  total: 56039
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2076
  activeAssetCtx/SP500: 2076
  activeAssetCtx/XYZ100: 2076
  bbo/NVDA: 12620
  bbo/SP500: 13267
  bbo/XYZ100: 16956
  trades/NVDA: 2292
  trades/SP500: 2154
  trades/XYZ100: 2513

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:41 JST

process:
  pid: 846741
  elapsed: 00:37:36
  status: running

disk usage:
  56M

jsonl row counts:
  total: 59660
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2186
  activeAssetCtx/SP500: 2186
  activeAssetCtx/XYZ100: 2186
  bbo/NVDA: 13632
  bbo/SP500: 14047
  bbo/XYZ100: 17984
  trades/NVDA: 2473
  trades/SP500: 2266
  trades/XYZ100: 2691

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:43 JST

process:
  pid: 846741
  elapsed: 00:39:23
  status: running

disk usage:
  58M

jsonl row counts:
  total: 62737
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2289
  activeAssetCtx/SP500: 2289
  activeAssetCtx/XYZ100: 2289
  bbo/NVDA: 14526
  bbo/SP500: 14678
  bbo/XYZ100: 18901
  trades/NVDA: 2574
  trades/SP500: 2360
  trades/XYZ100: 2822

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:46 JST

process:
  pid: 846741
  elapsed: 00:42:35
  status: running

disk usage:
  64M

jsonl row counts:
  total: 68637
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2476
  activeAssetCtx/SP500: 2476
  activeAssetCtx/XYZ100: 2476
  bbo/NVDA: 16261
  bbo/SP500: 15951
  bbo/XYZ100: 20693
  trades/NVDA: 2774
  trades/SP500: 2489
  trades/XYZ100: 3032

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:48 JST

process:
  pid: 846741
  elapsed: 00:44:11
  status: running

disk usage:
  66M

jsonl row counts:
  total: 71417
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2568
  activeAssetCtx/SP500: 2568
  activeAssetCtx/XYZ100: 2568
  bbo/NVDA: 17105
  bbo/SP500: 16531
  bbo/XYZ100: 21490
  trades/NVDA: 2853
  trades/SP500: 2578
  trades/XYZ100: 3147

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:49 JST

process:
  pid: 846741
  elapsed: 00:45:12
  status: running

disk usage:
  68M

jsonl row counts:
  total: 73256
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2628
  activeAssetCtx/SP500: 2628
  activeAssetCtx/XYZ100: 2628
  bbo/NVDA: 17596
  bbo/SP500: 16932
  bbo/XYZ100: 22057
  trades/NVDA: 2928
  trades/SP500: 2623
  trades/XYZ100: 3227

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:50 JST

process:
  pid: 846741
  elapsed: 00:46:04
  status: running

disk usage:
  69M

jsonl row counts:
  total: 74706
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2678
  activeAssetCtx/SP500: 2678
  activeAssetCtx/XYZ100: 2678
  bbo/NVDA: 17978
  bbo/SP500: 17244
  bbo/XYZ100: 22521
  trades/NVDA: 2987
  trades/SP500: 2651
  trades/XYZ100: 3282

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:51 JST

process:
  pid: 846741
  elapsed: 00:46:59
  status: running

disk usage:
  71M

jsonl row counts:
  total: 76294
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2730
  activeAssetCtx/SP500: 2730
  activeAssetCtx/XYZ100: 2730
  bbo/NVDA: 18421
  bbo/SP500: 17583
  bbo/XYZ100: 22980
  trades/NVDA: 3066
  trades/SP500: 2708
  trades/XYZ100: 3337

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:52 JST

process:
  pid: 846741
  elapsed: 00:47:54
  status: running

disk usage:
  72M

jsonl row counts:
  total: 77934
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2784
  activeAssetCtx/SP500: 2784
  activeAssetCtx/XYZ100: 2784
  bbo/NVDA: 18859
  bbo/SP500: 17918
  bbo/XYZ100: 23474
  trades/NVDA: 3130
  trades/SP500: 2778
  trades/XYZ100: 3414

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:53 JST

process:
  pid: 846741
  elapsed: 00:48:52
  status: running

disk usage:
  74M

jsonl row counts:
  total: 79643
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2839
  activeAssetCtx/SP500: 2839
  activeAssetCtx/XYZ100: 2839
  bbo/NVDA: 19338
  bbo/SP500: 18295
  bbo/XYZ100: 23953
  trades/NVDA: 3216
  trades/SP500: 2817
  trades/XYZ100: 3498

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:54 JST

process:
  pid: 846741
  elapsed: 00:49:54
  status: running

disk usage:
  75M

jsonl row counts:
  total: 81461
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2899
  activeAssetCtx/SP500: 2899
  activeAssetCtx/XYZ100: 2899
  bbo/NVDA: 19856
  bbo/SP500: 18725
  bbo/XYZ100: 24492
  trades/NVDA: 3271
  trades/SP500: 2850
  trades/XYZ100: 3561

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:55 JST

process:
  pid: 846741
  elapsed: 00:50:51
  status: running

disk usage:
  77M

jsonl row counts:
  total: 83154
  __control__/__all__: 9
  activeAssetCtx/NVDA: 2956
  activeAssetCtx/SP500: 2956
  activeAssetCtx/XYZ100: 2956
  bbo/NVDA: 20353
  bbo/SP500: 19107
  bbo/XYZ100: 24998
  trades/NVDA: 3324
  trades/SP500: 2878
  trades/XYZ100: 3617

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:56 JST

process:
  pid: 846741
  elapsed: 00:51:51
  status: running

disk usage:
  78M

jsonl row counts:
  total: 84887
  __control__/__all__: 9
  activeAssetCtx/NVDA: 3013
  activeAssetCtx/SP500: 3013
  activeAssetCtx/XYZ100: 3013
  bbo/NVDA: 20817
  bbo/SP500: 19503
  bbo/XYZ100: 25524
  trades/NVDA: 3373
  trades/SP500: 2932
  trades/XYZ100: 3690

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

途中確認:

```text
checked_at:
  2026-06-01_22:57 JST

process:
  pid: 846741
  elapsed: 00:52:50
  status: running

disk usage:
  80M

jsonl row counts:
  total: 86641
  __control__/__all__: 9
  activeAssetCtx/NVDA: 3070
  activeAssetCtx/SP500: 3070
  activeAssetCtx/XYZ100: 3070
  bbo/NVDA: 21321
  bbo/SP500: 19907
  bbo/XYZ100: 25946
  trades/NVDA: 3448
  trades/SP500: 2971
  trades/XYZ100: 3829

log:
  tail -n 40 は空。標準出力/標準エラー上の異常はまだ出ていない。

注意:
  これは途中snapshotであり、完了判定ではない。
  data/manifests/trade_xyz_ws_capture_manifest.json はまだこの24時間runの完了manifestではない。
```

追加docs:

```text
runbook:
  docs/TRADE_XYZ_WS_COLLECTION_RUNBOOK_2026-06-01.md

finalize helper:
  scripts/finalize_trade_xyz_ws_observation.sh

WS raw field inventory:
  docs/集めるべき実データ0531-2108/README.md

backtest ingestion handoff:
  plan/TRADE_XYZ_BACKTEST_REAL_DATA_INGESTION_HANDOFF_2026-06-01.md
```

途中で見つかった問題と対処:

```text
1. 初回の3symbol 1分 smokeでは trades.data[] が list のため symbol=__all__ になり、unknown_symbol_count=50 になった。
   対処: list内の coin が単一なら symbol 解決に使うよう修正した。

2. 初回の15分 smokeでは期限後の無通信で process が残った。
   対処: source側で deadline を見て、期限後は追加ping待ちに入らず終了するよう修正した。

3. 初回の11symbol qualityでは trades の低流動間隔を gap_count に混ぜて status=warn になった。
   対処: trades gapを trade_gap_count / trade_source_ts_gap_count に分離し、quote/state gapだけを quality warn条件に残した。
```

まだ完了していないこと:

```text
3symbol 60分 smoke:
  完了。2026-06-01_20:54 JST 時点でpass。

11symbol 60分 smoke:
  実行済み。capture / REST parity はpass。qualityは AAPL bbo gap 1件でwarn。

24時間 read-only 観測:
  完走。2026-06-03_19:17 JST に isolated raw root からmanifestを生成した。
  captureは duration_seconds=86401.202231、row_count=1202996、reconnect_count=8、graceful_reconnect_count=7、unexpected_reconnect_count=1、error_count=1。
  qualityは status=warn、gap_count=8、trade_gap_count=35、trade_source_ts_gap_count=35。
  REST parityは status=pass。

Current Real Data Contract更新:
  一部完了。WS raw field inventoryとbacktest入力昇格前条件は追記済み。
  backtest ingestion handoff draftは作成済み。
  ただし、24時間runに unexpected_reconnect_count=1 / error_count=1 / quality status=warn が残るため、実装開始readyではない。

runbook作成:
  完了。docs/TRADE_XYZ_WS_COLLECTION_RUNBOOK_2026-06-01.md を追加済み。

data-ready判定:
  未完了。unexpected_reconnect_count=1、error_count=1、quality status=warn のため、まだ backtest_data_ready と呼んではいけない。
```

## 0.4 3symbol 24時間 read-only 観測 attempt manifest（2026-06-02_17:44 JST）

`scripts/finalize_trade_xyz_ws_observation.sh 846741` でmanifestを生成した。
ただし、これは24時間完走manifestではない。`duration_seconds=47309.895227` で約13.14時間、`reconnect.max_attempts=5` 到達により停止したattemptのmanifestである。

```text
raw root:
  data/raw/ws/trade_xyz/

started_at:
  2026-06-01T13:04:23.215004+00:00

ended_at:
  2026-06-02T02:12:53.110231+00:00

duration_seconds:
  47309.895227

disk usage:
  735M

capture manifest:
  path: data/manifests/trade_xyz_ws_capture_manifest.json
  row_count: 814598
  bytes_written: 770305139
  connection_count: 5
  reconnect_count: 5
  error_count: 5
  heartbeat_sent_count: 0
  pong_count: 0
  subscription_response_count: 45

quality manifest:
  path: data/manifests/trade_xyz_ws_quality_manifest.json
  status: warn
  row_count: 814598
  gap_count: 10
  source_ts_gap_count: 0
  trade_gap_count: 7
  trade_source_ts_gap_count: 4
  malformed_payload_count: 0
  unknown_symbol_count: 0
  bbo_bid_ask_inversion_count: 0
  duplicate_payload_count: 31558

REST parity manifest:
  path: data/manifests/trade_xyz_rest_parity_manifest.json
  status: pass
  request_error_count: 0
  missing_ws_symbols: []
  missing_rest_symbols: []
  mismatched_symbols: []
  known_gap_count: 0
```

A6 investigation:

```text
decision:
  blocks data-ready and blocks T9 completion.

reason:
  --duration-minutes 1440 was requested, but the run lasted only about 13.14 hours.
  websocket_collection.reconnect.max_attempts is 5.
  capture reached reconnect_count=5 and error_count=5, then stopped before 24 hours.

block_reasons:
  4x received 1000 (OK) Expired; then sent 1000 (OK) Expired
  1x sent 1011 (internal error) keepalive ping timeout; no close frame received

connection durations:
  20260601T130423Z-0001: 10063.747s
  20260601T155208Z-0002: 10592.277s
  20260601T184842Z-0003: 10002.009s
  20260601T213528Z-0004: 10468.465s
  20260602T003005Z-0005: 6137.587s

gap interpretation:
  non-trade recv gaps: 10
  non-trade source gaps: 0
  trade recv gaps: 7
  trade source gaps: 4
  control subscription_response gaps account for 4 non-trade recv gaps between reconnects.
  one final in-connection pause produced about 149-159s recv gaps across bbo/activeAssetCtx/trades.
  bbo/trades source timestamps around that pause did not show a non-trade source gap, but activeAssetCtx has no source timestamp, so the receive-time hole remains unresolved for state data.
```

判定:

```text
T9:
  未完了。
  attemptの capture / quality / REST parity manifest は生成済み。
  ただし24時間完走ではないため、3symbol 24時間read-only観測の完了条件を満たさない。

T10:
  未完了。
  REST parityはpassだが、24時間未完走、captureに reconnect_count=5 / error_count=5、qualityは status=warn。
  24時間完走または明示的な別基準が決まるまで backtest ingestion 実装開始ready、data-ready、backtest_data_ready=true と呼ばない。
```

A5 verification:

```text
command:
  ./scripts/check

result:
  pass

format fix before rerun:
  uv run ruff format src/sis/venues/trade_xyz/client.py
  1 file reformatted

confirmed:
  Python 3.13.7
  ruff check: pass
  ruff format --check: 376 files already formatted
  current docs check: 81 current docs ok
  pyrefly: 0 errors
  pytest: 791 passed in 22.48s

note:
  This verifies the repo gate after final manifests/docs updates.
  It does not change the T10 decision; data-ready remains blocked by reconnect/error/quality warn evidence.
```

A7 durability fix:

```text
implemented:
  src/sis/venues/trade_xyz/ws_recorder.py
  tests/test_trade_xyz_ws_recorder.py

change:
  WebSocket server "1000 (OK) Expired" close is now treated as an expected graceful reconnect.
  It increments reconnect_count and graceful_reconnect_count.
  It does not increment error_count.
  It does not consume the unexpected reconnect retry budget.

still counted as error:
  unexpected reconnects, including keepalive timeout / internal error style failures.

new manifest fields:
  graceful_reconnect_count
  unexpected_reconnect_count

focused verification:
  uv run pytest -q tests/test_trade_xyz_ws_recorder.py tests/test_trade_xyz_ws_quality.py
  13 passed
  uv run ruff check src/sis/venues/trade_xyz/ws_recorder.py tests/test_trade_xyz_ws_recorder.py
  pass
  uv run ruff format --check src/sis/venues/trade_xyz/ws_recorder.py tests/test_trade_xyz_ws_recorder.py
  pass

next observation:
  Run a new 3symbol 24h observation after broad verification.
  Do not reuse the 13.14h attempt as T9 completion.
```

A8/A9 verification and relaunch:

```text
A8:
  ./scripts/check
  pass
  pytest: 793 passed in 22.09s

A9:
  started_at_jst: 2026-06-02_19:02 JST
  pid: 1488133
  raw_root: data/raw/ws/trade_xyz_24h_20260602_1902
  log_path: .tmp/trade_xyz_ws_24h_logs/collect_3symbols_20260602_1902.log
  launch_mode: setsid -f

command:
  uv run sis collect-trade-xyz-ws --registry-path data/registry/trade_xyz_instrument_registry.json --symbols SP500,XYZ100,NVDA --subscriptions bbo,trades,activeAssetCtx --duration-minutes 1440 --output-dir data/raw/ws/trade_xyz_24h_20260602_1902 --write-control-messages

initial_check:
  process: running
  jsonl_files: 10
  row_count: 302
  disk_usage: 384K

finalize command after PID exits:
  SIS_TRADE_XYZ_WS_FINALIZE_RAW_ROOT=data/raw/ws/trade_xyz_24h_20260602_1902 \
  SIS_TRADE_XYZ_WS_FINALIZE_LOG_PATH=.tmp/trade_xyz_ws_24h_logs/collect_3symbols_20260602_1902.log \
  scripts/finalize_trade_xyz_ws_observation.sh 1488133
```

## 0.5 3symbol 24時間 read-only 観測 final manifest（2026-06-03_19:17 JST）

`data/raw/ws/trade_xyz_24h_20260602_1902` を isolated raw root として final manifest を生成した。

```text
raw root:
  data/raw/ws/trade_xyz_24h_20260602_1902

started_at:
  2026-06-02T10:03:22.093603+00:00

ended_at:
  2026-06-03T10:03:23.295834+00:00

duration_seconds:
  86401.202231

disk usage:
  1.1G

capture manifest:
  path: data/manifests/trade_xyz_ws_capture_manifest.json
  row_count: 1202996
  bytes_written: 1133437251
  connection_count: 9
  reconnect_count: 8
  graceful_reconnect_count: 7
  unexpected_reconnect_count: 1
  error_count: 1
  heartbeat_sent_count: 0
  pong_count: 0
  subscription_response_count: 81

quality manifest:
  path: data/manifests/trade_xyz_ws_quality_manifest.json
  status: pass
  row_count: 1202996
  gap_count: 0
  max_gap_seconds: 0.0
  source_ts_gap_count: 0
  trade_gap_count: 35
  max_trade_gap_seconds: 102.704
  trade_source_ts_gap_count: 35
  max_trade_source_ts_gap_seconds: 102.817
  malformed_payload_count: 0
  unknown_symbol_count: 0
  bbo_bid_ask_inversion_count: 0
  duplicate_payload_count: 78137

REST parity manifest:
  path: data/manifests/trade_xyz_rest_parity_manifest.json
  status: pass
  request_error_count: 0
  missing_ws_symbols: []
  missing_rest_symbols: []
  mismatched_symbols: []
  known_gap_count: 0
```

判定:

```text
T9:
  完了。3symbol 24時間runの capture / quality / REST parity manifest は生成済み。

T10:
  完了。
  24時間は完走し、REST parityはpass。
  qualityは control subscriptionResponse gap を市場データgapから除外する修正後にpass。
  unexpected_reconnect_count=1 / error_count=1 は約1.074秒のtransport reconnectで、60秒超のquote/state gapを作っていないため、3symbol 24時間WS取得基盤としては受容する。
  ただし、実務バックテスト全体の backtest_data_ready=true ではない。
```

A13 verification:

```text
command:
  ./scripts/check

result:
  pass

confirmed:
  Python 3.13.7
  ruff check: pass
  ruff format --check: 376 files already formatted
  current docs check: 81 current docs ok
  pyrefly: 0 errors
  pytest: 793 passed in 21.87s
```

A16 verification:

```text
command:
  ./scripts/check

result:
  pass

confirmed:
  Python 3.13.7
  ruff check: pass
  ruff format --check: 376 files already formatted
  current docs check: 81 current docs ok
  pyrefly: 0 errors
  pytest: 794 passed in 23.37s
```

A14/A15 investigation:

```text
question:
  unexpected_reconnect_count=1 / error_count=1 / quality warn の原因は何か。

unexpected reconnect cause:
  block_reasons の1件が "no close frame received or sent"。
  接続 20260602T185051Z-0004 が 5894.381s で終了し、次の接続 20260602T202906Z-0005 が開始した。
  前後の実recv時刻は 2026-06-02T20:29:05.479+00:00 -> 2026-06-02T20:29:06.553+00:00。
  再接続そのものの実停止は約1.074sで、60秒超の quote/state recv gap はこの境界では出ていない。

graceful reconnects:
  残り7件は "received 1000 (OK) Expired; then sent 1000 (OK) Expired"。
  これは A7 修正後、graceful_reconnect_count に分離済み。

quality warn cause before fix:
  quality manifest の gap_count=8 は __control__/__control__ の subscriptionResponse 間隔。
  各connection中は subscriptionResponse が初回だけなので、接続継続時間そのものが control stream の recv gap として数えられている。
  つまり、quality=warn は bbo / activeAssetCtx の 60秒超 recv gap ではない。

A15 fix:
  src/sis/venues/trade_xyz/ws_quality.py で __control__ stream を market data gap 判定から除外した。
  tests/test_trade_xyz_ws_quality.py に control gap が status=pass のまま情報値になる回帰テストを追加した。
  final quality manifest を data/raw/ws/trade_xyz_24h_20260602_1902 から再生成し、status=pass / gap_count=0 / source_ts_gap_count=0 を確認した。

quote/state gap:
  non-trade source_ts_gap_count=0。
  gap_count=8 の内訳は control subscriptionResponse gap のみ。
  malformed_payload_count=0、unknown_symbol_count=0、bbo_bid_ask_inversion_count=0。

trade gaps:
  trade_gap_count=35、trade_source_ts_gap_count=35。
  最大は NVDA trades の 102.704s recv / 102.817s source gap。
  trades は低流動で自然に間隔が空くため、現行 quality code でも status warn 条件には入れていない。

T10 decision:
  完了。
  3symbol 24時間WS取得基盤は v0.1 完了として受容する。
  理由は、duration_seconds=86401.202231、quality status=pass、REST parity status=pass、malformed/unknown/bbo inversion が0、source_ts_gap_count=0であり、unexpected reconnect 1件は60秒超のquote/state gapを伴わないtransport reconnectとして説明できるため。
  ただし、backtest_data_ready=false は維持する。account fee、長期quote coverage、oracle timestamp provenanceなどの全体readiness gapは別gateで残る。

A15 verification:
  uv run pytest -q tests/test_trade_xyz_ws_quality.py: 6 passed
  uv run ruff check src/sis/venues/trade_xyz/ws_quality.py tests/test_trade_xyz_ws_quality.py: pass
  uv run ruff format --check src/sis/venues/trade_xyz/ws_quality.py tests/test_trade_xyz_ws_quality.py: pass
  uv run python scripts/check_current_docs.py: checked 81 current docs
  git diff --check: pass
  ./scripts/check: pass, pytest 794 passed in 22.97s
```

## 0.6 WS raw ingestion adapter v0.1（2026-06-04_06:47 JST）

24時間run完了後の次工程として、WS raw rowを `QuoteLog` へ変換する最小adapterを追加した。

実装済み:

```text
src/sis/venues/trade_xyz/normalizer.py:
  quote_from_ws_bbo_row(row, ...)
  quote_from_ws_active_asset_ctx_row(row)

src/sis/storage/normalize.py:
  normalize_trade_xyz_ws_quotes(raw_ws_root, parquet_path, duckdb_path, ...)

src/sis/commands/quotes.py:
  uv run sis normalize-trade-xyz-ws-quotes

src/sis/backtest/trade_xyz/ws_ingestion.py:
  build_bbo_bars_with_active_asset_state(frame, ...)

tests/test_trade_xyz_normalizer.py:
  test_ws_bbo_row_to_quote_log_builds_fill_snapshot_candidate
  test_ws_active_asset_ctx_row_to_quote_log_builds_signal_state_candidate
  test_ws_active_asset_ctx_does_not_reuse_recv_timestamp_as_oracle_timestamp

tests/test_trade_xyz_collector.py:
  test_normalize_trade_xyz_ws_quotes_builds_quote_log_dataset

tests/test_cli_smoke.py:
  test_normalize_trade_xyz_ws_quotes_cli

tests/backtest/test_trade_xyz_ws_ingestion.py:
  test_build_bbo_bars_with_active_asset_state_uses_no_future_state
  test_ws_bbo_bar_fixture_runs_minimal_backtest
```

境界:

```text
bbo:
  fill snapshot candidate
  best_bid / best_ask / mid_price / spread_bps / exec_buy_price / exec_sell_price を設定する
  source_ts_ms は row.source_ts_ms または payload.data.time
  oracle_ts_ms は asset_ctx が無いため missing

activeAssetCtx:
  signal/state candidate
  mark_price / oracle_price / index_price / mid_price / funding_rate / open_interest_usd を設定する
  best_bid / best_ask / exec price は設定しない
  is_tradable=false
  block_reasons=[BLOCK_NO_BBO_FILL_SNAPSHOT]
  recv_ts_ms を oracle_ts_ms として使わない
```

近接検証:

```text
uv run pytest -q tests/test_trade_xyz_normalizer.py tests/test_trade_xyz_ws_quality.py:
  13 passed

uv run pytest -q tests/test_trade_xyz_normalizer.py tests/test_trade_xyz_collector.py tests/test_cli_smoke.py:
  98 passed

uv run ruff check src/sis/venues/trade_xyz/normalizer.py tests/test_trade_xyz_normalizer.py:
  pass

uv run ruff format --check src/sis/venues/trade_xyz/normalizer.py tests/test_trade_xyz_normalizer.py:
  pass
```

実データ確認:

```text
command:
  uv run sis normalize-trade-xyz-ws-quotes --raw-ws-root data/raw/ws/trade_xyz_24h_20260602_1902 --parquet-path .tmp/trade_xyz_ws_quotes_24h.parquet --duckdb-path .tmp/trade_xyz_ws_quotes_24h.duckdb --manifest-path .tmp/trade_xyz_ws_quotes_24h.manifest.json --quality-manifest-path data/manifests/trade_xyz_ws_quality_manifest.json --rest-parity-manifest-path data/manifests/trade_xyz_rest_parity_manifest.json --registry-path data/registry/trade_xyz_instrument_registry.json --symbols SP500,XYZ100,NVDA

result:
  pass

quote_count:
  1113529

source_counts:
  trade_xyz_ws_activeAssetCtx: 251670
  trade_xyz_ws_bbo: 861859

symbol_counts:
  NVDA: 351870
  SP500: 298738
  XYZ100: 462921

oracle_ts_non_null:
  0

active_tradable_rows:
  0

bbo_missing_bid:
  0

bbo_missing_ask:
  0

output:
  .tmp/trade_xyz_ws_quotes_24h.parquet: 140M
  .tmp/trade_xyz_ws_quotes_24h.duckdb: 273M
  .tmp/trade_xyz_ws_quotes_24h.manifest.json: 1.6K

performance:
  elapsed: 50.88s
  max_rss: 2458468 KB

manifest:
  schema_version: trade_xyz_ws_backtest_artifact_manifest.v1
  row_count_raw_seen: 1202996
  quote_count_written: 1113529
  bbo_quote_count: 861859
  active_asset_ctx_quote_count: 251670
  trade_row_count_skipped: 89383
  control_row_count_skipped: 81
  duplicate_count_skipped: 3
  malformed_count: 0
  other_row_count_skipped: 0
  subscriptions_included: [activeAssetCtx, bbo]
  subscriptions_excluded: [__control__, trades]
```

backtest接続確認:

```text
normalize_trade_xyz_market_data:
  SP500 bbo sample 1000 rows pass

prepare_quote_rows_for_backtest:
  event_time_source=source_ts_ms, close_source=mid_price pass

build_quote_bars:
  SP500 bbo sample 10000 rows -> 1h bars 2 rows
  exec_buy_price / exec_sell_price / fill_best_bid / fill_best_ask nullなし

build_bbo_bars_with_active_asset_state:
  SP500 sample 20000 rows -> 1h bars 3 rows
  state_mark_price / state_observed_ts_ms / fill_best_bid / fill_best_ask nullなし

run_backtest:
  BBO-only small fixture pass
  backtest_run.json と fills.parquet を生成
```

broad verification:

```text
command:
  ./scripts/check

result:
  pass

confirmed:
  Python 3.13.7
  ruff check: pass
  ruff format --check: 378 files already formatted
  current docs check: 81 current docs ok
  pyrefly: 0 errors
  pytest: 801 passed in 21.93s
```

まだ未完了:

```text
長期 quote coverage
oracle timestamp provenance
backtest_data_ready=true 判定
```

## 1. 目的

このRepoでは、Trade[XYZ] の純粋バックテストに流すための実データを集めている。

今回の目的は戦略最適化ではない。目的は、Trade[XYZ] の実データを誤読せず、`run_backtest()` へ流せる状態まで hardening することである。

スコープ外:

```text
live order
paper order
wallet
signing
exchange write
MT5
IC Markets
CFD
short
multi-symbol backtest
leverage
L2 replay
```

## 2. 現在の結論

現時点では、実務バックテスト用の全データ収集は完了していない。

最新の collection status:

```text
decision: COLLECT_MORE_QUOTES
backtest_data_ready: false
readiness_decision: NOT_READY
fail_count: 1
known_gap_count: 1
failing_requirements:
  - quote_coverage
known_gap_requirements:
  - oracle_timestamp_provenance
```

2026-06-04_16:49 JST の修正:

```text
status_artifact:
  data/ops/trade_xyz_collection_status.json
  generated_at: 2026-06-04T07:38:04.720674+00:00

readiness_manifest:
  data/manifests/trade_xyz_data_readiness_manifest.json
  generated_at: 2026-06-04T07:38:04.720674+00:00

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
  - quote_coverage

known_gap_requirements:
  - oracle_timestamp_provenance
```

`real_market_reference` は現在の readiness manifest では `pass` である。
以前の「real_market_reference が残る」という説明は古い。

account-specific fee は解決済みである。

```text
account_fee_manifest_status: pass
account_fee_manifest_user_matches_env: true
account_fee_user_taker_fee_bps: 4.5
account_fee_user_maker_fee_bps: 1.5
user_address_sha256:
  bc21e277c128ec8b528879da14eed5c0a7eba06e762cc79873cef63e77966e83
```

したがって、この状態を「実務BT ready」と呼んではいけない。ただし、feeだけを理由に止まっている状態ではない。

## 3. 根拠コマンド

現在状態は以下で再計算して確認した。

```bash
uv run sis build-trade-xyz-reference-data
SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=<public-user-address> \
  uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness
```

根拠artifact:

```text
data/ops/trade_xyz_collection_status.json
data/reports/trade_xyz_collection_status.md
data/manifests/trade_xyz_data_readiness_manifest.json
data/manifests/trade_xyz_quote_coverage_manifest.json
data/manifests/trade_xyz_account_fee_manifest.json
data/manifests/trade_xyz_real_market_reference_manifest.json
data/manifests/oracle_timestamp_manifest.json
data/archive/pre_2026_05_31_unusable_real_data/ARCHIVE_MANIFEST.json
```

確認時点:

```text
data/ops/trade_xyz_collection_status.json:
  generated_at: 2026-06-01T06:03:43.402583+00:00

data/manifests/trade_xyz_data_readiness_manifest.json:
  generated_at: 2026-06-01T06:03:43.402583+00:00
```

## 4. 重要な現在ルール

### 4.1 2026-05-30以前の実データは禁止

2026-05-30 以前の実データは、現在のTrade[XYZ] backtest/readiness作業では使えない。

該当データは archive 済みである。

```text
archive root:
  data/archive/pre_2026_05_31_unusable_real_data/

archive manifest:
  data/archive/pre_2026_05_31_unusable_real_data/ARCHIVE_MANIFEST.json

moved_count:
  75

policy:
  All real data dated 2026-05-30 or earlier is unusable for current Trade[XYZ] backtest/readiness work and must remain archived.
```

古い raw quotes、funding history、normalized parquet、research artifacts、paper artifacts、evidence artifacts、古いstatus/manifest/report がこのarchiveに入っている。

### 4.2 収集対象は設定ファイルから読む

非秘密の収集設定は、コードやshell scriptに直書きしない。

正本:

```text
configs/trade_xyz_data_collection.yaml
```

このYAMLが持つもの:

```text
symbols
quote_collection.duration_minutes
quote_collection.interval_seconds
readiness.min_days
readiness.max_gap_minutes
readiness.max_oracle_lag_minutes
signal_candles.intervals
signal_candles.period_days
historical_archive.coins
historical_archive.start_date
data_cutoff.usable_start_date
```

秘密情報や環境依存情報はYAMLに入れない。

YAMLに入れないもの:

```text
AWS credentials
AWS profile value
wallet secret
private key
account fee user address
API key
```

## 5. 現在の実行状態

24時間 read-only data cycle の wrapper は動いている。
ただし `trade_xyz_collection_status.json` の `collector_process` は `uv run sis ...` の子プロセス検出であり、bash wrapper PIDを常に collector_running として数えるとは限らない。

```text
wrapper_pid: 2484910
wrapper_command: bash scripts/collect_trade_xyz_data_cycle.sh
log_path: logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
started_log_line: [2026-06-04T07:39:32Z] Trade[XYZ] data cycle starting

status_artifact_collector_process:
  running: false
  process_count: 0
```

再開時は `ps -fp 2484910` と log tail を見る。
理由なくcollectorを止める必要はない。

## 6. 現在使えるもの

| 項目 | 状態 | 備考 |
|---|---|---|
| Trade[XYZ] quote collector | 稼働中 | `collecting_ok` |
| signal candles | pass | `row_count=571`, `symbol_count=11`, `request_error_count=0` |
| funding events | pass | `source=quote_snapshot_hourly_bucket`, `row_count=187`, `skipped={}` |
| fee snapshots | pass | symbol-level fee snapshotsあり |
| account-specific fee | pass | userFees由来、taker `4.5bps`, maker `1.5bps` |
| session / reference dataset生成 | 実装済み | readiness artifactに接続済み |
| real market reference | pass | `data/manifests/trade_xyz_real_market_reference_manifest.json` |
| collection config | 実装済み | `configs/trade_xyz_data_collection.yaml` |
| archive manifest | 作成済み | 5/30以前の実データ75件をarchive |

## 7. 現在使えないもの

| 項目 | 状態 | 理由 |
|---|---|---|
| 実務BT全体 | NOT_READY | `backtest_data_ready=false` |
| quote coverage | fail | 30日相当に達していない |
| oracle timestamp provenance | known gap | source payloadにoracle timestamp fieldが無い |
| historical archive backfill | blocked | AWS credentialsが無く preflight fail。downloadは未実行 |

## 8. 現在の不足詳細

### 8.1 quote coverage

```text
failing_requirement:
  quote_coverage

coverage_passed:
  false

row_count:
  10318

raw_row_count:
  10318

traceable_only:
  true

completion_ratio_by_span:
  0.021836354993441356

min_span_days:
  0.6550906498032407

min_days_required:
  30.0

max_gap_seconds:
  151.034367

estimated_max_collection_days_required:
  30
```

11銘柄すべてが `span_days_below_min` で不足している。行数は伸びているが、30日相当の連続coverageにはまだ遠い。

### 8.2 real market reference

現在の readiness manifest では `real_market_reference` は pass である。
以前の「2026-05-31以降の取得で多くの株式/ETF/index proxyが欠損し fail」という記述は古い。

```text
status:
  pass

row_count:
  3782

manifest:
  data/manifests/trade_xyz_real_market_reference_manifest.json
```

古いreference dataをarchiveから戻してready判定に使ってはいけない、という禁止は維持する。

### 8.3 account-specific fee

解決済みである。

```text
source:
  hyperliquid_info_userFees

manifest:
  data/manifests/trade_xyz_account_fee_manifest.json

raw_artifact:
  data/raw/fees/trade_xyz_account/2026-06-01_bc21e277c128.json

status:
  pass

matches_configured_user:
  true

user_taker_fee_bps:
  4.5

user_maker_fee_bps:
  1.5
```

これは public user address による read-only `userFees` 取得であり、wallet/signing/exchange write は不要である。

### 8.4 oracle timestamp provenance

```text
oracle_timestamp_provenance_status:
  known_gap

row_count:
  16654

oracle_ts_present_count:
  0

oracle_ts_missing_count:
  16654

oracle_ts_missing_rate:
  1.0

oracle_ts_missing_reasons:
  asset_ctx_missing_oracle_timestamp_field: 16654
```

Repoの方針:

```text
source_ts_ms、recv timestamp、client timestampを oracle_ts_ms として流用しない。
asset context payloadに既知のoracle timestamp fieldがある場合だけ oracle_ts_ms として認める。
```

今回、`oracle_ts_ms` とは別に snapshot freshness proxy を追加した。

```text
oracle_freshness_proxy:
  description: Not oracle_ts_ms. This proxy measures raw snapshot lag using source_ts_ms and recv_ts_ms for rows that include oracle_price.
  observed_count: 8536
  missing_count: 1782
  observed_rate: 0.8272921108742004
  status_counts:
    observed_snapshot_lag: 8536
    invalid_clock_order: 1782
  lag_ms_min: 0
  lag_ms_max: 781
```

これは `oracle_ts_ms` の代替ではない。oracle timestamp provenance は引き続き known gap である。

### 8.5 historical archive

```text
historical_archive_bulk_plan_exists: true
historical_archive_bulk_plan_estimated_total_object_count: 7950
historical_archive_bulk_execution_status: planned
historical_archive_bulk_execution_dry_run: true
historical_archive_bulk_execution_selected_object_count: 10
historical_archive_bulk_execution_downloaded_object_count: 0
historical_archive_bulk_execution_command_error_count: 0
```

preflightはAWS credentials不足で失敗している。

```text
preflight_return_code: 255
stderr: Unable to locate credentials. You can configure credentials by running "aws configure".
```

requester-pays download は未実行である。費用承認なしに `--execute --acknowledge-requester-pays` を実行してはいけない。

## 9. 正しい次の手順

### 9.1 起動中24時間cycleを確認する

まず、すでに起動済みの quote coverage 用 data cycle を確認する。
同じ目的のcollectorを重複起動しない。

```bash
ps -fp 2484910
tail -80 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
```

### 9.2 cycle完了後にstatusを再判定する

PID `2484910` が終了したら、coverage と readiness を再生成する。

```bash
SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=<public-user-address> \
  uv run sis trade-xyz-collection-status --refresh-coverage --refresh-readiness --strict
```

期待する判定:

```text
quote_coverage:
  span_days が増える

real_market_reference:
  pass のまま

oracle_timestamp_provenance:
  known_gap のままなら偽装せず維持

backtest_data_ready:
  quote_coverage が fail の間は false
```

### 9.3 coverageがまだ不足なら24時間cycleを繰り返す

現 artifact 上の追加日数見込み:

```text
estimated_max_collection_days_required: 29
symbols: AAPL,AMD,AMZN,EWJ,GOOGL,META,MSFT,NVDA,SP500,TSLA,XYZ100
insufficient_reason: span_days_below_min
```

次のcycleを起動するのは、現在の PID が終了し、status再判定でまだ `quote_coverage=fail` の時だけ。

```bash
SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT=0 \
SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE=0 \
scripts/collect_trade_xyz_data_until_ready.sh
```

Better案:

```text
1. 毎日1回だけ cycle 完了確認と status 再判定を行う
2. `trade-xyz-collection-status` の next_actions を正本にする
3. coverageが30日へ近づくまで、real_market_referenceを再収集対象に戻さない
4. signal candles は既に request_error_count=0 なので、起動中cycleでは --skip-signal-candles を維持する
```

### 9.4 historical archiveを使う場合

まずAWS credentialsを設定し、preflightを通す。

```bash
uv run sis check-trade-xyz-historical-archive-preflight
uv run sis execute-trade-xyz-historical-archive-bulk --max-objects 10
```

dry-run確認後、費用と対象objectを承認してからだけ実行する。

```bash
uv run sis execute-trade-xyz-historical-archive-bulk \
  --execute \
  --acknowledge-requester-pays \
  --max-objects 10
```

historical archive は quote coverage を短縮できる可能性があるが、AWS credentials、requester-pays費用、対象object承認が必要である。
承認なしに実行しない。

### 9.5 oracle timestamp provenanceを扱う

oracle timestamp は、現payloadに明示fieldが無いため `known_gap` である。
これは quote coverage とは別の判定で、次を守る。

```bash
uv run sis build-trade-xyz-reference-data
uv run sis build-trade-xyz-data-readiness --strict
```

```text
してはいけない:
  recv_ts_ms を oracle_ts_ms にする
  source_ts_ms を oracle_ts_ms にする
  oracle_freshness_proxy を oracle timestamp の代替にする
```

### 9.6 完了判定

```bash
uv run sis trade-xyz-collection-status --strict --fail-on-not-ready
```

このコマンドが exit 0 になるまで、全データ収集は完了ではない。

known gap を許容する運用判定を別途使う場合:

```bash
uv run sis build-trade-xyz-data-readiness --allow-known-gaps
```

ただし、その場合も「strict ready」ではなく、oracle timestamp provenance gap を明記した `READY_WITH_KNOWN_GAPS` として扱う。

### 9.7 2026-06-04_16:39 JST のエラー潰し結果

2026-06-04_16:39 JST に、残っていた `trade_xyz_signal_candles_manifest.json` の `request_error_count=5` を再確認した。
原因は Hyperliquid info endpoint の一時的な `429 null` で、対象は次の5件だった。

```text
META 1d
TSLA 30m
TSLA 1d
TSLA 3d
AMD 30m
```

次の read-only 再収集を実行し、signal candle artifactを現行manifest shapeへ更新した。

```bash
uv run sis collect-trade-xyz-signal-candles \
  --registry-path data/registry/trade_xyz_instrument_registry.json \
  --intervals 30m,4h,1d,3d \
  --period-days 365 \
  --request-delay-seconds 1.5
```

結果:

```text
manifest_path: data/manifests/trade_xyz_signal_candles_manifest.json
row_count: 67765
new_row_count: 67765
symbol_count: 11
symbols: AAPL, AMD, AMZN, EWJ, GOOGL, META, MSFT, NVDA, SP500, TSLA, XYZ100
requested_intervals: 30m, 4h, 1d, 3d
request_error_count: 0
request_errors: []
```

その後、readiness/statusを再生成した。

```bash
uv run sis build-trade-xyz-data-readiness --strict
uv run sis trade-xyz-collection-status --no-refresh-coverage --refresh-readiness --strict
```

現在のstrict結果:

```text
decision: COLLECT_MORE_QUOTES
backtest_data_ready: False
readiness_decision: NOT_READY
fail_count: 1
known_gap_count: 1
failing_requirements: quote_coverage
known_gap_requirements: oracle_timestamp_provenance
signal_candles_status: pass
signal_candles_request_error_count: 0
estimated_max_collection_days_required: 29
coverage_completion_ratio_by_span: 0.03528847867939815
```

つまり、すぐ潰せる `signal_candles` のAPI request errorは解消済み。
残るstrict failは、quote coverageが約1.06日分しかなく30日要件に届かないこと。
これは即時の再実行だけでは完了せず、collector継続または承認済みhistorical archive backfillが必要である。

quote coverageを伸ばすため、次の24時間read-only data cycleを起動した。

```text
lock_pid: 2484910
command:
  scripts/collect_trade_xyz_data_cycle.sh

effective sis command:
  uv run sis collect-trade-xyz-data-cycle \
    --collection-config configs/trade_xyz_data_collection.yaml \
    --duration-minutes 1440 \
    --interval-seconds 60 \
    --seed-path configs/instrument_registry.seed.json \
    --symbols AAPL,AMD,AMZN,EWJ,GOOGL,META,MSFT,NVDA,SP500,TSLA,XYZ100 \
    --strict \
    --skip-signal-candles

log_path:
  logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log

launcher_log:
  .tmp/launchers/trade_xyz_data_cycle_20260604_073932.setsid.log
```

再開時の確認:

```bash
ps -fp 2484910
tail -80 logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log
uv run sis trade-xyz-collection-status --no-refresh-coverage --refresh-readiness --strict
```

### 9.8 2026-06-04_17:10 JST の再発防止実装

`signal_candles_request_error_count=5` と同種の 429 rate limit error を再発させにくくし、同じ失敗が出ても既存の成功データを壊さないようにした。

実装済みの境界:

```text
request pacing:
  collect-trade-xyz-signal-candles default request_delay_seconds = 1.5
  configs/trade_xyz_data_collection.yaml signal_candles.request_delay_seconds = 1.5
  collect-trade-xyz-data-cycle / build-trade-xyz-data-bundle に --signal-candle-request-delay-seconds を追加
  scripts/collect_trade_xyz_data_cycle.sh は SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_REQUEST_DELAY_SECONDS を受け取る

retry:
  初回失敗 key だけを1回 retryする
  retry_delay_seconds default = max(request_delay_seconds * 2, 3.0)
  readiness next_action は request_errors に含まれる failed symbols / intervals だけを再取得するcommandを出す

lossless partial failure:
  最終失敗 key は既存 parquet rows と既存 raw candle JSON を保持する
  最終失敗は data/raw/candles/trade_xyz_errors/<interval>/<symbol>.json に分離して保存する
  成功 key だけ既存 parquet rows を置き換える
  APIが正常に空payloadを返した場合は successful empty として扱い、その key の既存 rows を空に置き換える

manifest:
  retry_delay_seconds
  successful_request_count
  failed_request_count
  retry_attempt_count
  retry_success_count
  preserved_existing_row_count
  replaced_key_count
  failed_keys
  estimated_rate_limit_weight
  artifacts.raw_candle_errors_root
```

変更:

```text
src/sis/venues/trade_xyz/candles.py:
  default delay, failed-key retry, partial failure preservation, error artifact, manifest fields

src/sis/commands/quotes.py:
  collect-trade-xyz-data-cycle / build-trade-xyz-data-bundle に --signal-candle-request-delay-seconds を追加

src/sis/venues/trade_xyz/collection_config.py:
  signal_candles.request_delay_seconds を collection config から読む

src/sis/venues/trade_xyz/data_bundle.py:
  signal_candle_request_delay_seconds を bundle build へ伝搬

scripts/collect_trade_xyz_data_cycle.sh:
  SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_REQUEST_DELAY_SECONDS を検証してCLIへ渡す

src/sis/venues/trade_xyz/readiness.py:
  request_errors がある場合、failed symbols / intervals だけを長めのdelayで再取得する next_action を出す

docs/OPERATIONS_RUNBOOK.md:
  delay、retry、partial failure preservation、error artifactを記載

schemas/trade_xyz_signal_candles_manifest.v1.schema.json:
  新しいmanifest fieldsをschemaへ追加
```

確認:

```text
bash -n scripts/collect_trade_xyz_data_cycle.sh:
  pass

jq empty schemas/trade_xyz_signal_candles_manifest.v1.schema.json:
  pass

uv run sis collect-trade-xyz-data-cycle --symbols SP500 --duration-minutes 1 --interval-seconds 60 --signal-candle-request-delay-seconds 2.5 --dry-run:
  signal_candles=enabled intervals=30m,4h,1d,3d period_days=1 request_delay_seconds=2.5

focused pytest:
  uv run pytest -q tests/test_trade_xyz_candles.py tests/test_trade_xyz_collection_config.py tests/test_trade_xyz_data_readiness.py::test_build_trade_xyz_data_readiness_manifest_suggests_signal_candle_failed_subset tests/test_trade_xyz_data_bundle.py::test_build_trade_xyz_data_collection_bundle_passes_signal_candle_delay tests/test_cli_smoke.py::test_collect_trade_xyz_data_cycle_cli_dry_run
  15 passed

ruff:
  uv run ruff check <changed python files>
  pass
  uv run ruff format --check <changed python files>
  pass

full gate:
  ./scripts/check
  pass; pytest 807 passed in 75.50s
```

## 10. やってはいけないこと

```text
2026-05-30以前の実データを戻してready判定に使う
archive配下のデータを現行data/へ手動コピーする
source_ts_ms / recv_ts_ms / client timestampをoracle_ts_msとして偽装する
oracle_freshness_proxyをoracle_ts_msの代替として扱う
signal candlesとfill snapshot quotesを同じbar入力に混ぜる
real market referenceを古いarchive dataで上書きする
collector/supervisorを理由なくkillする
requester-pays downloadを費用承認なしに実行する
live/paper/wallet/signing/exchange writeへ進む
```

## 11. 第三者向けまとめ

このRepoは、Trade[XYZ]実データ収集の仕組み自体は揃ってきている。collector、readiness、coverage、signal candles、funding、archive preflight、account fee collection、status reportは実装済みである。

しかし、現在はまだ `NOT_READY` である。主な理由は、30日quote coverage不足と oracle timestamp provenance のsource欠損である。`real_market_reference` は現在の readiness manifest では pass である。

次の担当者は、まず `ps -fp 2484910`、`logs/trade_xyz_data_cycle/trade_xyz_data_cycle_20260604_073932.log`、`trade-xyz-collection-status` を見る。5/30以前のデータは使わず、AWS/requester-paysを使う場合は費用と対象objectを承認してから、strict readiness gateを通す。
