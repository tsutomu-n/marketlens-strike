<!--
作成日: 2026-06-27_11:27 JST
更新日: 2026-06-28_10:32 JST
-->

# Strategy Idea Candidates

## 結論

`strategy_idea_candidates` は、既存 `strategy_idea.v1` に渡す前の未検証候補を保存する pre-intake artifact です。

この実装で使えるのは、candidate set contract、Python validation、deterministic generator Python API、Bitget USDT-FUTURES 前提の `crypto-perp-risk-taker` profile、split / leakage policy validation API、split materialization sidecar、Perp shortlist constraint validation、selection-adjusted metrics local engine、Perp cost estimate sidecar、operator review Markdown surface、richer review packet、Strategy Authoring preflight、fixture E2E、canonical JSON / Markdown writer、JSONL search ledger、public CLI、manual AI packet/import、non-PASS input evidence の blocked artifact、shortlist の `strategy_idea.v1` draft export、sidecar manifest、outcome-backed Perp estimate bridge、C9 v0 Prep Watchdeck authoring bridge までです。実 market data から alpha を掘る evaluator、実測 Perp cost evaluator、paper / live permission はまだありません。

現行実装が自動で通す次 gate は `strategy-intake-validate` です。Strategy Authoring preflight は readiness gap を列挙するだけです。C9 v0 Prep Watchdeck authoring bridge は、対応 family に限って candidate-scoped spec / suite / bundle / backtest pack を生成し、変換不能・source 不足・pack 失敗は machine-readable blocker を返す fail-closed 経路です。全候補の backtest 成功保証ではありません。

用語、family ID、最終ゴール、次の未完了 scope、`Strategy Lab / backtest full bridge` の正確な定義は [GOAL_AND_GLOSSARY.md](GOAL_AND_GLOSSARY.md) を正とします。

## 実装済み artifact

- `schemas/strategy_idea_candidate_set.v1.schema.json`
- `schemas/strategy_idea_candidate_export_manifest.v1.schema.json`
- `schemas/strategy_idea_candidate_authoring_bridge.v1.schema.json`
- `src/sis/strategy_idea_candidates/`
- `src/sis/commands/strategy_idea_candidates.py`
- `tests/strategy_idea_candidates/`

## 役割

- input contract validation refs と source artifact path / hash / status / available-at / max observed timestamp を candidate set に複製する。
- `validation_status=PASS` でも source-level evidence が missing / invalid / hash mismatch / timestamp missing の場合は候補生成を止める。
- `candidate_set_status` を `BUILT`、`BLOCKED_INPUT_EVIDENCE`、`INVALID_CANDIDATE_SET` に分ける。
- candidate-level `decision` を `SHORTLISTED` と `REJECTED` に分ける。
- count mismatch、selected / rejected ID mismatch、selected-only inventory、sealed test selection、paper / live / auto-promote / final flag を Python validation で落とす。
- same input から deterministic な `strategy_idea_candidate_set.json` と `strategy_idea_candidate_set.md` を出す。
- `trend_momentum`、`volatility_regime`、`liquidity_spread`、`cross_sectional_rank`、`mean_reversion` の fixed family と finite parameter grid から candidate inventory を作る。
- `parameter_grids`、stable `parameter_grid_hash`、`candidate_cap`、`cap_rejection_count`、`duplicate_rejection_count` を candidate set に保存する。
- duplicate / cap 超過 candidate を silent drop せず、`REJECTED` と `rejection_reason` つきで inventory に残す。
- split / leakage / purge / embargo policy record の最低限の時刻境界と sealed-test non-use を検査する。
- reports 上で `raw_validation_metrics` と `selection_adjusted_metrics_status` を分け、raw metrics を proof と呼ばない。
- operator review Markdown に探索量、棄却理由、selection policy、known gaps、policy validation、false boundary を出す。
- fixture で input evidence から candidate set、policy validation、operator review、shortlist export、intake validation まで通す。
- shortlist だけを strict `strategy_idea.v1` draft に export し、candidate set path / hash は sidecar manifest に置く。
- `strategy-idea-candidates-build` で candidate set、operator review、search ledger JSONL、任意の shortlist export manifest を作る。
- `strategy-idea-candidates-build` は `selection_metrics.json`、`perp_cost_estimates.json`、`split_materialization.json`、`review/strategy_idea_candidate_review_packet.json`、`authoring_preflight.json` も出力する。
- `crypto-perp-risk-taker` profile では Bitget `USDT-FUTURES`、isolated margin、USDT margin coin、leverage modeling cap 3x を既定にする。
- Perp shortlisted candidate は `side_bias`、funding assumption、fee model ref、slippage model ref、liquidation buffer、max notional、max daily loss、kill conditions を `parameter_set` に持つ必要がある。
- selection-adjusted metrics local engine は raw p-value がある場合だけ Benjamini-Hochberg FDR を `AVAILABLE` にし、DSR / PBO / White Reality Check は必要入力が無い場合 `NOT_ESTIMABLE` と明記する。
- Perp cost estimate は funding / fee / slippage / liquidation buffer を local parameter estimate として保存する。actual cash result ではありません。
- `strategy-idea-candidates-perp-estimate` は shortlisted Perp candidate と `crypto_perp_outcome.v1` から candidate-scoped `crypto_perp_tournament_rows.v2` estimate を作る。
- `strategy-idea-candidates-authoring-bridge` は shortlisted Perp candidate を `/home/tn/projects/prep-watchdeck` の local read-only source から candidate-scoped Strategy Authoring spec / suite / bundle / standard backtest pack へ変換する。
- `strategy-idea-candidates-ai-packet-build` は外部 API を呼ばず、candidate set / ledger summary / Perp constraints を manual AI 用 packet にする。
- `strategy-idea-candidates-ai-import` は manual AI response を検証し、AI候補を `source_kind=ai_generated`、`UNVERIFIED_CANDIDATE`、human shortlist required として取り込む。

