<!--
作成日: 2026-06-27_10:15 JST
更新日: 2026-06-27_10:15 JST
-->

# Strategy Idea Generation Dependency Research 2026-06-27

## 結論

依存関係は、今すぐ core dependencies に追加しない。戦略アイデア候補生成の P0 / P1 は、現行の `polars`、`duckdb`、`pyarrow`、`pydantic`、`jsonschema` だけで実装できる。

より良くする余地はある。ただし追加順は次に固定した方がよい。

1. P0 / P1: 依存追加なし。まず `strategy_idea_candidate_set.v1` と deterministic candidate pack を作る。
2. P2: `idea-stats` optional extra として `scipy` を第一候補にする。必要なら `statsmodels`、時系列 bootstrap が必要なら `arch` を足す。
3. P3: `idea-ml` optional extra として `scikit-learn` を検討する。candidate artifact、search ledger、sealed test 境界ができてから。
4. P4 以降: `lightgbm` は明示タスクがある時だけ optional。`xgboost`、`optuna`、`tsfresh` は初期採用しない。
5. `mlfinlab` 系は採用しない。ライセンス、配布、Python 3.13 適合、保守性の不確実性が大きく、現 repo の初期 candidate generator には重い。

防御側機能を強くする依存を先に入れ、探索を増やす依存は後回しにする。これは保守のためだけではなく、戦略候補生成で最も危険な「探索して偶然良かったものを発見と誤認する」問題を避けるためです。

## 調査質問

入力データから戦略アイデア候補を作る機能をより良くするために、依存関係を追加すべきか。追加するなら、どの package を、どの順番で、どの optional boundary に置くべきか。

鮮度リスク:

- Python package の最新 version、Python 3.13 対応、transitive dependency は current。
- 公式 docs と `uv pip install --dry-run` を 2026-06-27_10:15 JST に確認した。
- 実際に `pyproject.toml` / `uv.lock` を変更する時は、再度 `uv add --optional ...` または lock dry-run で確認する。

## repo の現在依存

`pyproject.toml` の core dependency は、CLI、schema validation、market data read、Polars / DuckDB / Arrow 系に寄っている。

主要 core:

- `typer`, `rich`, `loguru`
- `pydantic`, `pydantic-settings`, `jsonschema`, `pyyaml`
- `httpx`, `tenacity`, `websockets`
- `polars`, `duckdb`, `pyarrow`
- `exchange-calendars`
- `yfinance`, `yahooquery`, `fredapi`, `pandas-datareader`

既存 optional extra:

- `vectorbt = ["vectorbt==1.0.0"]`
- `bt = ["bt==1.2.0"]`
- `metrics = ["empyrical-reloaded==0.5.12"]`
- `reports = ["quantstats==0.0.81"]`

`uv tree --package marketlens-strike --depth 2` では、optional extra 経由で `scipy`, `scikit-learn`, `numba`, `matplotlib` などは解決対象に入る。ただし default 環境の import check では `scipy`, `scikit-learn`, `statsmodels`, `arch`, `vectorbt`, `bt`, `empyrical`, `quantstats`, `matplotlib`, `xgboost`, `lightgbm`, `optuna`, `tsfresh` は未導入だった。

このため、候補生成の初期実装で core dependency を増やす必要はない。

## 候補 dependency 評価

| package | 役割 | 価値 | リスク | 判断 |
|---|---|---|---|---|
| `scipy` | bootstrap、permutation test、FDR 補正 | raw metric に confidence interval、permutation test、multiple testing 補正を足せる | 追加 package は重めだが、既存 optional extra でも解決済み | P2 で optional `idea-stats` 第一候補 |
| `statsmodels` | 多重検定、回帰、robust covariance | `multipletests`、OLS、HAC / Newey-West 系に進める | pandas / scipy 前提。初期 generator には不要 | P2 で条件付き採用 |
| `arch` | 時系列 bootstrap、financial econometrics | dependent return / residual の bootstrap 評価に使える | `statsmodels` も入り、初期 MVP には重い | P2 後半で条件付き採用 |
| `scikit-learn` | time split、pipeline、regularized model、tree model | `TimeSeriesSplit`、`Pipeline`、`RandomForest`、`HistGradientBoosting` など ML 候補生成の標準基盤 | artifact/ledger 前に入れると探索過多になる | P3 optional `idea-ml` |
| `lightgbm` | 高速 GBDT | Polars / Arrow / pandas 入力を扱える。tabular signal には強い | model complexity と tuning bias が増える | P4 以降の明示 task だけ |
| `xgboost` | GBDT / ranking | sklearn interface と early stopping がある | `uv pip install --dry-run xgboost` で `nvidia-nccl-cu12` も解決される。初期には重い | 初期採用しない |
| `optuna` | hyperparameter optimization | search history を持てる。複雑な search に強い | まさに探索回数を増やす道具。ledger と sealed test なしでは危険 | 初期採用しない |
| `tsfresh` | 自動 feature extraction | 時系列 feature を大量生成できる | feature 数が増え、多重検定と data snooping が急増する。transitive dependency も重い | MVP では避ける |
| `mlfinlab` / 類似 | finance ML 手法集 | Purged K-Fold など方向性は近い | 商用・配布・互換性・保守性が不確実。必要部分は小さく自前実装がよい | 採用しない |
| TA indicator library | indicator catalog | すぐ候補数を増やせる | indicator explosion と似た候補の重複を招く | 初期採用しない |

