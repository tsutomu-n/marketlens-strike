<!--
作成日: 2026-06-04_16:48 JST
更新日: 2026-06-04_17:10 JST
-->

# Operations Runbook

この runbook は current repo を再開・再検証・再生成するための最短手順です。`data/` は git 管理外なので、artifact は必要に応じて作り直します。

## Restart

```bash
uv run sis implementation-status --write
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

読む順番:

1. `docs/CURRENT_STATE.md`
2. `docs/CODE_STATUS.md`
3. `data/reports/current_state_index.md`
4. `data/reports/readiness_snapshot.md`
5. `data/reports/phase_gate_review.md`
6. `data/reports/operations_dashboard.md`

## Trade[XYZ] Migration Surfaces

registry / universe:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-data-cycle --dry-run
uv run sis collect-trade-xyz-data-cycle --duration-minutes 1440 --interval-seconds 60
uv run sis collect-trade-xyz-real-market-reference --period-days 365 --interval 1d
uv run sis collect-trade-xyz-account-fee --user-address 0x...
uv run sis collect-trade-xyz-historical-l2-archive --coin xyz:XYZ100 --date 2026-05-01 --hour 9
uv run sis collect-trade-xyz-historical-asset-ctxs-archive --date 2026-05-01
uv run sis plan-trade-xyz-historical-archive-bulk --coins xyz:AAPL,xyz:AMD,xyz:AMZN,xyz:EWJ,xyz:GOOGL,xyz:META,xyz:MSFT,xyz:NVDA,xyz:SP500,xyz:TSLA,xyz:XYZ100 --start-date 2026-05-01 --end-date 2026-05-30
uv run sis check-trade-xyz-historical-archive-preflight
uv run sis execute-trade-xyz-historical-archive-bulk --max-objects 10
uv run sis execute-trade-xyz-historical-archive-bulk --execute --acknowledge-requester-pays --max-objects 10
uv run sis normalize-trade-xyz-historical-archive-bulk
uv run sis normalize-trade-xyz-historical-archive-quotes --l2-jsonl-path data/raw/historical_archive/hyperliquid/market_data/20260501/9/l2Book/xyz:XYZ100.jsonl --asset-ctxs-path data/raw/historical_archive/hyperliquid/asset_ctxs/20260501.csv --coin xyz:XYZ100
uv run sis trade-xyz-collection-status
uv run sis trade-xyz-collection-status --fail-on-archive-preflight
uv run sis trade-xyz-collection-status --fail-on-account-fee-missing
uv run sis trade-xyz-collection-status --stale-after-minutes 180 --fail-on-stale
uv run sis trade-xyz-collection-status --fail-on-lock-stale
uv run sis trade-xyz-collection-status --fail-on-progress-warning
scripts/check_trade_xyz_data_prereqs.sh
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

long-running wrapper:

```bash
SIS_TRADE_XYZ_CYCLE_DRY_RUN=1 scripts/collect_trade_xyz_data_cycle.sh
scripts/collect_trade_xyz_data_cycle.sh
scripts/collect_trade_xyz_data_until_ready.sh
setsid -f scripts/collect_trade_xyz_data_until_ready.sh >/tmp/trade_xyz_until_ready.nohup 2>&1 < /dev/null
```

wrapper env:

```text
SIS_TRADE_XYZ_COLLECTION_CONFIG=configs/trade_xyz_data_collection.yaml
SIS_TRADE_XYZ_CYCLE_DURATION_MINUTES=1440
SIS_TRADE_XYZ_CYCLE_INTERVAL_SECONDS=60
SIS_TRADE_XYZ_CYCLE_SYMBOLS=
SIS_TRADE_XYZ_CYCLE_LOG_DIR=logs/trade_xyz_data_cycle
SIS_TRADE_XYZ_CYCLE_LOCK_DIR=.tmp/trade_xyz_data_cycle.lock
SIS_TRADE_XYZ_CYCLE_DRY_RUN=0
SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=
SIS_TRADE_XYZ_CYCLE_ALLOW_KNOWN_GAPS=0
SIS_TRADE_XYZ_CYCLE_REFRESH_REGISTRY=1
SIS_TRADE_XYZ_CYCLE_REGISTRY_SEED_PATH=configs/instrument_registry.seed.json
SIS_TRADE_XYZ_CYCLE_COLLECT_SIGNAL_CANDLES=1
SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_INTERVALS=
SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_PERIOD_DAYS=
SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_MAX_AGE_HOURS=
SIS_TRADE_XYZ_UNTIL_READY_POLL_SECONDS=300
SIS_TRADE_XYZ_UNTIL_READY_MAX_CYCLES=0
SIS_TRADE_XYZ_UNTIL_READY_LOG_DIR=logs/trade_xyz_data_cycle
SIS_TRADE_XYZ_UNTIL_READY_LOCK_DIR=.tmp/trade_xyz_data_until_ready.lock
SIS_TRADE_XYZ_UNTIL_READY_STALE_AFTER_MINUTES=180
SIS_TRADE_XYZ_UNTIL_READY_FAIL_ON_RUNNING_STALE=1
SIS_TRADE_XYZ_UNTIL_READY_FAIL_ON_LOCK_STALE=1
SIS_TRADE_XYZ_UNTIL_READY_ALLOW_KNOWN_GAPS=0
SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT=1
SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE=1
```

`SIS_TRADE_XYZ_CYCLE_SYMBOLS`、`SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_INTERVALS`、
`SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_PERIOD_DAYS`、
`SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_MAX_AGE_HOURS` が空の場合は
`configs/trade_xyz_data_collection.yaml` を使う。非秘密の対象銘柄、interval、
readiness閾値、archive対象coinはこのYAMLに置く。AWS profile、account fee用public
user address、credential類はYAMLへ入れず、環境変数またはCLI引数で渡す。

2026-05-30以前の実データは現在のTrade[XYZ]バックテスト/readiness作業では使わない。
該当データは `data/archive/pre_2026_05_31_unusable_real_data/` に移動済みで、
manifestは `data/archive/pre_2026_05_31_unusable_real_data/ARCHIVE_MANIFEST.json`。
5/30以前を含むartifactを再利用してready判定を作らない。

quote ingest:

- `collect-trade-xyz-quotes` は `probe trade-xyz` が生成した registry を読んで raw quote JSONL を収集する。
- `collect-trade-xyz-data-cycle` は read-only registry refresh、quote収集、normalization、reference/session/funding/readiness artifact再生成を1 cycleで実行する。30日coverageを作る通常運用ではこちらを使う。
- registry refresh はデフォルト有効。固定済みregistryだけで再現したい調査時は `--use-existing-registry`、wrapperでは `SIS_TRADE_XYZ_CYCLE_REFRESH_REGISTRY=0` を使う。
- `collect-trade-xyz-real-market-reference` は registry の `real_market_symbol` から yfinance reference barsを収集する。これはresearch/backtest参照用で、live execution dataではない。
- `collect-trade-xyz-signal-candles` は Hyperliquid `/info` の `candleSnapshot` から historical OHLCV を収集する。これは signal input 用で、fill snapshot と混ぜない。
- `collect-trade-xyz-signal-candles` は連続 `/info` request の 429 を避けるため `--request-delay-seconds` を持つ。デフォルトは `1.5` 秒。初回失敗 key は1回だけ retryし、retry delayは既定で `max(request_delay_seconds * 2, 3.0)` 秒。
- signal candle の最終失敗 key は、既存の成功済み parquet rows と raw candle JSON を上書きしない。失敗詳細は `data/raw/candles/trade_xyz_errors/<interval>/<symbol>.json` に保存し、manifest の `failed_keys` / `preserved_existing_row_count` / `request_errors` を見る。
- APIが正常に空payloadを返した場合は successful empty として扱う。この場合だけ、その key の既存 rows は空に置き換わる。timeout / 429 / schema mismatch などの例外とは区別する。
- `collect-trade-xyz-data-cycle` と `build-trade-xyz-data-bundle` は `--signal-candle-request-delay-seconds` を持つ。wrapperでは `SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_REQUEST_DELAY_SECONDS` を使う。
- `collect-trade-xyz-data-cycle` はデフォルトで `30m,4h,1d,3d` の signal candles も確認する。既存artifactが完全で `SIS_TRADE_XYZ_CYCLE_SIGNAL_CANDLE_MAX_AGE_HOURS` より新しければ再取得せず、quote coverage収集を優先する。
- `collect-trade-xyz-historical-l2-archive` は Hyperliquid historical L2 archive の raw requester-pays S3 download入口。デフォルトは dry-run で、実downloadには `--execute --acknowledge-requester-pays` と `aws` CLI が必要。archiveは月次更新・欠損ありで、通常の30日live quote collectorやreadiness coverageへ自動混入しない。
- `collect-trade-xyz-historical-asset-ctxs-archive` は同じ requester-pays S3 archive から日次 asset contexts CSV を取得する入口。historical L2 を実務利用する場合は、L2 bookだけでなく asset_ctxs も取得し、mark / oracle / funding context 欠損を別途検証する。
- `plan-trade-xyz-historical-archive-bulk` は複数coin・日付・時間の requester-pays S3 object一覧をmanifest化する。30日・11銘柄・全24時間なら L2 object は `7920`、asset_ctxs は `30`、合計 `7950` object になる。実download前に必ず費用・欠損・対象coin名を確認する。
- `execute-trade-xyz-historical-archive-bulk` はbulk plan manifestを読み、selected objectをdownloadする。デフォルトはdry-runで、実downloadには `--execute --acknowledge-requester-pays` と pass済みの `check-trade-xyz-historical-archive-preflight` が必要。まずdry-runの `--max-objects 1` や `--max-objects 10` で対象を確認し、費用とAWS preflightを受け入れる場合だけ `--execute --acknowledge-requester-pays` を付ける。download後もquote coverageは変わらず、normalizeが別途必要。
- archive download commandは `SIS_AWS_COMMAND` があればそれを使い、system `aws` が無ければ `uv run --with awscli aws` fallbackを使う。fallbackは初回tool installにnetworkを使うため、固定したい運用では `SIS_AWS_COMMAND="aws --profile <profile>"` を設定する。
- `check-trade-xyz-historical-archive-preflight` はAWS identity確認結果を `data/manifests/trade_xyz_historical_archive_preflight_manifest.json` に保存する。失敗時もmanifest化し、`trade-xyz-collection-status` の `historical_archive_preflight_status` から確認できる。
- `trade-xyz-collection-status` はarchive backfill用に `preflight_command`、bulk planの推定object数、bulk executionのdry-run/download/error数、bulk normalizationの処理済みfile数も出す。実download前に `sts get-caller-identity` が通ること、対象object数、直近dry-run結果を確認してから requester-pays downloadへ進む。
- archive preflightの失敗を監視で落としたい場合は `trade-xyz-collection-status --fail-on-archive-preflight` を使う。これはquote coverage未達とは別に、AWS資格情報やcommand設定の問題を明示的に失敗扱いにする。
- account-specific fee未取得を監視で落としたい場合は `trade-xyz-collection-status --fail-on-account-fee-missing` を使う。wrapperでは `SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS` を設定すると次のdata cycleでread-only userFees取得が走る。
- `scripts/check_trade_xyz_data_prereqs.sh` は archive preflight と account fee env をまとめて確認し、必要なら `--fail-on-archive-preflight` / `--fail-on-account-fee-missing` 付きの status を実行する。未設定時は `SIS_AWS_COMMAND="aws --profile <profile>"` と `SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS=0x...` のsetup hint、前提設定後の `scripts/collect_trade_xyz_data_until_ready.sh`、最終確認の `uv run sis trade-xyz-collection-status --strict --fail-on-not-ready` も出す。`SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS` が設定済みなら、このwrapper内で `collect-trade-xyz-account-fee` をread-only実行し、manifestを更新してからstatusを確認する。archiveを使わない検証では `SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT=0`、account feeをknown gapとして許す検証では `SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE=0` を使う。
- 外部前提が未設定でも quote coverage だけ伸ばす場合、wrapper が出す `continue_quote_collection_without_archive_or_account_fee_command` を使う。これは最終実務readyではなく、AWS/account feeが揃うまでの organic quote collection 継続用。
- `normalize-trade-xyz-historical-archive-bulk` はbulk planのdecompressed l2Bookと同日asset_ctxsをまとめて `data/raw/quotes/trade_xyz/*.jsonl` に変換し、既存coverageから見えるflat raw quote fileとして保存する。実download後の通常入口はこちらを使い、単体検証だけ `normalize-trade-xyz-historical-archive-quotes` を使う。
- `normalize-trade-xyz-historical-archive-quotes` はdownload済みの decompressed L2 JSONL と optional asset_ctxs CSV/JSON から traceable raw quote JSONL を生成する。`--normalize` を付けた時だけ `data/normalized/quotes.parquet` も再生成する。asset_ctxs が無い行は `BLOCK_HISTORICAL_ASSET_CTX_MISSING` 付きで `is_tradable=false` のまま保存する。
- `collect-trade-xyz-account-fee` は public user address だけで Hyperliquid `/info` の `userFees` をread-only取得する。wallet / signing / exchange write は使わない。
- `collect-trade-xyz-account-fee` の manifest は user addressをsha256だけで保存し、`user_taker_fee_bps` / `user_maker_fee_bps` を readiness の account-specific fee evidence に使う。
- `SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS` を設定している場合、readiness は `trade_xyz_account_fee_manifest.json` の `user_address_sha256` と設定値のsha256一致も確認する。別アカウントの古いmanifestは `account_specific_fee` の known gap として扱う。
- `collect-trade-xyz-data-cycle` と `build-trade-xyz-data-bundle` は `--account-fee-user-address 0x...` が指定された時だけ account fee snapshotも更新する。wrapperでは `SIS_TRADE_XYZ_ACCOUNT_FEE_USER_ADDRESS` を使う。
- wrapper / until-ready はデフォルトで strict readiness を使い、account-specific fee などの known gap が残る状態を完了扱いしない。研究用途で known gap を許す場合だけ `SIS_TRADE_XYZ_CYCLE_ALLOW_KNOWN_GAPS=1` / `SIS_TRADE_XYZ_UNTIL_READY_ALLOW_KNOWN_GAPS=1` を使う。
- builder fee approval は `builder` address が必要なので、この通常runbookでは取得しない。builder codeを使う別scopeが決まるまで `builder_fee_bps` を0扱いしない。
- `scripts/collect_trade_xyz_data_cycle.sh` は同じcycle commandをログ付きで実行する長時間運用入口。cron/systemdから呼ぶ場合もこのwrapperを使う。
- `scripts/collect_trade_xyz_data_until_ready.sh` は `trade-xyz-collection-status` をpollし、collectorが止まっていて `backtest_data_ready=false` の場合だけ `collect_trade_xyz_data_cycle.sh` を再起動する。30日coverage完了までtmux/systemd等で走らせる入口。`SIS_TRADE_XYZ_REQUIRE_ARCHIVE_PREFLIGHT=1` / `SIS_TRADE_XYZ_REQUIRE_ACCOUNT_FEE=1` の場合でも、collector稼働中は外部前提の失敗を理由に organic quote collection を止めない。collectorが止まっていて次cycleを起動する前だけ `--fail-on-archive-preflight` / `--fail-on-account-fee-missing` 付きstatusを実行し、AWS資格情報やaccount fee未設定を起動前gateとして扱う。
- until-ready supervisor は collector稼働中に最新raw fileが stale になった場合、または supervisor lock / 稼働中collectorのcycle lockが stale になった場合に異常終了する。`SIS_TRADE_XYZ_UNTIL_READY_FAIL_ON_RUNNING_STALE=0` / `SIS_TRADE_XYZ_UNTIL_READY_FAIL_ON_LOCK_STALE=0` で無効化できる。
- shell終了後も継続させる場合は `setsid -f ... >/tmp/trade_xyz_until_ready.nohup 2>&1 < /dev/null` のようにdetachする。通常のforeground実行はterminal/session終了で止まる前提で扱う。
- wrapperは `.tmp/trade_xyz_data_cycle.lock` で重複起動を止める。pid付きstale lockは起動時に回復し、pid無しの空lock directoryも回復する。非空lockや実processが残る場合は、既存processとlogを確認する。
- until-ready supervisorは `.tmp/trade_xyz_data_until_ready.lock` で重複起動を止める。pid付きstale lockは起動時に回復する。既存collectorが動いている場合は新しいcycleを重複起動せず、poll sleepに戻る。
- wrapperは実行後に `trade-xyz-collection-status` を呼び、最新status artifactを更新する。
- `trade-xyz-collection-status` は `data/ops/trade_xyz_collection_status.json` と `data/reports/trade_xyz_collection_status.md` を生成し、traceable rows、coverage残日数、`coverage_min_span_days`、`coverage_max_remaining_days_exact`、`coverage_completion_ratio_by_span`、最新raw file age、次のcycle commandを出す。
- readinessの残項目は `fail_count` / `known_gap_count` / `failing_requirements` / `known_gap_requirements` で確認する。通常の長期収集中は `failing_requirements=quote_coverage`、public user address未指定なら `known_gap_requirements=account_specific_fee` が残る。
- `trade-xyz-collection-status` は readiness の key別 details も出す。特に `funding_events_status` / `funding_events_skipped`、`oracle_timestamp_provenance_status` / `oracle_ts_missing_rate`、`signal_candles_status` / `signal_candles_request_error_count` を見る。
- account fee は `account_fee_user_address_configured` だけで判断しない。`account_fee_manifest_exists` / `account_fee_manifest_status` / `account_fee_manifest_user_matches_env` / `account_fee_user_taker_fee_bps` / `account_fee_user_maker_fee_bps` を合わせて確認し、envと古いmanifestの不一致やpartial manifestを見落とさない。
- oracle timestamp は `oracle_timestamp_manifest.json` の行数だけで完了扱いにしない。`oracle_ts_missing_count > 0` または `oracle_ts_present_count = 0` の場合、readinessは `oracle_timestamp_provenance` を known gap として扱う。`source_ts_ms`、受信時刻、client時刻で `oracle_ts_ms` を埋めない。
- session state は `session_state_manifest.json` の行数だけで完了扱いにしない。`session_type_counts` が空なら `session_state` は fail。`internal_session_open` / `maintenance_window` の欠損は supported symbol以外で known gap として扱い、open/closed に読み替えない。
- funding は `funding_history_join_manifest.json` の `row_count` だけで完了扱いにしない。`skipped` に非ゼロ項目がある場合は `funding_events` を known gap とし、oracle quote join漏れを確認する。
- real-market reference は `row_count` だけで完了扱いにしない。`missing_mapped_symbols` または `missing_requested_symbols` が残る場合は fail。
- signal candles は `row_count` だけで完了扱いにしない。registryがある場合は active Trade[XYZ] symbols が `symbols` に揃っていること、`requested_intervals` が `intervals` に揃っていること、かつ `request_error_count=0` を確認する。失敗時の再実行は readiness の `collect_signal_candles` next action を優先し、failed symbols / intervals だけを長めのdelayで再取得する。
- `trade-xyz-collection-status` は collector / supervisor process と lock も確認し、`collector_running` / `collector_process_count` / `cycle_lock_stale` / `supervisor_lock_stale` をreportに出す。coverage未達かつcollectorが止まっている場合は `scripts/collect_trade_xyz_data_cycle.sh` を next action に出す。
- `trade-xyz-collection-status` は前回statusとの差分も保存し、`progress_status` / `traceable_row_count_delta` をreportに出す。collectorが動いているのに十分な間隔後も traceable row が増えない場合は `progress_status=warning` を調査する。
- `trade-xyz-collection-status` はデフォルトで現在の raw quote JSONL から quote coverage manifest を再計算し、data readiness manifest も再評価する。古いmanifestをそのまま見たい調査時だけ `--no-refresh-coverage` / `--no-refresh-readiness` を使う。
- `--fail-on-stale` は最新raw fileが `--stale-after-minutes` を超えた場合に exit 2 を返す。監視ではこれを使う。
- `--fail-on-lock-stale` は cycle / supervisor lock のpidが死んでいる、またはpid fileが壊れている場合に exit 2 を返す。再起動監視ではこれも使う。
- `--fail-on-progress-warning` は `progress_status=warning` の場合に exit 2 を返す。collectorが動いているのにtraceable rowsが増えない状態の監視に使う。
- `--fail-on-account-fee-missing` は readiness の known gap だけでなく、`trade_xyz_account_fee_manifest.json` の有無、`status=pass`、maker/taker bps、env設定時のuser hash一致も直接確認して exit 2 を返す。
- `--fail-on-not-ready` は `backtest_data_ready=false` で exit 2 を返す。30日収集完了後のgate確認に使う。
- default では normalize まで実行する。raw JSONL だけ欲しい時は `--no-normalize` を使う。
- `--symbols`, `--max-symbols`, `--duration-minutes`, `--interval-seconds`, `--replace`, `--dry-run`, `--write-summary`, `--write-report`, `--output-dir` で収集対象と artifact 出力を絞れる。
- `--write-summary` は `data/ops/trade_xyz_quote_collection_summary.json`、`--write-report` は `data/reports/trade_xyz_quote_collection_report.md` を出す。
- registry / raw quote の fee fields は `configs/fee_model.trade_xyz.yaml` 由来。`fee_mode_unknown_rate` が再発した場合は config / registry / quote propagation を先に確認する。
- Trade[XYZ] diagnostics と phase gate は current artifact として latest quote file を見る。古い raw JSONL は audit trail として残り得る。
- legacy `gtrade` / `ostium` replay command は active CLI から削除済み。

real market and tracking:

```bash
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
```

## Strategy Research Lab

Strategy Lab は研究、候補生成、評価、paper 昇格判断までの surface です。live order surface ではありません。

canonical docs:

- `docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md`
- `docs/strategy_research_lab/README.md`
- `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md`
- `src/sis/research/strategy_lab/`
- `schemas/*strategy*`, `schemas/*candidate*`, `schemas/*intent*`

paper-only preview path:

```bash
uv run sis strategy-preview
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

artifact boundary:

- `data/research/strategy_signals.parquet` is the Strategy Lab signal artifact.
- `data/research/strategy_signals.jsonl` is the Strategy Lab line-delimited export.
- `data/research/signals.csv` is a legacy thin export, not the Strategy Lab source of truth.
- `data/research/trial_ledger.jsonl` records all trials, not only the best trial.
- `data/research/paper_candidate_pack.json` contains candidates and selected/rejected IDs.
- `data/research/promotion_decision.json` is the human decision artifact required before paper intent preview.
- `data/bot/paper_intent_preview.json` is paper-only and must be revalidated before paper execution.

stop conditions:

- Do not treat `data/research/signals.csv` as the Strategy Lab source of truth.
- Do not build `PaperIntentPreview` without `PromotionDecision`.
- Do not treat `PaperIntentPreview` as `OrderIntent` or live order.
- Do not override `live_conversion_allowed=false`, `wallet_used=false`, or `exchange_write_used=false`.
- Use `profitability_claimed`, `paper_ready_claimed`, `tiny_live_ready_claimed`, and `live_ready_claimed` for forbidden claim names. Legacy `*_claim` names are not the current Strategy Lab claim names.

Alpaca provider:

- `fetch_alpaca_bars()` は silent empty stub ではない。
- credentials が無い場合は `AlpacaProviderUnavailable` で止まる。
- live fetch を使う場合は `.env` に `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY` を書く。`ALPACA_API_KEY` / `ALPACA_SECRET_KEY`、`SIS_ALPACA_API_KEY` / `SIS_ALPACA_SECRET_KEY` も fallback として使える。
- credentials を repo に書かない。

`.env` setup:

```bash
cp .env.example .env
$EDITOR .env
```

`.env` に書く最小値:

```bash
APCA_API_KEY_ID=...
APCA_API_SECRET_KEY=...
```

Alpaca credentials smoke:

```bash
uv run sis alpaca-smoke --symbol NVDA --timeframe 15m --limit 1 --feed iex
```

Historical connectivity smoke:

```bash
uv run sis alpaca-smoke --symbol NVDA --timeframe 1d --start 2025-05-01 --end 2025-05-02 --limit 1 --feed iex
```

Expected artifacts:

- `data/ops/alpaca_live_smoke_summary.json`
- `data/reports/alpaca_live_smoke.md`
- `data/raw/real_market/alpaca/NVDA_15m_latest.json`

Failure behavior:

- credentials が無い場合も summary / report を書いて `status=failed` で終了する。
- Alpaca が正常な JSON response を返しても `bars={}` の場合は `status=blocked`, `provider_connectivity_status=pass`, `data_availability_status=empty`, `live_suitability_reasons=BLOCK_ALPACA_NO_BARS` とする。
- live bars が返っても `source_confidence` が閾値未満なら `status=blocked` とし、`live_suitability_reasons=BLOCK_LOW_SOURCE_CONFIDENCE` を出す。
- historical connectivity smoke は API / credentials の疎通確認用。古いbarなので `status=blocked` でも `provider_connectivity_status=pass` なら provider connectivity は確認できている。
- Alpaca 公式 docs 上、latest bars は最新分足 endpoint、free/live data の標準 feed は IEX、stock bar は取引がない interval では生成されない。したがって `bars={}` は credentials/API failure ではなく data availability failure として扱う。
- summary / report / raw payload に credential secret を書かない。
- `status=pass` は Alpaca provider が live bars を返し、live suitability blocker が無いことを示す。production live trading ready ではない。

## Trade[XYZ] Pure Backtest

Trade[XYZ] pure backtest v0.1 は public CLI ではなく Python API surface です。`uv run sis build-backtest` は既存 bridge 系 command であり、pure backtest の入口ではありません。

docs:

- `docs/backtest/README.md`
- `docs/backtest/TRADE_XYZ_PURE_BACKTEST_V0_1.md`

focused verification:

```bash
uv run pytest -q tests/backtest
```

実データ smoke は `data/normalized/quotes.parquet` が存在する場合だけ検査します。

```bash
uv run pytest -q tests/backtest/test_real_data_smoke.py
```

主な artifact:

- `backtest_run.json`
- `orders.parquet`
- `fills.parquet`
- `trades.parquet`
- `equity_curve.parquet`
- `metrics.json`
- `data_quality.json`
- `data_manifest.json`
- `candidate_result.json`
- `backtest_report.md`
- `backtest_report.html`

stop conditions:

- Do not expose a public CLI without a separate scope decision.
- Do not connect pure backtest artifacts to live order submission.
- Do not use wallet, signing, or exchange write APIs.
- Do not treat Strategy Authoring fixed-horizon metrics as the same engine.

## Paper Operations

paper state を 1 cycle 進める:

```bash
uv run sis paper-operations-cycle
```

関連 artifact:

- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`
- `data/reports/daily_paper_report.md`
- `data/reports/paper_operations_runbook.md`

## Execution And Ops Artifacts

read-only execution surface:

```bash
uv run sis execution-snapshot
uv run sis execution-venue-comparison
uv run sis execution-venue-diagnostics
uv run sis execution-read-only-surfaces
```

single-command surface:

```bash
uv run sis healthcheck
uv run sis notification-outbox --level warn --title "Stale" --body "recollect live evidence"
```

## Live Evidence

gTrade / Ostium の legacy collector は `archive/gtrade_ostium_legacy_archive_*.zip` に圧縮済みで、展開済み file tree は active repo から削除済み。legacy sidecar command を直接呼ぶ手順は current CLI として扱わない。

dry-run:

```bash
uv run python scripts/run_live_evidence.py --dry-run
```

run:

```bash
uv run python scripts/run_live_evidence.py --duration-minutes 120 --metadata-interval-seconds 60
```

この non-dry-run path は現在停止する。legacy gTrade/Ostium collector はZIP化済みなので、現行の収集は次のTrade[XYZ] refresh pathを使う。

Trade[XYZ] refresh path:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
uv run sis bot-preview
```

`check-go-no-go` と `build-evidence-card` は補助reportとして残る。Bot前の現行判定は `phase-gate-review` を正本にする。
`bot-preview` は read-only のHOLD判定 artifact を実行時に生成する。wallet、署名、exchange write APIは使わない。`data/bot/bot_decision.json` と `data/reports/bot_orders_preview.md` が無い場合は未実装ではなく、まだ実行されていない可能性が高い。

PR12 fresh read-only smoke path:

```bash
uv run sis probe trade-xyz
uv run sis collect-trade-xyz-quotes --symbols SP500,XYZ100,NVDA,AAPL,MSFT --duration-minutes 60 --interval-seconds 60 --normalize --replace --write-summary --write-report
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis build-signals
uv run sis check-research-quality
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis paper-operations-cycle
uv run sis refresh-operations-artifacts
uv run sis phase-gate-review
```

2026-05-28 の current artifact:

- `data/ops/trade_xyz_quote_collection_summary.json`: 11 active Trade[XYZ] rows in the latest refresh
- `data/ops/phase_gate_review_summary.json`: `phase_gate_decision=READ_ONLY_GO`, `phase2_entry_allowed=true`, `blockers=[]`
- `data/ops/phase_gate_review_summary.json`: `execution_drift_classification_counts={"P2_BLOCKER":0,"LIVE_READINESS_BLOCKER":5}`

2026-05-27 の PR12 long-window evidence:

- `data/ops/trade_xyz_quote_collection_summary.json`: 310 rows, 3673.995702 observed seconds
- `data/ops/pr12_fresh_read_only_smoke_summary.json`: `final_decision=READ_ONLY_GO`
- `data/reports/pr12_fresh_read_only_smoke_report.md`: 5 symbols x 62 rows

`docs/archive/legacy_read_only_collectors_2026-05-28/` 配下の 3 文書は、この legacy read-only collector chain の補助資料です。`Trade[XYZ]` migration 完了そのものの説明ではありません。

## Daemon And Notifications

bounded local loop:

```bash
uv run sis daemon-run --mode paper --command "uv run sis paper-step" --max-cycles 1
```

dry-run:

```bash
uv run sis daemon-dry-run --mode paper --command "uv run sis paper-step" --every-minutes 30
```

`daemon-run` は local command-loop runner です。external supervisor や remote orchestration は未完了です。

## Micro Live Boundary

`Trade[XYZ]` micro live canary は code/test surface としては存在するが、現時点では public CLI command を公開していない。

標準確認:

```bash
uv run pytest tests/test_trade_xyz_live_order_policy.py tests/test_trade_xyz_adapter_safety.py tests/test_micro_live_canary.py -q
```

manual live smoke は標準運用手順に含めない。wallet / signing / exchange write integration は別途レビュー前提。

## Stop Conditions

- `phase-gate-review` が `phase2_entry_allowed=false` の間は、運用上の昇格完了と扱わない。ただし legacy artifact blocker が出ている場合は current Trade[XYZ] path と legacy path を分けて読む。
- generated artifact が欠けている場合、推測で判断せず再生成する。
- `READ_ONLY_GO` を production live trading ready と読まない。fee mode unknown の再発、execution drift degraded、micro live public CLI 不在は別 gate として扱う。
- `execution_drift_classification_counts.LIVE_READINESS_BLOCKER > 0` の間は live trading ready と扱わない。
- micro live code path があることをもって live trading ready と解釈しない。
- Strategy Lab schema / candidate / paper preview があることをもって live-ready と解釈しない。
- Strategy Lab の JSON Schema は thin guard。詳細 validation は `src/sis/research/strategy_lab/` の Pydantic model に従う。
- migration docs と legacy live evidence docs を混同しない。