## 境界

- `strategy_idea.v1` schema は拡張していません。
- `strategy_idea_candidate_set.v1` は alpha proof、paper readiness、live readiness、注文許可ではありません。
- `BLOCKED_INPUT_EVIDENCE` は候補生成を止めた証跡です。候補生成の成功 artifact ではありません。
- JSONL search ledger は candidate generation の全候補 row を保存する sidecar です。raw metric や AI score を proof として扱いません。
- selection-adjusted metrics sidecar は local disclosure engine です。`AVAILABLE` は FDR 計算が可能だったことだけを示し、alpha proof や profit proof ではありません。
- `perp_cost_estimates.json` と Perp estimate bridge は estimate artifact です。`crypto-perp-tournament-report` の actual-cash input ではありません。
- C9 v0 `Strategy Lab / backtest bridge` は `perp_momentum_continuation` と `perp_funding_rate_carry_filter` だけを対応します。candidate-scoped spec / suite / bundle / output を使い、default TradeXYZ / QQQ example backtest を候補 proof として流用しません。Bitget Perp の local feature / quote / cost-estimate source は `/home/tn/projects/prep-watchdeck` を使いますが、同 repo は板厚・実測 slippage evaluator ではありません。
- C9 v0 bridge の `venue_cost_matrix.csv` は `ESTIMATE_ONLY` です。`quotes.parquet` の bid/ask は service DB に無い場合 `spread_bps_estimate` から推定し、source manifest に残します。
- AI packet/import は local/manual だけです。repo 内から AI / LLM API へ送信しません。
- `crypto-perp-risk-taker` は quick validation estimate までの候補生成 profile であり、wallet、signing、exchange write、live order を許可しません。
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

## CLI

```bash
uv run sis strategy-idea-candidates-build \
  --contract data/strategy_inputs/btc_perp/strategy_input_contract.json \
  --validation data/strategy_inputs/btc_perp/strategy_input_contract_validation.json \
  --profile crypto-perp-risk-taker \
  --candidate-cap 250 \
  --shortlist-count 10 \
  --out data/strategy_idea_candidates/btc-perp

uv run sis strategy-idea-candidates-ai-packet-build \
  --candidate-set data/strategy_idea_candidates/btc-perp/strategy_idea_candidate_set.json \
  --ledger data/strategy_idea_candidates/btc-perp/search_ledger.jsonl \
  --out data/strategy_idea_candidates/btc-perp/ai_packet

uv run sis strategy-idea-candidates-ai-import \
  --packet data/strategy_idea_candidates/btc-perp/ai_packet/ai_candidate_packet.json \
  --response data/strategy_idea_candidates/btc-perp/manual_ai_response.json \
  --out data/strategy_idea_candidates/btc-perp/ai_import

uv run sis strategy-idea-candidates-perp-estimate \
  --candidate-set data/strategy_idea_candidates/btc-perp/strategy_idea_candidate_set.json \
  --outcome data/crypto_perp/outcomes/event-1.json \
  --out data/strategy_idea_candidates/btc-perp/perp_estimate_bridge

uv run sis strategy-idea-candidates-authoring-bridge \
  --candidate-set data/strategy_idea_candidates/btc-perp/strategy_idea_candidate_set.json \
  --export-manifest data/strategy_idea_candidates/btc-perp/exported_strategy_ideas/strategy_idea_candidate_export_manifest.json \
  --ledger data/strategy_idea_candidates/btc-perp/search_ledger.jsonl \
  --prep-watchdeck-root /home/tn/projects/prep-watchdeck \
  --out data/strategy_idea_candidates/btc-perp/authoring_bridge
```

## 検証

```bash
uv run pytest tests/strategy_idea_candidates
uv run python scripts/check_current_docs.py
uv run python scripts/check_cli_catalog.py
git diff --check
```