## `uv pip install --dry-run` で確認した解決結果

実行時点: 2026-06-27_10:15 JST。

```text
uv pip install --dry-run scipy
=> scipy==1.18.0

uv pip install --dry-run scikit-learn
=> joblib==1.5.3, narwhals==2.22.1, scikit-learn==1.9.0, scipy==1.18.0, threadpoolctl==3.6.0

uv pip install --dry-run scipy statsmodels arch scikit-learn
=> arch==8.0.0, joblib==1.5.3, narwhals==2.22.1, patsy==1.0.2,
   scikit-learn==1.9.0, scipy==1.18.0, statsmodels==0.14.6, threadpoolctl==3.6.0

uv pip install --dry-run lightgbm
=> lightgbm==4.6.0, scipy==1.18.0

uv pip install --dry-run xgboost
=> nvidia-nccl-cu12==2.30.7, scipy==1.18.0, xgboost==3.3.0

uv pip install --dry-run optuna
=> alembic==1.18.5, colorlog==6.10.1, greenlet==3.5.3,
   mako==1.3.12, markupsafe==3.0.3, optuna==4.9.0, sqlalchemy==2.0.51

uv pip install --dry-run tsfresh
=> cloudpickle==3.1.2, joblib==1.5.3, llvmlite==0.47.0, narwhals==2.22.1,
   numba==0.65.1, patsy==1.0.2, pywavelets==1.9.0, scikit-learn==1.9.0,
   scipy==1.18.0, statsmodels==0.14.6, stumpy==1.14.1,
   threadpoolctl==3.6.0, tsfresh==0.21.2
```

この結果からも、`scipy` 単体は比較的局所的だが、`tsfresh` や `xgboost` は候補生成 MVP に対して依存面の増分が大きい。

## 推奨 optional extras 案

実装時に exact pin / upper bound は再確認する前提で、設計上は次の分離がよい。

```toml
[project.optional-dependencies]
idea-stats = [
  "scipy>=1.18,<2",
]
idea-regression = [
  "statsmodels>=0.14,<0.15",
]
idea-bootstrap = [
  "arch>=8,<9",
]
idea-ml = [
  "scikit-learn>=1.9,<2",
]
idea-gbdt = [
  "lightgbm>=4.6,<5",
]
```

`idea-gbdt` は最初から入れない。必要になったら別 task で採用する。

`xgboost` を入れる場合は、GPU / CUDA 系 transitive dependency をどう扱うかを先に決める。現時点の dry-run では `nvidia-nccl-cu12` が入るため、default optional extra に置かない。

`optuna` は `idea-search` のような名前で後から分離できるが、最初は入れない。入れるなら `study_id`、`trial_count`、`objective`、`sampler`、`pruner`、`seed`、`storage`、`validation_peek_count` を artifact に必須保存する。

## 何が Better になるか

### `scipy` を足す価値

- `scipy.stats.bootstrap` で候補 metric の信頼区間を出せる。
- `scipy.stats.permutation_test` で「偶然でも出そうな差」を検査できる。
- `scipy.stats.false_discovery_control` で FDR 補正を入れられる。

これは候補生成器を派手にする依存ではなく、候補を落とすための依存です。最初に足すならこれが最も整合的。

### `statsmodels` / `arch` を足す価値

`statsmodels` は multiple testing、regression、robust covariance へ広げられる。`arch` は bootstrap module があり、NumPy / pandas data に対する high-level / low-level bootstrapping interface を提供する。金融時系列の依存構造を意識した検定を入れる段階では価値がある。

ただし P0 / P1 で入れると早い。まず trial ledger と split policy を artifact 化してからでよい。

### `scikit-learn` を足す価値

`TimeSeriesSplit` は、時系列順序を保つ cross-validation split として使える。`Pipeline`、regularized linear model、tree ensemble、feature selection など、candidate family を広げる標準基盤になる。

ただし、ML で候補を作る前に、候補 artifact に次を持たせる必要がある。

- `model_family`
- `feature_columns_used`
- `target_definition`
- `train_window`
- `validation_window`
- `sealed_test_window`
- `hyperparameter_space`
- `trial_count`
- `selection_policy`
- `seed`
- `leakage_check_status`

これがないと、`scikit-learn` は品質向上ではなく探索過多の入口になる。

