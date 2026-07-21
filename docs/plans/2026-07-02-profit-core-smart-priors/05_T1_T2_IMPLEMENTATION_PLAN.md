<!--
作成日: 2026-07-02_19:54 JST
更新日: 2026-07-02_20:08 JST
-->

# T1-T2 Implementation Plan

## 結論

このチェックポイントでは、`edge_candidate_factory` のpackage skeletonとartifact契約だけを追加する。候補生成、CLI、writer、runtime artifact、external API、paper/live/actual cash連携は実装しない。

## チェックポイントID

CP1 / PR #17 T1-T2

## 目的

Smart Edge Candidate Factoryの後続実装が、未接続の自由形式JSONではなく、Pydantic modelとDraft 2020-12 JSON Schemaに従って進められる状態を作る。

## 現状

- `src/sis/strategy_idea_candidates/models.py` には既存の候補系モデルがある。
- `schemas/strategy_idea_candidate_set.v1.schema.json` には既存候補artifactのschemaがある。
- `edge_candidate_factory` packageはまだ存在しない。
- PR #17の計画ではT2で7つの新artifact契約を先に固定する。

## 制約

- public CLI commandは増やさない。
- writerや`data/`出力は作らない。
- 依存関係を追加しない。
- network、credentials、wallet、signing、live order、production exchange write、actual cash判断を使わない。
- safety boundaryは既存repo語彙を省略しない。
- Virtual artifactのdemo/testnet例外は契約として許容するが、既定fixtureは全安全fieldをfalseにする。

## 対象ファイル

新規:

- `src/sis/edge_candidate_factory/__init__.py`
- `src/sis/edge_candidate_factory/_contracts.py`
- `src/sis/edge_candidate_factory/models.py`
- `tests/edge_candidate_factory/__init__.py`
- `tests/edge_candidate_factory/fixtures.py`
- `tests/edge_candidate_factory/test_models.py`
- `tests/edge_candidate_factory/test_schema_validation.py`
- `schemas/smart_candidate_prior_report.v1.schema.json`
- `schemas/edge_candidate_search_ledger.v1.schema.json`
- `schemas/trial_multiplicity_account.v1.schema.json`
- `schemas/backtest_kill_gate.v1.schema.json`
- `schemas/virtual_execution_gate.v1.schema.json`
- `schemas/edge_candidate_risk_actual_cash_handoff.v1.schema.json`
- `schemas/llm_adversarial_evidence_review.v1.schema.json`

変更:

- なし。必要が出ても、このチェックポイントでは既存CLIや既存domain moduleを変更しない。

## 実装方針

1. 既存候補系モデルと同じく、Pydantic `BaseModel`、`ConfigDict(extra="forbid")`、`Literal[False]` safety boundaryを使う。
2. ID、sha256、pathの基本検証は既存の `REVIEW_ID_PATTERN`、`SHA256_PATTERN`、`normalize_repo_relative_posix_path` を再利用する。
3. Datetimeは既存のUTC `Z` serializerに寄せる。
4. SchemaはDraft 2020-12としてvalidにし、fixture payloadとPydantic dumpの両方を通す。
5. `models.py` は800行以下に保つため、共通enum/helper/boundary/refは `_contracts.py` に分ける。
6. 7つのartifactは同一package内に置くが、生成・ファイル書き込み・CLI登録は作らない。

## 実装手順

1. RED: package import、model validation、schema validationのfocused testsを追加する。
2. GREEN: `src/sis/edge_candidate_factory/__init__.py`、`_contracts.py`、`models.py` を追加する。
3. GREEN: 7 schemaを追加し、fixturesのpayloadとmodel dumpに合わせる。
4. REFACTOR: 重複したschema defsとmodel helperを必要最小限だけ整理する。
5. VERIFY: focused pytest、import、ruff、current-docs、diff whitespaceを確認する。

## テスト方針

```bash
uv run pytest tests/edge_candidate_factory/test_models.py -q
uv run pytest tests/edge_candidate_factory/test_schema_validation.py -q
uv run python -c "import sis.edge_candidate_factory"
uv run ruff check src/sis/edge_candidate_factory tests/edge_candidate_factory
uv run python scripts/check_current_docs.py
git diff --check
```

## 完了条件

- `import sis.edge_candidate_factory` が通る。
- Pydantic fixture dumpが7つのschemaを通る。
- 各schemaがDraft 2020-12としてvalid。
- `extra="forbid"` により不要fieldが落ちる。
- unsafe boundary true flagがmodelとschemaの両方で拒否される。
- public CLI commandが増えていない。

## 失敗条件

- CLIやwriterを先に追加し、未接続surfaceを増やす。
- schemaとPydantic modelが同じpayloadを受け付けない。
- `exchange_write_used` や `permits_live_order` などの安全fieldにtrueを許す。
- Virtual artifactをactual cash evidenceとして扱える形にする。

## 影響範囲

新規package、schema、testsのみ。既存command、runtime、data artifact、CI設定には影響させない。

## ロールバック方針

このチェックポイントで追加した新規package、tests、schemas、plan docを削除すれば戻せる。既存ファイル変更を予定しないため、移行不要。

## 代替案

- 代替案A: T1だけを先に入れる。importだけでは後続タスクの契約が固定されず、実装価値が低い。
- 代替案B: T2をschemaだけにする。Pydantic writer予定のrepoではmodel/schema driftを防げない。
- 採用案: T1とT2を同一チェックポイントにし、contract-onlyで閉じる。

## 未解決事項

なし。このチェックポイントの範囲ではユーザー判断は不要。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-smart-priors-20260702-1952`

## 移行手順

なし。既存artifactの読み替えやDB/schema migrationは行わない。

## 批判レビュー1

- 7 schemaを同時追加するため、詳細なbusiness logicを入れると過剰になる。今回はartifact必須field、boundary、status、最低限の整合だけに限定する。
- `edge_candidate_search_ledger.v1` はJSONL運用予定だが、schemaは1行payload用にする。ファイル読み書きの形式検証はT4以降へ送る。
- `virtual_execution_gate.v1` はdemo/testnet exchange write例外があるが、T2では実行環境のモデル表現だけに留め、実際のexchange write経路は作らない。

## 批判レビュー2

- Backtest Kill Gate metricsは既存artifact抽出がT6の本体なので、T2 modelで推定ロジックを持たせない。`metrics` はnullable値を持てる契約にする。
- Risk / Actual Cash handoffはactual cash rowsが無い場合のblocked表現を固定するだけにする。既存`crypto-perp-actual-cash-report-gate`へ接続するadapterはT9へ送る。
- LLM reviewはapprovalではなくadversarial evidenceだけを表す。`llm_approval_ignored=true` と override禁止fieldを必須化する。
