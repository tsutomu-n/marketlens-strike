<!--
作成日: 2026-05-29_10:40 JST
更新日: 2026-06-05_08:11 JST
-->

# Live Readiness Blocker Decomposition Plan 2026-05-29

この文書は `./.ai_memory/HANDOFF.md` の A5 後に実行する詳細計画です。古い chat transcript や archive docs は前提にしません。判断の正本は current code、tests、`data/ops/`、`data/reports/`、tracked current docs です。

## 結論

次にやることは、`LIVE_READINESS_BLOCKER=5` をすぐ消すことではありません。最初にやるべきことは、5 個の blocker が本当に 5 個の独立問題なのか、`execution_snapshot_summary.venues=[]` から派生した 1 系統の live-readiness 未接続なのかを、code path と artifact で固定することです。

最良の順序:

1. A1-A5 で current gate を再確認する。
2. C1-C2 で execution snapshot 起点の root cause と blocker lineage を確定する。
3. C3 で reason code / report lineage を先に直すか判断する。
4. C4 で read-only execution state collector が必要か決める。
5. C5 は collector が必要な場合だけ計画する。
6. B7 で strict validation、phase gate、repo health を閉じる。

現時点の境界:

- read-only Phase 2 entry: green
- latest phase gate: `READ_ONLY_GO`
- `phase2_entry_allowed=true`
- `P2_BLOCKER=0`
- `LIVE_READINESS_BLOCKER=5`
- live order submission: 対象外
- exchange write API: 対象外
- wallet / signing work: 対象外
- public micro live CLI: 対象外

この計画の目的は live trading を開始することではありません。目的は、live execution readiness に残る blocker を、named signal、source artifact、owning code path、root cause、修正方針、検証コマンドまで落とすことです。

## Verified Current Facts

この節は、計画上の前提と推測を混ぜないための確認済み facts です。

| fact | value | source |
|---|---|---|
| `_write_execution_snapshot` input | `build_execution_snapshot_report(venue_snapshots=[])` | `src/sis/commands/execution_artifacts.py` |
| unsupported legacy adapter behavior | `_adapter_for_venue(...)` raises `Unsupported venue`; legacy gTrade/Ostium adapters removed; Trade[XYZ] live execution is micro-live safety path | `src/sis/commands/execution_artifacts.py` |
| execution snapshot status | `overall_status=degraded` | `data/ops/execution_snapshot_summary.json` |
| execution snapshot venue count | `venue_count=0` | `data/ops/execution_snapshot_summary.json` |
| execution snapshot venues | `[]` | `data/ops/execution_snapshot_summary.json` |
| snapshot report status rule | empty `venue_snapshots` becomes `overall_status=degraded` | `src/sis/reports/execution_snapshot.py` |

Implication:

`LIVE_READINESS_BLOCKER=5` は、現時点では production live execution が壊れている証拠というより、standard operations artifact に Trade[XYZ] execution venue snapshot が接続されていない状態を phase gate が live-readiness blocker として正しく残している可能性が高い。

ただし、これはまだ最終結論ではありません。C1-C2 で downstream artifact を確認し、empty snapshot 由来ではない blocker が混ざっていないかを必ず分けます。

## External Research Notes 2026-05-29

短時間調査と Context7 で確認した実装判断:

- Hyperliquid の read-only 側は `POST https://api.hyperliquid.xyz/info` に集約され、fills、order status、open orders、user state などは Info endpoint で扱える。B1-B4 相当の分解では Exchange endpoint / live write API に進まず、まず read-only execution state と artifact comparison を厚くする。
- Hyperliquid の REST aggregate weight は IP 単位で `1200/min`。`l2Book`, `allMids`, `clearinghouseState`, `orderStatus`, `spotClearinghouseState`, `exchangeStatus` は weight 2、fills 系は返却件数に応じた追加 weight がある。collector を作る場合は endpoint type、request count、weight assumption、pagination window、returned row count、error class を artifact に残す。
- Alpaca latest stock bar は feed が `sip`, `iex`, `delayed_sip`, `boats`, `overnight`, `otc` に分かれ、default feed は subscription に依存する。fresh source confidence は `status=pass` だけでなく、`feed`, `latest_bar_ts`, `market_session`, `requested_window`, `source_confidence_reason` を artifact に残す。
- `httpx` は default timeout を持つ。connect retry は `HTTPTransport(retries=...)` で扱えるが、429/500/provider-specific retry は明示的な retry policy として扱う。既存 dependency の `tenacity` を使う場合も、retry 対象、最大試行、stop condition を artifact に残す。
- Context7 では `/hyperliquid-dex/hyperliquid-python-sdk`, `/alpacahq/alpaca-py`, `/encode/httpx` を確認した。SDK 追加はまだ必須ではない。現 repo の `httpx` + fixture / mock test 方針で、read-only contract を先に固めるのが局所的。

