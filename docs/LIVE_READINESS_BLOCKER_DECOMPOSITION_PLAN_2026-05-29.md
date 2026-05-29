# Live Readiness Blocker Decomposition Plan 2026-05-29

この文書は、`./.ai_memory/HANDOFF.md` と `docs/NEXT_IMPLEMENTATION_PLAN_AFTER_P0_P1_2026-05-28.md` の A5 後に実行する詳細計画です。

古い chat transcript や archive docs は前提にしません。判断の正本は current code、tests、`data/ops/`、`data/reports/`、tracked current docs です。

## 結論

次にやることは、read-only Phase 2 entry を維持したまま、`LIVE_READINESS_BLOCKER=6` を production live readiness の blocker として分解することです。

現時点の境界:

- read-only Phase 2 entry: green
- latest phase gate: `READ_ONLY_GO`
- `phase2_entry_allowed=true`
- `P2_BLOCKER=0`
- `LIVE_READINESS_BLOCKER=6`
- live order submission: 対象外
- exchange write API: 対象外
- wallet / signing work: 対象外
- public micro live CLI: 対象外

この計画の目的は live trading を開始することではありません。目的は、live execution readiness に残る blocker を、named signal、source artifact、owning code path、修正方針、検証コマンドまで落とすことです。

## Second Review 2026-05-29

読み返し後の結論:

初稿の B1-B7 は安全側ではあるが、ベストな実装計画ではない。理由は、6 個の blocker を独立した 6 問題として扱いすぎていたためです。

コードを読むと、現行の live-readiness blocker はかなりの部分が 1 つの upstream 設計から連鎖しています。

```text
src/sis/commands/execution_artifacts.py
  _write_execution_snapshot(...)
    build_execution_snapshot_report(venue_snapshots=[])
```

つまり、現行 runtime は execution snapshot を意図的に空で生成しています。その結果:

- `execution_snapshot_summary.venue_count=0`
- `execution_venue_comparison_summary.all_registries_present=false`
- `execution_venue_diagnostics_summary.balance_gap_detected=true`
- `execution_venue_diagnostics_summary.fills_gap_detected=true`
- state comparison / snapshot drift history に `degraded -> None` 系 mismatch が残る
- phase gate ではそれらが `LIVE_READINESS_BLOCKER=6` として分類される

これは直ちに code regression とは言えません。legacy gTrade/Ostium adapter を ZIP 化して active tree から外し、Trade[XYZ] live execution は micro-live safety path に閉じているため、標準 operations artifact へ execution venue snapshot を流していない、という現行設計の結果です。

したがって、ベストな進め方は次です。

1. **まず root-cause inventory に寄せる**  
   6 blocker を 6 実装に分ける前に、`venue_snapshots=[]` 起点の downstream blocker と、別原因の blocker を分離する。

2. **すぐ新しい collector を作らない**  
   `read-only execution state collector` は新機能です。実装に入る前に、live readiness で本当に必要な snapshot fields と、read-only API だけで取れる fields を決める。

3. **最初の実装修正候補は report/lineage の明確化**  
   blocker を消すより先に、`execution_snapshot_summary` と downstream reports に `reason=trade_xyz_live_execution_snapshot_not_connected` のような明示 reason を持たせる方が小さく、正直で、事故りにくい。

4. **collector 実装は別 gate にする**  
   実際に balance / fills / open orders / order status を取得するなら、`src/sis/venues/trade_xyz/client.py` の `/info` read-only method を拡張する別タスクにする。これは B1 の単なる棚卸しではない。

5. **green にすることを目的にしない**  
   `LIVE_READINESS_BLOCKER=6` を 0 にすることより、`why blocked` が正確に読めることを先に完了条件にする。真値がない blocker は accepted blocker として残す。

更新後の推奨実行順:

```text
A1-A5: current gate 再確認
C1: execution snapshot root-cause inventory
C2: blocker lineage map 作成
C3: report/summary reason code 追加の要否判断
C4: read-only execution state collector が必要か scope decision
C5: collector が必要な場合だけ実装計画へ進む
B7: verification closeout
```

