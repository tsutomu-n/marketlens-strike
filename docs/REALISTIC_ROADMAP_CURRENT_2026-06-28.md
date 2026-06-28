<!--
作成日: 2026-06-28_14:56 JST
更新日: 2026-06-28_15:01 JST
-->

# Realistic Roadmap Current

## 結論

次にやるべきことは、追加機能を増やすことではなく、C9 bridge（shortlist 済みの戦略アイデア候補を、この repo の Strategy Authoring spec / backtest pack まで候補別に接続する変換経路）修正後に実データで再実行し、evidence quality（候補判断に使う証拠の実データ性、欠損の明示、actual cash との距離の明確さ）を上げることです。

backtest、Strategy Review、Workbench は判断材料です。profit proof、paper execution permission、live readiness、wallet readiness、signing readiness、exchange write readiness ではありません。

この文書は standalone roadmap です。既存入口 docs からリンクしません。品質確認だけは `scripts/check_current_docs.py` の対象に入れます。

## 正本

この roadmap は次を正本として読みます。

- [CURRENT_STATE.md](CURRENT_STATE.md)
- [IMPLEMENTED_SURFACES.md](IMPLEMENTED_SURFACES.md)
- [NEXT_DIRECTION_CURRENT.md](NEXT_DIRECTION_CURRENT.md)
- [strategy_idea_candidates/README.md](strategy_idea_candidates/README.md)
- [strategy_idea_candidates/GOAL_AND_GLOSSARY.md](strategy_idea_candidates/GOAL_AND_GLOSSARY.md)
- [runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md](runbooks/CRYPTO_PERP_TRUTH_CYCLE_RUNBOOK.md)
- [crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md](crypto_perp/PROFIT_READINESS_ACCEPTANCE_VOCABULARY.md)
- `uv run sis --help`

実装の正本は `src/`、`tests/`、`schemas/`、`configs/`、`scripts/`、lockfile、CI、CLI help です。`data/` は runtime / generated state であり、fresh checkout では再生成対象です。

`./.ai_memory/HANDOFF.md` は restart artifact です。現 checkout では stale の可能性があるため、この roadmap の正本にしません。

固定 pass count、固定 current-doc count、古い artifact snapshot はこの文書に置きません。必要な時にコマンドを再実行します。

## Lane 1: Strategy Idea / C9 Bridge

最短の次実務は、C9 bridge（shortlist 済み候補を Strategy Authoring と標準 backtest pack に候補別 artifact として渡す変換経路）の実データ再実行です。

1. `strategy-idea-candidates-bitget-source-refresh` で C9 bridge 互換 source root（bridge が読める形式に整えた Bitget public market data の local directory）を作る。
2. `strategy-idea-candidates-authoring-bridge` を相対 `--out` で再実行する。
3. bridge manifest（候補ごとに入力、出力、生成 artifact、停止理由をつなぐ一覧）の `BRIDGED`（候補別 spec / suite / bundle / backtest pack validation まで通った状態）と `BLOCKED_*`（変換不能、source 不足、validation 失敗などで止めた状態）を候補単位で整理する。
4. `BRIDGED` 候補だけを Strategy Review / Workbench（人間レビューや静的 HTML 表示で候補の証拠を読むための surface）に流す。
5. `BLOCKED_*` 候補は手動で成功扱いにしない。

C9 v0（C9 bridge の最初の限定版。全候補ではなく、対応 family だけを安全に変換し、変換不能なら blocker として止める実装）の対応 family は `perp_momentum_continuation` と `perp_funding_rate_carry_filter` だけです。その他の Perp family（この repo の候補 generator が使う戦略テンプレート分類）は v0 対応外として止めます。

`venue_cost_matrix.csv` は `ESTIMATE_ONLY` です。実測 slippage、実 fill、actual cash、live measurement の証拠として読んではいけません。

```bash
SIS_ALLOW_PUBLIC_NETWORK=1 uv run sis strategy-idea-candidates-bitget-source-refresh \
  --symbol BTCUSDT \
  --product-type USDT-FUTURES \
  --granularity 5m \
  --limit 200 \
  --out data/strategy_idea_candidates/btc-perp/bitget_public_source

uv run sis strategy-idea-candidates-authoring-bridge \
  --candidate-set data/strategy_idea_candidates/btc-perp/strategy_idea_candidate_set.json \
  --export-manifest data/strategy_idea_candidates/btc-perp/exported_strategy_ideas/strategy_idea_candidate_export_manifest.json \
  --ledger data/strategy_idea_candidates/btc-perp/search_ledger.jsonl \
  --prep-watchdeck-root data/strategy_idea_candidates/btc-perp/bitget_public_source/source_root \
  --out data/strategy_idea_candidates/btc-perp/authoring_bridge
```

public network は明示承認と opt-in がある時だけ使います。承認がない場合は local source root の存在確認、bridge help、fixture / existing artifact の検査までに止めます。

## Lane 2: Crypto Perp Profit Evidence

利益判断の次段は、同じ event set で `REVERSAL_SHORT`、`CONTINUATION_LONG`、`NO_TRADE` を比較することです。

`NO_TRADE` は失敗ではありません。正式 action として比較し、`NO_TRADE` が leader の時は無理に trade action を採用しません。