参照:

- Hyperliquid Info endpoint: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint
- Hyperliquid rate limits: https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/rate-limits-and-user-limits
- Alpaca latest bars: https://docs.alpaca.markets/us/reference/stocklatestbars-1
- Alpaca-py stock historical data: https://alpaca.markets/sdks/python/api_reference/data/stock/historical.html
- HTTPX timeouts: https://www.python-httpx.org/advanced/timeouts/
- HTTPX transports: https://www.python-httpx.org/advanced/transports/

## Non-Negotiable Boundaries

| boundary | allowed | forbidden |
|---|---|---|
| Phase 2 read-only entry | preserve `READ_ONLY_GO`, strict validation green, artifact lineage clear | treat `READ_ONLY_GO` as live trading ready |
| Execution readiness | classify blockers, improve reason codes, add read-only collector only if scoped | live order submission, exchange write API, public micro live CLI |
| Secrets | use env-driven controlled failure, never print secrets | write API keys/secrets to repo, docs, logs, fixtures |
| Artifacts | regenerate or compare real artifacts | dummy balance/fills/position artifact to make green |
| History | classify historical drift | rewrite historical artifacts without reproducible reason |
| Tests | failing targeted test or fixture comparison before code fix | report-only changes that hide broken comparison |

## Error Risk Audit

この計画で潰すべき誤謬リスク:

| risk | bad conclusion | correct handling |
|---|---|---|
| `LIVE_READINESS_BLOCKER=5` を 5 独立バグと読む | 不要な collector / adapter 実装を始める | C1-C2 で root signal と derived signal を分ける |
| `venue_count=0` を regression と断定する | legacy adapter 削除を巻き戻す | current architecture では intentional not-connected surface の可能性を先に検証する |
| blocker を消すことを目的化する | phase gate 緩和や dummy artifact が混ざる | blocker が正確に説明されることを先に完了条件にする |
| read-only と write API を混ぜる | secrets / signing / live order risk が出る | Info endpoint 相当の read-only collector と live write path を別 interface にする |
| Alpaca historical success を fresh pass と読む | source confidence を過大評価する | feed、timestamp、market session、request window を artifact に必須化する |
| rate limit を軽視する | fills / history 取得で 429 や不安定化 | bounded window、pagination、weight assumption を artifact に残す |
| `./scripts/check` の test count を固定真実と見る | test 数変更を regression と誤読する | pass/fail、実数、変更理由を記録する |
| git status だけで data 鮮度を判断する | stale artifact を current と誤読する | summary timestamp、row count、digest、source path を確認する |

## Omission Audit

割愛しない確認項目:

- source artifact: どの JSON/markdown が blocker を出しているか。
- owning code path: どの Python module がその signal を生成しているか。
- root or derived: その blocker が直接原因か、empty snapshot から派生した下流 signal か。
- freshness: artifact の timestamp、row count、raw path、summary path。
- classification: `P2_BLOCKER`, `LIVE_READINESS_BLOCKER`, `accepted blocker`, `stale artifact`, `code regression`, `policy decision`。
- read-only feasibility: Info endpoint 相当で取れるか、live write が必要か。
- risk metadata: timeout、429、schema mismatch、empty result、permission error を区別するか。
- verification: targeted test、fixture comparison、strict validation、phase gate、`./scripts/check`。
- stop condition: どこで止まるか。

## Execution Plan

### A1 Repo State Confirm

Run:

```bash
git status --short --branch --untracked-files=all
```

Expect:

- branch は `main...origin/main`
- user-owned docs/algo 変更があれば記録する
- 依頼外の変更は revert しない

Stop:

- 対象コードや generated artifact に、今回の調査と衝突する未確認変更がある

### A2 Fresh Quote Evidence Confirm

Run:

```bash
jq '{row_count,duration_minutes,interval_seconds,api_error_count,collected_symbols,started_at,ended_at}' data/ops/trade_xyz_quote_collection_summary.json
wc -l data/raw/quotes/trade_xyz/2026-05-28.jsonl
```

Expect:

- `row_count=660`
- `duration_minutes=60`
- `interval_seconds=60`
- `api_error_count=0`
- raw JSONL は 660 行

Stop:

- artifact が欠けている
- row count が summary と raw で一致しない

### A3 Strict Artifact Validation

Run:

```bash
uv run sis validate-artifacts --strict
```

Expect:

- `checked_files=12`
- `issues=0`

Stop:

- strict validation が失敗する
- Trade[XYZ] current artifact と legacy artifact のどちらが原因か切り分けられない

### A4 Phase Gate Confirm

Run:

