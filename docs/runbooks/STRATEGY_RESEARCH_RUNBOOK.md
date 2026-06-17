<!--
作成日: 2026-06-17_21:52 JST
更新日: 2026-06-18_02:42 JST
-->

# Strategy Research Runbook

Strategy Research Lab、backtest-first baseline、Bitget demo local smoke、Alpaca smoke の domain runbook です。Strategy Lab は研究、候補生成、評価、paper 昇格判断までの surface であり、live order surface ではありません。

## Strategy Research Lab

Strategy Lab は研究、候補生成、評価、paper 昇格判断までの surface です。live order surface ではありません。

canonical docs:

- `docs/strategy_research_lab/README.md`
- `docs/strategy_research_lab/05_OPERATOR_RUNBOOK.md`
- `docs/strategy_research_lab/08_CURRENT_CAPABILITIES.md`
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
- NDX/QQQ family records can remain in research/backtest artifacts. Without valid Layer 2.6/2.7 paper-observation evidence, paper promotion gates reject them before selected candidate, paper intent, or legacy paper order/fill generation. With valid evidence, they may proceed only to paper observation and still cannot become live orders.

stop conditions:

- Do not treat `data/research/signals.csv` as the Strategy Lab source of truth.
- Do not build `PaperIntentPreview` without `PromotionDecision`.
- Do not treat `PaperIntentPreview` as `OrderIntent` or live order.
- Do not manually force NDX/QQQ family rows into `selected_candidate_ids`, raw `PaperIntentPreview` JSON, or legacy `paper-step` output. Without valid Layer 2.6/2.7 paper-observation evidence, the expected fail-closed reason for `trade_xyz` proxy rows is `VENUE_REQUIRES_RESIDUAL_VALIDATION_AND_OPERATOR_PROMOTION`.
- Do not override `live_conversion_allowed=false`, `wallet_used=false`, or `exchange_write_used=false`.
- Use `profitability_claimed`, `paper_ready_claimed`, `tiny_live_ready_claimed`, and `live_ready_claimed` for forbidden claim names. Legacy `*_claim` names are not the current Strategy Lab claim names.

backtest-first baseline path:

```bash
uv run python scripts/seed_strategy_authoring_baseline_data.py
uv run sis strategy-author-validate --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml
uv run sis strategy-author-run --spec docs/strategy_research_lab/examples/trend_pullback_authoring_spec.yaml --through backtest
uv run sis strategy-backtest-acceptance --metrics-path data/research/strategy_backtest_metrics.json --out data/research/strategy_lifecycle --reports-dir data/reports
```

baseline artifacts:

- `data/research/strategy_authoring_baseline_feature_panel.parquet`
- `data/research/strategy_authoring_baseline_quotes.parquet`
- `data/research/strategy_authoring_baseline_venue_cost_matrix.csv`
- `data/research/strategy_signals.parquet`
- `data/research/strategy_backtest_metrics.json`
- `data/research/strategy_lifecycle/backtest_acceptance_decision.json`
- `data/research/strategy_authoring_run.json`
- `data/reports/strategy_backtest_report.md`
- `data/reports/strategy_backtest_acceptance_report.md`

Bitget demo local smoke:

```bash
uv run sis bitget-demo-smoke --help
uv run sis bitget-demo-smoke
```

Bitget demo env names:

```text
BITGET_DEMO_API_KEY=
BITGET_DEMO_API_SECRET=
BITGET_DEMO_PASSPHRASE=
```

Bitget demo boundaries:

- `bitget-demo-smoke` without credentials exits 2 with `status=blocked`.
- With the three env values present, it exits 0 with `status=configured`.
- `status=configured` only means local credentials are present; it does not prove Bitget network connectivity, account read, order submit, or fill sync.
- Current local smoke writes `data/ops/bitget_demo_smoke_summary.json` and `data/reports/bitget_demo_smoke.md`.
- Current local smoke always keeps `read_only_network_probe=not_executed`, `external_write_enabled=false`, and `exchange_write_used=false`.
- Credentialed read-only network smoke and demo order lifecycle are future explicit opt-in tasks. Do not run external Bitget API calls or write APIs unless the user gives credentials and explicitly authorizes that step.

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
