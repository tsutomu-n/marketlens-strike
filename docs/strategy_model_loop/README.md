<!--
作成日: 2026-06-19_01:25 JST
更新日: 2026-06-19_01:25 JST
-->

# Strategy Model / Optimizer Loop

## 結論

`strategy-model-run-record` は、ML / DL / GA / optimizer の結果を採用する command ではありません。

外部または手元で実行した trial を、成功・失敗・pruned・running を含めて `strategy_optimizer_trial_ledger.v1` に記録し、training data hash、label definition、split、seed、search space、best trial、holdout result、limitations を `strategy_model_run.v1` に固定する first slice です。

## Command

```bash
uv run sis strategy-model-run-record \
  --strategy-id <strategy-id> \
  --training-data data/features/training.csv \
  --label-definition "next_10_bar_return" \
  --split "train=2024,validation=2025,holdout=2026" \
  --search-space-json '{"lookback":[20,80]}' \
  --trial-json '{"trial_id":"trial-001","status":"complete","parameters":{"lookback":20},"objective_value":0.12,"metrics":{"validation_return":0.12}}' \
  --trial-json '{"trial_id":"trial-002","status":"failed","parameters":{"lookback":80},"metrics":{},"failure_reason":"insufficient_samples"}' \
  --best-trial-id trial-001 \
  --holdout-result-json '{"return":0.03}' \
  --limitation "small holdout window" \
  --out data/strategy_model_loop/<strategy-id>
```

## Artifacts

```text
data/strategy_model_loop/<strategy-id>/
  strategy_model_run.json
  strategy_model_run.md
  strategy_optimizer_trial_ledger.json
  strategy_optimizer_trial_ledger.md
```

`strategy_optimizer_trial_ledger.v1`:

- all trials
- failed / pruned / running trials
- best trial id
- holdout result
- `success_only_reporting=false`

`strategy_model_run.v1`:

- training data path / hash
- label definition
- split
- seed
- search space hash
- optimizer trial ledger path / hash
- limitations
- output route

## 境界

- optimizer は実行しない。実行済み結果を記録する。
- 成功 trial だけの reporting を許さない。
- model / optimizer output は Idea Intake または Revision Request に戻すだけ。
- Strategy Authoring YAML を直接編集しない。
- paper order、live order、wallet、signing、exchange write は使わない。
- `optuna` 依存はこの first slice では追加しない。generic ledger contract を先に固定する。

## Verification

```bash
uv run pytest tests/strategy_model_loop -q
uv run sis strategy-model-run-record --help
uv run python scripts/check_current_docs.py
```
