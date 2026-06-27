<!--
作成日: 2026-06-28_06:46 JST
更新日: 2026-06-28_06:46 JST
-->

# Actual Cash Semantic Repair Plan

## Checkpoint

I1: `outcome_before_cost_proxy` を `actual_cash_result_usd` report として通せる経路を止める。

## Purpose

`crypto-perp-tournament-report --rows tournament_rows_preview.json` を失敗させ、actual cash report には actual cash 責任を持つ JSONL / manual `TournamentEventResult` input だけを残す。

## Current State

- `crypto-perp-tournament-report` は JSON object input の `schema_version` と `known_gaps` を読み、preview rows も `TournamentEventResult` として report 化できる。
- `crypto-perp-tournament-rows-preview` の Markdown は proxy 値を `actual_cash_result_usd` 見出しで表示している。
- docs には preview rows の known gaps が report へ継承される記述がある。

## Constraints

- preview JSON schema はこの作業では変えない。
- `TournamentEventResult` はリネームしない。
- `crypto-perp-tournament-rows-v2` は estimate / cost-aware surface として維持する。
- public network、credential、exchange write、live order、dependency change、git push はしない。

## Target Files

- `src/sis/commands/crypto_perp_tournament_report.py`
- `src/sis/commands/crypto_perp_tournament_rows.py`
- `tests/crypto_perp/test_tournament.py`
- `tests/crypto_perp/test_tournament_rows.py`
- `docs/crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md`
- `docs/runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md`

## Implementation

1. `crypto-perp-tournament-report` に preview schema / known gap guard を追加する。
2. Error text に `PREVIEW_ROWS_NOT_ACTUAL_CASH` と `crypto-perp-tournament-rows-v2` を含める。
3. preview Markdown の列名を `outcome_before_cost_proxy_usd` に変える。
4. runbook / vocabulary docs に preview rows は display / dogfood only で report input 不可と明記する。

## Test Plan

- `tests/crypto_perp/test_tournament.py`: preview JSON input が exit code `2` と `PREVIEW_ROWS_NOT_ACTUAL_CASH` で落ちること。
- `tests/crypto_perp/test_tournament.py`: actual-cash JSONL report は通ること。
- `tests/crypto_perp/test_tournament_rows.py`: v2 estimate rows は `actual_cash_result_usd is None` のまま。
- `uv run pytest tests/crypto_perp/test_tournament.py tests/crypto_perp/test_tournament_rows.py`
- `uv run python scripts/check_current_docs.py`
- `git diff --check`

## Completion

- preview rows JSON / known gap input は tournament report で拒否される。
- actual-cash caller-owned JSONL input は維持される。
- preview Markdown と docs が actual cash と proxy を混同しない。

## Failure Conditions

- actual-cash JSONL input が壊れる。
- v2 estimate path の `actual_cash_result_usd is None` 境界が崩れる。
- preview JSON schema をこの作業で変更してしまう。

## Impact And Rollback

影響は CLI ingestion guard、preview Markdown 表示、docs のみ。rollback は本ブランチの該当差分を戻す。

## Critique

この修正は report schema redesign ではなく、誤入力を入口で止める局所修正に留める。preview artifact を消す案は下流 dogfood / display 用途まで壊すため採らない。known gap guard は schema_version が欠けた JSON object input でも既知の危険な proxy を止めるため必要。