## Revised Plan: C-Series First

### C1 Execution Snapshot Root-Cause Inventory

目的:

`LIVE_READINESS_BLOCKER=6` の upstream root が `execution_snapshot_summary.venues=[]` かどうかを、artifact と code path で確認する。

読むもの:

```bash
sed -n '1,120p' src/sis/commands/execution_artifacts.py
sed -n '1,140p' src/sis/reports/execution_snapshot.py
jq '.' data/ops/execution_snapshot_summary.json
jq '.' data/ops/execution_venue_comparison_summary.json
jq '.' data/ops/execution_venue_diagnostics_summary.json
jq '.execution_drift_classifications' data/ops/phase_gate_review_summary.json
```

確認する facts:

- `_write_execution_snapshot` が `venue_snapshots=[]` を渡している
- `execution_snapshot_summary.venue_count=0`
- downstream comparison / diagnostics が空 snapshot 由来で degraded になっている
- `phase_gate_review` はそれを P2 blocker ではなく live-readiness blocker として分類している

成果物:

- root cause table
- downstream blocker lineage
- `code regression`, `intentional not-connected surface`, `stale artifact` の分類

止める条件:

- empty snapshot 以外の原因が混じっているのに、全部を同じ root cause と断定しそうになる

### C2 Blocker Lineage Map

目的:

6 blocker を independent blocker ではなく lineage として整理する。

初期仮説:

```text
execution_snapshot.venues=[]
  -> execution_comparison_all_registries_present=false
  -> execution_balance_gap_detected=true
  -> execution_fills_gap_detected=true
  -> execution_drift_overview_status=degraded
  -> execution_state_comparison_mismatching_count=3
  -> execution_snapshot_drift_mismatching_snapshot_count=3
```

成果物:

- blocker lineage diagram
- each signal の upstream source
- each signal が direct root か derived signal か

完了条件:

- 6 signals のうち、どれが root signal で、どれが derived signal か説明できる

### C3 Reason-Code First Fix Decision

目的:

最初の実装修正を「blocker 解消」ではなく「なぜ blocked かを artifact に正確に出す」方向にするか判断する。

候補:

- `execution_snapshot_summary` に `snapshot_reason` を追加
- `execution_venue_comparison_summary` に `source_snapshot_empty_reason` を追加
- `execution_venue_diagnostics_summary` に `degraded_reason` を追加
- phase gate classification reason を `trade_xyz_live_execution_snapshot_not_connected` まで具体化

実装する場合の target:

- `src/sis/commands/execution_artifacts.py`
- `src/sis/reports/execution_snapshot.py`
- `src/sis/reports/execution_venue_comparison.py`
- `src/sis/reports/execution_venue_diagnostics.py`
- `src/sis/reports/phase_gate_review.py`
- corresponding tests

完了条件:

- `READ_ONLY_GO` は維持
- `LIVE_READINESS_BLOCKER` は消さない
- blocker の理由が `degraded` だけでなく、Trade[XYZ] execution snapshot 未接続として読める

### C4 Read-Only Execution State Collector Scope Decision

目的:

collector を作るかどうかを実装前に決める。

collector が必要な場合だけ検討する read-only fields:

- account / clearinghouse state
- positions
- open orders
- order status
- fills by time window
- request metadata: endpoint type, request window, pagination, returned row count, rate-limit weight assumption, error class

実装しない場合:

- `LIVE_READINESS_BLOCKER` は accepted blocker として残す
- micro live safety path と operations artifact の未接続を明記する

止める条件:

- live write API、wallet、signing、secret が必要になる
- public micro live CLI を増やす必要が出る

### C5 Collector Implementation Plan

この段階は C4 で collector が必要と判断した場合だけ実行する。

方針:

- `src/sis/venues/trade_xyz/client.py` に read-only `/info` method を追加する
- `src/sis/execution/trade_xyz_adapter.py` の live write safety path と混ぜない
- fixture / mocked `httpx` tests を先に追加する
- live network smoke は opt-in、secrets なし、write なしにする

対象外:

- order placement
- cancel
- signing
- wallet integration
- public live CLI

## External Research Notes 2026-05-29

短時間調査で確認した実装判断:

- Hyperliquid の read-only 側は `POST https://api.hyperliquid.xyz/info` に集約され、fills、order status、open orders、user state などは Info endpoint で扱える。したがって、B1-B4 は Exchange endpoint / live write API に進まず、まず read-only execution state collector と artifact comparison を厚くする。
- Hyperliquid の rate limit は IP 単位で REST aggregate weight `1200/min`。`l2Book`, `allMids`, `clearinghouseState`, `orderStatus`, `spotClearinghouseState`, `exchangeStatus` は weight 2、fills 系は返却件数に応じた追加 weight がある。collector は endpoint weight と row count を artifact に残す。
- Alpaca latest stock bar は feed が `sip`, `iex`, `delayed_sip`, `boats`, `overnight`, `otc` に分かれ、default feed は subscription に依存する。fresh source confidence は `status=pass` だけでなく、`feed`, `latest_bar_ts`, `market_session`, `requested_window`, `subscription/feed assumption` を artifact に残す。
- `httpx` は default timeout を持つ。connect retry は `HTTPTransport(retries=...)` で扱えるが、429/500/provider-specific retry は明示的な retry policy として扱う。既存 dependency の `tenacity` を使うなら、retry 対象と stop condition を artifact に残す。
- Context7 では `/hyperliquid-dex/hyperliquid-python-sdk`, `/alpacahq/alpaca-py`, `/encode/httpx` を確認した。SDK 追加はまだ必須ではない。現 repo の `httpx` + fixture / mock test 方針で、read-only contract を先に固めるのが局所的。

参照:

- Hyperliquid Info endpoint: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
- Hyperliquid rate limits: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits
- Alpaca latest bars: https://docs.alpaca.markets/us/reference/stocklatestbars-1
- Alpaca-py stock historical data: https://alpaca.markets/sdks/python/api_reference/data/stock/historical.html
- HTTPX timeouts: https://www.python-httpx.org/advanced/timeouts/
- HTTPX transports: https://www.python-httpx.org/advanced/transports/

## Review Pass: 抜け・漏れ・誤謬リスク

現計画の弱点と補強:

| 観点 | リスク | 補強 |
|---|---|---|
| API 境界 | `Trade[XYZ]` は repo 内の仮称で、外部 docs は Hyperliquid 相当として読む必要がある | docs では provider 名を一般化せず、repo 内 symbol は `trade_xyz` のまま扱う |
| read-only / write 境界 | balance / fills / order status を取る過程で Exchange endpoint に寄る危険 | B1-B4 は Info endpoint 相当の read-only collector だけを対象にする |
| rate limit | fills/history を毎回全量取得して 1200 weight/min や追加 weight を踏む危険 | request window、pagination、endpoint weight、returned row count を artifact に保存する |
| Alpaca freshness | historical IEX bar success を fresh live suitability pass と誤読する危険 | feed、bar timestamp、session、request window、source confidence reason を必須出力にする |
| artifact drift | stale generated file と code regression を混同する危険 | B1 で source artifact と owning code path を分け、B6 で regeneration / code fix / policy decision に分類する |
| greenwashing | dummy balance / fills で blocker を消す危険 | dummy artifact 禁止。真値がないものは accepted live-readiness blocker として残す |
| test strategy | report の表示だけ直して実データ比較が壊れたままになる危険 | targeted fixture comparison または failing unit test を先に作る |

つっこみどころ:

