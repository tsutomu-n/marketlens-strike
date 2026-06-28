<!--
作成日: 2026-06-27_11:38 JST
更新日: 2026-06-28_09:45 JST
-->

# Strategy Idea Candidate Goal And Glossary

## 結論

現在の最終ゴールは、入力証跡つきの未検証 strategy idea candidate を生成し、探索全量と棄却理由を保存し、shortlist だけを既存 `strategy_idea.v1` draft と sidecar manifest に分けて次の gate へ渡せる candidate generation pipeline を作ることです。

ただし、最終ゴール全体が完了したわけではない。deterministic generator、split / leakage policy validation API、split materialization sidecar、selection-adjusted metrics local engine、Perp local cost estimate、operator review Markdown surface、richer review packet、Strategy Authoring preflight、fixture E2E、public CLI、Bitget USDT-FUTURES 用 `crypto-perp-risk-taker` profile、JSONL search ledger、manual AI packet/import、Perp estimate bridge は focused tests まで実装済みです。現行実装が自動で通す次 gate は `strategy-intake-validate` で、Strategy Authoring / backtest / Strategy Review への full bridge と実測 Perp cost evaluator は未実装です。

## Fixed Vocabulary

| 用語 | 固定する意味 | 使ってはいけない意味 |
|---|---|---|
| Strategy Idea Candidate | `strategy_idea.v1` に export する前の未検証 strategy idea 候補 | trade candidate、paper candidate、注文候補、alpha proof |
| Strategy Idea Candidate Set | 1 回の候補生成 run の全候補 inventory と証跡 artifact | selected candidates だけの結果ファイル |
| candidate generation pipeline | input evidence から未検証候補を作り、探索全量、棄却理由、source/time/leakage/split 証跡、shortlist export を通す全体工程 | ML/LLM で良さそうな戦略を探すだけの処理 |
| deterministic generator | 入力、family、parameter grid、cap、seed なしの固定順序から同じ candidate set を再現する generator | 学習器、optimizer、LLM、外部 API、broad indicator catalog |
| Candidate Family | generator が使う候補テンプレートの小さな分類 | 戦略の有効性や market regime の証明 |
| parameter grid | family ごとの有限な parameter 組み合わせ定義 | 探索後に都合よく増やす自由記述 |
| candidate cap | 1 run で生成してよい candidate 数の上限 | 良い候補が出るまで続ける試行回数 |
| candidate inventory | `SHORTLISTED` と `REJECTED` を含む全 candidate 一覧 | shortlist だけの成功報告 |
| candidate decision | candidate-level の `SHORTLISTED` または `REJECTED` | paper / live 許可 |
| candidate status | 常に `UNVERIFIED_CANDIDATE` | ready、approved、tradable |
| rejection reason | `REJECTED` candidate を落とした理由 | 実装者向け debug note だけの任意情報 |
| duplicate rejection reason | 同一または近すぎる signal / parameter を落とした理由 | silent dedupe |
| input evidence | input contract validation refs と source path/hash/status/available-at/max observed timestamp | source path だけの参照 |
| PASS source evidence guard | `validation_status=PASS` でも source-level evidence の missing / invalid / hash mismatch / timestamp missing を候補生成前に拒否する guard | validation status 文字列だけを信用すること |
| source summary | candidate set に複製する source evidence の要約 | source file 本体の再保存 |
| search ledger summary | family count、candidate count、trial count、parameter grid hash、peek/rerank count の summary | JSONL / CSV の行単位 ledger |
| search ledger rows | C4 以降で実データ行が出てから追加する JSONL / CSV row output | C3 の必須 output |
| raw validation metrics | raw と明示して保存する未補正 metric | 発見、証明、採用理由 |
| selection-adjusted metrics | local engine による補正 metric disclosure。raw p-value がある場合だけ Benjamini-Hochberg FDR を `AVAILABLE` にし、入力不足は `NOT_ESTIMABLE` | raw metric の言い換え、alpha proof、profit proof |
| split policy | train / validation / sealed test の役割を保存する policy record | 完全な split engine の実装証明 |
| leakage policy | available-at、purge、embargo、sealed-test non-use の policy record | no-lookahead が実証済みという主張 |
| operator review surface | 人間が探索量、棄却数、selection policy、known gaps を読む surface | paper/live approval UI |
| sidecar manifest | `strategy_idea_candidate_export_manifest.v1`。candidate set path/hash と exported idea path/hash を持つ | `strategy_idea.v1` への metadata 押し込み |
| `crypto-perp-risk-taker` profile | Bitget USDT-FUTURES 前提で大量の未検証 Perp 仮説を作る高速実験 profile | live trading profile、wallet/signing profile、profit proof |
| Perp shortlist constraint | funding、fee、slippage、leverage、liquidation buffer、position loss limit、kill conditions が揃わない Perp candidate を shortlist しない guard | paper/live readiness |
| manual AI packet | candidate set と ledger summary を人間が任意AIへ渡すための local packet | repo が外部AI APIを呼ぶ処理 |
| AI import | manual AI response を検証し `source_kind=ai_generated` の未検証候補として取り込む処理 | AI候補の自動採用、AI scoreによる許可 |