```bash
uv run sis phase-gate-review
```

Expect:

- `decision=READ_ONLY_GO`
- `phase2_entry_allowed=True`
- `P2_BLOCKER=0`
- `LIVE_READINESS_BLOCKER=5`

Stop:

- `P2_BLOCKER > 0`
- `phase2_entry_allowed=false`
- live-readiness-only drift が P2 remediation loop に戻っている

### A5 Repository Health Gate

Run:

```bash
./scripts/check
```

Expect:

- Python `3.13.7`
- `ruff` pass
- `pyrefly` 0 errors
- pytest pass

Note:

以前の handoff では `pytest 294 passed`。実行時の test count が違う場合は、test 追加/削除由来か regression かを分けて記録する。

Stop:

- `./scripts/check` が失敗する
- 失敗原因が generated artifact 鮮度なのか code regression なのか切り分けられない

### C1 Execution Snapshot Root-Cause Inventory

Purpose:

`LIVE_READINESS_BLOCKER=5` の upstream root が `execution_snapshot_summary.venues=[]` かどうかを、artifact と code path で確認する。

Read:

```bash
sed -n '1,140p' src/sis/commands/execution_artifacts.py
sed -n '1,160p' src/sis/reports/execution_snapshot.py
jq '.' data/ops/execution_snapshot_summary.json
jq '.' data/ops/execution_venue_comparison_summary.json
jq '.' data/ops/execution_venue_diagnostics_summary.json
jq '.execution_drift_classifications' data/ops/phase_gate_review_summary.json
```

Confirm:

- `_write_execution_snapshot` が `venue_snapshots=[]` を渡している
- `execution_snapshot_summary.venue_count=0`
- downstream comparison / diagnostics が空 snapshot 由来で degraded になっているか
- `phase_gate_review` はそれを P2 blocker ではなく live-readiness blocker として分類しているか

Deliverable:

| blocker | root source | derived from empty snapshot? | code path | classification |
|---|---|---|---|---|
| `execution_drift_overview_status` | TBD | TBD | TBD | TBD |
| `execution_balance_gap_detected` | TBD | TBD | TBD | TBD |
| `execution_fills_gap_detected` | TBD | TBD | TBD | TBD |
| `execution_comparison_all_registries_present` | TBD | TBD | TBD | TBD |
| `execution_state_comparison_mismatching_count` | TBD | TBD | TBD | TBD |
| `execution_snapshot_drift_mismatching_snapshot_count` | TBD | TBD | TBD | TBD |

Stop:

- empty snapshot 以外の原因が混じっているのに、全部を同じ root cause と断定しそうになる
- generated artifact が stale で、current code path と対応しない

### C2 Blocker Lineage Map

Purpose:

6 blocker を independent blocker ではなく lineage として整理する。

Initial hypothesis:

```text
execution_snapshot.venues=[]
  -> execution_comparison_all_registries_present=false
  -> execution_balance_gap_detected=true
  -> execution_fills_gap_detected=true
  -> execution_drift_overview_status=degraded
  -> execution_state_comparison_mismatching_count=3
  -> execution_snapshot_drift_mismatching_snapshot_count=3
```

Required output:

- blocker lineage diagram
- root signal / derived signal の分類
- each signal の upstream source artifact
- each signal の owning code path
- each signal の recommended next action

Completion:

- 6 signals のうち、どれが root signal で、どれが derived signal か説明できる
- root cause が 1 つなら、6 個を別々に実装しない判断ができる
- root cause が複数なら、実装 task を root cause 単位に分けられる

### C3 Reason-Code First Fix Decision

Purpose:

最初の実装修正を「blocker 解消」ではなく「なぜ blocked かを artifact に正確に出す」方向にするか判断する。

Candidate reason codes:

- `trade_xyz_live_execution_snapshot_not_connected`
- `legacy_execution_adapter_surface_removed`
- `micro_live_safety_path_not_exported_to_operations_snapshot`
- `execution_snapshot_empty_by_design`
- `read_only_execution_state_collector_not_implemented`

Candidate target files:

- `src/sis/commands/execution_artifacts.py`
- `src/sis/reports/execution_snapshot.py`
- `src/sis/reports/execution_venue_comparison.py`
- `src/sis/reports/execution_venue_diagnostics.py`
- `src/sis/reports/execution_drift_overview.py`
- `src/sis/reports/phase_gate_review.py`
- corresponding tests

Acceptance:

- `READ_ONLY_GO` は維持
- `LIVE_READINESS_BLOCKER` は消さない
- blocker reason が `degraded` だけでなく、Trade[XYZ] execution snapshot 未接続として読める
- JSON summary と markdown report の両方に reason が出る
- tests が reason code を固定する

Stop:

- reason code 追加が phase gate 条件緩和に変質する
- live-readiness blocker を消すためだけの表示変更になる

### C4 Read-Only Execution State Collector Scope Decision

Purpose:

collector を作るかどうかを実装前に決める。collector は新機能なので、C3 の reason-code fix と混ぜない。

Collector が必要な場合だけ検討する read-only fields:

- account / clearinghouse state
- positions
- open orders
- order status
- fills by bounded time window
- request metadata: endpoint type, request window, pagination, returned row count, rate-limit weight assumption, error class

Read-only collector requirements:

- Info endpoint 相当だけを使う。
- order placement、cancel、modify、signing は対象外。
- empty result、API error、timeout、429、permission error、schema mismatch を区別する。
- returned row count と endpoint weight assumption を artifact に出す。
- network smoke は opt-in にする。

If not implementing:

- `LIVE_READINESS_BLOCKER` は accepted blocker として残す
- micro live safety path と operations artifact の未接続を明記する
- 次の実装は C3 の reason-code hardening に限定する

Stop:

- live write API、wallet、signing、secret が必要になる
- public micro live CLI を増やす必要が出る
- dummy state artifact で snapshot を green にしようとする

### C5 Collector Implementation Plan

この段階は C4 で collector が必要と判断した場合だけ実行する。

Implementation direction:

- `src/sis/venues/trade_xyz/client.py` に read-only `/info` method を追加する
- `src/sis/execution/trade_xyz_adapter.py` の live write safety path と混ぜない
- `src/sis/commands/execution_artifacts.py` は collector result を operations snapshot に渡すだけにする
- fixture / mocked `httpx` tests を先に追加する
- live network smoke は opt-in、secrets なし、write なしにする

Minimum tests:

- read-only client request body and response normalization
- timeout / 429 / schema mismatch are not empty success
- snapshot summary includes request metadata
- diagnostics distinguish unavailable from empty
- phase gate keeps `LIVE_READINESS_BLOCKER` if collector is unavailable

Out of scope:

- order placement
- cancel
- signing
- wallet integration
- public live CLI
- production live trading

### B7 Verification Closeout

Run:

```bash
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
./scripts/check
jq '.execution_drift_classification_counts' data/ops/phase_gate_review_summary.json
jq '.execution_drift_classifications' data/ops/phase_gate_review_summary.json
```

Expect:

- strict validation: `issues=0`
- phase gate: `READ_ONLY_GO`
- `phase2_entry_allowed=True`
- `P2_BLOCKER=0`
- live-readiness blocker が残る場合は `LIVE_READINESS_BLOCKER` として残る
- live-readiness blocker を解消した場合でも、live order submission は別 gate として扱う

Stop:

- `LIVE_READINESS_BLOCKER=0` だけを根拠に production live trading ready と判断しそうになる
- live order submission、exchange write API、wallet / signing work へ進みそうになる
- `P2_BLOCKER` と `LIVE_READINESS_BLOCKER` が混ざる

## Implementation Backlog Shape

C1-C4 の後、実装 backlog はこの形で残す。

| id | task | target files | acceptance | verification | stop |
|---|---|---|---|---|---|
| R1 | reason-code hardening | report modules + tests | blocker reason is explicit; blocker not hidden | targeted pytest + phase gate | phase gate relaxation |
| R2 | lineage report cleanup | execution drift reports + tests | root/derived signals are visible | fixture comparison | historical rewrite |
| R3 | read-only collector contract | client + models + tests | no live write, metadata emitted | mocked httpx tests | secrets/signing required |
| R4 | operations snapshot integration | execution artifacts + tests | snapshot gets real read-only state or explicit unavailable reason | targeted pytest + generated summary | dummy artifact |
| R5 | Alpaca feed-aware freshness | Alpaca provider/reports + tests | feed/timestamp/session/source confidence reason emitted | mocked provider + optional smoke | feed error treated as empty |

## Completion Criteria

この計画は、次を満たしたら完了です。

- A1-A5 の再確認結果が記録されている
- 6 個の live-readiness blocker が named signal と source artifact に落ちている
- 各 blocker に owning code path がある
- 各 blocker が root signal か derived signal か分類されている
- `execution_snapshot_summary.venues=[]` 由来の blocker と、別原因の blocker が分離されている
- 次に実装する小タスクが番号付きで選べる
- read-only Phase 2 entry と live execution readiness の境界が維持されている

## Do Not Do

- live order submission
- exchange write API
- wallet / signing work
- public micro live CLI の追加
- secrets の表示、記録、commit
- dummy balance / fills / position artifact の作成
- historical artifact の根拠なき書き換え
- phase gate 条件を緩めて blocker を消すこと
- `LIVE_READINESS_BLOCKER=0` だけで production live trading ready と判断すること