- A5 の期待値 `pytest 294 passed` は repo の現時点とずれる可能性がある。A5 実行時は pass/fail と実数を記録し、数が変わった場合は test 追加/削除由来か regression かを分ける。
- `LIVE_READINESS_BLOCKER=0` になっても production live trading ready ではない。wallet / signing / live order submission は別 gate。
- Alpaca fresh pass は市場時間と feed 権限に依存するため、失敗を即 regression と読まない。
- untracked/generated data がある場合、git status だけでは `data/` の鮮度を保証しない。artifact の timestamp / row count / summary digest を見る。

## 実行前 Gate

### A1 Repo State Confirm

実行:

```bash
git status --short --branch --untracked-files=all
```

期待値:

- branch は `main...origin/main`
- user-owned docs 変更があれば記録する
- 依頼外の変更は revert しない

止める条件:

- 対象コードや generated artifact に、今回の調査と衝突する未確認変更がある

### A2 Fresh Quote Evidence Confirm

実行:

```bash
jq '{row_count,duration_minutes,interval_seconds,api_error_count,collected_symbols,started_at,ended_at}' data/ops/trade_xyz_quote_collection_summary.json
wc -l data/raw/quotes/trade_xyz/2026-05-28.jsonl
```

期待値:

- `row_count=660`
- `duration_minutes=60`
- `interval_seconds=60`
- `api_error_count=0`
- raw JSONL は 660 行

止める条件:

- artifact が欠けている
- row count が summary と raw で一致しない

### A3 Strict Artifact Validation

実行:

```bash
uv run sis validate-artifacts --strict
```

期待値:

- `checked_files=12`
- `issues=0`

止める条件:

- strict validation が失敗する
- Trade[XYZ] current artifact と legacy artifact のどちらが原因か切り分けられない

### A4 Phase Gate Confirm

実行:

```bash
uv run sis phase-gate-review
```

期待値:

- `decision=READ_ONLY_GO`
- `phase2_entry_allowed=True`
- `P2_BLOCKER=0`
- `LIVE_READINESS_BLOCKER=6`

止める条件:

- `P2_BLOCKER > 0`
- `phase2_entry_allowed=false`
- live-readiness-only drift が P2 remediation loop に戻っている

### A5 Repository Health Gate

実行:

```bash
./scripts/check
```

期待値:

- Python `3.13.7`
- `ruff` pass
- `pyrefly` 0 errors
- `pytest` 294 passed

止める条件:

- `./scripts/check` が失敗する
- 失敗原因が generated artifact 鮮度なのか code regression なのか切り分けられない

## B1 Blocker Inventory

目的:

6 個の `LIVE_READINESS_BLOCKER` を named blocker として固定し、各 blocker に source artifact、likely owning code path、read-only collector requirement を付ける。

読む artifact:

```bash
jq '.' data/ops/phase_gate_review_summary.json
jq '.' data/ops/execution_drift_overview_summary.json
jq '.' data/ops/execution_venue_diagnostics_summary.json
jq '.' data/ops/execution_venue_comparison_summary.json
jq '.' data/ops/execution_state_comparison_history_summary.json
jq '.' data/ops/execution_snapshot_drift_history_summary.json
```

初期 blocker:

| ID | signal | observed | expected | source artifact |
|---|---|---:|---:|---|
| B1-1 | `execution_drift_overview_status` | `degraded` | `ok` | `data/ops/phase_gate_review_summary.json`, `data/ops/execution_drift_overview_summary.json` |
| B1-2 | `execution_balance_gap_detected` | `true` | `false` | `data/ops/phase_gate_review_summary.json`, `data/ops/execution_venue_diagnostics_summary.json` |
| B1-3 | `execution_fills_gap_detected` | `true` | `false` | `data/ops/phase_gate_review_summary.json`, `data/ops/execution_venue_diagnostics_summary.json` |
| B1-4 | `execution_comparison_all_registries_present` | `false` | `true` | `data/ops/phase_gate_review_summary.json`, `data/ops/execution_venue_comparison_summary.json` |
| B1-5 | `execution_state_comparison_mismatching_count` | `3` | `0` | `data/ops/phase_gate_review_summary.json`, `data/ops/execution_state_comparison_history_summary.json` |
| B1-6 | `execution_snapshot_drift_mismatching_snapshot_count` | `3` | `0` | `data/ops/phase_gate_review_summary.json`, `data/ops/execution_snapshot_drift_history_summary.json` |

