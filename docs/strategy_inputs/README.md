<!--
作成日: 2026-06-18_23:00 JST
更新日: 2026-06-22_17:16 JST
-->

# Strategy Inputs

## 結論

Strategy Input Contract / Idea Intake は、戦略を作る前に入力データと戦略の種を local artifact として検査する first gate です。

これは paper / live permission ではありません。`READY_FOR_AUTHORING_DRAFT` は Strategy Authoring draft に進める最低条件であり、利益、paper 実行、live 実行を保証しません。

## できること

- `strategy_input_contract.v1` で、入力データの path、hash、schema version、generated_at、available_at、revision policy、survivorship policy、execution reality、任意の `validation_expectations` を記録する。
- `strategy-input-contract-validate` で、source missing、sha256 mismatch、boundary violation、required column missing、available_at column missing、future timestamp violation を検査する。
- `strategy_idea.v1` で、hypothesis、baseline、invalidation、risk、required input contract、execution assumptions を記録する。
- `strategy-intake-validate` で、戦略の種を `READY_FOR_AUTHORING_DRAFT`、`NEEDS_SPEC`、`NEEDS_DATA_CHECK`、`NEEDS_RISK_SPEC`、`REJECT` に分ける。
- `strategy-review-build --input-contract --strategy-idea` で、input contract と strategy idea を Strategy Review packet の optional source artifact として読む。

## Command

```bash
uv run sis strategy-input-contract-validate \
  --contract configs/strategy_inputs/<contract>.yaml \
  --out data/strategy_inputs/<contract-id> \
  --strict

uv run sis strategy-intake-validate \
  --idea configs/strategy_ideas/<idea>.yaml \
  --input-contract-validation data/strategy_inputs/<contract-id>/strategy_input_contract_validation.json \
  --out data/strategy_ideas/<idea-id> \
  --strict
```

## Artifact

- `strategy_input_contract_validation.json`
- `strategy_input_contract_validation.md`
- `strategy_intake_decision.json`
- `strategy_intake_decision.md`

`data/` 配下の artifact は runtime / generated state です。fresh checkout では再生成してください。

`validation_expectations` を source に付けると、CSV / JSONL / NDJSON / Parquet の column と timestamp を最小検査できます。

```yaml
validation_expectations:
  required_columns:
    - ts
    - close
    - spread_bps
  timestamp_column: ts
  max_allowed_timestamp: "2026-06-18T12:00:00Z"
  available_at_column: available_at
  available_at_column_required: true
```

検査結果は source result に次を出します。

- `required_columns_present`
- `missing_columns`
- `timestamp_check_passed`
- `max_observed_timestamp`
- `available_at_column_present`

代表的な error code:

- `MISSING_REQUIRED_COLUMN`
- `AVAILABLE_AT_COLUMN_MISSING`
- `FUTURE_DATA_VIOLATION`

## 境界

- wallet、signing、exchange write、live order は使わない。
- `READY_FOR_AUTHORING_DRAFT` は paper observation 許可ではない。
- input contract は指定された source artifact を read-only で検査する。source artifact を生成・修正しない。
- Strategy Review optional source connection は read-only summary です。input / idea を必須化せず、paper / live permission も出しません。

## 実装履歴

- [../archive/2026-06-22-doc-routing/STRATEGY_INPUT_CONTRACT_AND_IDEA_INTAKE_IMPLEMENTATION_PLAN_2026-06-18.md](../archive/2026-06-22-doc-routing/STRATEGY_INPUT_CONTRACT_AND_IDEA_INTAKE_IMPLEMENTATION_PLAN_2026-06-18.md)
