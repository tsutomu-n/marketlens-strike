# Operator Runbook

この runbook は Strategy Research Lab を paper-only preview まで動かすための手順です。

## 前提

`data/` は git 管理外です。artifact が無い場合は未実装と判断せず、必要な command で再生成します。

Setup:

```bash
uv sync --dev --locked
uv run sis --help
```

## 1. Research data を用意する

```bash
uv run sis ingest-research-data
uv run sis build-event-calendar
uv run sis build-feature-panel
uv run sis check-research-quality
```

期待する主な artifact:

- `data/research/feature_panel.parquet`
- `data/reports/research_quality.md`

`build-signals()` は `data/research/feature_panel.parquet` が無いと止まります。

## 2. Strategy signal を作る

```bash
uv run sis strategy-preview
```

登録済み generator を明示する場合:

```bash
uv run sis strategy-preview --generator-id sp500_trend_rates_vix
```

出力:

- `data/research/strategy_signals.parquet`
- `data/research/strategy_signal_manifest.json`
- `data/research/strategy_signals.jsonl`
- `data/research/signals.csv`
- `data/reports/strategy_signals_preview.md`

読み方:

- `strategy_signals.parquet` が canonical artifact。
- `strategy_signal_manifest.json` は generator metadata と no-signal lineage。
- `signals.csv` は legacy export。
- `strategy_signals_preview.md` は軽い preview report。

## 3. Strategy Lab evaluation を行う

```bash
uv run sis evaluate-strategy-lab
```

出力:

- `data/research/trial_ledger.jsonl`
- `data/reports/strategy_trial_report.md`

止まり方:

- `data/research/strategy_signals.parquet` が無い場合、exit code 2。
- empty `strategy_signals.parquet` で `strategy_signal_manifest.json` が無い場合、exit code 2。
- 1 つの `strategy_signals.parquet` に複数の strategy / symbol identity が混在している場合、exit code 2。

現行の注意:

- 現行 CLI の evaluation は簡易 artifact chain 実装です。
- `TrialRecord` schema と ledger append の契約は存在しますが、汎用 walk-forward engine ではありません。
- 同じ signal artifact の再評価では、同じ `trial_id` を重複追記しません。
- `trial_id`, `trial_group_id`, `paper_candidate_pack.pack_id`, `promotion_id` は signal artifact content 由来の deterministic `run_id` で作られます。

## 4. Paper candidate pack を作る

```bash
uv run sis build-paper-candidate-pack
```

出力:

- `data/research/paper_candidate_pack.json`
- `data/reports/paper_candidate_pack.md`

読み方:

- selected candidate は `selected_candidate_ids`。
- rejected candidate は `rejected_candidate_ids`。
- blocked candidate は candidate-level `status` と `block_reasons` で見る。

任意 ledger:

```bash
uv run sis build-paper-candidate-pack --trial-ledger data/research/trial_ledger.jsonl
```

任意 trial group:

```bash
uv run sis build-paper-candidate-pack --trial-group-id trial-group-<run_id>
```

現行 CLI は default で ledger 内の latest trial group だけを pack 化します。selected candidate は最新 `ts_signal` の 1 signal から作ります。

## 5. Promotion decision を作る

通常はまず `hold` で止める:

```bash
uv run sis promotion-decision --decision hold
```

出力:

- `data/research/promotion_decision.json`
- `data/reports/promotion_decision.md`

`promote` する場合:

```bash
uv run sis promotion-decision --decision promote
```

注意:

- required evidence が揃っていない `promote` は validation で止まる。
- `promote` は paper observation への許可であり、live-ready ではない。
- `source_pack_id` は読み込んだ `PaperCandidatePack.pack_id` になります。

## 6. Paper intent preview を作る

```bash
uv run sis build-paper-intent-preview
```

出力:

- `data/bot/paper_intent_preview.json`
- `data/reports/paper_intent_preview.md`

止まり方:

- `data/research/promotion_decision.json` が無い場合、exit code 2。
- `data/research/paper_candidate_pack.json` が無い場合、exit code 2。
- `promotion_decision.source_pack_id` と `paper_candidate_pack.pack_id` が一致しない場合、exit code 2。

読み方:

- `promotion.decision == "promote"` の時だけ selected candidate から intent が生成される。
- `hold` / `reject` の場合、intent list は空になり得る。
- intent は `paper_only=true` で、live conversion 禁止。

## 7. Paper runner で再検証する

```bash
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

必要 artifact:

- `data/normalized/quotes.parquet`

出力:

- `data/paper/orders.parquet`
- `data/paper/fills.parquet`
- `data/paper/positions.parquet`
- `data/paper/paper_observation_ledger.jsonl`

block reason:

- `INTENT_EXPIRED`
- `LATEST_QUOTE_MISSING`
- `PAPER_BROKER_REVALIDATION_BLOCKED`

## 最短再生成

```bash
uv run sis ingest-research-data
uv run sis build-feature-panel
uv run sis strategy-preview
uv run sis evaluate-strategy-lab
uv run sis build-paper-candidate-pack
uv run sis promotion-decision --decision hold
uv run sis build-paper-intent-preview
```

paper まで進めるには quote artifact も必要です。

```bash
uv run sis collect-trade-xyz-quotes --write-summary --write-report
uv run sis paper-from-intents --intents-path data/bot/paper_intent_preview.json
```

## Operator stop conditions

- `strategy_signals.parquet` が無いのに `evaluate-strategy-lab` を通そうとしない。
- no-signal artifact の manifest 不在を迂回しない。
- 複数 generator / strategy / symbol の signal を 1 つの `strategy_signals.parquet` に混ぜて評価しない。
- 古い trial group と現在の signal artifact run_id を混ぜて pack 化しない。
- `promotion_decision.json` が無いのに `build-paper-intent-preview` を通そうとしない。
- `paper_candidate_pack.json` が無いのに `promotion-decision` や `build-paper-intent-preview` を通そうとしない。
- pack と promotion decision の `source_pack_id` 不一致を迂回しない。
- `promotion-decision --decision promote` が validation で止まった時に evidence guard を迂回しない。
- `paper_intent_preview.json` を live adapter に渡さない。
- `wallet_used`, `exchange_write_used` を true にする変更をしない。
- `signals.csv` だけを見て Strategy Lab 評価済みと判断しない。

## Review command

docs と schema surface の最低確認:

```bash
rg -n "PaperIntentPreview|TradeCandidate|strategy_signals.parquet|live_conversion_allowed|wallet_used|exchange_write_used" docs/strategy_research_lab docs/STRATEGY_RESEARCH_LAB_DOC_AUDIT_AND_SPEC_2026-05-30.md
uv run pytest tests/test_strategy_lab_*.py tests/test_strategy_run_profile.py tests/test_paper_from_intents.py
```