成果物:

- blocker inventory table
- each blocker の `signal`, `observed`, `expected`, `source artifact`, `owning code path`, `classification`
- each blocker の `read_only_endpoint_requirement`
- endpoint weight / request window / pagination が必要な blocker では、その記録方針
- `P2_BLOCKER` ではなく `LIVE_READINESS_BLOCKER` として残す理由

推定 owning code path:

- `src/sis/reports/phase_gate_review.py`
- `src/sis/reports/execution_venue_diagnostics.py`
- `src/sis/reports/execution_venue_comparison.py`
- `src/sis/reports/execution_gap_history.py`
- `src/sis/reports/execution_state_comparison_history.py`
- `src/sis/reports/execution_snapshot_drift_history.py`
- `src/sis/execution/`

止める条件:

- blocker を消すために phase gate 条件を緩める必要が出る
- balance / fills / order state 不足を read-only P2 blocker として扱い始める
- source artifact が欠けているのに推測で blocker 原因を断定する
- Exchange endpoint / live write API を呼ばないと進めない形になった場合は、read-only 分解を止めて accepted live-readiness blocker として記録する

## B2 Execution Adapter Coverage

目的:

live execution readiness に必要な execution adapter の coverage gap を、read-only capability と live write capability に分けて、コードと tests で特定する。

読むもの:

```bash
find src/sis/execution -maxdepth 2 -type f -print | sort
rg -n "dry|live|write|order|cancel|balance|fill|position|sign|wallet|secret" src/sis/execution tests/test_trade_xyz_adapter_safety.py tests/test_micro_live_canary.py tests/test_trade_xyz_live_order_policy.py
```

確認対象:

- read-only path と live write path の境界
- dry-run / fake exchange / mock policy test の範囲
- balance / fills / positions / order status の取得責務
- Info endpoint 相当の read-only method と Exchange endpoint 相当の write method が同じ public path に混ざっていないこと
- endpoint weight、timeout、retry、pagination の扱い
- public CLI に live order execution が exposed されていないこと
- wallet / signing / secret が repo artifact に漏れていないこと

成果物:

- adapter capability matrix
- test coverage matrix
- uncovered behavior list
- 修正対象を `test only`, `report logic`, `read_only_adapter_contract`, `live_write_boundary`, `policy decision` に分類

標準 targeted tests:

```bash
uv run pytest tests/test_trade_xyz_live_order_policy.py tests/test_trade_xyz_adapter_safety.py tests/test_micro_live_canary.py -q
```

止める条件:

- 実取引 API write が必要になる
- wallet / signing / secret の投入が必要になる
- public CLI に live order execution を露出する必要が出る
- SDK 追加なしでは実装できないと判断した場合は、まず現行 `httpx` 実装で足りない具体理由を記録する

## B3 Balance / Fills Gap Resolution

目的:

`execution_balance_gap_detected=true` と `execution_fills_gap_detected=true` の原因を、artifact 不足、比較ロジック不一致、adapter 未接続、policy decision のどれかに分類する。

読む artifact:

```bash
jq '.' data/ops/execution_snapshot_summary.json
jq '.' data/ops/execution_gap_history_summary.json
jq '.' data/ops/execution_venue_diagnostics_summary.json
jq '.' data/ops/execution_venue_comparison_summary.json
```

現時点の既知値:

- `execution_venue_diagnostics_summary.overall_status=degraded`
- `execution_venue_diagnostics_summary.venue_count=0`
- `execution_balance_gap_detected=true`
- `execution_fills_gap_detected=true`
- `registry_gap_detected=true`
- `execution_venue_comparison_summary.all_registries_present=false`

切り分け:

