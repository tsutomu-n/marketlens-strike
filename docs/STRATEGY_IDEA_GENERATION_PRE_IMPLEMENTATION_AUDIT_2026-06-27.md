<!--
作成日: 2026-06-27_10:36 JST
更新日: 2026-06-27_10:36 JST
-->

# Strategy Idea Generation Pre-Implementation Audit 2026-06-27

## 結論

実装へ進めてよい。ただし、進めてよいのは P0 の artifact / schema / docs / fixture test までです。データ mining、ML、LLM によるアイデア生成、依存関係追加にはまだ進まない。

現実的な最初の目的は、「良い戦略を作る」ではなく、「入力データから作られた未検証候補を、探索履歴・棄却候補・入力 hash・時刻境界つきで保存し、既存 gate に渡す前に誤読を止める」ことです。

この事前監査で修正する判断は次です。

1. `StrategyIdeaCandidate` / `IdeaCandidateSet` は新しい pre-intake artifact。既存の `TradeCandidate`、`PaperCandidatePack`、`strategy_idea.v1` と混ぜない。
2. P0 / P1 は依存追加なし。`pyproject.toml` と `uv.lock` は変更しない。
3. `scikit-learn TimeSeriesSplit` は便利だが、financial label overlap の purged / embargoed split を証明しない。P3 以降の補助候補に留める。
4. `mlfinlab` は現 `uv pip install --dry-run mlfinlab` で解決不能。`mlfinpy` と `pandas-ta` は NumPy downgrade を伴う。初期採用しない理由を明記する。
5. 既存 `strategy_optimizer_trial_ledger.v1` の `search_space` / `trials` / `holdout_result` / false boundary を参考にし、候補生成の探索証跡を別形式で重複発明しない。

## 調査対象

コードを正として確認したもの:

- CLI: `uv run sis --help`
- schema: `schemas/strategy_idea.v1.schema.json`
- schema: `schemas/strategy_input_contract.v1.schema.json`
- schema: `schemas/strategy_input_contract_validation.v1.schema.json`
- schema: `schemas/strategy_intake_decision.v1.schema.json`
- schema: `schemas/strategy_optimizer_trial_ledger.v1.schema.json`
- schema: `schemas/paper_candidate_pack.v1.schema.json`
- code: `src/sis/commands/strategy_inputs.py`
- code: `src/sis/strategy_inputs/validation.py`
- code: `src/sis/research/strategy_lab/candidates.py`
- docs: `docs/strategy_inputs/README.md`
- docs: `docs/strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md`
- docs: `docs/strategy_research_lab/03_SIGNAL_TO_TRADE_CANDIDATE_SPEC.md`
- docs: `docs/strategy_research_lab/06_GENERATOR_AND_EXPERIMENT_SPEC.md`
- docs: `docs/strategy_research_lab/07_VALIDATION_STOP_CONDITIONS_AND_TEST_MATRIX.md`
- dependency resolver: `uv pip install --dry-run ...`

外部 source として確認したもの:

- scikit-learn `TimeSeriesSplit`
- PyPI `mlfinpy`
- PyPI `pandas-ta`
- PyPI `ta`

## 現在の repo 事実

現状は「戦略アイデア生成器」ではなく「入力済みアイデアと入力契約の検査」です。

- `uv run sis --help` には `strategy-input-contract-validate` と `strategy-intake-validate` がある。
- `strategy-idea-candidates-build` のような public CLI はない。
- `strategy_idea.v1` は `hypothesis`、`mechanism`、`baseline`、`invalidation`、`risk`、`execution_assumptions`、`authoring_intent`、`boundary` を必須にする。
- `strategy_idea.v1` は `authoring_intent.auto_generate_spec=false` を要求する。自動生成した spec をそのまま正規 authoring spec にしない設計です。
- `strategy_input_contract.v1` は source path、hash、generated_at、available_at、revision policy、survivorship policy、execution reality、required columns、timestamp / available_at column を扱う。
- `strategy_input_contract_validation.v1` は hash、column、timestamp、available_at column の検査結果を保存する。
- `strategy_intake_decision.v1` の最上位判定は `REJECT`、`NEEDS_SPEC`、`NEEDS_DATA_CHECK`、`NEEDS_RISK_SPEC`、`READY_FOR_AUTHORING_DRAFT` まで。paper / live permission はない。
- `TradeCandidate` は Strategy Lab の signal / trial 後に paper candidate pack へ渡す売買候補で、pre-intake の戦略アイデア候補ではない。
- `PaperCandidatePack` はさらに後段の selected / rejected paper candidate pack で、利益証明・paper readiness・live readiness ではない。
- `strategy_optimizer_trial_ledger.v1` は `search_space`、`trials`、`holdout_result`、`summary` を持ち、`paper_execution_allowed=false`、`live_allowed=false`、`auto_applied=false`、`direct_spec_edit_allowed=false` を要求する。
- Strategy Lab docs は、現行 `--split-method` / `--era-unit` が full walk-forward backtester ではなく、metrics 記録に留まると明記している。

