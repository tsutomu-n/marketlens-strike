<!--
作成日: 2026-06-17_21:52 JST
更新日: 2026-07-01_20:42 JST
-->

# Paper And Execution Runbook

Paper operations、read-only execution artifacts、legacy live evidence、daemon、micro-live boundary の domain runbook です。ここにある手順は paper / read-only / local loop の確認であり、wallet、signing、exchange write、production live trading permission ではありません。

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

## Strategy Lifecycle Readback

NDX paper observation session や `strategy-paper-observation-cycle` の後は、paper execution の成否だけでなく Strategy Lifecycle の status を読む。canonical NDX review artifact は `data/research/ndx/paper_observation_review_decision.json`。

```bash
uv run sis strategy-lifecycle-review \
  --data-dir data \
  --paper-review-path data/research/ndx/paper_observation_review_decision.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports

uv run sis strategy-paper-observation-status \
  --data-dir data \
  --canonical-review-path data/research/ndx/paper_observation_review_decision.json \
  --lifecycle-review-path data/research/strategy_lifecycle/strategy_lifecycle_review.json \
  --out data/research/strategy_lifecycle \
  --reports-dir data/reports
```

読む値:

- `latest_normal_requirement_gaps.trading_days`
- `normal_thresholds_met`
- `smoke_pass_counts_as_normal_pass=false`
- `permits_live_order=false`
- `live_conversion_allowed=false`

詳細は [docs/strategy_lifecycle/README.md](../strategy_lifecycle/README.md) と [docs/research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md](../research/ndx/15_LAYER_2_8_PAPER_OBSERVATION_REVIEW.md) を読む。

## Execution And Ops Artifacts

read-only execution surface:

```bash
uv run sis execution-snapshot
uv run sis execution-venue-comparison
uv run sis execution-venue-diagnostics
uv run sis execution-read-only-surfaces
```

Trade[XYZ] の read-only execution state collector は、通常実行では external API を呼ばない。public user address と明示 opt-in がない場合は、`trade_xyz_execution_state_user_address_missing` または opt-in required として artifact に残る。

read-only account state を明示的に取りたい場合だけ、local `.env` で次を設定する。これは公開 user address だけであり、wallet secret、signing、live order、exchange write credential ではない。

```bash
SIS_TRADE_XYZ_EXECUTION_STATE_USER_ADDRESS=<public-user-address>
SIS_TRADE_XYZ_EXECUTION_STATE_COLLECTOR_ENABLED=1
```

この設定後に `uv run sis execution-read-only-surfaces` と `uv run sis execution-snapshot` を再実行する。production live trading ready とは読まない。

single-command surface:

```bash
uv run sis healthcheck
uv run sis notification-outbox --level warn --title "Stale" --body "recollect live evidence"
```

## Live Evidence

gTrade / Ostium の legacy collector は active repo から削除済み。必要な場合だけ ignored local `/archive/` 配下に legacy package を置く。fresh clone は legacy package を含まず、legacy sidecar command を直接呼ぶ手順は current CLI として扱わない。

dry-run:

```bash
uv run python scripts/run_live_evidence.py --dry-run
```

run:

```bash
uv run python scripts/run_live_evidence.py --duration-minutes 120 --metadata-interval-seconds 60
```

この non-dry-run path は現在停止する。legacy gTrade/Ostium collector は active repo には存在しないので、現行の収集は次のTrade[XYZ] refresh pathを使う。

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

artifact の読み方:

- `data/ops/phase_gate_review_summary.json`: `phase_gate_decision`、`phase2_entry_allowed`、`blockers`、`execution_drift_classification_counts`、`execution_snapshot_reason`、`execution_snapshot_next_action` を読む。
- `data/manifests/trade_xyz_data_readiness_manifest.json`: `decision`、`backtest_data_ready`、失敗理由、known gaps、`real_market_reference`、`signal_candles`、`account_specific_fee` を読む。
- `data/manifests/funding_history_join_manifest.json`: `row_count`、`usable_as_backtest_funding_event`、`skipped` を読む。値は artifact 再生成で変わり得る。
- `data/ops/pr12_fresh_read_only_smoke_summary.json`: `final_decision`、対象 symbol、row count、report path を読む。fixed snapshot を runbook にコピーしない。
- 過去の PR12 long-window evidence の行数や観測秒数は historical snapshot として扱う。現在値の証明には、上の command を再実行して runtime artifact を読む。

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

`paper-step` is the legacy paper loop over `data/research/signals.csv`. If that
legacy export contains NDX/QQQ family rows, the current code skips paper
order/fill generation and records `legacy_paper_blocked_count` plus
`legacy_paper_blocked_reason_counts` in the step summary.

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
