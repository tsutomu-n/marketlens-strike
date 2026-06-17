<!--
作成日: 2026-06-16_20:09 JST
更新日: 2026-06-17_19:36 JST
-->

# Strategy Review Dogfood Review 2026-06-16

## 結果

`strategy-review-build` を実 artifact と失敗系 fixture に当て、`review.md` が人間レビューの判断資料として読めることを確認した。

今回の Dogfood で見つかった読みづらさは、renderer を最小 hardening して解消した。現行 `review.md` は Summary、Readiness Disclaimer、Source Artifact Status、Backtest Pack / Validation Summary、Strategy Definition、Lifecycle Summary、Safety Boundary、Missing / Invalid / Blocked Details、Source Hash Table、Next Human Review Checklist の順で読む。

copy-paste 用の現行 recipe は [OPERATOR_REVIEW_PACKET_RECIPE.md](OPERATOR_REVIEW_PACKET_RECIPE.md) を見る。

2026-06-17_19:36 JST 現在、Strategy Review の後続 artifact として `strategy-review-record` / `operator_review.yaml` も実装済み。これはこの dogfood 初回実施時点の未実装項目だったが、現行手順では packet build 後に人間判断を hash 付きで保存・再検証できる。

## 実行結果

| Pattern | Command summary | Exit | review_status | 判定 |
|---|---|---:|---|---|
| complete | current `data/research/backtest_pack/*` | 0 | `READY_FOR_HUMAN_REVIEW` | pass |
| missing lenient | missing pack / validation path | 0 | `INCOMPLETE_ARTIFACTS` | pass |
| missing strict | same missing paths + `--strict` | 2 | `INCOMPLETE_ARTIFACTS` | pass |
| boundary fixture | `.tmp/strategy_review_dogfood/` pack with `wallet_used=true` | 2 | `BLOCKED_BOUNDARY_VIOLATION` | pass |
| operator record | `dogfood-operator-current` + `strategy-review-record --decision REVIEWED_FOR_CONTEXT` | 0 | `READY_FOR_HUMAN_REVIEW` | pass |
| operator validate | `dogfood-operator-current` + `strategy-review-record --validate-existing` | 0 | `READY_FOR_HUMAN_REVIEW` | pass |

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
- `data/strategy_reviews/dogfood-operator-current/review.md`
- `data/strategy_reviews/dogfood-operator-current/review_manifest.json`
- `data/strategy_reviews/dogfood-operator-current/operator_review.yaml`

## Operator Review Dogfood

`dogfood-operator-current` は、現行の `strategy-review-build` と `strategy-review-record` を通す stable review id として使った。2026-06-17_19:36 JST の local artifact loop では、通常 paper observation を1回追加し、Strategy Backtest Pack の signal artifact を pack 専用 `source_artifacts` に分離した後、既存の `data/research/backtest_pack/strategy_backtest_pack.json`、`data/research/backtest_pack/strategy_backtest_pack_validation.json`、`data/research/strategy_lifecycle/strategy_lifecycle_review.json` を使って再 build / record / validate した。

確認した値:

- `review_status=READY_FOR_HUMAN_REVIEW`
- `source_safety.status=PASS`
- `pack_validation_pass_is_readiness_proof=false`
- `operator_review.yaml` の `decision=REVIEWED_FOR_CONTEXT`
- `operator_review.yaml` の `live_allowed=false`
- `operator_review.yaml` の `paper_execution_allowed=false`
- `Lifecycle Summary` は `decision=CONTINUE_PAPER_OBSERVATION` / `decision_reasons=PAPER_OBSERVATION_INSUFFICIENT`
- `strategy-review-record --validate-existing` は `status=pass`

`operator_review.yaml` 内には `review.md` と `review_manifest.json` の hash が保存される。この文書は tracked doc なので、runtime hash は固定して写さない。hash の一致確認は `strategy-review-record --validate-existing` で行う。

## 合格条件チェック

- complete は `READY_FOR_HUMAN_REVIEW`。
- missing lenient は exit 0 で `INCOMPLETE_ARTIFACTS`、markdown の `Missing / Invalid / Blocked Details` に上がる。
- missing strict は manifest / markdown を書いたうえで exit 2。
- boundary fixture は `BLOCKED_BOUNDARY_VIOLATION`。
- `pack_validation_pass_is_readiness_proof=false` は manifest と markdown の両方で読める。
- complete markdown は先頭から、戦略定義、入力 artifact、pack 要約、lifecycle decision / next action、境界、未解決点の順で読める。
- operator review dogfood は `REVIEWED_FOR_CONTEXT` として保存でき、`--validate-existing` で現在の packet と一致する。
- `live_allowed=false` / `paper_execution_allowed=false` は operator review でも固定され、lifecycle decision は paper / live 許可として読まない。

## 3分レビューで次に見る点

complete の場合、人間はまず `Summary` で `review_status` と `source_safety.status` を確認する。次に `Source Artifact Status` で必須 artifact と optional artifact の status / hash を確認し、`Backtest Pack / Validation Summary` で pack と validation が present / PASS であることを確認する。その後 `Strategy Definition` で `strategy_id`、symbol binding、entry / hold / exit / sizing / backtest 設定を確認し、`Lifecycle Summary` の `decision=CONTINUE_PAPER_OBSERVATION` と `next_actions` を次の状態整理として読む。最後に `Source Hash Table` で path、bytes、hash、schema version を確認する。

missing / boundary の場合は、`Missing / Invalid / Blocked Details` の該当行を先に直す。`pack_validation PASS` は readiness proof ではないため、戦略評価や live 可否として読まない。paper observation 候補にする場合も、この review から直接 `paper-from-intents` を呼ばない。

## 補正した実装点

- `authoring_spec` は JSON reader ではなく既存 `load_authoring_spec()` で YAML / Pydantic validation する。
- boundary true key に `venue_write_used`、`credentials_used`、`external_api_used` を追加する。
- `lifecycle_review` は `schema_version == strategy_lifecycle_review.v1` を要求し、`venue_write_used=true` も boundary violation として扱う。
- optional `authoring_spec` / `lifecycle_review` は `required=false` source artifact として扱い、missing optional は `review_status` を変えない。

## 残リスク

- `data/strategy_reviews/*` は runtime artifact であり、この文書には hash 値を固定しない。
- paper bridge、Strategy Case registry、UI は未実装。
- `operator_review.yaml` は後続実装済み。ただし paper / live 許可 artifact ではなく、`live_allowed=false` / `paper_execution_allowed=false` を固定する。
- この review は入力 artifact の信頼性確認であり、alpha、paper readiness、live readiness を証明しない。