## Fixed Candidate Family IDs

C4 の初期 family ID は次に固定する。追加は C4 後の別 checkpoint で扱う。

| family_id | 目的 | 初期扱い |
|---|---|---|
| `trend_momentum` | trend / momentum follow-through 仮説を作る | C4 対象 |
| `volatility_regime` | volatility expansion / compression 仮説を作る | C4 対象 |
| `liquidity_spread` | liquidity / spread 条件を使う仮説を作る | C4 対象 |
| `cross_sectional_rank` | universe 内 ranking 仮説を作る | C4 対象 |
| `mean_reversion` | overextension / reversal 仮説を作る | C4 対象 |
| `regime_filter` | 他 family の filter 条件を作る | C4 では standalone candidate にしない |
| `perp_momentum_continuation` | Perp mark/index momentum continuation 仮説 | crypto-perp-risk-taker 対象 |
| `perp_reversal_after_liquidation_move` | liquidation move 後の reversal 仮説 | crypto-perp-risk-taker 対象 |
| `perp_funding_rate_carry_filter` | funding-rate carry/filter 仮説 | crypto-perp-risk-taker 対象 |
| `perp_basis_mark_index_spread` | mark-index spread / basis 仮説 | crypto-perp-risk-taker 対象 |
| `perp_volatility_breakout_compression` | volatility compression / breakout 仮説 | crypto-perp-risk-taker 対象 |
| `perp_liquidity_spread_filter` | liquidity / spread filter 仮説 | crypto-perp-risk-taker 対象 |
| `perp_open_interest_liquidation_pressure` | open-interest / liquidation-pressure placeholder 仮説 | crypto-perp-risk-taker 対象 |

## Final Goal

Strategy Idea Candidate Generation Pipeline の最終ゴール:

1. `strategy_input_contract_validation.v1` が `PASS` の input evidence だけを候補生成に使う。
2. 少数の fixed candidate family と finite parameter grid から `UNVERIFIED_CANDIDATE` を生成する。
3. `candidate_count_total`、`candidate_count_shortlisted`、`candidate_count_rejected`、`candidate_inventory`、`selection_policy`、`rejection_reason` を必ず保存する。
4. source path/hash/status、available-at、max observed timestamp、label window、prediction horizon、split policy、leakage policy、purge / embargo policy を candidate set に保存する。
5. raw metrics と selection-adjusted metrics status を分ける。engine が走っても必要入力がない場合は `NOT_ESTIMABLE` とする。
6. operator review surface で探索量、棄却数、selection policy、known gaps を人間が読めるようにする。
7. shortlist だけを strict `strategy_idea.v1` draft に export する。
8. candidate set path/hash と exported idea path/hash は `strategy_idea_candidate_export_manifest.v1` sidecar に置く。
9. 既存 `strategy-intake-validate`、Strategy Authoring、backtest、Strategy Review へ渡す。
10. alpha proof、profit proof、paper permission、live readiness、wallet/signing/exchange write permission を一切主張しない。

## Current Goal State

完了済み:

- C1: candidate set contract。
- C2: input evidence bridge。
- C3: canonical JSON / Markdown writer。
- C8: shortlist export と sidecar manifest。
- C4: deterministic generator Python API。fixed family、finite parameter grid、candidate cap、duplicate rejection、parameter grid hash を保存する。
- C5: split / leakage policy validation API と split materialization sidecar。time window ordering、sealed-test non-use、source available-at boundary、purge / embargo policy record を検査・保存する。
- C6: selection-adjusted metrics local engine。`raw_validation_metrics` と `selection_adjusted_metrics_status` を分け、BH FDR が可能な場合だけ `AVAILABLE`、入力不足は `NOT_ESTIMABLE` とし、raw metrics を proof と呼ばない。
- C10: operator review Markdown surface と richer review packet。探索量、棄却理由、selection policy、known gaps、policy validation、false boundary、人間 review template を読めるようにする。
- C11: fixture E2E。input evidence -> candidate set -> policy validation -> operator review -> shortlist export -> intake validation を通す。
- C12: public CLI。`strategy-idea-candidates-build`、`strategy-idea-candidates-ai-packet-build`、`strategy-idea-candidates-ai-import` を追加済み。
- C13: Bitget USDT-FUTURES Perp profile。`crypto-perp-risk-taker` family/grid、Perp risk metadata、shortlist constraint を追加済み。
- C14: JSONL search ledger。全 candidate row に source kind、parameter hash、decision、rejection reason、selection-adjusted metrics status、sealed-test non-use を保存済み。
- C15: manual AI packet/import。外部APIなしで packet を作り、manual AI response を検証して `ai_generated` candidate として取り込み済み。
- C16: Perp local cost estimate。funding / fee / slippage / liquidation buffer を local parameter estimate として保存済み。
- C17: Perp estimate bridge。shortlisted Perp candidate と `crypto_perp_outcome.v1` から candidate-scoped `crypto_perp_tournament_rows.v2` estimate を生成済み。
- C18: Strategy Authoring preflight。`strategy_idea.v1` export availability と authoring/backtest/paper/live readiness gap を保存済み。

未完了:

- C5 full statistical split engine。現状は validation と materialization sidecar まで。
- C9: Strategy Lab / backtest bridge。
- Perp funding / fee / slippage / liquidation の実測 evaluator。現状は candidate metadata と local estimate boundary まで。

## Next Goal

C5 以降の前に残っている正確なゴール:

C4/C5/C10/C11/C16/C17/C18 の pipeline evidence を前提に、selection-adjusted metrics は入力不足なら `NOT_ESTIMABLE` のまま誤読されないようにする。C9 Strategy Lab / backtest full bridge は、`strategy_idea.v1` draft を Strategy Authoring spec / backtest pack へ変換する明示 contract ができるまで未実装として扱う。

完了条件:

- C4 generator output は `write_strategy_idea_candidate_set` で canonical JSON / Markdown にできる。
- `strategy_idea.v1` export は既存 sidecar manifest 方式を維持する。
- external API、LLM API、new dependency、paper/live execution は使わない。

検証:

- `uv run pytest tests/strategy_idea_candidates`
- generator-specific focused tests
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`

## Non-Goals

- 実 market data から alpha を証明すること。
- ML / LLM API / optimizer を導入すること。
- `strategy_idea.v1` schema を広げること。
- AI score、AI同意、複数AI一致を採用許可にすること。
- Bitget spot、spot margin、wallet、signing、exchange write、live order を扱うこと。
- paper / live / order preview / wallet / signing / exchange write を許可すること。

## Stop Conditions

- input validation が `PASS` ではない。
- source hash、available-at、max observed timestamp、label window、prediction horizon が candidate set に残せない。
- selected-only artifact になり、rejected inventory が消える。
- duplicate rejection が silent drop になる。
- raw metric を発見、証明、採用理由として扱う必要が出る。
- `strategy_idea.v1` に candidate set provenance を入れないと成立しない設計になる。
- 新依存や外部 API がないと C4 を通せない。

## Draft Goal Command

```text
/goal Implement C4 Deterministic Candidate Generator v0 for docs/strategy_idea_candidates/GOAL_AND_GLOSSARY.md: given PASS input evidence and generator config, generate reproducible strategy_idea_candidate_set.v1 artifacts from the fixed family IDs and finite parameter grids, preserving full candidate inventory, rejection reasons, parameter_grid_hash, candidate cap behavior, duplicate rejection evidence, source/time/leakage/split policy records, and false paper/live boundaries. Verify with focused tests under tests/strategy_idea_candidates, current-docs, CLI catalog, and git diff check. Do not add dependencies, public CLI, external API calls, LLM generation, strategy_idea.v1 schema changes, paper/live/order/wallet/signing/exchange-write behavior, or alpha/profit claims. Work checkpoint by checkpoint and stop with evidence if the generator cannot preserve these artifacts without scope expansion.
```