## 実装前に修正した抜け

### 1. 用語衝突を避ける

`candidate` という語は既に `TradeCandidate` と `PaperCandidatePack` で使われている。新機能で単に `Candidate` と呼ぶと、paper candidate や注文候補と誤読される。

実装名は次のように限定する。

- module: `src/sis/strategy_idea_candidates/`
- schema: `strategy_idea_candidate_set.v1`
- object: `StrategyIdeaCandidate`
- object: `StrategyIdeaCandidateSet`
- output dir: `data/strategy_idea_candidates/<run-id>/`

使わない名前:

- `Candidate`
- `TradeCandidate`
- `PaperCandidate`
- `SignalCandidate`
- `PaperCandidatePack`

### 2. `strategy_idea.v1` を最初の出力にしない

`strategy_idea.v1` は人間が検査可能な仮説に近い artifact であり、探索履歴の全量を詰める箱ではない。候補生成の初期出力を直接 `strategy_idea.v1` にすると、探索回数、棄却候補、validation peek、source hash が落ちやすい。

P0 / P1 の出力は次に限定する。

- `strategy_idea_candidate_set.json`
- `strategy_idea_candidate_set.md`
- `candidate_search_ledger.jsonl`
- `candidate_metrics.csv`
- `candidate_rejections.csv`

`exported_strategy_ideas/` は shortlist / export task まで作らない。

### 3. label と時刻境界を必須にする

候補生成で最も壊れやすいのは future leakage です。`source_artifact_sha256` だけでは足りない。

候補 schema には最低限、次を必須にする。

- `target_definition`
- `prediction_horizon`
- `label_window_start`
- `label_window_end`
- `feature_observation_window_start`
- `feature_observation_window_end`
- `feature_available_at_policy`
- `max_source_timestamp`
- `max_feature_available_at`
- `source_artifact_sha256`
- `input_contract_validation_refs`
- `purge_policy`
- `embargo_policy`
- `uses_sealed_test_for_selection=false`

### 4. 探索全量を保存する

「選りすぐりだけを残す」設計は、偶然よく見えたものを発見と誤認する。候補生成器は defense gate に渡す前に、自分の探索汚染を明示する必要がある。

P0 schema で必要な summary:

- `family_count`
- `candidate_count_total`
- `candidate_count_shortlisted`
- `candidate_count_rejected`
- `trial_count_total`
- `parameter_grid_hash`
- `selection_policy`
- `validation_peek_count`
- `rerank_count`
- `success_only_reporting=false`
- `sealed_test_used_for_selection=false`

### 5. 既存 optimizer ledger を再利用候補に入れる

既存 `strategy_optimizer_trial_ledger.v1` は search ledger の考え方を持っている。候補生成で完全に別の ledger を作ると、同じ概念が二重化する。

P0 では次を検討対象にする。

- `search_space`
- `trials`
- `holdout_result`
- `summary`
- `paper_execution_allowed=false`
- `live_allowed=false`
- `auto_applied=false`
- `direct_spec_edit_allowed=false`

ただし、そのまま使い回すとは限らない。`strategy_optimizer_trial_ledger.v1` は既存 strategy optimizer 向けであり、pre-intake の idea candidate には `source_artifacts`、`label_window`、`feature_available_at_policy`、`rejection_inventory` が追加で必要です。

## 依存関係の修正判断

### P0 / P1

依存追加なし。

理由:

