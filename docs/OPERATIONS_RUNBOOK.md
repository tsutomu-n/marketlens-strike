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
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis diagnose-quotes --venue trade_xyz
uv run sis validate-artifacts --strict
uv run sis phase-gate-review
```

quote ingest:

- `collect-trade-xyz-quotes` は `probe trade-xyz` が生成した registry を読んで raw quote JSONL を収集する。
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

Alpaca provider:

- `fetch_alpaca_bars()` は silent empty stub ではない。
- credentials が無い場合は `AlpacaProviderUnavailable` で止まる。
- live fetch を使う場合は `APCA_API_KEY_ID` / `APCA_API_SECRET_KEY`、または `ALPACA_API_KEY` / `ALPACA_SECRET_KEY`、または `SIS_ALPACA_API_KEY` / `SIS_ALPACA_SECRET_KEY` を環境変数で渡す。
- credentials を repo に書かない。

Alpaca credentials smoke:

```bash
uv run sis alpaca-smoke --symbol NVDA --timeframe 15m --limit 1 --feed iex
```

Expected artifacts:

- `data/ops/alpaca_live_smoke_summary.json`
- `data/reports/alpaca_live_smoke.md`
- `data/raw/real_market/alpaca/NVDA_15m_latest.json`

Failure behavior:

- credentials が無い場合も summary / report を書いて `status=failed` で終了する。
- live bars が返っても `source_confidence` が閾値未満なら `status=blocked` とし、`live_suitability_reasons=BLOCK_LOW_SOURCE_CONFIDENCE` を出す。
- summary / report / raw payload に credential secret を書かない。
- `status=pass` は Alpaca provider が live bars を返し、live suitability blocker が無いことを示す。production live trading ready ではない。

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
- `data/ops/phase_gate_review_summary.json`: `execution_drift_classification_counts={"P2_BLOCKER":0,"LIVE_READINESS_BLOCKER":6}`

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
- migration docs と legacy live evidence docs を混同しない。
