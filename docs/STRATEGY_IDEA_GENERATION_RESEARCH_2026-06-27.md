<!--
作成日: 2026-06-27_09:53 JST
更新日: 2026-06-27_10:54 JST
-->

# Strategy Idea Generation Research 2026-06-27

## 結論

入力データから戦略アイデア候補を作る機能は、実装する価値がある。ただし、作るべきものは「儲かる戦略の自動発明機」ではなく、「未検証候補を大量に作り、探索履歴を隠さず、既存の防御側 gate に渡す候補生成器」です。

現実的な実装方針は次です。

1. 既存の `strategy_idea.v1` を直接自動生成の主 artifact にしない。
2. まず `strategy_idea_candidate_set.v1` のような候補束 artifact を作る。
3. 候補ごとに、使った入力データ、列、期間、探索 family、parameter grid、試行回数、選別理由、棄却理由を残す。
4. 既存の `strategy-intake-validate`、Strategy Authoring、backtest pack、Strategy Review、paper observation へ進める候補は、人間または明示 gate が shortlist したものだけにする。
5. paper / live permission は絶対に出さない。候補生成の出力は常に `UNVERIFIED_CANDIDATE` として扱う。

この方針なら、既存の防御側機能と整合する。一方で、探索数、holdout、future leakage、public leaderboard 的な feedback overfit を記録しない実装は、見た目の勝率を作るだけなので採用しない。

依存関係の追加判断は [STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md](STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md) を読む。結論は、P0 / P1 では依存追加なし、P2 で `scipy` を optional extra として検討、ML / GBDT / hyperparameter search 系は candidate artifact と search ledger の後です。

実装直前の用語衝突、schema 必須項目、TimeSeriesSplit の限界、`mlfinlab` / `mlfinpy` / TA 系依存の追加調査による修正判断は [STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md](STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md) を読む。実装へ進めてよいのは P0 の artifact / schema / Python validation / docs / fixture test までで、mining logic と依存追加はまだ対象外です。

candidate generation pipeline の checkpoint と到達順は [STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md](STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md) を読む。input contract / source evidence bridge は generator の後ではなく、artifact writer / generator の前提として扱う。

## 調査質問

論文、研究、Kaggle、Numerai の知見から見て、`marketlens-strike` に「入力データから戦略アイデア候補を作る機能」を追加するのは現実的か。追加するなら、何を必須制約にすべきか。

鮮度リスク:

- 論文の中核知見は stable。
- Kaggle / Numerai の仕様、scoring、payout、platform wording は current。2026-06-27 に公式ページを確認したが、今後変わる可能性がある。

## まず repo 側の現在地

コードを正とすると、現状は「アイデア生成」ではなく「既存アイデアの検査」です。

- `schemas/strategy_idea.v1.schema.json` は、`hypothesis`、`mechanism`、`baseline`、`invalidation`、`risk`、`execution_assumptions`、`boundary` を必須にする。
- 同 schema は `authoring_intent.auto_generate_spec` を `false` に固定している。
- `schemas/strategy_intake_decision.v1.schema.json` は `REJECT`、`NEEDS_SPEC`、`NEEDS_DATA_CHECK`、`NEEDS_RISK_SPEC`、`READY_FOR_AUTHORING_DRAFT` の intake 判定を表す。
- `src/sis/strategy_inputs/validation.py` の `validate_strategy_intake` は、入力済み `strategy_idea.v1` と input contract validation を読み、欠落、risk、boundary、input validation status を検査する。
- `src/sis/commands/strategy_inputs.py` の public CLI は `strategy-input-contract-validate` と `strategy-intake-validate`。候補生成 command はない。
- `docs/strategy_inputs/README.md` も、input contract と idea intake を first gate と説明している。

したがって、ドキュメント上の「戦略アイデア整理」は「曖昧な案を検査可能にする」意味であり、「入力データから新しい戦略案を自動発見する」意味ではない。

## 論文・研究からの要点