- schema validation、artifact write、CSV / JSONL 出力、source hash、deterministic template generation は現行依存で足りる。
- 依存を先に増やすと、実装の本質が「証跡保存」から「探索拡張」にずれる。

### `scikit-learn`

P3 以降の optional 候補。P0 / P1 では入れない。

scikit-learn 公式の `TimeSeriesSplit` は time-ordered data の train/test index を作り、`gap` で train 末尾から test 前の sample を除外できる。一方で、公式説明は equally spaced sample と単純な gap を前提にしており、金融 label の overlapping horizon、event end time、purged K-Fold、embargo の完全実装を保証するものではない。

したがって、`TimeSeriesSplit` を採用する場合でも、`label_window`、`prediction_horizon`、`purge_policy`、`embargo_policy` は repo 側 schema で別に持つ。

### `mlfinlab` / `mlfinpy`

初期採用しない。

追加確認:

- `uv pip install --dry-run mlfinlab` は `No solution found`。現 resolver では package を解決できない。
- PyPI の `mlfinpy` は 0.1.2、Alpha classifier、Python `<4.0, >=3.11`。説明上は financial ML toolbox だが、現 resolver では `numba==0.60.0` と `numpy==1.26.4` へ downgrade を伴う。

この repo の Python 3.13 / locked workspace では、large finance ML toolbox を最初に入れるより、必要な policy と artifact を小さく実装する方が安全です。

### `pandas-ta` / `ta`

初期採用しない。

追加確認:

- `pandas-ta` は PyPI 上では 0.4.71b0、Python `>=3.12`、150 超の indicator / 60 candlestick pattern を掲げる。現 resolver では `numpy==2.4.6` から `numpy==2.2.6` への downgrade を伴う。
- `ta` は 0.11.0、2023-11-02 release、classifiers は Python 3.6 / 3.7、Pandas built の technical analysis library。単体 dry-run は小さいが、初期候補生成では indicator explosion を招きやすい。

初期 generator は broad indicator catalog ではなく、少数の明示 family と parameter grid を保存する。

### `vectorbt`

初期採用しない。

現 resolver では `vectorbt==1.0.0` に加えて、`ipython`、`ipywidgets`、`plotly`、`matplotlib`、`numba`、`scikit-learn`、`scipy` など 45 package 追加になる。既存 optional extra としてはあるが、戦略アイデア候補生成 P0 / P1 の目的には過剰です。

## P0 実装で必須にする artifact contract

`strategy_idea_candidate_set.v1` の top-level 必須候補:

- `schema_version`
- `candidate_set_id`
- `generated_at`
- `producer`
- `generator_version`
- `input_contract_validation_refs`
- `source_artifacts`
- `candidate_inventory`
- `search_ledger_summary`
- `selection_policy`
- `split_policy`
- `leakage_policy`
- `dependency_versions`
- `boundary`

`StrategyIdeaCandidate` の必須候補:

- `idea_candidate_id`
- `status`
- `family`
- `hypothesis_template`
- `mechanism_status`
- `signal_expression`
- `parameter_set`
- `parameter_grid_ref`
- `target_definition`
- `prediction_horizon`
- `label_window`
- `feature_observation_window`
- `feature_columns_used`
- `available_at_policy`
- `source_artifact_sha256`
- `trial_count_refs`
- `baseline_refs`
- `novelty_checks`
- `raw_validation_metrics`
- `selection_adjusted_metrics_status`
- `leakage_checks`
- `rejection_reason` または `shortlist_reason`
- `boundary`

必須 boundary:

- `permits_live_order=false`
- `permits_paper_candidate=false`
- `permits_paper_intent_preview=false`
- `live_conversion_allowed=false`
- `wallet_used=false`
- `signing_used=false`
- `exchange_write_used=false`
- `auto_promote=false`
- `generated_strategy_idea_is_final=false`

## 実装できる重要度順

### P0A: schema と fixture

対象:

- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `tests/strategy_idea_candidates/`
- `docs/strategy_idea_candidates/README.md`

完了条件:

- valid fixture が schema を通る。
- live / paper / auto promote 系 flag が true なら落ちる。
- `candidate_count_total` と `candidate_count_shortlisted + candidate_count_rejected` の不整合を落とす。
- `success_only_reporting=true` を落とす。
- `uses_sealed_test_for_selection=true` を落とす。
- `source_artifact_sha256` 欠落を落とす。
- `label_window` / `prediction_horizon` 欠落を落とす。

