<!--
作成日: 2026-07-02_20:13 JST
更新日: 2026-07-02_20:13 JST
-->

# T3 Implementation Plan

## 結論

T3ではSmart Prior taxonomyと初期family定義だけを追加する。source ingestion、candidate generation run、JSON writer、CLI registration、backtest接続は作らない。

## チェックポイントID

CP2 / PR #17 T3

## 目的

候補生成を単なるfeature listから始めず、flow cause、mechanism、required source、execution precheck、kill condition、information gainを持つ静的default catalogとして固定する。

## 現状

- CP1で `SmartCandidateCard`、`CandidateMechanismCard`、`CandidateSourceRequirement`、`CandidateExecutionPrecheck`、`CandidatePriorScore` のmodel契約は追加済み。
- 既存 `strategy_idea_candidates/generator.py` には候補familyがあるが、Smart Priorのcause-first taxonomyではない。
- PR #17 T3は10個の初期familyと9個のcause priorを要求している。

## 制約

- CLI、writer、`data/` runtime出力は作らない。
- 外部API、credential、wallet、signing、live order、exchange writeは使わない。
- family定義はPydantic artifactへ変換できる形にするが、run_idやsource artifact hashを必要とするruntime modelは作らない。
- `volatility_compression_breakout` をstandalone structural causeと誤読させない。
- `spread_widening_no_trade` をtrade actionとして出さない。

## 対象ファイル

新規:

- `src/sis/edge_candidate_factory/smart_priors.py`
- `tests/edge_candidate_factory/test_smart_priors.py`

変更:

- `src/sis/edge_candidate_factory/__init__.py`
- `.ai-work/state.md`
- `.ai-work/checkpoints.md`

## 実装方針

1. `dataclass(frozen=True)` の `SmartPriorDefinition` と `SmartPriorFamily` を作る。
2. `DEFAULT_SMART_PRIOR_DEFINITIONS` と `DEFAULT_SMART_PRIOR_FAMILIES` をtupleで固定する。
3. public helperは `default_smart_prior_families()`、`default_smart_prior_family_ids()`、`smart_prior_family_by_id()`、`build_default_candidate_card()` に絞る。
4. `build_default_candidate_card()` はCP1の `SmartCandidateCard` を返すが、runtime source hashやreportは作らない。
5. `volatility_compression_breakout` には `structural_cause_role="regime_state"` を持たせる。
6. `spread_widening_no_trade` には `family_role="filter_no_trade"` と `default_action_set=("no_trade",)` を持たせる。

## 実装手順

1. RED: T3 acceptanceをテスト化する。
2. GREEN: `smart_priors.py` にtaxonomy、family、helperを追加する。
3. REFACTOR: 重複したsource/precheck/default scoreをprivate helperへ寄せる。
4. VERIFY: T3 tests、CP1 tests、import、ruff、type、docs、diff whitespaceを確認する。

## テスト方針

```bash
uv run pytest tests/edge_candidate_factory/test_smart_priors.py -q
uv run pytest tests/edge_candidate_factory/test_models.py tests/edge_candidate_factory/test_schema_validation.py -q
uv run python -c "import sis.edge_candidate_factory"
uv run ruff check src/sis/edge_candidate_factory tests/edge_candidate_factory
uv run ruff format --check src/sis/edge_candidate_factory tests/edge_candidate_factory
uv run pyrefly check src/sis/edge_candidate_factory
uv run ty check src/sis/edge_candidate_factory --python-version 3.13 --output-format concise
uv run python scripts/check_current_docs.py
git diff --check
```

## 完了条件

- 10個の初期family IDが全て定義される。
- 9個のcause priorがallowlistとして全て定義される。
- 各familyがcause prior、required source、kill conditionを1つ以上持つ。
- 各familyから `SmartCandidateCard` を生成できる。
- `volatility_compression_breakout` はregime/statistical stateとして検査される。
- `spread_widening_no_trade` はno-trade/filterとして検査される。

## 失敗条件

- T3でCLIやwriterを作る。
- family定義に自由文字列のobservableを混ぜ、CP1の `Observable` allowlistを迂回する。
- no-trade familyがtrade actionを持つ。
- volatility compressionをcause priorそのものとして扱う。

## 影響範囲

`edge_candidate_factory` package内の静的catalogとテストのみ。既存command、schema、runtime artifact、dataには影響させない。

## ロールバック方針

T3で追加した `smart_priors.py`、`test_smart_priors.py`、`__init__.py` export、計画docを戻せばよい。既存artifact migrationは不要。

## 代替案

- 代替案A: YAML config化する。v0では設定読み込み・schema・path検証が増え、T3には重い。
- 代替案B: 既存 `strategy_idea_candidates/generator.py` に混ぜる。責務分離を崩し、PR #17のpackage分離と衝突する。
- 採用案: Pythonの静的catalogで始め、T4以降のgeneratorから参照する。

## 未解決事項

なし。このチェックポイントの範囲ではユーザー判断は不要。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/profit-core-smart-priors-20260702-1952`

## 移行手順

なし。

## 批判レビュー1

- familyを増やしすぎると検証不能な夢リストになる。T3はPR #17で列挙済みの10 familyだけに固定する。
- source requirementは現物のavailability検査ではない。`status=NOT_ESTIMABLE` ではなくdefault catalogとしての要求を保持し、runtime availability判定はT4以降へ送る。
- default candidate cardはprofit proofではない。`proof_status=not_alpha_or_profit_proof` と安全boundaryを維持する。

## 批判レビュー2

- `volatility_compression_breakout` は単独causeではなくregime/statistical stateなので、cause priorは `EXECUTION_FRICTION` などへ逃がさず、`CROWDED_POSITIONING` や `DATA_OBSERVABILITY` と合わせて補助状態として扱う。
- `spread_widening_no_trade` はaction候補ではなく除外filter。`action_set` は `no_trade` のみ、family roleは `filter_no_trade` とする。
- `build_default_candidate_card()` は便利だが、run artifactを生成するとT4へ踏み込む。T3では1 familyから1 deterministic cardを返すだけにする。
