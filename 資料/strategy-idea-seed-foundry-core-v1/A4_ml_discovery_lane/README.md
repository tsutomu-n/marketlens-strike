<!--
作成日: 2026-07-16_16:10 JST
更新日: 2026-07-16_16:10 JST
-->

> `00_overview/core_v1_engineering_execution_plan.md`からA4部分を分割した実装用仕様です。共通契約、横断テスト、Reason CodeはOverview正本を参照してください。

# A4 — ML Discovery Lane

## A4.1 ゴール定義

A3の固定Datasetから、XGBoostとLightGBMをScoutとして学習し、Tree Pathを提案として抽出し、Rule単独再評価とDistillationを経てML SeedをArchiveへ追加する。

ML Seedは因果または利益を主張しない。Data上で観測された条件とPath Labelの関連を、Evidence Scope付きで記録する。

## A4.2 Entry Criteria

- A3が`IMPLEMENTATION_COMPLETE`。
- 対象Label/FoldがProduction Configの最低Data条件を満たす。
- A2 Archive/Fragment/Resumeが動作する。
- ML依存をCoreから分離する方針が確定している。

## A4.3 対象範囲

### 実装する

- Optional Dependency Probe
- Scout Engine Protocol
- XGBoost Runner
- LightGBM Runner
- Fixed Trial Grid
- Model/Metric/Dump Artifact
- Engine別Tree Parser
- Raw Path抽出
- Standalone Rule Evaluation
- Rule Distillation
- Rule Observation Evaluation
- Engine Matching
- ML Payload/Seed
- Planted/Null Control
- ML専用CI

### 実装しない

- Optuna
- SHAP必須化
- Deep Learning
- Modelを直接売買Ruleとして採用
- Sealed Test
- PnL/Cost
- 自動Candidate Export

## A4.4 対象ファイル

```text
src/sis/strategy_idea_seeds/ml/engines/
  protocol.py
  probe.py
  xgboost_runner.py
  lightgbm_runner.py

src/sis/strategy_idea_seeds/ml/rules/
  canonical_tree.py
  xgboost_parser.py
  lightgbm_parser.py
  path_extractor.py
  evaluator.py
  distiller.py
  engine_matching.py

src/sis/strategy_idea_seeds/ml/
  models.py
  seed_builder.py
  controls.py
  artifacts.py

schemas/
  strategy_idea_seed_ml_payload.v1.schema.json
  strategy_idea_seed_model_trial.v1.schema.json
  strategy_idea_seed_model_discovery.v1.schema.json

configs/strategy_idea_seeds/ml/
  scout_grid_v1.yaml
  rule_policy_v1.yaml

tests/strategy_idea_seeds/ml/engines/
tests/strategy_idea_seeds/ml/rules/
tests/fixtures/strategy_idea_seeds/model_dumps/
```

変更:

```text
pyproject.toml
uv.lock
.github/workflows/ci.yml
```

## A4.5 Dependency Probe

調査時点の候補はXGBoost 3.3系、LightGBM 4.6系だが、Versionを計画書だけで固定しない。

Probe:

1. Python 3.13 Wheel解決。
2. Core NumPy/Scipy/Polarsを不適切にDowngradeしない。
3. CPU Mini Train。
4. Prediction。
5. Native Model Save/Load。
6. JSON Tree Dump。
7. Parser Fixture作成。
8. `./scripts/check`維持。
9. Focused ML CI時間測定。

Probe成功後、Exact Versionを`uv.lock`へ固定する。

## A4.6 Scout Protocol

```python
class ScoutEngine(Protocol):
    engine_id: str
    engine_version: str

    def probe(self) -> EngineProbeResult: ...
    def train(self, request: ModelTrainingRequest) -> ModelRunResult: ...
    def save_model(self, model, path: Path) -> ArtifactRef: ...
    def dump_trees(self, model, path: Path) -> ArtifactRef: ...
    def predict(self, model, frame) -> PredictionResult: ...
```

Model本体とTree Dumpを別Artifactにする。DumpからModelを復元しない。

## A4.7 Initial Trial Policy

Binary ModelをLabel/Horizon/Directionごとに作る。

Metric:

```text
average_precision
log_loss
positive_rate
top_quantile_lift
```

Accuracy単独を使わない。

Fixed Variant ListをConfigに列挙する。全直積を生成しない。

例:

```yaml
xgboost:
  - max_depth: 4
    min_child_weight: 20
    subsample: 0.8
    colsample_bytree: 0.8
    learning_rate: 0.05

lightgbm:
  - num_leaves: 31
    max_depth: 6
    min_data_in_leaf: 100
    feature_fraction: 0.8
    bagging_fraction: 0.8
    learning_rate: 0.05
```

Seedは複数用意するが、Trial数はBudgetで制御する。

## A4.8 Reproducibility

XGBoost:

- CPU
- `tree_method=hist`
- Thread数固定
- Seed固定
- Model/Engine Version保存

LightGBM:

- CPU
- `deterministic=true`
- Seed群をすべて明示
- Thread数固定
- `force_col_wise=true`またはProbeで選んだ方式を固定

要求するのは同一OS、同一Lock、同一Config内の意味的再現性である。異OS/異CompilerのByte一致は要求しない。

## A4.9 Raw Rule抽出

Candidate Path選択はProposal Filterにすぎない。

初期Filter:

- Positive class方向のLeaf Value
- Minimum Cover
- Maximum Raw Condition Count
- Parserが解釈可能
- Missing Branch依存を明示