| 分類 | 判定条件 | 次の扱い |
|---|---|---|
| artifact missing | expected file が無い、または current run に含まれない | regeneration command を特定 |
| comparison mismatch | source はあるが expected と observed がずれる | comparison logic と expected schema を確認 |
| adapter unconnected | adapter が balance / fills を出せない | adapter contract を明記、実 write なしで stub 禁止 |
| policy decision | live readiness に必須だが read-only P2 には不要 | `LIVE_READINESS_BLOCKER` として残す |

read-only collector requirement:

- balance / user state は Info endpoint 相当の read-only API から取得できる範囲だけを対象にする。
- fills は time window と pagination を明示し、returned row count と request weight assumption を artifact に残す。
- order status / open orders は read-only status check として扱い、cancel / place / modify は対象外にする。
- API error、timeout、429、schema mismatch は empty result と区別して artifact に残す。

成果物:

- balance gap reason
- fills gap reason
- expected source artifact
- regeneration で解消するか、code fix が必要か、policy blocker として残すか

止める条件:

- missing balance / fills を dummy data で埋める必要が出る
- live write API なしでは真値を得られないものを、推測で pass 扱いする必要が出る
- fills の全量取得が rate limit や pagination 上危険な場合は、windowed collection へ落として blocker 分解を続ける

## B4 State Comparison And Snapshot Drift Cleanup

目的:

`execution_state_comparison_mismatching_count=3` と `execution_snapshot_drift_mismatching_snapshot_count=3` を、どの snapshot / state がずれているかまで分解する。

読む artifact:

```bash
jq '.' data/ops/execution_state_comparison_history_summary.json
jq '.' data/ops/execution_snapshot_drift_history_summary.json
jq '.' data/ops/execution_drift_overview_summary.json
```

現時点の既知値:

- state comparison: `mismatching_count=3`
- state comparison pair counts: `degraded -> None = 3`, `degraded -> degraded = 43`
- snapshot drift: `mismatching_snapshot_count=3`
- snapshot drift diagnostics pair counts: `degraded -> None = 3`, `degraded -> degraded = 39`

調査観点:

- `None` 側の missing artifact はどれか
- `degraded -> None` が historical artifact 欠落なのか、schema/key rename なのか
- latest run だけの問題か、history aggregation の問題か
- expected policy change による drift か、regression か

成果物:

- mismatch 3 件の artifact / timestamp / field
- `expected policy change`, `generated artifact missing`, `code regression`, `history aggregation mismatch` の分類
- 修正する場合の failing targeted test または reproducible artifact comparison
- comparison input の freshness と digest

止める条件:

- historical artifact を根拠なく書き換える必要が出る
- mismatch を消すために comparison を弱める必要が出る

## B5 Fresh Alpaca Source Confidence Pass

目的:

policy 上必要な場合だけ、Alpaca source confidence を fresh bar で再確認する。

前提:

- credentials なしの controlled failure と、credentials ありの provider connectivity / data availability は別物
- historical IEX bar の success は fresh live `status=pass` と同義ではない
- fallback provider を primary truth として silent 採用しない
- Alpaca stock latest bar の feed default は subscription に依存するため、feed を artifact に明示する

現時点の既知値:

- `provider_connectivity_status=pass`
- `data_availability_status=pass`
- `bar_count=1`
- `source_confidence=0.65`
- `live_suitability_reasons=["BLOCK_LOW_SOURCE_CONFIDENCE"]`
- `status=blocked`

読む artifact:

```bash
jq '.' data/ops/alpaca_live_smoke_summary.json
sed -n '1,120p' data/reports/alpaca_live_smoke.md
```

成果物:

- provider connectivity status
- data availability status
- live suitability status
- feed (`iex` / `sip` / `delayed_sip` など)
- latest bar timestamp
- market session / request window / provider response の記録
- source confidence reason
- `BLOCK_LOW_SOURCE_CONFIDENCE` が残る場合の次条件

止める条件:

- API key / secret を repo、docs、logs に書く必要が出る
- 市場時間外の no bars を live suitability fail と誤読しそうになる
- fallback provider を primary truth として採用する必要が出る
- feed 権限不足や 403/429 を empty bars と同じ扱いにする必要が出る

## B6 Remediation Task Split

目的:

B1-B5 の調査結果を、実装可能な小タスクに分ける。

タスク分類:

| 種別 | 例 | 実装前条件 |
|---|---|---|
| report logic fix | summary key 欠落、aggregation mismatch | failing unit test or fixture comparison |
| artifact regeneration | stale or missing generated file | regeneration command と expected diff |
| adapter contract fix | read-only/dry-run capability の contract 不明 | public live CLI を増やさないこと |
| rate-limit hardening | request window / endpoint weight / pagination 未記録 | no live write, bounded request count |
| policy clarification | live readiness に必要だが今は未接続 | docs と blocker classification の明記 |
| no-op accepted blocker | live write なしでは解消不能 | `LIVE_READINESS_BLOCKER` として残す理由 |

成果物:

- numbered implementation backlog
- each item の target files
- each item の acceptance
- each item の verification command
- each item の stop condition
- each item が read-only か live-write-adjacent かの分類

止める条件:

- live order submission に進まないと backlog を閉じられない
- secret / wallet / signing が必要になる
- dummy artifact で green にする案しかない

## Better Implementation Direction

最良実装に寄せるための優先順位:

1. **B1 を先に厚くする**: いきなり code fix せず、6 blocker を source artifact と owning code path に固定する。
2. **read-only execution state collector を分離する**: balance、fills、open orders、order status を read-only capability として定義し、live order placement / cancel / signing と別 interface にする。
3. **rate-limit-aware artifact を出す**: endpoint type、request count、weight assumption、pagination window、returned row count、error class を保存する。
4. **comparison を fixture 化する**: B4 の mismatch 3 件は、まず fixture comparison か failing unit test にしてから修正する。
5. **Alpaca は feed-aware にする**: source confidence は feed と timestamp 鮮度を持たない限り green にしない。
6. **green の意味を分ける**: `READ_ONLY_GO`、`operations_ready`、`live_evidence_ready`、`execution_ready`、`production_live_ready` を同じ単語で扱わない。

## B7 Verification Closeout

実行:

```bash
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
./scripts/check
```

期待値:

- strict validation: `issues=0`
- phase gate: `READ_ONLY_GO`
- `phase2_entry_allowed=True`
- `P2_BLOCKER=0`
- live-readiness blocker が残る場合は `LIVE_READINESS_BLOCKER` として残る
- live-readiness blocker を解消した場合でも、live order submission は別 gate として扱う

追加で確認すること:

```bash
jq '.execution_drift_classification_counts' data/ops/phase_gate_review_summary.json
jq '.execution_drift_classifications' data/ops/phase_gate_review_summary.json
```

止める条件:

- `LIVE_READINESS_BLOCKER=0` だけを根拠に production live trading ready と判断しそうになる
- live order submission、exchange write API、wallet / signing work へ進みそうになる
- `P2_BLOCKER` と `LIVE_READINESS_BLOCKER` が混ざる

## 完了条件

この計画は、次を満たしたら完了です。

- A1-A5 の再確認結果が記録されている
- 6 個の live-readiness blocker が named signal と source artifact に落ちている
- 各 blocker に likely owning code path がある
- 各 blocker が `artifact regeneration`, `code fix`, `adapter contract`, `policy decision`, `accepted blocker` のどれかに分類されている
- 次に実装する小タスクが番号付きで選べる
- read-only Phase 2 entry と live execution readiness の境界が維持されている

## やらないこと

- live order submission
- exchange write API
- wallet / signing work
- public micro live CLI の追加
- secrets の表示、記録、commit
- dummy balance / fills / position artifact の作成
- historical artifact の根拠なき書き換え
- phase gate 条件を緩めて blocker を消すこと
