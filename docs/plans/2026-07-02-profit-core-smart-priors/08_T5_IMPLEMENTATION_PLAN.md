<!--
作成日: 2026-07-02_20:31 JST
更新日: 2026-07-02_20:31 JST
-->

# T5 Implementation Plan

## 結論

T5ではTrial Multiplicity Account生成を`generator.py`から専用moduleへ切り出し、selected-only検出、sealed-test禁止、peek/rerank会計をfocused testsで固定する。統計補正の推定はしない。

## チェックポイントID

CP4 / PR #17 T5

## 目的

大量候補生成を、候補カードの見た目だけで進めず、探索回数・棄却・cap・duplicate・validation peekを明示する会計artifactにする。

## 現状

- CP1で `TrialMultiplicityAccount` model/schemaは追加済み。
- CP3/T4でgenerator内にmultiplicity account構築処理が入っている。
- T5の正本は `01_TASK_CHAIN.md` の `Trial Multiplicity Account v0` であり、source availabilityではない。

## 制約

- return correlation、PBO、White Reality Check、DSRなどは推定しない。
- `effective_trial_count_status=NOT_ESTIMABLE` を正式結果として使う。
- `sealed_test_used_for_selection=true` はfail closed。
- selected-only outputを検出するが、rejectionが本当に存在しない小runまで誤検出しない。
- CLI surfaceは増やさない。

## 対象ファイル

新規:

- `src/sis/edge_candidate_factory/multiplicity.py`
- `tests/edge_candidate_factory/test_multiplicity.py`

変更:

- `src/sis/edge_candidate_factory/generator.py`
- `src/sis/edge_candidate_factory/__init__.py`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`

## 実装方針

1. `build_trial_multiplicity_account()` を追加し、T4 generatorから呼ぶ。
2. 入力は `search_ledger_rows`、`source_refs`、`candidate_run_id`、`created_at`、`expected_trial_count`、`validation_peek_count`、`rerank_count` にする。
3. `expected_trial_count` が実ledger row数より大きい場合はselected-only / omitted-trialとして失敗する。
4. `sealed_test_used_for_selection=True` は即失敗する。
5. `effective_trial_count` は未推定なら `None`、statusは `NOT_ESTIMABLE`。
6. `candidate_count_total` はledger rows数、`candidate_count_shortlisted` はgenerated rows数、`candidate_count_rejected` はrejected rows数にする。

## 実装手順

1. RED: multiplicity単体テストを追加する。
2. GREEN: `multiplicity.py` を追加する。
3. GREEN: `generator.py` のmultiplicity構築を新moduleへ移す。
4. REFACTOR: T4 testsが同じ結果を保つことを確認する。
5. VERIFY: focused tests、ruff/type、docs、full checkを確認する。

## テスト方針

```bash
uv run pytest tests/edge_candidate_factory/test_multiplicity.py -q
uv run pytest tests/edge_candidate_factory -q
uv run ruff check src/sis/edge_candidate_factory tests/edge_candidate_factory
uv run ruff format --check src/sis/edge_candidate_factory tests/edge_candidate_factory
uv run pyrefly check src/sis/edge_candidate_factory
uv run ty check src/sis/edge_candidate_factory --python-version 3.13 --output-format concise
uv run python scripts/check_current_docs.py
git diff --check
./scripts/check
```

## 完了条件

- selected-only / omitted-trialを検出して失敗する。
- `sealed_test_used_for_selection=true` を失敗させる。
- `validation_peek_count` と `rerank_count` がartifactに保存される。
- `effective_trial_count` 未計算時に `NOT_ESTIMABLE` と `None` が保存される。
- T4 CLI出力と既存edge_candidate testsが維持される。

## 失敗条件

- 統計補正を推定で埋める。
- 棄却rowが存在するはずなのにledger rowsから消える。
- source availabilityやbacktest gateへ踏み込む。
- CLI commandを増やす。

## 影響範囲

`edge_candidate_factory` package内のmultiplicity構築ロジックとテストのみ。public CLI数、schema、既存artifact名は変えない。

## ロールバック方針

`multiplicity.py`、`test_multiplicity.py`、`generator.py`の呼び出し変更、計画docを戻す。

## 代替案

- 代替案A: T4 generator内に置いたままにする。T5のselected-only検出や会計テストが弱い。
- 代替案B: PBO/DSR推定を入れる。必要入力が無いのでご都合主義になる。
- 採用案: 会計生成だけをmodule化し、未推定を明示する。

## 未解決事項

なし。このチェックポイントの範囲ではユーザー判断は不要。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-smart-priors-20260702-1952`

## 移行手順

なし。

## 批判レビュー1

- `candidate_count_shortlisted` というfield名はT4ではgenerated rowを意味しており、厳密にはshortlistではない。schema名に合わせて保存するが、known gapで「no promotion implied」を残す。
- selected-only検出は「rejectionが無いこと」だけで判定すると小runを誤検出する。`expected_trial_count` とledger row数の差分で検出する。
- duplicate/cap rejectionはsearch ledger rowなので、multiplicity countに含める。

## 批判レビュー2

- `effective_trial_count` をcandidate countで代用すると、推定値と誤読される。v0では `None` と `NOT_ESTIMABLE` を維持し、known gapに保守的上限としてcandidate countを記録する。
- sealed test usageは後からknown gapで済ませず、artifact生成前にfail closedにする。
- source availabilityはT6以降のBacktest Kill Gate input文脈で扱い、T5には混ぜない。