## 避けるべき依存

### `tsfresh`

tsfresh は時系列 feature を自動生成できるが、その強みがそのまま候補生成では危険になる。feature 数が増えるほど、多重検定、似た特徴量の重複、validation overfit が増える。

公式 docs でも、tsfresh は streaming data には向かず、model training は scikit-learn 等に委ねる立場です。現 repo の初期候補生成は、透明な family と parameter grid を記録する方が重要。

### `Optuna`

Optuna は hyperparameter optimization framework として強い。しかし、戦略候補生成の文脈では「探索回数を増やし、最良値を探す」機能そのものです。search ledger、sealed test、trial budget、rejection inventory が実装される前に入れるべきではない。

### `LightGBM` / `XGBoost`

どちらも tabular model として有力だが、初期 candidate generator には不要。特に `xgboost` は今回の dry-run で GPU / CUDA 系の `nvidia-nccl-cu12` まで解決された。依存負荷、CI 影響、環境差、model tuning bias の割に、P0 / P1 の目的には合わない。

### `mlfinlab`

方向性としては近い手法が多いが、現時点では repo の基盤依存にしない。理由は次です。

- 商用・配布・ライセンス面の不確実性がある。
- Python 3.13 / uv locked workspace への適合をこの場で十分に確認できない。
- 必要な考え方は、purged split、embargo、triple barrier、uniqueness など個別に小さく実装できる。
- 最初に必要なのは large framework ではなく、candidate artifact の完全な証跡です。

## 導入 gate

依存を足すなら、次を満たすまで core には入れない。

- optional extra である。
- `uv lock --python /usr/bin/python3.13` が通る。
- `./scripts/check` が通る。
- 追加 dependency が必要な command は、extra 未導入時に明確な error message を出す。
- 生成 artifact に dependency version、random seed、input hash、trial count を保存する。
- dependency の有無で既存 CLI の結果が変わらない。
- paper / live permission path に影響しない。

## 実装順への反映

`docs/STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md` の実装順に依存判断を足すなら、次になる。

1. P0: `strategy_idea_candidate_set.v1` schema。依存追加なし。
2. P1: deterministic template generator。依存追加なし。
3. P2: time / era split evaluation。最初は自前 + Polars。統計補強が必要になったら `idea-stats` に `scipy`。
4. P2.5: multiple testing / bootstrap pack。`statsmodels` / `arch` を optional に検討。
5. P3: existing intake export。依存追加なし。
6. P4: review / backtest pack 連携。依存追加なし。
7. P5: ML-derived candidates。`scikit-learn` optional。
8. P6: advanced search / GBDT。`lightgbm`、必要なら `optuna` を別 task で検討。`xgboost` は環境負荷を再評価してから。

## 参照ソース

公式 docs:

- scikit-learn `TimeSeriesSplit` - https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html
- SciPy `bootstrap` - https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html
- SciPy `permutation_test` - https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html
- SciPy `false_discovery_control` - https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.false_discovery_control.html
- statsmodels `multipletests` - https://www.statsmodels.org/stable/generated/statsmodels.stats.multitest.multipletests.html
- arch bootstrapping - https://arch.readthedocs.io/en/latest/bootstrap/bootstrap.html
- LightGBM Python package introduction - https://lightgbm.readthedocs.io/en/latest/Python-Intro.html
- XGBoost Python package introduction - https://xgboost.readthedocs.io/en/stable/python/python_intro.html
- Optuna docs - https://optuna.readthedocs.io/en/stable/
- tsfresh introduction - https://tsfresh.readthedocs.io/en/latest/text/introduction.html
- tsfresh feature overview - https://tsfresh.readthedocs.io/en/latest/text/list_of_features.html

repo-local:

- `pyproject.toml`
- `uv.lock`
- `uv tree --package marketlens-strike --depth 2`
- `uv pip install --dry-run ...`

## 抜け・漏れ・誤謬リスク

- `uv pip install --dry-run` は resolver の結果であり、実インストール、import、runtime test まではしていない。
- 依存 version は current。実装時には変わり得る。
- package の license / wheel availability / CI platform compatibility は採用直前に再確認が必要。
- `scipy`、`statsmodels`、`arch` の統計手法は、入れれば正しく使えるわけではない。金融時系列では独立同分布でない前提が壊れやすい。
- `LightGBM` は Polars / Arrow 入力に対応しており魅力はあるが、model tuning と feature search の統制が先。
- `mlfinlab` 系の不採用判断は、この repo の Python 3.13 / uv / open implementation bias に基づく。別環境や商用利用前提なら再評価余地はある。

## 次にやること

依存追加は今しない。実装再開時は、まず依存なしで `strategy_idea_candidate_set.v1` と deterministic generator を作る。統計評価が必要になった段階で、最小 optional extra として `idea-stats = ["scipy>=1.18,<2"]` を検討する。
