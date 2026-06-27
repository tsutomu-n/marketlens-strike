<!--
作成日: 2026-06-27_11:38 JST
更新日: 2026-06-27_11:47 JST
-->

# Strategy Idea Candidate Goal And Glossary

## 結論

現在の最終ゴールは、入力証跡つきの未検証 strategy idea candidate を生成し、探索全量と棄却理由を保存し、shortlist だけを既存 `strategy_idea.v1` draft と sidecar manifest に分けて次の gate へ渡せる candidate generation pipeline を作ることです。

ただし、次に実装するゴールは最終ゴール全体ではない。C4 `Deterministic Candidate Generator v0` は Python API と focused tests まで実装済みです。

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
| source summary | candidate set に複製する source evidence の要約 | source file 本体の再保存 |
| search ledger summary | family count、candidate count、trial count、parameter grid hash、peek/rerank count の summary | JSONL / CSV の行単位 ledger |
| search ledger rows | C4 以降で実データ行が出てから追加する JSONL / CSV row output | C3 の必須 output |
| raw validation metrics | raw と明示して保存する未補正 metric | 発見、証明、採用理由 |
| selection-adjusted metrics | selection bias 補正済み metric。未実装なら `NOT_IMPLEMENTED` | raw metric の言い換え |
| split policy | train / validation / sealed test の役割を保存する policy record | 完全な split engine の実装証明 |
| leakage policy | available-at、purge、embargo、sealed-test non-use の policy record | no-lookahead が実証済みという主張 |
| operator review surface | 人間が探索量、棄却数、selection policy、known gaps を読む surface | paper/live approval UI |
| sidecar manifest | `strategy_idea_candidate_export_manifest.v1`。candidate set path/hash と exported idea path/hash を持つ | `strategy_idea.v1` への metadata 押し込み |

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

## Final Goal

Strategy Idea Candidate Generation Pipeline の最終ゴール:

1. `strategy_input_contract_validation.v1` が `PASS` の input evidence だけを候補生成に使う。
2. 少数の fixed candidate family と finite parameter grid から `UNVERIFIED_CANDIDATE` を生成する。
3. `candidate_count_total`、`candidate_count_shortlisted`、`candidate_count_rejected`、`candidate_inventory`、`selection_policy`、`rejection_reason` を必ず保存する。
4. source path/hash/status、available-at、max observed timestamp、label window、prediction horizon、split policy、leakage policy、purge / embargo policy を candidate set に保存する。
5. raw metrics と selection-adjusted metrics status を分ける。補正済み metric がない場合は `NOT_IMPLEMENTED` とする。
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

未完了:

- C5: split engine。現状は policy record まで。
- C6: selection-adjusted metrics。現状は `NOT_IMPLEMENTED` 表示まで。
- C9: Strategy Lab / backtest bridge。
- C10: dedicated operator review surface。
- C11: public CLI / fixture E2E。

## Next Goal

C5 以降の前に残っている正確なゴール:

C4 で生成した `strategy_idea_candidate_set.v1` を前提に、split / leakage / purge / embargo policy record をより検証可能な bridge へ進め、selection-adjusted metrics は未実装なら `NOT_IMPLEMENTED` のまま誤読されないようにする。

完了条件:

- C4 generator output は `write_strategy_idea_candidate_set` で canonical JSON / Markdown にできる。
- `strategy_idea.v1` export は既存 sidecar manifest 方式を維持する。
- external API、LLM、new dependency、paper/live execution は使わない。

検証:

- `uv run pytest tests/strategy_idea_candidates`
- generator-specific focused tests
- `uv run python scripts/check_current_docs.py`
- `uv run python scripts/check_cli_catalog.py`
- `git diff --check`

## Non-Goals

- 実 market data から alpha を証明すること。
- ML / LLM / optimizer を導入すること。
- `strategy_idea.v1` schema を広げること。
- public CLI をこの段階で追加すること。
- JSONL / CSV row ledger を C4 前に追加すること。
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