### 1. 大量探索は、勝って見える候補を必ず作る

Bailey, Borwein, Lopez de Prado, Zhu の “The Probability of Backtest Overfitting” は、通常の holdout が投資 backtest では不安定になり得ること、CSCV で backtest overfitting probability を推定する枠組みを提案している。

実装への意味:

- 候補生成器は、候補の勝ち負けだけでなく、探索空間と試行数を保存する必要がある。
- 「一番良かった候補」だけを出す UI は危険。
- `candidate_count`、`trial_count`、`family_count`、`parameter_grid_hash`、`selection_policy` がない artifact は review に進めない方がよい。

### 2. Sharpe や total return だけでは足りない

Bailey and Lopez de Prado の Deflated Sharpe Ratio は、多重検定、選択バイアス、非正規リターンによる性能水増しを補正するための指標を扱う。論文の問題意識は、金融 data set と machine learning / high-performance computing により膨大な戦略を backtest できるようになり、最良 backtest の性能が膨らみやすい点にある。

実装への意味:

- 初期 MVP で DSR まで実装しない場合でも、候補 artifact には「補正未実装」「raw metric のみ」「selection-adjusted metric なし」を明示する。
- 候補 shortlist の条件を raw Sharpe / raw return だけにしない。
- 後続 phase で DSR、PBO、White Reality Check / SPA 系の selection adjustment を入れる余地を残す。

### 3. 新 factor の有意性ハードルは通常より高い

Harvey, Liu, Zhu の “... and the Cross-Section of Expected Returns” は、多数の factor 研究がある状況では通常の t-statistic 2.0 前後では甘く、新 factor はより高いハードルを超えるべきだと論じる。

実装への意味:

- 候補生成機能では、`p_value` や `t_stat` があってもそのまま「発見」と呼ばない。
- 「新規性が高い候補」ほど、探索調整後の証拠、out-of-sample、paper observation を重く見る。
- literature-seeded candidates と pure data-mined candidates を分ける。

### 4. 公開後・外部化後に edge は落ちる

McLean and Pontiff は、学術文献にある 97 個の stock return predictor を対象に、out-of-sample と publication 後の return predictability が落ちることを示している。報告値では portfolio return が out-of-sample で 26% 低く、publication 後で 58% 低い。

実装への意味:

- 文献由来の candidate でも、そのまま現在の edge と扱わない。
- `source_type=literature` の候補には、`publication_decay_risk=true` や `crowding_risk` を記録する。
- 現在の自分の対象 universe / cost / liquidity で再検証するまで、候補に留める。

### 5. ML は有効になり得るが、防御なしでは壊れる

Gu, Kelly, Xiu の “Empirical Asset Pricing via Machine Learning” は、木系モデルや neural networks が nonlinear interaction を扱い、out-of-sample の改善を示す一方で、time-ordered train / validation / test 分割、regularization、hyperparameter tuning の分離を重視している。同論文は dominant predictive signals として momentum、liquidity、volatility 系を挙げる。

実装への意味:

- 「機械学習で何でも探す」より、既存の robust factor family から開始する方が現実的。
- MVP の generator family は momentum / trend、liquidity、volatility、spread / cost、regime、cross-sectional rank から始める。
- ML-derived idea generation は Phase 2 以降にし、初期は deterministic template + transparent scoring にする。

### 6. White Reality Check / data snooping は候補生成器の中心リスク

White の Reality Check は、同じデータを何度も使って model selection した時に、良く見える結果が偶然である可能性を扱う。Sullivan, Timmermann, White は技術的売買 rule 群の data-snooping bias を bootstrap で評価している。

実装への意味:

- 候補生成は data snooping そのものなので、隠してはいけない。
- generator は `searched_universe` と `full_candidate_inventory` を出す必要がある。
- 候補を 1 件だけ出す command より、全候補と棄却理由を含む pack を出す command がよい。

## Kaggle からの要点

### 1. public leaderboard は validation として使いすぎると壊れる

