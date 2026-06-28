<!--
作成日: 2026-06-28_09:04 JST
更新日: 2026-06-28_09:04 JST
-->

# Perp Hypothesis Factory Implementation Plan

## チェックポイントID

CP1-CP4

## 目的

`strategy_idea_candidates` を Bitget USDT-FUTURES 前提の高速仮説生成ファネルへ拡張する。生成量、human shortlist、manual AI variation、quick validation handoff を速くするが、paper / live permission、wallet、signing、exchange write、live order は実装しない。

## 現状

- `strategy_idea_candidate_set.v1`、deterministic generator Python API、policy validation、operator review、canonical writer、shortlist export は実装済み。
- `docs/strategy_idea_candidates/README.md` は public CLI と JSONL search ledger を未実装と明記している。
- `crypto-perp-tournament-report` は actual cash 専用 guard を持ち、preview / estimate rows を拒否する。
- `strategy_idea.v1` は strict draft schema であり、candidate provenance は sidecar manifest に分離されている。

## 制約

- 外部 API、LLM API、public network、credentialed read、wallet、signing、exchange write、live order を使わない。
- `strategy_idea.v1` schema を広げない。
- raw metrics、estimate rows、AI score、AI同意を proof や採用許可と呼ばない。
- Bitget USDT-FUTURES、isolated margin、USDT margin coin、leverage modeling cap 3x を既定にする。

## 対象ファイル

- `src/sis/cli.py`
- `src/sis/commands/strategy_idea_candidates.py`
- `src/sis/strategy_idea_candidates/generator.py`
- `src/sis/strategy_idea_candidates/ledger.py`
- `src/sis/strategy_idea_candidates/ai.py`
- `src/sis/strategy_idea_candidates/policies.py`
- `docs/strategy_idea_candidates/README.md`
- `docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md`
- `docs/final-summary.md`
- `tests/strategy_idea_candidates/`
- `tests/crypto_perp/`

## 実装方針

1. `strategy-idea-candidates-build` を Typer root CLI に登録する。
2. 既存 generator に `crypto-perp-risk-taker` profile を追加し、Perp family と default parameter grids を実装する。
3. Perp 固有情報は `parameter_set` と `raw_validation_metrics` に保存し、candidate schema は壊さない。
4. `search_ledger.jsonl` sidecar を追加し、shortlisted / rejected / duplicate / cap-exceeded / AI-imported rows を全量記録する。
5. `strategy-idea-candidates-ai-packet-build` と `strategy-idea-candidates-ai-import` を追加する。packet/import は local file only とし、AI候補は常に `UNVERIFIED_CANDIDATE` にする。
6. optional export は既存 `export_shortlisted_strategy_ideas` を呼ぶ。`strategy_idea.v1` は未実行 draft のままにする。

## 実装手順

1. CP1: `.ai-work` と本計画を作成する。
2. CP2: Perp profile、ledger writer、build CLI、focused tests を実装する。
3. CP3: AI packet/import、validation、focused tests を実装する。
4. CP4: docs/final-summary を更新し、verification を実行する。

## テスト方針

- CLI help と happy path を `CliRunner` で検証する。
- Perp candidate set が schema validation と policy validation を通ることを確認する。
- funding / fee / slippage / liquidation buffer 欠落 candidate が shortlist されないことを確認する。
- ledger が rejected、duplicate、cap-exceeded、AI-imported rows を保存することを確認する。
- AI packet に secrets/account/wallet/exchange-write fields が出ないことを確認する。
- AI import が malformed JSON、missing prompt hash、spot product、funding/liquidation 欠落、live permission claim を拒否することを確認する。
- `crypto-perp-tournament-report` が preview / estimate rows を actual cash report として受け取らない既存 guard を維持する。

## 完了条件

- `strategy-idea-candidates-build`、`strategy-idea-candidates-ai-packet-build`、`strategy-idea-candidates-ai-import` が CLI help に出る。
- default Perp run が candidate set JSON/MD、operator review、search ledger JSONL、任意の export manifest を出す。
- 全 candidate は `UNVERIFIED_CANDIDATE` で、selection-adjusted metrics は未実装なら `NOT_IMPLEMENTED` と明記される。
- preview / estimate rows は actual-cash tournament report へ入らない。

## 失敗条件

- `strategy_idea.v1` schema 拡張が必要になる。
- AI import が live permission、wallet、signing、exchange write を許可する。
- successful candidates だけを保存する形になる。
- raw metrics、estimate rows、AI評価を proof として扱う必要が出る。
- public network または credentialed service が必要になる。

## 影響範囲

`strategy_idea_candidates` と local/offline CLI の追加に限定する。Crypto Perp は actual-cash guard の regression test だけを触る。既存 Trade[XYZ]、NDX Layer 2.2、paper/live order path は対象外。

## ロールバック方針

新規 `src/sis/commands/strategy_idea_candidates.py`、`src/sis/strategy_idea_candidates/ledger.py`、`src/sis/strategy_idea_candidates/ai.py`、関連 tests/docs を戻し、`src/sis/cli.py` の登録 import / register 呼び出しを削除する。既存 schema と既存 generator API は互換維持するため、ロールバック時の data migration は不要。

## 代替案

- `strategy_idea_candidate_set.v1` schema を拡張する案: 今回は採用しない。strict downstream artifact を壊しやすい。
- AI review 既存 surface に統合する案: 今回は採用しない。candidate import は candidate-specific validation と ledger 記録が必要。
- Crypto Perp estimate rows を直接 tournament report に流す案: 採用しない。actual cash guard に反する。

## 未解決事項

なし。前提は user plan の推奨値で固定する。

## 破壊的変更の有無

なし。

## ブランチ名

`ai/perp-hypothesis-factory-20260628-0904`

## 移行手順

なし。既存 artifact の書き換えは行わない。
