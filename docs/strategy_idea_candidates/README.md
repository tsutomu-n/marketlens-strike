<!--
作成日: 2026-06-27_11:27 JST
更新日: 2026-06-27_11:47 JST
-->

# Strategy Idea Candidates

## 結論

`strategy_idea_candidates` は、既存 `strategy_idea.v1` に渡す前の未検証候補を保存する pre-intake artifact です。

この実装で使えるのは、candidate set contract、Python validation、C4 deterministic generator Python API、C5 split / leakage policy validation API、C10 operator review Markdown surface、C11 fixture E2E、canonical JSON / Markdown writer、non-PASS input evidence の blocked artifact、shortlist の `strategy_idea.v1` draft export、sidecar manifest までです。実 market data から alpha を掘る evaluator、JSONL / CSV ledger、public CLI、paper / live permission はまだありません。

用語、family ID、最終ゴール、次の未完了 scope は [GOAL_AND_GLOSSARY.md](GOAL_AND_GLOSSARY.md) を正とします。

## 実装済み artifact

- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `schemas/strategy_idea_candidate_export_manifest.v1.schema.json`
- `src/sis/strategy_idea_candidates/`
- `tests/strategy_idea_candidates/`

## 役割

- input contract validation refs と source artifact path / hash / status / available-at / max observed timestamp を candidate set に複製する。
- `candidate_set_status` を `BUILT`、`BLOCKED_INPUT_EVIDENCE`、`INVALID_CANDIDATE_SET` に分ける。
- candidate-level `decision` を `SHORTLISTED` と `REJECTED` に分ける。
- count mismatch、selected / rejected ID mismatch、selected-only inventory、sealed test selection、paper / live / auto-promote / final flag を Python validation で落とす。
- same input から deterministic な `strategy_idea_candidate_set.json` と `strategy_idea_candidate_set.md` を出す。
- `trend_momentum`、`volatility_regime`、`liquidity_spread`、`cross_sectional_rank`、`mean_reversion` の fixed family と finite parameter grid から candidate inventory を作る。
- `parameter_grids`、stable `parameter_grid_hash`、`candidate_cap`、`cap_rejection_count`、`duplicate_rejection_count` を candidate set に保存する。
- duplicate / cap 超過 candidate を silent drop せず、`REJECTED` と `rejection_reason` つきで inventory に残す。
- split / leakage / purge / embargo policy record の最低限の時刻境界と sealed-test non-use を検査する。
- operator review Markdown に探索量、棄却理由、selection policy、known gaps、policy validation、false boundary を出す。
- fixture で input evidence から candidate set、policy validation、operator review、shortlist export、intake validation まで通す。
- shortlist だけを strict `strategy_idea.v1` draft に export し、candidate set path / hash は sidecar manifest に置く。

## 境界

- public CLI はまだありません。
- `strategy_idea.v1` schema は拡張していません。
- `strategy_idea_candidate_set.v1` は alpha proof、paper readiness、live readiness、注文許可ではありません。
- `BLOCKED_INPUT_EVIDENCE` は候補生成を止めた証跡です。候補生成の成功 artifact ではありません。
- JSONL / CSV の search ledger や metrics row output は、実 generator が行単位の探索結果を出す checkpoint まで追加しません。
- dependency は追加していません。

## Python API

```python
from sis.strategy_idea_candidates.generator import (
    CandidateFamilyId,
    StrategyIdeaCandidateGeneratorConfig,
    build_deterministic_candidate_set_from_input_evidence,
)
from sis.strategy_idea_candidates.policies import validate_split_and_leakage_policy
from sis.strategy_idea_candidates.operator_review import (
    write_strategy_idea_candidate_operator_review,
)
from sis.strategy_idea_candidates.service import (
    build_blocked_candidate_set_from_input_evidence,
    write_strategy_idea_candidate_set,
)
from sis.strategy_idea_candidates.export import export_shortlisted_strategy_ideas
```

## 検証

```bash
uv run pytest tests/strategy_idea_candidates
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
```