Kaggle は public / private leaderboard を分ける。Kaggle competition setup docs でも、private leaderboard は overfitting 防止のための split と説明されている。

Moritz Hardt の Kaggle leaderboard 解説と、Whitehill の “Climbing the Kaggle Leaderboard by Exploiting the Log-Loss Oracle” は、leaderboard feedback が holdout 情報を漏らし、最終 test には効かない改善を作れることを示す。

実装への意味:

- `marketlens-strike` の候補生成にも、public leaderboard 相当の validation score と、sealed private test 相当の最終評価を分ける。
- 候補生成器は sealed test を使って候補選択してはいけない。
- `submission_count` 相当として `selection_iterations`、`validation_peek_count`、`rerank_count` を artifact に残す。

### 2. 金融 Kaggle は実務感があるが、取引可能性の証明ではない

JPX Tokyo Stock Exchange Prediction は、約 2,000 銘柄を ranking して将来 return を予測する競技として説明される。Jane Street Real-Time Market Data Forecasting は、匿名化された real market data 由来の time series、79 features、9 responders を扱う。

実装への意味:

- Kaggle 的な `rank stocks by predicted return` や `predict responders` は candidate generation の参考になる。
- ただし competition の hidden target / data split / scoring は、そのまま実取引の slippage、borrow、latency、capacity、税、約定を証明しない。
- `marketlens-strike` 側では、候補生成の後に execution assumptions、cost stress、paper observation を別 gate にする既存設計を維持する。

## Numerai からの要点

### 1. Numerai Tournament は obfuscated data で model を作る

Numerai docs は、Tournament を stock market prediction の data science competition と説明している。dataset は obfuscated され、外部の自前取引には使えないと明記している。

実装への意味:

- Obfuscated data で勝つ model は、mechanism が弱い場合がある。
- `marketlens-strike` の candidate は、最低限 `mechanism` または `mechanism_unknown=true` を明示し、mechanism が弱い候補を高リスク扱いにする。

### 2. era と delayed live scoring は参考になる

Numerai は row を `era` で扱い、target は将来 return として説明される。Scoring は 20D2L のように遅れて確定し、validation diagnostics に頼りすぎる過剰適合への注意も公式 docs にある。

実装への意味:

- candidate evaluation は calendar split ではなく、`era` / regime / volatility state で見る方がよい。
- paper observation は即時勝敗ではなく、target horizon が満了してから評価する。
- validation diagnostics を見た回数を増やすほど selection bias が増える。

### 3. Signals は「独自性」を評価する発想が近い

Numerai Signals は、ユーザーが自分の unique signal を持ち込み、Numerai が既存 signal に neutralize したうえで unique component を評価する設計を説明している。

実装への意味:

- 候補生成器にも、既存 baseline / known factor との correlation を測る `novelty` または `residual_value` が必要。
- 既存 factor とほぼ同じ候補は「発見」ではなく、known factor clone として扱う。
- ただし novelty だけを目的にすると偶然の noise を拾いやすいので、stability と cost を同時に見る。

## 実装に落とすなら何を作るか

### 推奨 MVP

新 CLI:

```bash
uv run sis strategy-idea-candidates-build \
  --input-contract-validation data/strategy_inputs/<contract-id>/strategy_input_contract_validation.json \
  --source data/research/<feature-panel>.parquet \
  --out data/strategy_idea_candidates/<run-id> \
  --family trend \
  --family volatility \
  --family liquidity \
  --max-candidates 200 \
  --selection-policy validation_only
```

期待 artifact:

- `strategy_idea_candidate_set.json`
- `strategy_idea_candidate_set.md`
- `candidate_search_ledger.jsonl`
- `candidate_metrics.csv`
- `candidate_rejections.csv`
- `shortlist.json`
- `exported_strategy_ideas/` optional。shortlist 後だけ `strategy_idea.v1` draft を出す。

境界:

- `permits_live_order=false`
- `permits_paper_candidate=false`
- `auto_promote=false`
- `uses_sealed_test_for_selection=false`
- `oos_status=NOT_EVALUATED` から開始
- `generated_strategy_idea_is_draft=true`

### Candidate に必須の field

- `candidate_id`
- `generator_version`
- `generated_at`
- `source_contract_refs`
- `source_artifact_path`
- `source_artifact_sha256`
- `feature_columns_used`
- `target_definition`
- `available_at_policy`
- `lookback_window`
- `holding_horizon`
- `universe`
- `family`
- `signal_expression`
- `parameter_set`
- `parameter_grid_ref`
- `family_trial_count`
- `total_trial_count`
- `selection_policy`
- `selected_from_rank`
- `baseline_refs`
- `correlation_to_known_factors`
- `raw_validation_metrics`
- `selection_adjusted_metrics` または `selection_adjusted_metrics_status=NOT_IMPLEMENTED`
- `leakage_checks`
- `invalidation`
- `risk_defaults`
- `execution_assumption_defaults`
- `rejection_reason` または `shortlist_reason`
- `boundary`

## 重要度順の実装順

### P0: 候補生成の artifact 契約

目的:
候補を出す前に、候補をどう記録するかを固定する。

対象:

- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `src/sis/strategy_idea_candidates/`
- `tests/strategy_idea_candidates/`
- `docs/strategy_idea_candidates/README.md`

完了条件:

- schema validation がある。
- boundary が paper / live permission を絶対に出さない。
- trial count と search ledger が必須。

### P1: deterministic template generator

目的:
LLM や black-box ML ではなく、再現可能な候補を作る。

候補 family:

- trend / momentum
- volatility expansion / compression
- liquidity / spread
- regime filter
- cross-sectional rank
- mean reversion
- event window

完了条件:

- 同じ input artifact と config から同じ candidate set が再生成される。
- 候補数 cap がある。
- rejected candidates も保存される。

### P2: time / era split evaluation

目的:
Kaggle public leaderboard 的な overfit を避ける。

完了条件:

- train / validation / sealed test の役割を artifact で分ける。
- sealed test は selection に使わない。
- `validation_peek_count` と `selection_iterations` を記録する。

### P3: 既存 intake への export

目的:
shortlist された候補だけを既存 `strategy_idea.v1` draft に落とす。

完了条件:

- `strategy_idea.v1` の `authoring_intent.auto_generate_spec=false` は維持。
- export した draft も `strategy-intake-validate` を通す。
- export は paper / live permission を出さない。

### P4: Strategy Review / backtest pack 連携

目的:
候補生成履歴を review packet に含め、人間が「どれだけ探索したか」を見られるようにする。

完了条件:

- review packet が candidate search ledger の path / hash / summary を持つ。
- backtest result だけでなく、探索数と棄却候補数を表示する。

### P5: ML / LLM 補助

目的:
deterministic generator で足場を作った後、model-derived interaction や LLM 説明生成を補助として使う。

完了条件:

- LLM 出力は hypothesis wording の補助に留める。
- LLM が作った narrative を evidence と扱わない。
- black-box model の candidate は feature importance、stability、leakage check がない限り shortlist しない。

## 作らない方がよいもの

- 入力データを渡すと 1 つの「おすすめ戦略」を返す command。
- 最良 Sharpe / 最良 return だけを表示する leaderboard。
- 棄却候補を保存しない探索。
- sealed test を使って候補を選ぶ flow。
- `strategy_idea.v1` に大量の探索 metadata を押し込む設計。
- LLM に「良さそうな戦略名と説明」を作らせ、それを仮説と呼ぶ設計。
- backtest pass から paper / live に自動昇格する設計。

## ドキュメント上の修正点

`docs/FEATURE_CAPABILITY_SUMMARY_2026-06-27.md` の「戦略アイデア整理」は、非技術者には「アイデアを自動生成できる」と読める余地があった。正しくは、現状は既存アイデアの整理と intake validation であり、データからの自動候補生成は未実装です。

