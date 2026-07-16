<!--
作成日: 2026-07-16_16:10 JST
更新日: 2026-07-16_21:00 JST
-->

# Reference

外部調査と設計根拠です。実装判断では`../00_overview/core_v1_engineering_execution_plan.md`を優先してください。

## 一次情報と採用箇所

| 対象 | 一次情報 | Core v1で採用する範囲 |
|---|---|---|
| JSON Schema | https://json-schema.org/draft/2020-12 | 個別Seed、Seed Set、Payload、Manifestを`$ref`で分割 |
| Pydantic Union | https://docs.pydantic.dev/latest/concepts/unions/ | レーン固有Model内の型安全なUnion。Common Envelopeは外部Payload参照 |
| JSON Canonicalization | https://www.rfc-editor.org/rfc/rfc8785 | Canonicalizationの必要性。完全準拠を偽称せず、Domain規則をVersion管理 |
| Polars as-of join | https://docs.pola.rs/api/python/stable/reference/dataframe/api/polars.DataFrame.join_asof.html | FundingのBackward As-of Join、Sortedness、Tolerance |
| Polars Lazy API | https://docs.pola.rs/user-guide/lazy/using/ | 大量ParquetのProjection/Predicate Pushdown |
| Python atomic replace | https://docs.python.org/3/library/os.html#os.replace | 同一Filesystem内でのArtifact公開。Temp、flush、fsyncを併用 |
| DuckDB concurrency | https://duckdb.org/docs/stable/connect/concurrency | Shared multi-process writerを避け、Worker FragmentとSingle Reducerを採用 |
| Python extras | https://packaging.python.org/en/latest/specifications/dependency-specifiers/#extras | XGBoost、LightGBMをOptional Extraへ分離 |
| XGBoost model dump | https://xgboost.readthedocs.io/en/stable/python/python_api.html | Tree DumpをRule抽出用に使用。Load可能Modelを別保存 |
| LightGBM parameters/API | https://lightgbm.readthedocs.io/en/latest/Parameters.html | CPU Determinism設定、Engine Version、Parser Versionを記録 |
| Time-series split | https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html | 時系列順とGapの考え方。実装は`label_end_at`を使うCustom Purge |
| LLM prompt injection | https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html | 外部資料を非信頼データとして分離し、出力検証とHuman-in-the-loopを維持 |
| GitHub Actions | https://docs.github.com/actions/writing-workflows/workflow-syntax-for-github-actions | Core/ML Job分離、Timeout、Concurrency |
| MAP-Elites | https://arxiv.org/abs/1504.04909 | Descriptorごとの多様性保持という考え方のみ。Full Algorithmは対象外 |

## 使用上の注意

- URLの存在は、その設計判断がMarketLens Strikeに最適であることを自動的に証明しません。
- 実装時は、現在の依存Version、Python 3.13対応、Repoの既存契約を再確認してください。
- XGBoost、LightGBMの正確なVersionは、Wheel、Mini Train、Save/Load、Tree Dump Probe後に固定します。
- このフォルダーは参考情報です。実装正本とタスク状態は`00_overview`を確認してください。
