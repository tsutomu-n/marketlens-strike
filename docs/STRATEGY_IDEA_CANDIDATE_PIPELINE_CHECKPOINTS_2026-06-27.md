<!--
作成日: 2026-06-27_10:59 JST
更新日: 2026-06-27_11:47 JST
-->

# Strategy Idea Candidate Pipeline Checkpoints 2026-06-27

## 結論

最終ゴールは candidate generation pipeline です。ただし、最終ゴールまでを一気に実装しない。実装は checkpoint ごとに進め、各 checkpoint は「次へ進めてよい証拠」と「止める条件」を持つ。

この pipeline が最終的に満たす状態:

1. 入力データと input contract validation を受け取る。
2. 未検証の `StrategyIdeaCandidate` を生成する。
3. 探索した候補、棄却した候補、shortlist した候補をすべて保存する。
4. source hash、available-at、label window、prediction horizon、purge / embargo policy、split policy を artifact に残す。
5. shortlist だけを既存 `strategy_idea.v1` draft に export する。
6. 既存 `strategy-intake-validate`、Strategy Authoring、backtest、Strategy Review に渡す。
7. どの出力も alpha proof、paper permission、live readiness を主張しない。

## 正本

この checkpoint plan は次の現物に基づく。

- `schemas/strategy_input_contract.v1.schema.json`
- `schemas/strategy_input_contract_validation.v1.schema.json`
- `schemas/strategy_idea.v1.schema.json`
- `schemas/strategy_intake_decision.v1.schema.json`
- `schemas/strategy_optimizer_trial_ledger.v1.schema.json`
- `src/sis/strategy_inputs/validation.py`
- `src/sis/commands/strategy_inputs.py`
- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `schemas/strategy_idea_candidate_export_manifest.v1.schema.json`
- `src/sis/strategy_idea_candidates/`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`
- `src/sis/strategy_model_loop/models.py`
- `docs/STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md`
- `docs/STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md`
- `docs/STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md`

## 実装状況

2026-06-27_11:47 JST 時点で、fixture-level の C1 / C2 / C3 / C4 / C8 slice は実装済みです。

- C1: `strategy_idea_candidate_set.v1` JSON Schema、Pydantic models、Python validation、fixture tests。
- C2: input contract validation refs と source path / hash / status / available-at / max observed timestamp summary。
- C3: canonical JSON と Markdown writer。JSONL / CSV は generator が実データ行を出す checkpoint まで未実装。
- C4: deterministic generator Python API。fixed family、finite parameter grid、candidate cap、duplicate rejection、parameter grid hash を保存する。
- C8: shortlist の strict `strategy_idea.v1` draft export と `strategy_idea_candidate_export_manifest.v1` sidecar。`strategy_idea.v1` schema は拡張していない。

未実装:

- C5 split engine。現時点では policy record の保存まで。
- C6 selection-adjusted metrics。未実装時は `NOT_IMPLEMENTED`。
- C9 Strategy Lab / backtest bridge。
- C10 専用 operator review surface。現時点では candidate set Markdown で読む。
- C11 public CLI E2E。

## Checkpoints

| CP | checkpoint | 目的 | 完了条件 | 止める条件 |
|---|---|---|---|---|
| C0 | docs baseline | 現在の調査・追補・pipeline plan を current docs に残す | current-docs check / CLI catalog / diff check が通る | docs が「実装済み」と誤読される |
| C1 | P0A artifact contract | `strategy_idea_candidate_set.v1` を定義する | JSON Schema、Python validation、fixture tests、docs がそろう | JSON Schema だけで cross-field invariant を済ませようとする |
| C2 | input evidence bridge | input contract validation と source evidence を候補 artifact の前提にする | required source hash、available-at、timestamp、validation status を candidate set に参照保存する | source hash / available-at / label window なしで候補を出す |
| C3 | P0B artifact writer | 候補生成前に artifact 出力器を作る | canonical JSON / Markdown が deterministic に出る | selected-only output、rejection inventory 欠落 |
| C4 | P1 deterministic generator | 少数 family から再現可能な候補を作る | family、parameter grid、candidate cap、rejection reason が保存される | LLM / ML / indicator catalog で先に探索を広げる |
| C5 | split and leakage policy | train / validation / sealed test と leakage policy を固定する | sealed test を selection に使わない。purge / embargo policy を保存する | `TimeSeriesSplit(gap=...)` だけで leakage 対策完了扱い |
| C6 | raw metric disclosure | raw metric を raw として記録する | raw metrics と selection-adjusted status が分かれる | raw Sharpe / return を発見や証明と呼ぶ |
| C7 | optional defensive stats | 必要になった時だけ統計補強する | `scipy` など optional extra は artifact / ledger 後に採用判断 | stats dependency を先に入れて探索を増やす |
| C8 | intake export | shortlist だけを `strategy_idea.v1` draft に export する | export draft が `strategy-intake-validate` を通る | bulk candidates を直接 `strategy_idea.v1` にする |
| C9 | Strategy Lab / backtest bridge | 既存 review / backtest chain に探索証跡を渡す | search ledger path / hash / summary が review/backtest 側で見える | backtest pass を paper/live permission と扱う |
| C10 | operator review surface | 人間が探索量と棄却理由を読める | review packet に候補数、棄却数、selection policy、known gaps が出る | best candidate だけを見せる |
| C11 | fixture E2E | pipeline を fixture で一通り通す | input validation -> candidate set -> shortlist -> export -> intake validation の fixture E2E が通る | 実データや外部 API がないと検証できない |
| C12 | ML / LLM assist | 足場ができた後に補助へ進む | feature importance、stability、leakage checks、ledger がある | narrative を evidence と扱う |

## 実装順

最短の安全ルート:

1. C0: docs baseline を確定する。
2. C1: P0A artifact contract を作る。
3. C2: input evidence bridge を作る。
4. C3: artifact writer を作る。
5. C4: deterministic generator Python API を作る。
6. C5: split and leakage policy を作る。
7. C8: intake export を作る。
8. C10: operator review surface を作る。
9. C9: Strategy Lab / backtest bridge を作る。
10. C11: fixture E2E を通す。

C4 は Python API と focused tests まで実装済み。C6 は C5 の前後で扱う。C7 と C12 は後回しでよい。C10 は C8 の直後、C9 の前に置く。

## Checkpoint Details

### C0: docs baseline

対象:

- `docs/STRATEGY_IDEA_GENERATION_PRE_IMPLEMENTATION_AUDIT_2026-06-27.md`
- `docs/STRATEGY_IDEA_GENERATION_RESEARCH_2026-06-27.md`
- `docs/STRATEGY_IDEA_GENERATION_DEPENDENCY_RESEARCH_2026-06-27.md`
- `docs/STRATEGY_IDEA_CANDIDATE_PIPELINE_CHECKPOINTS_2026-06-27.md`
- `README.md`
- `docs/CURRENT_STATE.md`
- `scripts/check_current_docs.py`

完了条件:

- current-docs checker にこの doc が入る。
- `README.md` と `docs/CURRENT_STATE.md` から読める。
- docs が未実装を実装済みと書かない。
- `uv run python scripts/check_current_docs.py` が通る。
- `uv run python scripts/check_cli_catalog.py` が通る。
- `git diff --check` が通る。

### C1: P0A artifact contract

対象:

- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `src/sis/strategy_idea_candidates/`
- `tests/strategy_idea_candidates/`
- `docs/strategy_idea_candidates/README.md`

必須 field:

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

Python validation で落とすもの:

- `candidate_count_total` と actual inventory count の不一致。
- `candidate_count_shortlisted + candidate_count_rejected` と total の不一致。
- selected / rejected ID の重複。
- selected / rejected ID が `candidate_inventory` に存在しない。
- `candidate_inventory` が selected だけの success-only artifact。
- `success_only_reporting=true`。
- `uses_sealed_test_for_selection=true`。
- source hash、label window、prediction horizon、available-at policy、purge / embargo policy の欠落。
- paper / live / auto-promote / final-strategy 系 flag が true。

### C2: input evidence bridge

目的:

`strategy_input_contract_validation.v1` を候補生成の前提にする。候補生成器が入力データの正体、hash、時刻境界を知らないまま候補を出さないようにする。

完了条件:

- candidate set が `input_contract_validation_refs` を必須にする。
- source artifact は path と `sha256:<hex>` を持つ。
- `available_at` と `max_observed_timestamp` を保存する。
- source validation status が `PASS` 以外なら、candidate set status を `BLOCKED_INPUT_EVIDENCE` または同等にする。
- missing required source で候補生成しない。

### C3: P0B artifact writer

目的:

生成ロジックより先に、保存形式と writer を固定する。

期待 artifact:

- `strategy_idea_candidate_set.json`
- `strategy_idea_candidate_set.md`

`candidate_search_ledger.jsonl`、`candidate_metrics.csv`、`candidate_rejections.csv` は C4 generator が実データ行を出してから追加する。

完了条件:

- 同じ input と config から同じ artifact path / ids / hashes を再現できる。
- selected candidate だけを出す mode がない。
- rejected candidates が空でも、空である理由を保存する。
- dependency versions と generator version を保存する。
- public CLI は任意。追加するなら help / docs / tests と同時に足す。

### C4: P1 deterministic generator

初期 family:

- trend / momentum
- volatility expansion / compression
- liquidity / spread
- cross-sectional rank
- mean reversion
- regime filter metadata only; standalone candidate にはしない

完了条件:

- family ごとに parameter grid が artifact に残る。
- candidate cap がある。
- raw metric は raw と明記する。
- duplicate / near-duplicate candidate の rejection reason が残る。
- `regime_filter` は standalone candidate にしない。
- LLM は使わない。
- broad TA indicator library は使わない。

### C5: split and leakage policy

完了条件:

- train / validation / sealed test の役割が artifact で分かれる。
- sealed test を selection に使わない。
- `validation_peek_count`、`selection_iterations`、`rerank_count` を保存する。
- `prediction_horizon`、`label_window`、`purge_policy`、`embargo_policy` を保存する。
- `TimeSeriesSplit` を使う場合でも、repo 側 policy として purge / embargo を別に記録する。

### C6: raw metric disclosure

完了条件:

- `raw_validation_metrics` と `selection_adjusted_metrics_status` を分ける。
- selection-adjusted metrics が未実装なら `NOT_IMPLEMENTED` と出す。
- report で raw metric を「発見」「証明」「採用」と呼ばない。

### C7: optional defensive stats

条件:

- C1-C6 が済むまで着手しない。
- 最初の候補は `scipy` optional extra。
- `statsmodels` / `arch` は必要が明確になってから。
- `pyproject.toml` / `uv.lock` 変更時は resolver、import、targeted tests を実行する。

### C8: intake export

完了条件:

- shortlist だけを `strategy_idea.v1` draft に export する。
- `authoring_intent.auto_generate_spec=false` を維持する。
- export draft が `strategy-intake-validate` を通る。
- export は paper / live permission を出さない。
- candidate set path / hash は `strategy_idea_candidate_export_manifest.v1` sidecar から辿れる。
- `strategy_idea.v1` schema は探索 metadata 用に拡張しない。

### C9: Strategy Lab / backtest bridge

完了条件:

- review / backtest artifact が candidate search ledger path / hash / summary を参照する。
- backtest result だけでなく、探索数と棄却候補数が見える。
- existing `TradeCandidate` / `PaperCandidatePack` と pre-intake candidate を混同しない。

### C10: operator review surface

完了条件:

- 人間向け review に `candidate_count_total`、`candidate_count_rejected`、`selection_policy`、`known_gaps` が出る。
- best candidate だけでなく、探索範囲と落とした理由が読める。
- operator decision が paper/live permission と混ざらない。

### C11: fixture E2E

完了条件:

- synthetic fixture で次が通る。
  - input contract validation
  - candidate set build
  - shortlist
  - export to `strategy_idea.v1`
  - `strategy-intake-validate`
- 外部 API、実 market data、credentials がなくても検証できる。
- CI / local check で再実行できる。

### C12: ML / LLM assist

条件:

- C1-C11 が通ってから検討する。
- ML は feature importance、stability、leakage checks、search ledger がある場合だけ。
- LLM は hypothesis wording / explanation 補助に限定する。
- LLM が作った narrative を evidence と扱わない。

## 重要な修正点

前回 checkpoint 表からの修正:

- input contract / source evidence bridge は generator 後では遅い。C2 として前に出す。
- P0A は schema だけではない。Python validation を含める。
- pipeline 完成は「ML/LLM 補助」ではない。fixture E2E が先。
- defensive stats は pipeline の品質を上げるが、最短ルートの必須ではない。
- C3 の初期 writer は canonical JSON / Markdown に限定する。JSONL / CSV は実 generator の row output ができてから追加する。
- C8 では `strategy_idea.v1` に candidate provenance を押し込まない。sidecar manifest に分ける。
- C10 operator review surface は C8 の直後に置く。人間が探索量、棄却数、selection policy、known gaps を見てから Strategy Lab / backtest bridge に進める。

## Scope 外

- live order。
- wallet / signing / exchange write。
- paper execution permission。
- production credentialed smoke。
- `mlfinlab`、`mlfinpy`、`pandas-ta`、`ta`、`vectorbt` の初期採用。
- `Optuna` / `LightGBM` / `XGBoost` / `tsfresh` の初期採用。
- DSR / PBO / White Reality Check / SPA の P0 実装。

## Readiness

- C0: ready
- C1: ready with assumptions
- C2: ready after C1 field shape is fixed
- C3: ready after C1-C2
- C4: implemented as Python API with focused tests
- C5: ready after C4
- C6: ready after C4-C5
- C7: not now
- C8: ready after C1-C6
- C9: ready after C8-C10
- C10: ready after C8
- C11: ready after C8-C10
- C12: not now

## 残リスク

- C1 の field name は実装時に tests と一緒に固定する必要がある。
- C2 で既存 `strategy_input_contract_validation.v1` を参照するだけで足りるか、candidate set 側に source summary を複製するかは実装時に決める必要がある。推奨は path/hash/status の summary 複製です。
- C5 の purge / embargo は最初は policy record に留め、実 split engine は別 checkpoint にしてもよい。
- C8 で `strategy_idea.v1` に探索 metadata を押し込みすぎると schema が肥大化する。sidecar manifest に candidate set path/hash を置く。
- C11 は fixture E2E であり、実データの alpha proof ではない。
