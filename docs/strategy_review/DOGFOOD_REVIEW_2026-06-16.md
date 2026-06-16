<!--
作成日: 2026-06-16_20:09 JST
更新日: 2026-06-16_20:25 JST
-->

# Strategy Review Dogfood Review 2026-06-16

## 結果

`strategy-review-build` を実 artifact と失敗系 fixture に当て、`review.md` が人間レビューの判断資料として読めることを確認した。

今回の Dogfood で見つかった読みづらさは、PR-REVIEW-01 実装前に renderer を最小 hardening して解消した。具体的には、`review.md` の先頭側に戦略定義、入力 artifact、Backtest Pack Summary、Lifecycle Summary を固定順で出し、`Missing / Invalid / Blocked (Needs Attention)` を明示した。

## 実行結果

| Pattern | Command summary | Exit | review_status | 判定 |
|---|---|---:|---|---|
| complete | current `data/research/backtest_pack/*` | 0 | `READY_FOR_HUMAN_REVIEW` | pass |
| missing lenient | missing pack / validation path | 0 | `INCOMPLETE_ARTIFACTS` | pass |
| missing strict | same missing paths + `--strict` | 2 | `INCOMPLETE_ARTIFACTS` | pass |
| boundary fixture | `.tmp/strategy_review_dogfood/` pack with `wallet_used=true` | 2 | `BLOCKED_BOUNDARY_VIOLATION` | pass |

生成先は `data/strategy_reviews`。`data/` は ignored runtime artifact なので commit 対象にしない。

## 確認した artifact

- `data/strategy_reviews/dogfood-complete-20260616/review.md`
- `data/strategy_reviews/dogfood-complete-20260616/review_manifest.json`
- `data/strategy_reviews/dogfood-missing-lenient-20260616/review.md`
- `data/strategy_reviews/dogfood-missing-lenient-20260616/review_manifest.json`
- `data/strategy_reviews/dogfood-missing-strict-20260616/review.md`
- `data/strategy_reviews/dogfood-missing-strict-20260616/review_manifest.json`
- `data/strategy_reviews/dogfood-boundary-20260616/review.md`
- `data/strategy_reviews/dogfood-boundary-20260616/review_manifest.json`

## 合格条件チェック

- complete は `READY_FOR_HUMAN_REVIEW`。
- missing lenient は exit 0 で `INCOMPLETE_ARTIFACTS`、markdown の `Missing / Invalid / Blocked (Needs Attention)` に上がる。
- missing strict は manifest / markdown を書いたうえで exit 2。
- boundary fixture は `BLOCKED_BOUNDARY_VIOLATION`。
- `pack_validation_pass_is_readiness_proof=false` は manifest と markdown の両方で読める。
- complete markdown は先頭から、戦略定義、入力 artifact、pack 要約、lifecycle decision / next action、境界、未解決点の順で読める。

## 3分レビューで次に見る点

complete の場合、人間はまず `戦略定義` で `strategy_id`、symbol binding、entry / hold / exit / sizing / backtest 設定を確認する。次に `入力artifact` で必須 artifact と optional artifact の status / hash を確認し、`Backtest Pack Summary` で pack と validation が present / PASS であることを確認する。最後に `Lifecycle Summary` の `decision=CONTINUE_PAPER_OBSERVATION` と `next_actions` を見て、次に paper observation を継続する判断資料として読む。

missing / boundary の場合は、`Missing / Invalid / Blocked (Needs Attention)` の該当行を先に直す。`pack_validation PASS` は readiness proof ではないため、戦略評価や live 可否として読まない。

## 補正した実装点

- `authoring_spec` は JSON reader ではなく既存 `load_authoring_spec()` で YAML / Pydantic validation する。
- boundary true key に `venue_write_used`、`credentials_used`、`external_api_used` を追加する。
- `lifecycle_review` は `schema_version == strategy_lifecycle_review.v1` を要求し、`venue_write_used=true` も boundary violation として扱う。
- optional `authoring_spec` / `lifecycle_review` は `required=false` source artifact として扱い、missing optional は `review_status` を変えない。

## 残リスク

- `data/strategy_reviews/*` は runtime artifact であり、この文書には hash 値を固定しない。
- PR-REVIEW-02 以降の `strategy_authoring_backtest_result`、`paper_intent_preview`、`paper_observation_session_manifest` は未実装。
- この review は入力 artifact の信頼性確認であり、alpha、paper readiness、live readiness を証明しない。