`crypto-perp-tournament-rows-preview` は before-cost proxy です。actual cash report の入力ではありません。

`crypto-perp-tournament-rows-v2` は cost-adjusted estimate / stress estimate です。fee、funding、slippage、operator time の見積を含められますが、実現損益ではありません。

actual cash report に進むには、cash ledger または live measurement artifact が必要です。欠損 source は 0 埋めせず、`INCONCLUSIVE_DATA` を正式な停止結果として残します。

```bash
uv run sis crypto-perp-source-availability --help
uv run sis crypto-perp-replay-slice --help
uv run sis crypto-perp-feature-pack --help
uv run sis crypto-perp-edge-score --help
uv run sis crypto-perp-tournament-rows-v2 --help
uv run sis crypto-perp-bias-guard --help
uv run sis crypto-perp-tournament-report --help
uv run sis crypto-perp-tournament-gate --help
```

actual cash path へ進める時だけ、cash ledger 系 surface を使います。

```bash
uv run sis crypto-perp-cash-ledger --help
uv run sis crypto-perp-actual-cash-rows-build --help
uv run sis crypto-perp-actual-cash-report-gate --help
```

## Lane 3: Strategy Ops / Paper Observation

Strategy Review の `READY_FOR_HUMAN_REVIEW` は、人間レビューの準備完了です。paper 実行許可ではありません。

normal paper observation には、新しい trading day を含む evidence が必要です。同日 artifact の再実行だけでは normal observation の日数は増えません。

smoke pass と normal threshold は分けて読みます。smoke は導通確認であり、normal paper observation pass ではありません。

Drift Review、Learning、Revision Request は authoring 改善の材料です。Strategy Authoring YAML を自動編集する許可ではありません。

```bash
uv run sis strategy-review-build --help
uv run sis strategy-review-record --help
uv run sis strategy-paper-observation-status --help
uv run sis strategy-drift-review --help
uv run sis strategy-learning-ledger-update --help
uv run sis strategy-revision-request-build --help
uv run sis strategy-revision-request-review --help
```

## Lane 4: NDX / Venue-Neutral Research

backtest-first / venue-neutral を維持します。

NDX Layer gates は local research / paper-observation gate です。alpha、wallet、exchange write、live readiness を証明しません。

Trade[XYZ] は実装済み read-only venue context ですが、default product axis に戻しません。Trade[XYZ] 前提の collector、readiness claim、order path work は、ユーザーが明示的に Trade[XYZ] scope を指定した時だけ扱います。

```bash
uv run sis research-layer22-validate --root configs/research_layer_2_2/ndx
uv run sis research-layer22-export --root configs/research_layer_2_2/ndx --out data/research/ndx
uv run sis research-layer22-review-pack --root configs/research_layer_2_2/ndx --out data/research/ndx/review
uv run sis research-layer22-review-import \
  --pack data/research/ndx/review/llm_review_input.json \
  --result data/research/ndx/review/llm_review_result.json
uv run sis research-layer22-exit-gate \
  --root configs/research_layer_2_2/ndx \
  --pack data/research/ndx/review/llm_review_input.json \
  --review data/research/ndx/review/normalized_review.json \
  --out data/research/ndx/review
```

## Lane 5: Human Approval / Tiny Live

`crypto-perp-tiny-live-shadow` と tiny-live review packet は、実発注なしの readiness artifact です。

tiny live measurement は、次が揃うまで roadmap の実行対象にしません。

- 別の明示承認
- isolated margin
- withdrawal disabled API key
- IP restriction
- max notional 25 USD
- flat reconciliation

production live trading、wallet、signing、exchange write、自動売買は通常の次手に入れません。

```bash
uv run sis crypto-perp-tiny-live-shadow --help
uv run sis crypto-perp-tiny-live-review-packet --help
uv run sis crypto-perp-tiny-live-shadow-readiness --help
```

## Stop Conditions

- C9 bridge（shortlist 済み候補を Strategy Authoring / backtest artifact に変換する経路）が `BLOCKED_*`（変換不能や source 不足などの明示的な停止結果）を返した候補を、手動で `BRIDGED`（候補別 backtest pack validation まで通った状態）扱いにしない。
- backtest validation `PASS` を profit proof と読まない。
- proxy / estimate rows を actual cash report に食わせない。
- source availability が不足している event を 0 埋めで進めない。
- `NO_TRADE` が leader の時に、無理に trade action を採用しない。
- event 数不足、profit concentration、largest loss、operator time が悪い場合は、追加実装より候補停止を優先する。
- explicit approval なしに public network、credentialed read、exchange write、live order、tiny-live measurement を実行しない。
- `READ_ONLY_GO`、`READY_FOR_HUMAN_REVIEW`、backtest pack validation `PASS` を、paper / live / wallet / signing / exchange-write permission と読まない。

## Verification

この文書を更新した時は、固定 count ではなく次のコマンドを再実行します。

```bash
uv run python scripts/check_current_docs.py
git diff --check
uv run sis --help
```

必要に応じて CLI 個別 help も spot check します。

```bash
uv run sis strategy-idea-candidates-authoring-bridge --help
uv run sis strategy-idea-candidates-bitget-source-refresh --help
uv run sis crypto-perp-profit-readiness-plan --help
uv run sis crypto-perp-profit-readiness-run-local --help
```