抽出後、必ずRule単独評価を行う。Leaf Value、Gain、CoverだけでSeed化しない。

## A4.10 Standalone Rule Evaluation

`rule_development`へRuleだけを適用する。

保存:

```text
support_rows
support_distinct_events
support_symbols
support_days
base_tail_rate
rule_tail_rate
tail_lift
excess_tail_probability
thresholds
```

Support 0はParser/Rule不整合として`RULE_SUPPORT_ZERO`、Ledger Onlyとする。

SupportはあるがPolicy未達なら`SMALL_SAMPLE` Seedとして残せる。利益理由で削除しない。

## A4.11 Distillation

Raw Ruleが5条件超の場合:

1. 各Clauseを一つずつ除外する。
2. `rule_development`上で再評価。
3. Tail Lift RetentionとSupportを保存。
4. 最良Removalを選ぶ。
5. 2～5条件まで繰り返す。
6. Fidelityを保てなければRaw Ruleのまま`COMPLEX_RULE`として保存する。

`rule_observation`はDistillationに使用しない。

## A4.12 Rule Observation

完成Ruleを固定し、`rule_observation`へ一度だけ適用する。

保存:

```text
observation_support
observation_distinct_events
observation_tail_rate
observation_lift
direction_consistency
```

Observationがない場合:

```text
evidence_scope=RULE_DEVELOPMENT_ONLY
seed_tags=[IN_SAMPLE_DISCOVERY_ONLY]
```

OOSと表現しない。

## A4.13 Engine Matching

A2 Semantic Descriptorを使う。

```text
DISCOVERED_BY_BOTH
XGBOOST_ONLY
LIGHTGBM_ONLY
ENGINE_DISAGREEMENT
```

`ENGINE_DISAGREEMENT`は、同一前提Clusterで両Engineに最低Supportがあり、方向またはLabelが矛盾する場合だけ付ける。

片方にRuleがないだけならSingle Engineである。

## A4.14 Control Dataset

### Planted Mechanism

既知のFeature InteractionでTail Labelが発生するSynthetic Datasetを作り、発見可能性を確認する。

### Null

```text
label shuffle
block shuffle
feature permutation
independent random walk
```

Nullから出たSeedも削除せず`NULL_CONTROL_DISCOVERY`を付ける。

実データとNullでRule数が同程度でも、Foundryの機能は完成し得るが、ML LaneのCurrent Data価値は`PAUSE_ML_NOISE_DOMINATED`とする。

## A4.15 Public CLI

```bash
uv run --extra seed-ml sis strategy-idea-seeds-ml-discover   --dataset-manifest <path>   --scout-config <path>   --rule-policy <path>   --archive-root <path>   --out <path>
```

## A4.16 詳細タスク

| ID | タスク |
|---|---|
| A4-01 | Optional Dependency Probeを実行 |
| A4-02 | Exact VersionをLock |
| A4-03 | Scout Protocol/Modelsを実装 |
| A4-04 | XGBoost Runnerを実装 |
| A4-05 | LightGBM Runnerを実装 |
| A4-06 | Trial Ledger/Artifactsを実装 |
| A4-07 | Golden Tree Dump Parserを実装 |
| A4-08 | Raw Path Extractorを実装 |
| A4-09 | Standalone Evaluatorを実装 |
| A4-10 | Distillerを実装 |
| A4-11 | Observation Evaluatorを実装 |
| A4-12 | Engine Matcherを実装 |
| A4-13 | ML Payload/Seed Builderを実装 |
| A4-14 | Planted/Null Controlsを実装 |
| A4-15 | CLI/Optional CIを追加 |

## A4.17 Test方針

- Same Input/Lock/SeedでTrial Metadataが一致。
- Model Save/Load Predictionが一致。
- Dump ParserがGolden FixtureをParse。
- Missing Branchが明示される。
- 同一Featureの複数条件を区間化。
- Contradictory Ruleを拒否。
- Rule単独Supportを再計算。
- DistillationがObservationを参照しない。
- One Engine Failureで他Engine Artifactが残る。
- Null Controlへ専用Tag。
- Core CIにML Packageが不要。

## A4.18 完了条件

### `IMPLEMENTATION_COMPLETE`

- 両EngineのProbe、Train、Save、Dump、Parseが成功。
- Rule単独再評価とDistillationが動作。
- ML SeedがArchiveへ追加される。
- Evidence Scopeが正しく表示される。
- Planted/Null Controlが実行可能。
- Core CIとML CIが分離される。

### `CURRENT_DATA_OPERATIONAL`

- A3 Current Datasetから少なくとも一つのModel Runが完走。
- Rule 0件でも正常Manifestを出す。
- Data不足またはNull優勢を明示できる。
- MLがTechnicalと異なるClusterを出すか測定できる。

## A4.19 停止・再設計条件

- Python 3.13 WheelがなくSource Build必須。
- ML依存がCoreを壊す。
- Tree Dump ParseがVersion固定でも不安定。
- Leaf ValueだけでSeed化する。
- Rule ObservationをRule作成へ使用する。
- Null Controlと実データを区別できないのに拡張を続ける。
- ML Ruleへ因果説明を事実として付与する。

## A4.20 Gate G4

```text
CONTINUE_ML_LANE
HOLD_ML_LANE
REVISE_A4
```

Technicalと異なる仮説を供給しない場合もCodeは維持できるが、高度化は行わない。