### P0B: artifact writer

対象:

- `src/sis/strategy_idea_candidates/`
- command はまだ private helper でもよい。public CLI にするなら docs / help / tests を同時に足す。

完了条件:

- 同じ input と config で deterministic artifact を出す。
- JSON / Markdown / JSONL / CSV の出力がそろう。
- dependency versions と generator version を保存する。
- selected only output を禁止する。

### P1: deterministic template generator

対象 family:

- trend / momentum
- volatility expansion / compression
- liquidity / spread
- regime filter
- cross-sectional rank
- mean reversion

完了条件:

- family / parameter grid / candidate count cap が明示される。
- 棄却候補も保存される。
- raw metric は raw と明記し、補正済み metric と偽らない。

### P2 以降

- 統計補強: optional `scipy` を検討。
- multiple testing / bootstrap: `statsmodels` / `arch` は必要になってから。
- ML: `scikit-learn` は P3 以降。
- GBDT / optimization: `lightgbm` / `optuna` は search ledger と sealed-test 境界ができた後。

## 実装でやらないこと

- `strategy_idea.v1` を直接大量生成する。
- selected candidate だけを出す。
- sealed test を使って shortlist する。
- `TradeCandidate` や `PaperCandidatePack` を pre-intake 候補に流用する。
- `TimeSeriesSplit` の `gap` を金融 leakage 対策完了と扱う。
- `pandas-ta` や `tsfresh` で feature / indicator を大量生成する。
- ML / LLM の narrative を evidence と扱う。
- backtest pass、review pass、candidate shortlist を paper / live permission と扱う。

## Readiness Verdict

実装 readiness:

- P0 schema / docs / fixture test: ready with assumptions
- P0 artifact writer: ready after schema acceptance
- P1 deterministic template generator: ready after P0 artifact writer
- P2 statistical evaluation: not yet; P0/P1 artifact が先
- P3 ML-derived candidates: not yet
- dependency addition: not now

この順番なら、既存の防御側機能を活かせる。一方で、P0 を飛ばして mining logic や依存関係から入ると、勝って見える候補を作れるが、なぜ選ばれたか、何を捨てたか、どのデータ時刻まで見たかが説明できない。

## 参照

repo-local:

- `schemas/strategy_idea.v1.schema.json`
- `schemas/strategy_input_contract.v1.schema.json`
- `schemas/strategy_input_contract_validation.v1.schema.json`
- `schemas/strategy_intake_decision.v1.schema.json`
- `schemas/strategy_optimizer_trial_ledger.v1.schema.json`
- `src/sis/commands/strategy_inputs.py`
- `src/sis/strategy_inputs/validation.py`
- `src/sis/research/strategy_lab/candidates.py`
- `docs/strategy_research_lab/02_ARTIFACT_FLOW_AND_LINEAGE.md`
- `docs/strategy_research_lab/03_SIGNAL_TO_TRADE_CANDIDATE_SPEC.md`
- `docs/strategy_research_lab/06_GENERATOR_AND_EXPERIMENT_SPEC.md`
- `docs/strategy_research_lab/07_VALIDATION_STOP_CONDITIONS_AND_TEST_MATRIX.md`

external:

- scikit-learn `TimeSeriesSplit` - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- PyPI `mlfinpy` - https://pypi.org/project/mlfinpy/
- PyPI `pandas-ta` - https://pypi.org/project/pandas-ta/
- PyPI `ta` - https://pypi.org/project/ta/

## 残リスク

- dependency dry-run は resolver 確認であり、実 import / runtime test ではない。
- 実装時点で package version と wheel availability は変わり得る。
- P0 schema の exact required field は実装時に tests と一緒に固定する必要がある。
- JSON Schema だけでは cross-field invariant を全部表現しづらい。`candidate_count_total` 整合や selected / rejected の重複検査は Python validation も併用する可能性が高い。
- 研究論文で推奨される DSR / PBO / White Reality Check / SPA を P0 に入れると過剰実装になる。P0 は「未補正を未補正と表示し、探索全量を消さない」ことを優先する。