この research memo を current docs に追加し、今後の新機能開発ではここを候補生成機能の実装判断資料として扱う。

実装へ入る前の最終境界は [STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md](STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md) に分ける。特に `StrategyIdeaCandidate` は pre-intake artifact であり、既存の `TradeCandidate` / `PaperCandidatePack` / `strategy_idea.v1` とは別物として扱う。

## 参照ソース

論文・研究:

- Bailey, Borwein, Lopez de Prado, Zhu, “The Probability of Backtest Overfitting” - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253
- Bailey and Lopez de Prado, “The Deflated Sharpe Ratio: Correcting for Selection Bias, Backtest Overfitting and Non-Normality” - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2460551
- Harvey, Liu, Zhu, “... and the Cross-Section of Expected Returns” - https://academic.oup.com/rfs/article/29/1/5/1843824
- McLean and Pontiff, “Does Academic Research Destroy Stock Return Predictability?” - https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2156623
- White, “A Reality Check for Data Snooping” - https://www.ssc.wisc.edu/~bhansen/718/White2000.pdf
- Sullivan, Timmermann, White, “Data-Snooping, Technical Trading Rule Performance, and the Bootstrap” - https://ideas.repec.org/a/bla/jfinan/v54y1999i5p1647-1691.html
- Gu, Kelly, Xiu, “Empirical Asset Pricing via Machine Learning” - https://academic.oup.com/rfs/article/33/5/2223/5758276
- Whitehill, “Climbing the Kaggle Leaderboard by Exploiting the Log-Loss Oracle” - https://arxiv.org/abs/1707.01825
- Neto et al., “Reducing overfitting in challenge-based competitions” - https://arxiv.org/abs/1607.00091
- Moritz Hardt, “Competing in a data science contest without reading the data” - https://blog.mrtz.org/2015/03/09/competition.html

Kaggle:

- Kaggle Competition Setup Documentation - https://www.kaggle.com/docs/competitions-setup
- JPX Tokyo Stock Exchange Prediction - https://www.kaggle.com/competitions/jpx-tokyo-stock-exchange-prediction
- Jane Street Real-Time Market Data Forecasting - https://www.kaggle.com/competitions/jane-street-real-time-market-data-forecasting

Numerai:

- Numerai Docs Overview - https://docs.numer.ai/
- Numerai Tournament Scoring - https://docs.numer.ai/numerai-tournament/scoring
- Numerai Signals Overview - https://docs.numer.ai/numerai-signals/signals-overview
- Numerai Signals Submissions - https://docs.numer.ai/numerai-signals/submissions

## 抜け・漏れ・誤謬リスク

- Kaggle の competition page は JavaScript rendering が強く、本文を完全には抽出できなかった。公式 URL と search result snippet で確認したが、細かい rules / metric は各 competition page の live 表示を別途確認する余地がある。
- Numerai の scoring / payout は変わり得る。ここでは platform mechanics の思想だけを実装判断に使い、現在の payout 条件をこの repo の仕様にはしない。
- DSR / PBO / White Reality Check / SPA を初期 MVP に全部入れると重い。初期は「raw metric は未補正」と明示し、trial ledger を消さないことを優先する。
- 研究論文の positive finding は、そのまま今の対象 universe の edge ではない。cost、liquidity、capacity、data availability、execution assumptions で別途落とす必要がある。
- LLM を候補生成に使う場合、文章の説得力と検証可能性を混同しやすい。初期 MVP では LLM を generator 本体にしない方がよい。

## 次にやること

実装へ進めるなら、最初の task は `strategy_idea_candidate_set.v1` schema、Python validation、docs / tests です。データ mining logic より前に、探索履歴を保存する artifact 契約を作る。

依存追加は最初の task には含めない。統計補強が必要になった段階で、`scipy` を optional extra として検討する。

P0 の実装前には [STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md](STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md) の `Readiness Verdict` を優先し、schema / Python validation / fixture / docs に限定する。
